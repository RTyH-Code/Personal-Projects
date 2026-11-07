using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Text;

namespace FF1Bridge.Core;

public sealed class PathException : Exception
{
    public PathException(string message) : base(message) { }
}

/// <summary>What a path evaluated to: a value, or (for a bare type name) the type itself.</summary>
public readonly record struct PathResult(object? Value, Type? StaticType);

/// <summary>
/// Evaluates dotted paths against the game's live objects with plain .NET reflection.
/// Il2CppInterop's generated proxy classes expose the game's fields as properties and its
/// methods as methods, so the same code works on the real game and on test objects.
///
/// Path syntax:  Full.Type.Name.Member.Method(1, "x").List[0].as(Other.Type).Field
/// </summary>
public static class Reflector
{
    const BindingFlags Instance = BindingFlags.Public | BindingFlags.Instance;
    const BindingFlags Static = BindingFlags.Public | BindingFlags.Static | BindingFlags.FlattenHierarchy;

    static readonly Dictionary<string, Type?> TypeCache = new();
    static readonly HashSet<string> HiddenMembers = new()
    {
        "Pointer", "ObjectClass", "WasCollected", "isWrapped", "pooledPtr",
    };

    // ---------- types ----------

    public static Type? FindType(string fullName)
    {
        lock (TypeCache)
        {
            if (TypeCache.TryGetValue(fullName, out var cached)) return cached;
            Type? found = null;
            foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
            {
                try { found = asm.GetType(fullName, false); } catch { }
                if (found != null) break;
            }
            TypeCache[fullName] = found;
            return found;
        }
    }

    public static IEnumerable<Type> AllTypes()
    {
        foreach (var asm in AppDomain.CurrentDomain.GetAssemblies())
        {
            Type?[] types;
            try { types = asm.GetTypes(); }
            catch (ReflectionTypeLoadException e) { types = e.Types; }
            catch { continue; }
            foreach (var t in types)
                if (t != null) yield return t;
        }
    }

    public static List<string> SearchTypes(string pattern, int limit)
    {
        return AllTypes()
            .Where(t => t.FullName != null && t.FullName.IndexOf(pattern, StringComparison.OrdinalIgnoreCase) >= 0)
            .Select(t => t.FullName!)
            .Where(n => !n.Contains("<"))
            .Distinct()
            .OrderBy(n => n.Length).ThenBy(n => n)
            .Take(limit)
            .ToList();
    }

    // ---------- path parsing ----------

    sealed record Segment(string Name, List<string>? Args, List<string> Indexes)
    {
        public bool IsPlain => Args == null && Indexes.Count == 0;
    }

    static List<string> SplitTopLevel(string text, char separator)
    {
        var parts = new List<string>();
        var sb = new StringBuilder();
        int depth = 0;
        bool quoted = false;
        foreach (var c in text)
        {
            if (c == '"') quoted = !quoted;
            if (!quoted)
            {
                if (c == '(' || c == '[') depth++;
                if (c == ')' || c == ']') depth--;
                if (c == separator && depth == 0)
                {
                    parts.Add(sb.ToString().Trim());
                    sb.Clear();
                    continue;
                }
            }
            sb.Append(c);
        }
        if (depth != 0 || quoted) throw new PathException($"Unbalanced brackets or quotes in '{text}'.");
        parts.Add(sb.ToString().Trim());
        return parts;
    }

    static Segment ParseSegment(string token)
    {
        var indexes = new List<string>();
        var rest = token;
        while (rest.EndsWith("]"))
        {
            int open = rest.LastIndexOf('[');
            if (open < 0) throw new PathException($"Bad index in '{token}'.");
            indexes.Insert(0, rest.Substring(open + 1, rest.Length - open - 2).Trim());
            rest = rest.Substring(0, open);
        }
        List<string>? args = null;
        int paren = rest.IndexOf('(');
        if (paren >= 0)
        {
            if (!rest.EndsWith(")")) throw new PathException($"Bad call in '{token}'.");
            var inner = rest.Substring(paren + 1, rest.Length - paren - 2).Trim();
            args = inner.Length == 0 ? new List<string>() : SplitTopLevel(inner, ',');
            rest = rest.Substring(0, paren);
        }
        if (rest.Length == 0) throw new PathException($"Empty name in '{token}'.");
        return new Segment(rest.Trim(), args, indexes);
    }

