// A stand-in for the game: the bridge core serving a few fake objects shaped like the
// real ones, with a "main thread" loop that pumps requests and moves the player.
using System;
using System.Collections.Generic;
using System.Threading;
using FF1Bridge.Core;

int port = args.Length > 0 ? int.Parse(args[0]) : 0;
var server = new BridgeServer(port, Console.WriteLine);
server.Start();
Console.WriteLine($"PORT {server.Port}");
Console.Out.Flush();
while (true)
{
    server.Pump(8);
    Last.Management.UserDataManager.Instance().Tick();
    Thread.Sleep(5);
}

namespace Last.Management
{
    public enum MoveState { Walk, Dush }

    public class ConfigData { public int IsAutoDash { get; set; } = 1; }

    public class OwnedCharacterData
    {
        public string Name { get; set; } = "";
        public int Level { get; set; }
        public int Hp { get; set; }
        public int MaxHp { get; set; }
        public int Throws => throw new InvalidOperationException("broken getter");
    }

    public struct Vector3 { public float x, y, z; public Vector3 normalized => this; }

    public class UserDataManager
    {
        static readonly UserDataManager instance = new();
        public static UserDataManager Instance() => instance;

        public int OwendGil { get; set; } = 500;
        public ConfigData Config { get; } = new();
        public MoveState State { get; set; } = MoveState.Walk;
        public Vector3 Position;
        public List<OwnedCharacterData> Party { get; } = new()
        {
            new() { Name = "Warrior", Level = 3, Hp = 50, MaxHp = 60 },
            new() { Name = "Mage", Level = 2, Hp = 20, MaxHp = 25 },
        };
        public Dictionary<int, string> Flags { get; } = new() { [1] = "bridge" };
        public int Steps { get; private set; }
        public OwnedCharacterData GetCharacter(int i) => Party[i];
        public void Tick() { Steps++; Position.x = Steps % 10; }
    }
}
