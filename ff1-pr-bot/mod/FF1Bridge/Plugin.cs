using System;
using BepInEx;
using BepInEx.Unity.IL2CPP;
using FF1Bridge.Core;
using Il2CppInterop.Runtime.Injection;
using UnityEngine;

namespace FF1Bridge;

[BepInPlugin("ff1bot.bridge", "FF1 Bridge", BridgeServer.Version)]
public class Plugin : BasePlugin
{
    internal static BridgeServer? Server;

    public override void Load()
    {
        var port = Config.Bind("Bridge", "Port", 52323, "Port on 127.0.0.1 that the bot connects to.").Value;
        Server = new BridgeServer(port, msg => Log.LogInfo(msg));

        // Keep the game (and this bridge) running while another window has focus.
        Application.runInBackground = true;

        ClassInjector.RegisterTypeInIl2Cpp<BridgeComponent>();
        var go = new GameObject("FF1Bridge") { hideFlags = HideFlags.HideAndDontSave };
        GameObject.DontDestroyOnLoad(go);
        go.AddComponent<BridgeComponent>();

        Server.Start();
    }
}

/// <summary>Runs the bot's requests on Unity's main thread, a few ms each frame.</summary>
public sealed class BridgeComponent : MonoBehaviour
{
    public BridgeComponent(IntPtr ptr) : base(ptr) { }

    public void Update()
    {
        try { Plugin.Server?.Pump(8); }
        catch (Exception e) { Debug.LogError($"FF1 Bridge: {e}"); }
    }
}
