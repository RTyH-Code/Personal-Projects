# Engine changes for later moves batch 3 (run once after 'moves.py <showdown>/data 3').
# Paths are relative to the repo root.
import re, sys
R = ''
def sub(path, old, new, count=1):
    p = R + path; s = open(p).read()
    n = s.count(old)
    if n != count: sys.exit(f"{path}: expected {count} got {n}: {old[:80]!r}")
    open(p, 'w').write(s.replace(old, new))

# ---- effects
sub('include/constants/battle_move_effects.h', "#define EFFECT_HACK_SPDEF_DOWN2_HIT 216\n",
"#define EFFECT_HACK_SPDEF_DOWN2_HIT 216\n#define EFFECT_HACK_UTURN 217\n#define EFFECT_HACK_FIELD 218\n#define EFFECT_HACK_DRAG 219\n")
sub('data/battle_scripts_1.s', "\t.4byte BattleScript_EffectHackSpDefDown2Hit      @ EFFECT_HACK_SPDEF_DOWN2_HIT\n",
"\t.4byte BattleScript_EffectHackSpDefDown2Hit      @ EFFECT_HACK_SPDEF_DOWN2_HIT\n\t.4byte BattleScript_EffectHackUTurn              @ EFFECT_HACK_UTURN\n\t.4byte BattleScript_EffectHackField              @ EFFECT_HACK_FIELD\n\t.4byte BattleScript_EffectHackDrag               @ EFFECT_HACK_DRAG\n")
HIT = """	attackcanceler
	accuracycheck BattleScript_PrintMoveMissed, ACC_CURR_MOVE
	attackstring
	ppreduce
	critcalc
	damagecalc
	typecalc
	adjustnormaldamage
	attackanimation
	waitanimation
	effectivenesssound
	hitanimation BS_TARGET
	waitstate
	healthbarupdate BS_TARGET
	datahpupdate BS_TARGET
	critmessage
	waitmessage B_WAIT_TIME_LONG
	resultmessage
	waitmessage B_WAIT_TIME_LONG
	tryfaintmon BS_TARGET
"""
sub('data/battle_scripts_1.s', "BattleScript_EffectHackSpDefDown2Hit::\n", f"""BattleScript_EffectHackUTurn::
{HIT}	callnative Hack_BS_UTurnDecide
	moveendall
	callnative Hack_BS_UTurnCheck
	jumpifcantswitch SWITCH_IGNORE_ESCAPE_PREVENTION | BS_ATTACKER, BattleScript_HackUTurnEnd
	openpartyscreen BS_ATTACKER, BattleScript_HackUTurnEnd
	switchoutabilities BS_ATTACKER
	waitstate
	switchhandleorder BS_ATTACKER, 2
	returntoball BS_ATTACKER
	getswitchedmondata BS_ATTACKER
	switchindataupdate BS_ATTACKER
	hpthresholds BS_ATTACKER
	printstring STRINGID_SWITCHINMON
	switchinanim BS_ATTACKER, TRUE
	waitstate
	switchineffects BS_ATTACKER
BattleScript_HackUTurnEnd::
	end

BattleScript_EffectHackDrag::
{HIT}	jumpifmovehadnoeffect BattleScript_MoveEnd
	jumpifhasnohp BS_TARGET, BattleScript_MoveEnd
	jumpifstatus2 BS_TARGET, STATUS2_SUBSTITUTE, BattleScript_MoveEnd
	jumpifability BS_TARGET, ABILITY_SUCTION_CUPS, BattleScript_MoveEnd
	jumpifstatus3 BS_TARGET, STATUS3_ROOTED, BattleScript_MoveEnd
	forcerandomswitch BattleScript_MoveEnd
	goto BattleScript_MoveEnd

BattleScript_HackDragOut::
	switchoutabilities BS_TARGET
	returntoball BS_TARGET
	waitstate
	jumpifbattletype BATTLE_TYPE_TRAINER, BattleScript_HackDragOutTrainer
	setbyte gBattleOutcome, B_OUTCOME_PLAYER_TELEPORTED
	finishaction

BattleScript_HackDragOutTrainer::
	getswitchedmondata BS_TARGET
	switchindataupdate BS_TARGET
	switchinanim BS_TARGET, FALSE
	waitstate
	printstring STRINGID_PKMNWASDRAGGEDOUT
	waitmessage B_WAIT_TIME_LONG
	switchineffects BS_TARGET
	goto BattleScript_MoveEnd

BattleScript_EffectHackField::
	attackcanceler
	attackstring
	ppreduce
	callnative Hack_BS_FieldMove
	attackanimation
	waitanimation
	printfromtable gHackFieldStringIds
	waitmessage B_WAIT_TIME_LONG
	callnative Hack_BS_FieldAfter
	call BattleScript_HackSelfStatRet
	goto BattleScript_MoveEnd

BattleScript_HackToxicSpikes::
	statusanimation BS_EFFECT_BATTLER
	printfromtable gHackToxicSpikesStringIds
	waitmessage B_WAIT_TIME_LONG
	updatestatusicon BS_EFFECT_BATTLER
	waitstate
	return

BattleScript_EffectHackSpDefDown2Hit::
""")
sub('data/battle_scripts_1.s', "BattleScript_PrintHurtBySpikes::\n\tprintstring STRINGID_PKMNHURTBYSPIKES\n",
    "BattleScript_PrintHurtBySpikes::\n\tprintfromtable gHackHazardHurtStringIds\n")
