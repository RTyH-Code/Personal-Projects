# Engine changes for later moves batch 2 (run once after 'moves.py <showdown>/data 2').
# Paths are relative to the repo root.
import sys
R=''
def sub(path, old, new, count=1):
    p=R+path; s=open(p).read()
    n=s.count(old)
    if n!=count: sys.exit(f"{path}: expected {count} got {n}: {old[:80]!r}")
    open(p,'w').write(s.replace(old,new))

# ---- effects
sub('include/constants/battle_move_effects.h', "#define EFFECT_CAMOUFLAGE 213\n",
"#define EFFECT_CAMOUFLAGE 213\n#define EFFECT_HACK_STAT_SET 214\n#define EFFECT_HACK_SUCKER_PUNCH 215\n#define EFFECT_HACK_SPDEF_DOWN2_HIT 216\n")
sub('data/battle_scripts_1.s', "\t.4byte BattleScript_EffectCamouflage             @ EFFECT_CAMOUFLAGE\n",
"\t.4byte BattleScript_EffectCamouflage             @ EFFECT_CAMOUFLAGE\n\t.4byte BattleScript_EffectHackStatSet            @ EFFECT_HACK_STAT_SET\n\t.4byte BattleScript_EffectHackSuckerPunch        @ EFFECT_HACK_SUCKER_PUNCH\n\t.4byte BattleScript_EffectHackSpDefDown2Hit      @ EFFECT_HACK_SPDEF_DOWN2_HIT\n")
sub('data/battle_scripts_1.s', "BattleScript_EffectCamouflage::\n", """@ FireRed QoL+Hard: later moves (tools/hack/moves.py)
BattleScript_EffectHackStatSet::
	attackcanceler
	attackstring
	ppreduce
	callnative Hack_BS_StatSetCheck
	attackanimation
	waitanimation
BattleScript_HackStatSetLoop::
	callnative Hack_BS_StatSetNext
	call BattleScript_HackSelfStatRet
	goto BattleScript_HackStatSetLoop

BattleScript_HackSelfStatRet::
	playanimation BS_SCRIPTING, B_ANIM_STATS_CHANGE, sB_ANIM_ARG1
	printstring STRINGID_HACKSELFSTAT
	waitmessage B_WAIT_TIME_LONG
	return

BattleScript_EffectHackSuckerPunch::
	attackcanceler
	callnative Hack_BS_SuckerPunch
	goto BattleScript_HitFromAccCheck

BattleScript_EffectHackSpDefDown2Hit::
	setmoveeffect MOVE_EFFECT_SP_DEF_MINUS_2
	goto BattleScript_EffectHit

BattleScript_EffectCamouflage::
""")
sub('include/battle_scripts.h', "extern const u8 BattleScript_HackAbilityStatRet[];\n",
"extern const u8 BattleScript_HackAbilityStatRet[];\nextern const u8 BattleScript_HackSelfStatRet[];\nextern const u8 BattleScript_ButItFailedAtkStringPpReduce[];\n")

# ---- string
sub('include/constants/battle_string_ids.h', "#define STRINGID_HACKANTICIPATION    401\n\n#define BATTLESTRINGS_COUNT     402",
"#define STRINGID_HACKANTICIPATION    401\n#define STRINGID_HACKSELFSTAT        402\n\n#define BATTLESTRINGS_COUNT     403")
sub('src/battle_message.c', 'static const u8 sText_HackAnticipation[] = _("{B_SCR_ACTIVE_NAME_WITH_PREFIX} shuddered!");\n',
'static const u8 sText_HackAnticipation[] = _("{B_SCR_ACTIVE_NAME_WITH_PREFIX} shuddered!");\nstatic const u8 sText_HackSelfStat[] = _("{B_SCR_ACTIVE_NAME_WITH_PREFIX}\'s {B_BUFF1}\\n{B_BUFF2}");\n')
sub('src/battle_message.c', "    [STRINGID_HACKANTICIPATION - BATTLESTRINGS_TABLE_START]              = sText_HackAnticipation,\n",
"    [STRINGID_HACKANTICIPATION - BATTLESTRINGS_TABLE_START]              = sText_HackAnticipation,\n    [STRINGID_HACKSELFSTAT - BATTLESTRINGS_TABLE_START]                  = sText_HackSelfStat,\n")

