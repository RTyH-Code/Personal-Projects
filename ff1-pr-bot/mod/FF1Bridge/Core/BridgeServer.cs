using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;

namespace FF1Bridge.Core;

/// <summary>
/// A tiny local server: one JSON request per line in, one JSON response per line out.
/// Requests are read on background threads but run on the game's main thread
/// (from Pump, called every frame), because Unity objects must only be touched there.
/// </summary>
public sealed class BridgeServer
{
    public const string Version = "0.1.0";

    sealed class Job
    {
        public readonly string Request;
        public string? Response;
        public readonly ManualResetEventSlim Done = new(false);
        public Job(string request) { Request = request; }
    }

    readonly int _port;
    readonly Action<string> _log;
    readonly ConcurrentQueue<Job> _jobs = new();
    TcpListener? _listener;

    public BridgeServer(int port, Action<string> log)
    {
        _port = port;
        _log = log;
    }

    public int Port => ((IPEndPoint?)_listener?.LocalEndpoint)?.Port ?? _port;

    public void Start()
    {
        _listener = new TcpListener(IPAddress.Loopback, _port);
        _listener.Start();
        new Thread(AcceptLoop) { IsBackground = true, Name = "FF1Bridge accept" }.Start();
        _log($"FF1 Bridge {Version} listening on 127.0.0.1:{Port}");
    }

    void AcceptLoop()
    {
        while (true)
        {
            TcpClient client;
            try { client = _listener!.AcceptTcpClient(); }
            catch (Exception e) { _log($"FF1 Bridge stopped accepting: {e.Message}"); return; }
            new Thread(() => Serve(client)) { IsBackground = true, Name = "FF1Bridge client" }.Start();
        }
    }

    void Serve(TcpClient client)
    {
        try
        {
            using (client)
            using (var stream = client.GetStream())
            using (var reader = new StreamReader(stream, new UTF8Encoding(false)))
            using (var writer = new StreamWriter(stream, new UTF8Encoding(false)) { NewLine = "\n" })
            {
                string? line;
                while ((line = reader.ReadLine()) != null)
                {
                    if (line.Trim().Length == 0) continue;
                    var job = new Job(line);
                    _jobs.Enqueue(job);
                    var response = job.Done.Wait(TimeSpan.FromSeconds(10))
                        ? job.Response!
                        : Error("The game didn't answer within 10 s (is it frozen, or paused while unfocused?).");
                    writer.WriteLine(response);
                    writer.Flush();
                }
            }
        }
        catch (IOException) { }
        catch (Exception e) { _log($"FF1 Bridge client error: {e}"); }
    }

    /// <summary>Runs queued requests on the calling (main) thread for up to maxMs.</summary>
    public void Pump(int maxMs)
    {
        var sw = Stopwatch.StartNew();
        while (sw.ElapsedMilliseconds < maxMs && _jobs.TryDequeue(out var job))
        {
            job.Response = Handle(job.Request);
            job.Done.Set();
        }
    }

    // ---------- commands ----------

    public static string Handle(string request)
    {
        try
        {
            using var doc = JsonDocument.Parse(request);
            var root = doc.RootElement;
            var cmd = Str(root, "cmd") ?? throw new PathException("Missing \"cmd\".");
            var buffer = new MemoryStream();
            using (var w = new Utf8JsonWriter(buffer))
            {
                w.WriteStartObject();
                w.WriteBoolean("ok", true);
                w.WritePropertyName("result");
                Run(cmd, root, w);
                w.WriteEndObject();
            }
            return Encoding.UTF8.GetString(buffer.ToArray());
        }
        catch (Exception e)
        {
            return Error($"{(e is PathException ? "" : e.GetType().Name + ": ")}{e.Message}");
        }
    }