sub('include/battle_scripts.h', "extern const u8 BattleScript_HackSelfStatRet[];\n",
"extern const u8 BattleScript_HackSelfStatRet[];\nextern const u8 BattleScript_HackUTurnEnd[];\nextern const u8 BattleScript_HackDragOut[];\nextern const u8 BattleScript_HackToxicSpikes[];\n")

# ---- strings
names = ["HACKTAILWIND", "HACKTRICKROOM", "HACKTRICKROOMEND", "HACKSTEALTHROCK", "HACKTOXICSPIKES",
         "HACKSTICKYWEB", "HACKDEFOG", "HACKHURTBYROCKS"]
texts = ["{B_ATK_NAME_WITH_PREFIX} whipped\\nup a tailwind!",
         "{B_ATK_NAME_WITH_PREFIX} twisted\\nthe dimensions!",
         "The twisted dimensions\\nreturned to normal!",
         "Pointed stones float in the air\\naround the opponent's side!",
         "Poison spikes were scattered all\\naround the opponent's side!",
         "A sticky web spreads out on\\nthe opponent's side!",
         "{B_ATK_NAME_WITH_PREFIX} blew away\\nhazards and barriers!",
         "Pointed stones dug into\\n{B_SCR_ACTIVE_NAME_WITH_PREFIX}!"]
ids = "".join(f"#define STRINGID_{n:<20} {403 + i}\n" for i, n in enumerate(names))
sub('include/constants/battle_string_ids.h', "#define STRINGID_HACKSELFSTAT        402\n\n#define BATTLESTRINGS_COUNT     403",
    f"#define STRINGID_HACKSELFSTAT        402\n{ids}\n#define BATTLESTRINGS_COUNT     {403 + len(names)}")
decl = "".join(f'static const u8 sText_{n.title()}[] = _("{t}");\n' for n, t in zip(names, texts))
sub('src/battle_message.c', 'static const u8 sText_HackSelfStat[]', decl + 'static const u8 sText_HackSelfStat[]')
tab = "".join(f"    [STRINGID_{n} - BATTLESTRINGS_TABLE_START] = sText_{n.title()},\n" for n in names)
sub('src/battle_message.c', "    [STRINGID_HACKSELFSTAT - BATTLESTRINGS_TABLE_START]                  = sText_HackSelfStat,\n",
    "    [STRINGID_HACKSELFSTAT - BATTLESTRINGS_TABLE_START]                  = sText_HackSelfStat,\n" + tab)
sub('src/battle_message.c', "const u16 gHackAbilityStatStringIds[] = {STRINGID_HACKABILITYRAISED, STRINGID_HACKABILITYLOWERED};\n",
"""const u16 gHackAbilityStatStringIds[] = {STRINGID_HACKABILITYRAISED, STRINGID_HACKABILITYLOWERED};
const u16 gHackFieldStringIds[] = {STRINGID_HACKTAILWIND, STRINGID_HACKTRICKROOM, STRINGID_HACKTRICKROOMEND, STRINGID_HACKSTEALTHROCK,
                                   STRINGID_HACKTOXICSPIKES, STRINGID_HACKSTICKYWEB, STRINGID_HACKDEFOG};
const u16 gHackHazardHurtStringIds[] = {STRINGID_PKMNHURTBYSPIKES, STRINGID_HACKHURTBYROCKS};
const u16 gHackToxicSpikesStringIds[] = {STRINGID_PKMNWASPOISONED, STRINGID_PKMNBADLYPOISONED};
""")