# ---- battle_util.c: stat changes from moves, Sucker Punch, move-end effects
sub('src/battle_util.c', "bool8 Hack_MoveEndAbilities(void)\n{", r"""// ---------------------------------------------------------------------------
// FireRed QoL+Hard: later moves
// ---------------------------------------------------------------------------
static const struct { u16 move; u8 stat; s8 amount; } sHackMoveStatChanges[] =
{
    {MOVE_QUIVER_DANCE, STAT_SPATK, 1}, {MOVE_QUIVER_DANCE, STAT_SPDEF, 1}, {MOVE_QUIVER_DANCE, STAT_SPEED, 1},
    {MOVE_SHELL_SMASH, STAT_DEF, -1}, {MOVE_SHELL_SMASH, STAT_SPDEF, -1}, {MOVE_SHELL_SMASH, STAT_ATK, 2},
    {MOVE_SHELL_SMASH, STAT_SPATK, 2}, {MOVE_SHELL_SMASH, STAT_SPEED, 2},
    {MOVE_COIL, STAT_ATK, 1}, {MOVE_COIL, STAT_DEF, 1}, {MOVE_COIL, STAT_ACC, 1},
    {MOVE_HONE_CLAWS, STAT_ATK, 1}, {MOVE_HONE_CLAWS, STAT_ACC, 1},
    {MOVE_WORK_UP, STAT_ATK, 1}, {MOVE_WORK_UP, STAT_SPATK, 1},
    {MOVE_COTTON_GUARD, STAT_DEF, 3},
    // after a hit
    {MOVE_CLOSE_COMBAT, STAT_DEF, -1}, {MOVE_CLOSE_COMBAT, STAT_SPDEF, -1},
    {MOVE_HAMMER_ARM, STAT_SPEED, -1},
    {MOVE_FLAME_CHARGE, STAT_SPEED, 1}, {MOVE_TRAILBLAZE, STAT_SPEED, 1},
    {MOVE_CHARGE_BEAM, STAT_SPATK, 1},
};
static u8 sHackStatIdx;
static bool8 sHackStatRolled;

// Like a stat-changing move effect, but on the user and without the checks
// that protect against foes (Clear Body, Mist...). Contrary and Simple apply.
static bool8 Hack_MoveStatChange(u8 battler, u8 stat, s8 amount)
{
    s8 stage = gBattleMons[battler].statStages[stat];
    s8 newStage, diff;
    u16 str;
    u8 idx;

    if (gBattleMons[battler].ability == ABILITY_CONTRARY)
        amount = -amount;
    if (gBattleMons[battler].ability == ABILITY_SIMPLE)
        amount *= 2;
    newStage = stage + amount;
    if (newStage > MAX_STAT_STAGE)
        newStage = MAX_STAT_STAGE;
    if (newStage < MIN_STAT_STAGE)
        newStage = MIN_STAT_STAGE;
    if (newStage == stage)
        return FALSE;
    gBattleMons[battler].statStages[stat] = newStage;
    diff = newStage - stage;
    if (diff >= 2)
        gBattleScripting.animArg1 = stat + STAT_ANIM_PLUS2 - 1;
    else if (diff > 0)
        gBattleScripting.animArg1 = stat + STAT_ANIM_PLUS1 - 1;
    else if (diff <= -2)
        gBattleScripting.animArg1 = stat + STAT_ANIM_MINUS2 - 1;
    else
        gBattleScripting.animArg1 = stat + STAT_ANIM_MINUS1 - 1;
    gBattleScripting.animArg2 = 0;
    gBattleScripting.battler = battler;
    PREPARE_STAT_BUFFER(gBattleTextBuff1, stat);
    gBattleTextBuff2[0] = B_BUFF_PLACEHOLDER_BEGIN;
    idx = 1;
    if (diff >= 2 || diff <= -2)
    {
        str = diff > 0 ? STRINGID_STATSHARPLY : STRINGID_STATHARSHLY;
        gBattleTextBuff2[idx++] = B_BUFF_STRING;
        gBattleTextBuff2[idx++] = str;
        gBattleTextBuff2[idx++] = str >> 8;
    }
    str = diff > 0 ? STRINGID_STATROSE : STRINGID_STATFELL;
    gBattleTextBuff2[idx++] = B_BUFF_STRING;
    gBattleTextBuff2[idx++] = str;
    gBattleTextBuff2[idx++] = str >> 8;
    gBattleTextBuff2[idx] = B_BUFF_EOS;
    return TRUE;
}

static bool8 Hack_NextMoveStat(u8 battler)
{
    while (sHackStatIdx < ARRAY_COUNT(sHackMoveStatChanges))
    {
        u8 i = sHackStatIdx++;
        if (sHackMoveStatChanges[i].move == gCurrentMove
         && Hack_MoveStatChange(battler, sHackMoveStatChanges[i].stat, sHackMoveStatChanges[i].amount))
            return TRUE;
    }
    return FALSE;
}

void Hack_BS_StatSetCheck(void)
{
    u8 i;
    bool8 possible = FALSE;

    for (i = 0; i < ARRAY_COUNT(sHackMoveStatChanges); i++)
    {
        s8 amount = sHackMoveStatChanges[i].amount;
        s8 stage = gBattleMons[gBattlerAttacker].statStages[sHackMoveStatChanges[i].stat];

        if (sHackMoveStatChanges[i].move != gCurrentMove)
            continue;
        if (gBattleMons[gBattlerAttacker].ability == ABILITY_CONTRARY)
            amount = -amount;
        if ((amount > 0 && stage < MAX_STAT_STAGE) || (amount < 0 && stage > MIN_STAT_STAGE))
            possible = TRUE;
    }
    sHackStatIdx = 0;
    if (possible)
        gBattlescriptCurrInstr += 5;
    else
        gBattlescriptCurrInstr = BattleScript_ButItFailed;
}

void Hack_BS_StatSetNext(void)
{
    if (Hack_NextMoveStat(gBattlerAttacker))
        gBattlescriptCurrInstr += 5;
    else
        gBattlescriptCurrInstr = BattleScript_MoveEnd;
}

// Sucker Punch only works if the target is about to use a damaging move.
void Hack_BS_SuckerPunch(void)
{
    u8 target = gBattlerTarget;
    u16 move = gChosenMoveByBattler[target];
    u8 pos;

    for (pos = 0; pos < gBattlersCount && gBattlerByTurnOrder[pos] != target; pos++)
        ;
    if (gChosenActionByBattler[target] != B_ACTION_USE_MOVE || move == MOVE_NONE || gBattleMoves[move].power == 0
     || pos < gCurrentTurnActionNumber)
        gBattlescriptCurrInstr = BattleScript_ButItFailedAtkStringPpReduce;
    else
        gBattlescriptCurrInstr += 5;
}

bool8 Hack_MoveEndAbilities(void)
{""")
sub('src/battle_util.c', """            if (Hack_TryDefiant(i))
            {
                BattleScriptPushCursor();
                gBattlescriptCurrInstr = BattleScript_HackAbilityStatRet;
                return TRUE;
            }
        }
        break;
    }
    return FALSE;
}""", """            if (Hack_TryDefiant(i))
            {
                BattleScriptPushCursor();
                gBattlescriptCurrInstr = BattleScript_HackAbilityStatRet;
                return TRUE;
            }
        }
        gHackMoveEndStep = 3;
        sHackStatIdx = 0;
        sHackStatRolled = (gCurrentMove != MOVE_CHARGE_BEAM || Random() % 10 < 7);
        // fall through
    case 3:
        // stat changes on the user after a hit (Close Combat, Flame Charge...)
        if (gBattleMoves[gCurrentMove].power != 0 && sHackStatRolled && gBattleMons[gBattlerAttacker].hp != 0
         && TARGET_TURN_DAMAGED && !(gMoveResultFlags & MOVE_RESULT_NO_EFFECT) && Hack_NextMoveStat(gBattlerAttacker))
        {
            BattleScriptPushCursor();
            gBattlescriptCurrInstr = BattleScript_HackSelfStatRet;
            return TRUE;
        }
        gHackMoveEndStep = 4;
        // fall through
    case 4:
        gHackMoveEndStep = 5;
        if (gBattleMons[gBattlerTarget].hp == 0 || gBattlerAttacker == gBattlerTarget || !TARGET_TURN_DAMAGED
         || (gMoveResultFlags & MOVE_RESULT_NO_EFFECT) || (gBattleMons[gBattlerTarget].status2 & STATUS2_SUBSTITUTE))
            break;
        // the elemental fangs' second effect: 10% flinch
        if ((gCurrentMove == MOVE_FIRE_FANG || gCurrentMove == MOVE_ICE_FANG || gCurrentMove == MOVE_THUNDER_FANG)
         && gBattleMons[gBattlerTarget].ability != ABILITY_INNER_FOCUS && (Random() % 10) == 0)
            gBattleMons[gBattlerTarget].status2 |= STATUS2_FLINCHED;
        // Flare Blitz: 10% burn on top of the recoil
        if (gCurrentMove == MOVE_FLARE_BLITZ && gBattleMons[gBattlerTarget].status1 == 0 && (Random() % 10) == 0)
        {
            gBattleCommunication[MOVE_EFFECT_BYTE] = MOVE_EFFECT_BURN;
            BattleScriptPushCursor();
            gBattlescriptCurrInstr = BattleScript_ApplySecondaryEffect;
            return TRUE;
        }
        break;
    }
    return FALSE;
}""")