    // ---------- evaluation ----------

    public static PathResult Eval(string path)
    {
        var tokens = SplitTopLevel(path.Trim(), '.');
        var segments = tokens.Select(ParseSegment).ToList();

        // The longest run of plain names at the start that names a type is the root.
        Type? root = null;
        int start = 0;
        for (int k = segments.Count; k >= 1; k--)
        {
            if (!segments.Take(k).All(s => s.IsPlain)) continue;
            root = FindType(string.Join(".", segments.Take(k).Select(s => s.Name)));
            if (root != null) { start = k; break; }
        }
        if (root == null)
            throw new PathException($"No type found at the start of '{path}'. Use find_types to look one up.");

        object? value = null;
        Type? staticType = root;
        for (int i = start; i < segments.Count; i++)
        {
            var seg = segments[i];
            var where = string.Join(".", tokens.Take(i));
            if (staticType == null && value == null)
                throw new PathException($"'{where}' is null, so '{seg.Name}' can't be read.");
            value = Access(value, staticType, seg);
            staticType = null;
            foreach (var idx in seg.Indexes)
            {
                if (value == null) throw new PathException($"'{where}.{seg.Name}' is null, so it can't be indexed.");
                value = Index(value, idx);
            }
        }
        return new PathResult(value, staticType);
    }

    static object? Access(object? target, Type? staticType, Segment seg)
    {
        var type = staticType ?? target!.GetType();
        var flags = staticType != null ? Static : Instance;

        if (seg.Args != null)
        {
            if (seg.Name == "as" && staticType == null)
            {
                if (seg.Args.Count != 1) throw new PathException("as() takes one type name.");
                var to = FindType(seg.Args[0]) ?? throw new PathException($"Unknown type '{seg.Args[0]}'.");
                return Cast(target!, to);
            }
            return Call(target, type, flags, seg.Name, seg.Args);
        }

        var prop = FindProperty(type, flags, seg.Name);
        if (prop != null) return Unwrap(() => prop.GetValue(target));
        var field = FindField(type, flags, seg.Name);
        if (field != null) return Unwrap(() => field.GetValue(target));

        // Allow calling a no-argument method without the parentheses.
        if (type.GetMethods(flags).Any(m => m.Name == seg.Name && m.GetParameters().Length == 0 && !m.IsGenericMethodDefinition))
            return Call(target, type, flags, seg.Name, new List<string>());

        throw new PathException($"No {(staticType != null ? "static " : "")}member '{seg.Name}' on {type.FullName}. Use members to list them.");
    }

    static PropertyInfo? FindProperty(Type type, BindingFlags flags, string name)
    {
        var props = type.GetProperties(flags).Where(p => p.GetIndexParameters().Length == 0 && p.CanRead).ToList();
        return props.FirstOrDefault(p => p.Name == name)
               ?? props.FirstOrDefault(p => string.Equals(p.Name, name, StringComparison.OrdinalIgnoreCase));
    }

    static FieldInfo? FindField(Type type, BindingFlags flags, string name)
    {
        var fields = type.GetFields(flags);
        return fields.FirstOrDefault(f => f.Name == name)
               ?? fields.FirstOrDefault(f => string.Equals(f.Name, name, StringComparison.OrdinalIgnoreCase));
    }