# ---- battle_util.h / battle_util.c: field state and helpers
sub('include/battle_util.h', "bool8 Hack_MoveEndAbilities(void);\n", """bool8 Hack_MoveEndAbilities(void);

// FireRed QoL+Hard: field effects from later moves (reset at the start of each battle)
struct HackField
{
    u8 tailwindUntil[2];
    u8 trickRoomUntil;
    u8 stealthRock[2];
    u8 toxicSpikes[2];
    u8 stickyWeb[2];
    u8 hazardDone[MAX_BATTLERS_COUNT];
};
extern struct HackField gHackField;
void Hack_ResetField(void);
bool8 Hack_TailwindActive(u8 side);
bool8 Hack_TrickRoomActive(void);
bool8 Hack_SideHasHazards(u8 side);
void Hack_ClearHazards(u8 side);
bool8 Hack_MoveStatChange(u8 battler, u8 stat, s8 amount);
""")
sub('src/battle_util.c', "static bool8 Hack_MoveStatChange(u8 battler, u8 stat, s8 amount)\n", "bool8 Hack_MoveStatChange(u8 battler, u8 stat, s8 amount)\n")
sub('src/battle_util.c', "    {MOVE_CHARGE_BEAM, STAT_SPATK, 1},\n};",
"    {MOVE_CHARGE_BEAM, STAT_SPATK, 1},\n    {MOVE_DRAGON_ASCENT, STAT_DEF, -1}, {MOVE_DRAGON_ASCENT, STAT_SPDEF, -1},\n    {MOVE_FELL_STINGER, STAT_ATK, 3},\n};")
sub('src/battle_util.c', "        sHackStatRolled = (gCurrentMove != MOVE_CHARGE_BEAM || Random() % 10 < 7);\n",
"        sHackStatRolled = (gCurrentMove != MOVE_CHARGE_BEAM || Random() % 10 < 7)\n                       && (gCurrentMove != MOVE_FELL_STINGER || gBattleMons[gBattlerTarget].hp == 0);\n")
# Sucker Punch helper also handles Poltergeist
sub('src/battle_util.c', """    if (gChosenActionByBattler[target] != B_ACTION_USE_MOVE || move == MOVE_NONE || gBattleMoves[move].power == 0
     || pos < gCurrentTurnActionNumber)""", """    if (gCurrentMove == MOVE_POLTERGEIST)
    {
        if (gBattleMons[target].item == ITEM_NONE)
            gBattlescriptCurrInstr = BattleScript_ButItFailedAtkStringPpReduce;
        else
            gBattlescriptCurrInstr += 5;
        return;
    }
    if (gChosenActionByBattler[target] != B_ACTION_USE_MOVE || move == MOVE_NONE || gBattleMoves[move].power == 0
     || pos < gCurrentTurnActionNumber)""")