    static void Run(string cmd, JsonElement root, Utf8JsonWriter w)
    {
        int maxItems = Int(root, "max_items") ?? 100;
        var json = new JsonOut(w, maxItems);
        switch (cmd)
        {
            case "ping":
                w.WriteStartObject();
                w.WriteString("version", Version);
                w.WriteEndObject();
                break;

            case "find_types":
                JsonSerializer.Serialize(w, Reflector.SearchTypes(Str(root, "pattern") ?? "", Int(root, "limit") ?? 100));
                break;

            case "get":
            {
                var r = Reflector.Eval(Required(root, "path"));
                json.Write(r.StaticType != null ? r.StaticType.FullName : r.Value, Int(root, "depth") ?? 1);
                break;
            }

            case "state":
            {
                int defaultDepth = Int(root, "depth") ?? 0;
                w.WriteStartObject();
                if (root.TryGetProperty("paths", out var paths))
                {
                    foreach (var entry in paths.EnumerateObject())
                    {
                        string path = entry.Value.ValueKind == JsonValueKind.String
                            ? entry.Value.GetString()!
                            : Required(entry.Value, "path");
                        int depth = entry.Value.ValueKind == JsonValueKind.Object ? Int(entry.Value, "depth") ?? defaultDepth : defaultDepth;
                        w.WritePropertyName(entry.Name);
                        WriteOrError(w, json, path, depth);
                    }
                }
                w.WriteEndObject();
                break;
            }

            case "members":
                WriteMembers(w, Reflector.Eval(Required(root, "path")));
                break;

            case "set":
            {
                if (!root.TryGetProperty("value", out var v)) throw new PathException("Missing \"value\".");
                Reflector.Set(Required(root, "path"), JsonToObject(v));
                w.WriteBooleanValue(true);
                break;
            }

            default:
                throw new PathException($"Unknown command '{cmd}'.");
        }
    }

    static void WriteOrError(Utf8JsonWriter w, JsonOut json, string path, int depth)
    {
        // Serialize into a scratch writer first so a failure can't leave half an object behind.
        var scratch = new MemoryStream();
        try
        {
            using (var sw = new Utf8JsonWriter(scratch))
            {
                var r = Reflector.Eval(path);
                new JsonOut(sw, 100).Write(r.StaticType != null ? r.StaticType.FullName : r.Value, depth);
            }
            w.WriteRawValue(scratch.ToArray());
        }
        catch (Exception e)
        {
            w.WriteStartObject();
            w.WriteString("$error", e.Message);
            w.WriteEndObject();
        }
    }

    static void WriteMembers(Utf8JsonWriter w, PathResult r)
    {
        bool isStatic = r.StaticType != null;
        var type = r.StaticType ?? r.Value?.GetType() ?? throw new PathException("That path is null.");
        w.WriteStartObject();
        w.WriteString("type", type.FullName);
        w.WriteString("base", type.BaseType?.FullName);
        w.WriteBoolean("static", isStatic);
        w.WriteStartArray("properties");
        foreach (var p in Reflector.ReadableProperties(type, isStatic).OrderBy(p => p.Name))
            w.WriteStringValue($"{p.Name}: {TypeName(p.PropertyType)}");
        foreach (var f in Reflector.ReadableFields(type, isStatic).OrderBy(f => f.Name))
            w.WriteStringValue($"{f.Name}: {TypeName(f.FieldType)}");
        w.WriteEndArray();
        w.WriteStartArray("methods");
        foreach (var m in Reflector.Methods(type, isStatic).OrderBy(m => m.Name))
            w.WriteStringValue($"{m.Name}({string.Join(", ", m.GetParameters().Select(p => $"{TypeName(p.ParameterType)} {p.Name}"))}) -> {TypeName(m.ReturnType)}");
        w.WriteEndArray();
        w.WriteEndObject();
    }

    static string TypeName(Type t)
    {
        if (!t.IsGenericType) return t.FullName ?? t.Name;
        var name = t.Name.Split('`')[0];
        return $"{t.Namespace}.{name}<{string.Join(", ", t.GetGenericArguments().Select(TypeName))}>";
    }

    static object? JsonToObject(JsonElement v) => v.ValueKind switch
    {
        JsonValueKind.String => v.GetString(),
        JsonValueKind.True => true,
        JsonValueKind.False => false,
        JsonValueKind.Null => null,
        JsonValueKind.Number => v.TryGetInt64(out var l) ? l : v.GetDouble(),
        _ => throw new PathException("value must be a string, number, boolean or null."),
    };

    static string? Str(JsonElement e, string name) =>
        e.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;

    static int? Int(JsonElement e, string name) =>
        e.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetInt32() : null;

    static string Required(JsonElement e, string name) =>
        Str(e, name) ?? throw new PathException($"Missing \"{name}\".");

    static string Error(string message)
    {
        var buffer = new MemoryStream();
        using (var w = new Utf8JsonWriter(buffer))
        {
            w.WriteStartObject();
            w.WriteBoolean("ok", false);
            w.WriteString("error", message);
            w.WriteEndObject();
        }
        return Encoding.UTF8.GetString(buffer.ToArray());
    }
}
