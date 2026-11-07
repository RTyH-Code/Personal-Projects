using System;
using System.Linq;
using System.Text.Json;

namespace FF1Bridge.Core;

/// <summary>Writes live game objects as JSON, down to a given depth.</summary>
public sealed class JsonOut
{
    readonly Utf8JsonWriter _w;
    readonly int _maxItems;

    public JsonOut(Utf8JsonWriter writer, int maxItems)
    {
        _w = writer;
        _maxItems = maxItems;
    }

    public void Write(object? v, int depth)
    {
        switch (v)
        {
            case null: _w.WriteNullValue(); return;
            case bool b: _w.WriteBooleanValue(b); return;
            case string s: _w.WriteStringValue(s); return;
            case char c: _w.WriteStringValue(c.ToString()); return;
            case Enum e: _w.WriteStringValue(e.ToString()); return;
            case Type t: _w.WriteStringValue(t.FullName); return;
            case IntPtr: _w.WriteStringValue("<pointer>"); return;
            case float f: WriteDouble(f); return;
            case double d: WriteDouble(d); return;
            case decimal m: _w.WriteNumberValue(m); return;
            case sbyte or byte or short or ushort or int or uint or long:
                _w.WriteNumberValue(Convert.ToInt64(v)); return;
            case ulong ul: _w.WriteNumberValue(ul); return;
        }

        var items = Reflector.Enumerate(v);
        if (items != null)
        {
            _w.WriteStartArray();
            int n = 0;
            var it = items.GetEnumerator();
            while (true)
            {
                object? item;
                try
                {
                    if (!it.MoveNext()) break;
                    item = it.Current;
                }
                catch (Exception e)
                {
                    _w.WriteStringValue($"!error: {e.GetType().Name}: {e.Message}");
                    break;
                }
                if (n++ >= _maxItems) { _w.WriteStringValue($"...more items (limit {_maxItems})"); break; }
                Write(item, depth);
            }
            _w.WriteEndArray();
            return;
        }

        var type = v.GetType();
        if (depth <= 0)
        {
            _w.WriteStringValue($"<{type.Name}>");
            return;
        }

        _w.WriteStartObject();
        _w.WriteString("$type", type.FullName);
        var fields = Reflector.ReadableFields(type, false).ToList();
        foreach (var f in fields)
        {
            _w.WritePropertyName(f.Name);
            SafeWrite(() => f.GetValue(v), depth - 1);
        }
        // Structs (vectors, colors...) are described by their fields; their properties are derived values.
        if (!(type.IsValueType && fields.Count > 0))
        {
            foreach (var p in Reflector.ReadableProperties(type, false))
            {
                if (fields.Any(f => f.Name == p.Name)) continue;
                _w.WritePropertyName(p.Name);
                SafeWrite(() => Reflector.Unwrap(() => p.GetValue(v)), depth - 1);
            }
        }
        _w.WriteEndObject();
    }

    void SafeWrite(Func<object?> get, int depth)
    {
        object? value;
        try { value = get(); }
        catch (Exception e)
        {
            _w.WriteStringValue($"!error: {e.GetType().Name}: {e.Message}");
            return;
        }
        Write(value, depth);
    }

    void WriteDouble(double d)
    {
        if (double.IsNaN(d) || double.IsInfinity(d)) _w.WriteNullValue();
        else _w.WriteNumberValue(Math.Round(d, 5));
    }
}