    static object? Call(object? target, Type type, BindingFlags flags, string name, List<string> rawArgs)
    {
        var candidates = type.GetMethods(flags)
            .Where(m => m.Name == name && !m.IsGenericMethodDefinition && m.GetParameters().Length == rawArgs.Count)
            .ToList();
        if (candidates.Count == 0)
            throw new PathException($"No method {name} with {rawArgs.Count} argument(s) on {type.FullName}.");
        Exception? last = null;
        foreach (var m in candidates)
        {
            object?[] args;
            try { args = m.GetParameters().Select((p, i) => ConvertArg(rawArgs[i], p.ParameterType)).ToArray(); }
            catch (Exception e) { last = e; continue; }
            return Unwrap(() => m.Invoke(target, args));
        }
        throw new PathException($"Couldn't convert the arguments for {name}: {last?.Message}");
    }

    static object? Cast(object value, Type to)
    {
        var tryCast = value.GetType().GetMethods(Instance)
            .FirstOrDefault(m => m.Name == "TryCast" && m.IsGenericMethodDefinition && m.GetParameters().Length == 0);
        if (tryCast != null) return Unwrap(() => tryCast.MakeGenericMethod(to).Invoke(value, null));
        return to.IsInstanceOfType(value) ? value : null;
    }

    static object? Index(object value, string rawIndex)
    {
        if (!int.TryParse(rawIndex, NumberStyles.Integer, CultureInfo.InvariantCulture, out int i))
        {
            // Dictionary-style lookup by key.
            var getter = value.GetType().GetMethods(Instance).FirstOrDefault(m => m.Name == "get_Item" && m.GetParameters().Length == 1);
            if (getter == null) throw new PathException($"{value.GetType().FullName} can't be indexed by '{rawIndex}'.");
            return Unwrap(() => getter.Invoke(value, new[] { ConvertArg(rawIndex, getter.GetParameters()[0].ParameterType) }));
        }
        if (value is IList list) return list[i];
        var intGetter = value.GetType().GetMethods(Instance)
            .FirstOrDefault(m => m.Name == "get_Item" && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(int));
        if (intGetter != null) return Unwrap(() => intGetter.Invoke(value, new object[] { i }));
        int n = 0;
        foreach (var item in Enumerate(value) ?? throw new PathException($"{value.GetType().FullName} isn't a list."))
            if (n++ == i) return item;
        throw new PathException($"Index {i} is out of range.");
    }

    // ---------- helpers shared with the serializer ----------

    public static object? Unwrap(Func<object?> f)
    {
        try { return f(); }
        catch (TargetInvocationException e) when (e.InnerException != null) { throw e.InnerException; }
    }

    public static object? ConvertArg(string raw, Type type)
    {
        raw = raw.Trim();
        if (raw.Length >= 2 && raw.StartsWith("\"") && raw.EndsWith("\"")) raw = raw.Substring(1, raw.Length - 2);
        if (raw == "null" && !type.IsValueType) return null;
        return ConvertValue(raw, type);
    }

    public static object? ConvertValue(object? value, Type type)
    {
        if (value == null) return type.IsValueType ? Activator.CreateInstance(type) : null;
        var target = Nullable.GetUnderlyingType(type) ?? type;
        if (target.IsInstanceOfType(value)) return value;
        if (target.IsEnum)
        {
            var s = Convert.ToString(value, CultureInfo.InvariantCulture)!;
            return long.TryParse(s, NumberStyles.Integer, CultureInfo.InvariantCulture, out var n)
                ? Enum.ToObject(target, n)
                : Enum.Parse(target, s, true);
        }
        if (target == typeof(string)) return Convert.ToString(value, CultureInfo.InvariantCulture);
        return Convert.ChangeType(value, target, CultureInfo.InvariantCulture);
    }