# ---- pokemon.c: variable power and moves that use other stats
sub('src/pokemon.c', "s32 CalculateBaseDamage(struct BattlePokemon *attacker, struct BattlePokemon *defender, u32 move, u16 sideStatus, u16 powerOverride, u8 typeOverride, u8 battlerIdAtk, u8 battlerIdDef)\n{",
r"""// FireRed QoL+Hard: later moves whose power depends on the battle
static u32 Hack_EffSpeed(struct BattlePokemon *mon)
{
    u32 speed = mon->speed * gStatStageRatios[mon->statStages[STAT_SPEED]][0] / gStatStageRatios[mon->statStages[STAT_SPEED]][1];

    if (mon->status1 & STATUS1_PARALYSIS)
        speed /= 4;
    return speed ? speed : 1;
}

static u32 Hack_Weight(u16 species)
{
    u32 weight = GetPokedexHeightWeight(SpeciesToNationalPokedexNum(species), 1);
    return weight ? weight : 1;
}

static u16 Hack_VariablePower(u32 move, struct BattlePokemon *atk, struct BattlePokemon *def, u8 battlerDef, u16 power)
{
    u32 ratio;
    u8 i, boosts;

    switch (move)
    {
    case MOVE_HEX:
        if (def->status1 & STATUS1_ANY)
            power *= 2;
        break;
    case MOVE_VENOSHOCK:
        if (def->status1 & STATUS1_PSN_ANY)
            power *= 2;
        break;
    case MOVE_BRINE:
        if (def->hp <= def->maxHP / 2)
            power *= 2;
        break;
    case MOVE_ACROBATICS:
        if (atk->item == ITEM_NONE)
            power *= 2;
        break;
    case MOVE_STORED_POWER:
    case MOVE_POWER_TRIP:
        boosts = 0;
        for (i = 0; i < NUM_BATTLE_STATS; i++)
            if (atk->statStages[i] > DEFAULT_STAT_STAGE)
                boosts += atk->statStages[i] - DEFAULT_STAT_STAGE;
        power = 20 + 20 * boosts;
        break;
    case MOVE_GYRO_BALL:
        ratio = 25 * Hack_EffSpeed(def) / Hack_EffSpeed(atk) + 1;
        power = ratio > 150 ? 150 : ratio;
        break;
    case MOVE_ELECTRO_BALL:
        ratio = Hack_EffSpeed(atk) / Hack_EffSpeed(def);
        power = ratio >= 4 ? 150 : ratio >= 3 ? 120 : ratio >= 2 ? 80 : ratio >= 1 ? 60 : 40;
        break;
    case MOVE_HEAVY_SLAM:
    case MOVE_HEAT_CRASH:
        ratio = Hack_Weight(atk->species) / Hack_Weight(def->species);
        power = ratio >= 5 ? 120 : ratio >= 4 ? 100 : ratio >= 3 ? 80 : ratio >= 2 ? 60 : 40;
        break;
    case MOVE_PAYBACK:
        for (i = 0; i < gBattlersCount; i++)
            if (gBattlerByTurnOrder[i] == battlerDef)
                break;
        if (i < gCurrentTurnActionNumber)
            power *= 2;
        break;
    }
    return power;
}

s32 CalculateBaseDamage(struct BattlePokemon *attacker, struct BattlePokemon *defender, u32 move, u16 sideStatus, u16 powerOverride, u8 typeOverride, u8 battlerIdAtk, u8 battlerIdDef)
{""")
sub('src/pokemon.c', """    else
        gBattleMovePower = powerOverride;

    if (!typeOverride)""", """    else
        gBattleMovePower = powerOverride;
    gBattleMovePower = Hack_VariablePower(move, attacker, defender, battlerIdDef, gBattleMovePower);

    if (!typeOverride)""")