sub('src/battle_util.c', "bool8 Hack_MoveEndAbilities(void)\n{", r"""EWRAM_DATA struct HackField gHackField = {0};
static EWRAM_DATA bool8 sHackUTurnSwitch = FALSE;

void Hack_ResetField(void)
{
    memset(&gHackField, 0, sizeof(gHackField));
}

bool8 Hack_TailwindActive(u8 side)
{
    return gHackField.tailwindUntil[side] > gBattleResults.battleTurnCounter;
}

bool8 Hack_TrickRoomActive(void)
{
    return gHackField.trickRoomUntil > gBattleResults.battleTurnCounter;
}

bool8 Hack_SideHasHazards(u8 side)
{
    return gHackField.stealthRock[side] || gHackField.toxicSpikes[side] || gHackField.stickyWeb[side];
}

void Hack_ClearHazards(u8 side)
{
    gHackField.stealthRock[side] = gHackField.toxicSpikes[side] = gHackField.stickyWeb[side] = 0;
    gSideStatuses[side] &= ~SIDE_STATUS_SPIKES;
    gSideTimers[side].spikesAmount = 0;
}

// Tailwind, Trick Room, Stealth Rock, Toxic Spikes, Sticky Web and Defog
void Hack_BS_FieldMove(void)
{
    u8 side = GetBattlerSide(gBattlerAttacker);
    u8 foe = side ^ BIT_SIDE;
    u8 turn = gBattleResults.battleTurnCounter;
    u8 msg = 0;
    bool8 ok = TRUE;

    switch (gCurrentMove)
    {
    case MOVE_TAILWIND:
        ok = !Hack_TailwindActive(side);
        gHackField.tailwindUntil[side] = turn + 4;
        msg = 0;
        break;
    case MOVE_TRICK_ROOM:
        if (Hack_TrickRoomActive())
        {
            gHackField.trickRoomUntil = 0;
            msg = 2;
        }
        else
        {
            gHackField.trickRoomUntil = turn + 5;
            msg = 1;
        }
        break;
    case MOVE_STEALTH_ROCK:
        ok = !gHackField.stealthRock[foe];
        gHackField.stealthRock[foe] = 1;
        msg = 3;
        break;
    case MOVE_TOXIC_SPIKES:
        ok = gHackField.toxicSpikes[foe] < 2;
        if (ok)
            gHackField.toxicSpikes[foe]++;
        msg = 4;
        break;
    case MOVE_STICKY_WEB:
        ok = !gHackField.stickyWeb[foe];
        gHackField.stickyWeb[foe] = 1;
        msg = 5;
        break;
    case MOVE_DEFOG:
        Hack_ClearHazards(0);
        Hack_ClearHazards(1);
        gSideStatuses[GetBattlerSide(gBattlerTarget)] &= ~(SIDE_STATUS_REFLECT | SIDE_STATUS_LIGHTSCREEN | SIDE_STATUS_SAFEGUARD | SIDE_STATUS_MIST);
        msg = 6;
        break;
    }
    if (!ok)
    {
        gBattlescriptCurrInstr = BattleScript_ButItFailed;
        return;
    }
    gBattleCommunication[MULTISTRING_CHOOSER] = msg;
    gBattlescriptCurrInstr += 5;
}

// Defog also lowers the target's evasion
void Hack_BS_FieldAfter(void)
{
    if (gCurrentMove == MOVE_DEFOG && gBattlerTarget != gBattlerAttacker && gBattleMons[gBattlerTarget].hp != 0
     && !(gBattleMons[gBattlerTarget].status2 & STATUS2_SUBSTITUTE)
     && Hack_MoveStatChange(gBattlerTarget, STAT_EVASION, -1))
        gBattlescriptCurrInstr += 5;
    else
        gBattlescriptCurrInstr = BattleScript_MoveEnd;
}

// U-turn, Volt Switch, Flip Turn: switch out after a hit that landed
void Hack_BS_UTurnDecide(void)
{
    sHackUTurnSwitch = !(gMoveResultFlags & MOVE_RESULT_NO_EFFECT) && gBattleMons[gBattlerAttacker].hp != 0
                    && (gBattleMons[gBattlerTarget].hp != 0 || (gBattleTypeFlags & BATTLE_TYPE_TRAINER));
    gBattlescriptCurrInstr += 5;
}

void Hack_BS_UTurnCheck(void)
{
    if (sHackUTurnSwitch && gBattleMons[gBattlerAttacker].hp != 0 && gBattleOutcome == 0)
        gBattlescriptCurrInstr += 5;
    else
        gBattlescriptCurrInstr = BattleScript_HackUTurnEnd;
}

bool8 Hack_MoveEndAbilities(void)
{""")

# ---- battle_main.c: reset, Tailwind, Trick Room
sub('src/battle_main.c', "    gBattleResults.battleTurnCounter = 0;\n", "    gBattleResults.battleTurnCounter = 0;\n    Hack_ResetField();\n")
sub('src/battle_main.c', """    if (ignoreChosenMoves)
    {
        moveBattler1 = MOVE_NONE;""", """    // FireRed QoL+Hard: Tailwind doubles speed; Trick Room reverses the speed order
    if (Hack_TailwindActive(GetBattlerSide(battler1)) && speedBattler1 != UINT_MAX)
        speedBattler1 *= 2;
    if (Hack_TailwindActive(GetBattlerSide(battler2)) && speedBattler2 != UINT_MAX)
        speedBattler2 *= 2;
    if (Hack_TrickRoomActive())
    {
        if (speedBattler1 != UINT_MAX && gBattleMons[battler1].ability != ABILITY_STALL)
            speedBattler1 = UINT_MAX - 1 - speedBattler1;
        if (speedBattler2 != UINT_MAX && gBattleMons[battler2].ability != ABILITY_STALL)
            speedBattler2 = UINT_MAX - 1 - speedBattler2;
    }
    if (ignoreChosenMoves)
    {
        moveBattler1 = MOVE_NONE;""")