    /// <summary>Items of anything list-like: .NET collections, Il2Cpp lists, dictionaries and sets.</summary>
    public static IEnumerable<object?>? Enumerate(object value)
    {
        if (value is string) return null;
        if (value is IEnumerable e) return e.Cast<object?>();
        var type = value.GetType();
        var count = type.GetProperty("Count", Instance);
        var getItem = type.GetMethods(Instance)
            .FirstOrDefault(m => m.Name == "get_Item" && m.GetParameters().Length == 1 && m.GetParameters()[0].ParameterType == typeof(int));
        if (count != null && getItem != null) return IndexItems(value, count, getItem);
        var getEnum = type.GetMethod("GetEnumerator", Instance, null, Type.EmptyTypes, null);
        if (getEnum != null) return EnumeratorItems(value, getEnum);
        return null;
    }

    static IEnumerable<object?> IndexItems(object value, PropertyInfo count, MethodInfo getItem)
    {
        int n = Convert.ToInt32(count.GetValue(value));
        for (int i = 0; i < n; i++) yield return Unwrap(() => getItem.Invoke(value, new object[] { i }));
    }

    static IEnumerable<object?> EnumeratorItems(object value, MethodInfo getEnum)
    {
        var enumerator = getEnum.Invoke(value, null);
        if (enumerator == null) yield break;
        var et = enumerator.GetType();
        var moveNext = et.GetMethod("MoveNext", Instance, null, Type.EmptyTypes, null);
        var current = et.GetProperty("Current", Instance);
        if (moveNext == null || current == null) yield break;
        while ((bool)moveNext.Invoke(enumerator, null)!) yield return current.GetValue(enumerator);
    }

    public static bool IsHidden(MemberInfo m)
    {
        if (HiddenMembers.Contains(m.Name)) return true;
        var ns = m.DeclaringType?.Namespace ?? "";
        return m.DeclaringType == typeof(object) || m.DeclaringType == typeof(ValueType)
            || ns.StartsWith("Il2CppInterop", StringComparison.Ordinal);
    }

    public static IEnumerable<PropertyInfo> ReadableProperties(Type type, bool isStatic) =>
        type.GetProperties(isStatic ? Static : Instance)
            .Where(p => p.CanRead && p.GetIndexParameters().Length == 0 && !IsHidden(p)
                        && !typeof(Delegate).IsAssignableFrom(p.PropertyType));

    public static IEnumerable<FieldInfo> ReadableFields(Type type, bool isStatic) =>
        type.GetFields(isStatic ? Static : Instance)
            .Where(f => !IsHidden(f) && !typeof(Delegate).IsAssignableFrom(f.FieldType));

    public static IEnumerable<MethodInfo> Methods(Type type, bool isStatic) =>
        type.GetMethods(isStatic ? Static : Instance)
            .Where(m => !m.IsSpecialName && !IsHidden(m));

    /// <summary>Sets the field or property named by the last segment of a path.</summary>
    public static void Set(string path, object? value)
    {
        int cut = LastTopLevelDot(path);
        if (cut < 0) throw new PathException("set needs a path ending in a member name.");
        var parent = Eval(path.Substring(0, cut));
        var name = path.Substring(cut + 1).Trim();
        var type = parent.StaticType ?? parent.Value?.GetType() ?? throw new PathException("The parent object is null.");
        var flags = parent.StaticType != null ? Static : Instance;
        var prop = FindProperty(type, flags, name);
        if (prop != null && prop.CanWrite) { Unwrap(() => { prop.SetValue(parent.Value, ConvertValue(value, prop.PropertyType)); return null; }); return; }
        var field = FindField(type, flags, name);
        if (field != null) { Unwrap(() => { field.SetValue(parent.Value, ConvertValue(value, field.FieldType)); return null; }); return; }
        throw new PathException($"No writable member '{name}' on {type.FullName}.");
    }

    static int LastTopLevelDot(string path)
    {
        int depth = 0;
        bool quoted = false;
        int last = -1;
        for (int i = 0; i < path.Length; i++)
        {
            var c = path[i];
            if (c == '"') quoted = !quoted;
            if (quoted) continue;
            if (c == '(' || c == '[') depth++;
            else if (c == ')' || c == ']') depth--;
            else if (c == '.' && depth == 0) last = i;
        }
        return last;
    }
}