sub('src/pokemon.c', """    spAttack = attacker->spAttack;
    spDefense = defender->spDefense;
""", """    spAttack = attacker->spAttack;
    spDefense = defender->spDefense;

    // later moves that use other stats (stages restored with the Unaware ones)
    if (move == MOVE_FOUL_PLAY)
    {
        attack = defender->attack;
        attacker->statStages[STAT_ATK] = defender->statStages[STAT_ATK];
    }
    else if (move == MOVE_BODY_PRESS)
    {
        attack = attacker->defense;
        if (defender->ability != ABILITY_UNAWARE)
            attacker->statStages[STAT_ATK] = attacker->statStages[STAT_DEF];
    }
    if (move == MOVE_PSYSHOCK || move == MOVE_PSYSTRIKE)
    {
        spDefense = defender->defense;
        defender->statStages[STAT_SPDEF] = defender->statStages[STAT_DEF];
    }
""")

# ---- battle_script_commands.c
sub('src/battle_script_commands.c', """        gCritMultiplier = 1;

    gBattlescriptCurrInstr++;
}

static void Cmd_damagecalc(void)""", """        gCritMultiplier = 1;

    // Frost Breath and Storm Throw always land a critical hit
    if ((gCurrentMove == MOVE_FROST_BREATH || gCurrentMove == MOVE_STORM_THROW)
     && gBattleMons[gBattlerTarget].ability != ABILITY_BATTLE_ARMOR && gBattleMons[gBattlerTarget].ability != ABILITY_SHELL_ARMOR)
        gCritMultiplier = 2;

    gBattlescriptCurrInstr++;
}

static void Cmd_damagecalc(void)""")
sub('src/battle_script_commands.c', "static void Cmd_callnative(void);\n",
"static void Cmd_callnative(void);\n\n// Freeze-Dry is super effective against Water\n#define HACK_MUL(i, mv) (((mv) == MOVE_FREEZE_DRY && TYPE_EFFECT_DEF_TYPE(i) == TYPE_WATER) ? TYPE_MUL_SUPER_EFFECTIVE : TYPE_EFFECT_MULTIPLIER(i))\n")
sub('src/battle_script_commands.c', "ModulateDmgByType(TYPE_EFFECT_MULTIPLIER(i))", "ModulateDmgByType(HACK_MUL(i, gCurrentMove))", 2)
sub('src/battle_script_commands.c', "ModulateDmgByType2(TYPE_EFFECT_MULTIPLIER(i), move, &flags)", "ModulateDmgByType2(HACK_MUL(i, move), move, &flags)", 4)
sub('src/battle_script_commands.c', "(gBattleWeather & B_WEATHER_RAIN) && gBattleMoves[move].effect == EFFECT_THUNDER)",
"(gBattleWeather & B_WEATHER_RAIN) && (gBattleMoves[move].effect == EFFECT_THUNDER || move == MOVE_HURRICANE))")
sub('src/battle_script_commands.c', "gBattleWeather & B_WEATHER_SUN && gBattleMoves[move].effect == EFFECT_THUNDER)\n            moveAcc = 50;",
"gBattleWeather & B_WEATHER_SUN && (gBattleMoves[move].effect == EFFECT_THUNDER || move == MOVE_HURRICANE))\n            moveAcc = 50;")
sub('src/battle_script_commands.c', """            case MOVE_EFFECT_RECOIL_33: // Double Edge
                gBattleMoveDamage = gHpDealt / 3;""", """            case MOVE_EFFECT_RECOIL_33: // Double Edge
                gBattleMoveDamage = (gCurrentMove == MOVE_HEAD_SMASH) ? gHpDealt / 2 : gHpDealt / 3;""")
print("ok")