# ---- battle_script_commands.c: hazards on switch-in, Rapid Spin, Feint, drag-out script
sub('src/battle_script_commands.c', "static void Cmd_switchineffects(void)\n{", r"""// FireRed QoL+Hard: Stealth Rock, Toxic Spikes and Sticky Web on switch-in
static bool8 Hack_SwitchInHazards(u8 battler)
{
    u8 side = GetBattlerSide(battler);
    bool8 grounded = !IS_BATTLER_OF_TYPE(battler, TYPE_FLYING) && gBattleMons[battler].ability != ABILITY_LEVITATE;
    u8 *done = &gHackField.hazardDone[battler];
    u32 i, dmg;

    if (gBattleMons[battler].hp == 0)
        return FALSE;
    if (gHackField.stealthRock[side] && !(*done & 1))
    {
        *done |= 1;
        if (gBattleMons[battler].ability != ABILITY_MAGIC_GUARD)
        {
            dmg = gBattleMons[battler].maxHP;
            for (i = 0; TYPE_EFFECT_ATK_TYPE(i) != TYPE_ENDTABLE; i += 3)
            {
                if (TYPE_EFFECT_ATK_TYPE(i) != TYPE_ROCK)
                    continue;
                if (TYPE_EFFECT_DEF_TYPE(i) == gBattleMons[battler].type1)
                    dmg = dmg * TYPE_EFFECT_MULTIPLIER(i) / 10;
                if (TYPE_EFFECT_DEF_TYPE(i) == gBattleMons[battler].type2 && gBattleMons[battler].type1 != gBattleMons[battler].type2)
                    dmg = dmg * TYPE_EFFECT_MULTIPLIER(i) / 10;
            }
            gBattleMoveDamage = dmg / 8;
            if (gBattleMoveDamage == 0)
                gBattleMoveDamage = 1;
            gBattleScripting.battler = battler;
            gBattleCommunication[MULTISTRING_CHOOSER] = 1;
            BattleScriptPushCursor();
            if (gBattlescriptCurrInstr[1] == BS_TARGET)
                gBattlescriptCurrInstr = BattleScript_SpikesOnTarget;
            else if (gBattlescriptCurrInstr[1] == BS_ATTACKER)
                gBattlescriptCurrInstr = BattleScript_SpikesOnAttacker;
            else
                gBattlescriptCurrInstr = BattleScript_SpikesOnFaintedBattler;
            return TRUE;
        }
    }
    if (gHackField.toxicSpikes[side] && !(*done & 2) && grounded)
    {
        *done |= 2;
        if (IS_BATTLER_OF_TYPE(battler, TYPE_POISON))
        {
            gHackField.toxicSpikes[side] = 0; // a grounded Poison type absorbs them
        }
        else if (!IS_BATTLER_OF_TYPE(battler, TYPE_STEEL) && gBattleMons[battler].status1 == 0
              && gBattleMons[battler].ability != ABILITY_IMMUNITY && !(gSideStatuses[side] & SIDE_STATUS_SAFEGUARD))
        {
            gBattleMons[battler].status1 = gHackField.toxicSpikes[side] >= 2 ? STATUS1_TOXIC_POISON : STATUS1_POISON;
            gActiveBattler = battler;
            BtlController_EmitSetMonData(BUFFER_A, REQUEST_STATUS_BATTLE, 0, sizeof(gBattleMons[battler].status1), &gBattleMons[battler].status1);
            MarkBattlerForControllerExec(battler);
            gEffectBattler = battler;
            gBattleCommunication[MULTISTRING_CHOOSER] = gHackField.toxicSpikes[side] >= 2;
            BattleScriptPushCursor();
            gBattlescriptCurrInstr = BattleScript_HackToxicSpikes;
            return TRUE;
        }
    }
    if (gHackField.stickyWeb[side] && !(*done & 4) && grounded)
    {
        *done |= 4;
        if (Hack_MoveStatChange(battler, STAT_SPEED, -1))
        {
            BattleScriptPushCursor();
            gBattlescriptCurrInstr = BattleScript_HackSelfStatRet;
            return TRUE;
        }
    }
    return FALSE;
}

static void Cmd_switchineffects(void)
{""")
sub('src/battle_script_commands.c', """        spikesDmg = (5 - gSideTimers[GetBattlerSide(gActiveBattler)].spikesAmount) * 2;""",
"""        gBattleCommunication[MULTISTRING_CHOOSER] = 0;
        spikesDmg = (5 - gSideTimers[GetBattlerSide(gActiveBattler)].spikesAmount) * 2;""")
sub('src/battle_script_commands.c', """            gBattlescriptCurrInstr = BattleScript_SpikesOnFaintedBattler;
    }
    else
    {
        // There is a hack here in pokeemerald""", """            gBattlescriptCurrInstr = BattleScript_SpikesOnFaintedBattler;
    }
    else if (Hack_SwitchInHazards(gActiveBattler))
    {
    }
    else
    {
        // There is a hack here in pokeemerald""")
sub('src/battle_script_commands.c', """            gSideStatuses[GetBattlerSide(gActiveBattler)] &= ~SIDE_STATUS_SPIKES_DAMAGED;

            for (i = 0; i < gBattlersCount; i++)
            {
                if (gBattlerByTurnOrder[i] == gActiveBattler)""", """            gSideStatuses[GetBattlerSide(gActiveBattler)] &= ~SIDE_STATUS_SPIKES_DAMAGED;
            gHackField.hazardDone[gActiveBattler] = 0;

            for (i = 0; i < gBattlersCount; i++)
            {
                if (gBattlerByTurnOrder[i] == gActiveBattler)""")
sub('src/battle_script_commands.c', """    else if (gSideStatuses[GetBattlerSide(gBattlerAttacker)] & SIDE_STATUS_SPIKES)
    {
        gSideStatuses[GetBattlerSide(gBattlerAttacker)] &= ~SIDE_STATUS_SPIKES;
        gSideTimers[GetBattlerSide(gBattlerAttacker)].spikesAmount = 0;""", """    else if ((gSideStatuses[GetBattlerSide(gBattlerAttacker)] & SIDE_STATUS_SPIKES) || Hack_SideHasHazards(GetBattlerSide(gBattlerAttacker)))
    {
        Hack_ClearHazards(GetBattlerSide(gBattlerAttacker));""")
sub('src/battle_script_commands.c', """    if (gSpecialStatuses[gBattlerTarget].lightningRodRedirected)
    {
        gSpecialStatuses[gBattlerTarget].lightningRodRedirected = FALSE;""", """    if (gCurrentMove == MOVE_FEINT)
        gProtectStructs[gBattlerTarget].protected = FALSE; // Feint breaks through Protect

    if (gSpecialStatuses[gBattlerTarget].lightningRodRedirected)
    {
        gSpecialStatuses[gBattlerTarget].lightningRodRedirected = FALSE;""")
sub('src/battle_script_commands.c', "    gBattlescriptCurrInstr = BattleScript_SuccessForceOut;\n    return TRUE;",
"    gBattlescriptCurrInstr = gBattleMoves[gCurrentMove].effect == EFFECT_HACK_DRAG ? BattleScript_HackDragOut : BattleScript_SuccessForceOut;\n    return TRUE;")

# ---- pokemon.c: variable power
sub('src/pokemon.c', """    case MOVE_PAYBACK:""", """    case MOVE_WRING_OUT:
        power = 120 * def->hp / def->maxHP;
        if (power == 0)
            power = 1;
        break;
    case MOVE_HARD_PRESS:
        power = 100 * def->hp / def->maxHP;
        if (power == 0)
            power = 1;
        break;
    case MOVE_PUNISHMENT:
        boosts = 0;
        for (i = 0; i < NUM_BATTLE_STATS; i++)
            if (def->statStages[i] > DEFAULT_STAT_STAGE)
                boosts += def->statStages[i] - DEFAULT_STAT_STAGE;
        power = 60 + 20 * boosts;
        if (power > 200)
            power = 200;
        break;
    case MOVE_KNOCK_OFF:
        if (def->item != ITEM_NONE)
            power = power * 3 / 2;
        break;
    case MOVE_PAYBACK:""")

# ---- Knock Off: modern 65 power
p = 'src/data/battle_moves.h'; s = open(R + p).read()
s, n = re.subn(r"(\[MOVE_KNOCK_OFF\] =\s*\{\s*\.effect = EFFECT_KNOCK_OFF,\s*\.power = )\d+", r"\g<1>65", s)
assert n == 1
open(R + p, 'w').write(s)
print("ok")
