// Copyright Epic Games, Inc. All Rights Reserved.

using System;
using System.IO;
using System.Collections.Generic;
using UnrealBuildTool;

public class UnrealMCP : ModuleRules
{
    public UnrealMCP(ReadOnlyTargetRules Target) : base(Target)
    {
        PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

        PublicDefinitions.Add("UNREALMCP_EXPORTS=1");
        PublicDefinitions.Add("WITH_AI_NAV_MCP=1");

        PublicIncludePaths.AddRange(
            new string[] {
                Path.Combine(ModuleDirectory, "Public"),
                Path.Combine(ModuleDirectory, "Public/Commands"),
                Path.Combine(ModuleDirectory, "Public/Commands/BlueprintGraph"),
                Path.Combine(ModuleDirectory, "Public/Commands/BlueprintGraph/Nodes")
            }
        );

        PrivateIncludePaths.AddRange(
            new string[] {
                Path.Combine(ModuleDirectory, "Private"),
                Path.Combine(ModuleDirectory, "Private/Commands"),
                Path.Combine(ModuleDirectory, "Private/Commands/BlueprintGraph"),
                Path.Combine(ModuleDirectory, "Private/Commands/BlueprintGraph/Nodes")
            }
        );

        PublicDependencyModuleNames.AddRange(
            new string[]
            {
                "Core", "CoreUObject", "Engine", "InputCore",
                "Networking", "Sockets", "HTTP", "Json", "JsonUtilities",
                "GameplayTags", "AIModule",
                "DeveloperSettings", "EditorSubsystem",
                "PhysicsCore", "EngineSettings", "EnhancedInput",
                "UnrealEd", "BlueprintGraph", "KismetCompiler",
                "GeometryScriptingCore", "DynamicMesh", "GeometryFramework",
                "Renderer", "RHI", "CinematicCamera"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "EditorScriptingUtilities", "Slate", "SlateCore", "Kismet",
                "Projects", "AssetRegistry", "AssetTools", "NavigationSystem",
                "Navmesh", "AudioEditor", "RenderCore", "ImageWrapper",
                "UMGEditor", "UMG", "MovieScene", "MovieSceneTracks",
                "LevelSequence", "CommonUI", "CommonInput",
                "DeveloperToolSettings"
            }
        );

        PrivateDependencyModuleNames.AddRange(
            new string[]
            {
                "GeometryCore", "GeometryScriptingCore", "GeometryFramework",
                "DynamicMesh", "MeshDescription", "StaticMeshDescription"
            }
        );

        if (Target.bBuildEditor == true)
        {
            PrivateDependencyModuleNames.AddRange(
                new string[]
                {
                    "PropertyEditor", "ToolMenus", "BlueprintEditorLibrary",
                    "LevelEditor", "StaticMeshEditor", "GraphEditor",
                    "InputBlueprintNodes", "EditorWidgets", "ApplicationCore",
                    "WorkspaceMenuStructure", "DataLayerEditor",
                    "SourceControl", "DataValidation"
                }
            );
        }

        DynamicallyLoadedModuleNames.AddRange(new string[] {});

        // 234-stubs Wave 0 (#70): Optional module gates.
        AddOptionalModuleGates(Target);
    }

    private string ProjectDirOrNull(ReadOnlyTargetRules Target)
    {
        if (Target.ProjectFile == null) return null;
        return Path.GetDirectoryName(Target.ProjectFile.FullName);
    }

    private bool ProbeExists(string[] Probes)
    {
        foreach (string p in Probes)
        {
            if (!string.IsNullOrEmpty(p) && File.Exists(p)) return true;
        }
        return false;
    }

    private string[] PluginProbes(ReadOnlyTargetRules Target, string SubPathUnderPlugins, string UpluginName)
    {
        List<string> probes = new List<string>();
        probes.Add(Path.Combine(EngineDirectory, "Plugins", SubPathUnderPlugins, UpluginName));
        probes.Add(Path.Combine(EngineDirectory, "Plugins", "Marketplace", SubPathUnderPlugins, UpluginName));
        string projectDir = ProjectDirOrNull(Target);
        if (projectDir != null)
        {
            probes.Add(Path.Combine(projectDir, "Plugins", SubPathUnderPlugins, UpluginName));
        }
        return probes.ToArray();
    }

    private void AddDepSafe(string ModuleName)
    {
        if (string.IsNullOrEmpty(ModuleName)) return;
        if (!PrivateDependencyModuleNames.Contains(ModuleName))
        {
            PrivateDependencyModuleNames.Add(ModuleName);
        }
    }

    private void AddGate(
        string Key,
        bool Found,
        string[] RuntimeModules,
        string[] EditorOnlyModules,
        ReadOnlyTargetRules Target)
    {
        string Define = "WITH_" + Key + "_MCP";
        if (Found)
        {
            PublicDefinitions.Add(Define + "=1");
            if (RuntimeModules != null)
            {
                foreach (string m in RuntimeModules) AddDepSafe(m);
            }
            if (Target.bBuildEditor && EditorOnlyModules != null)
            {
                foreach (string m in EditorOnlyModules) AddDepSafe(m);
            }
        }
        else
        {
            PublicDefinitions.Add(Define + "=0");
        }
    }


    // Issue #70 requires per-module gates, not just per-category gates.  These
    // helpers locate a module by its *.Build.cs rule file and emit a stable
    // WITH_<MODULE>_MCP=1/0 define while only adding the dependency when the
    // rule exists in this UE 5.7 install (or the project plugin tree).  This
    // keeps minimal installs buildable and avoids hard-coding plugin layouts
    // that vary between source / launcher / marketplace builds.
    private string SanitizeModuleDefineKey(string ModuleName)
    {
        string Out = "";
        foreach (char c in ModuleName)
        {
            Out += char.IsLetterOrDigit(c) ? char.ToUpperInvariant(c) : '_';
        }
        return Out;
    }

    private bool ModuleRuleExists(ReadOnlyTargetRules Target, string ModuleName)
    {
        string RuleFile = ModuleName + ".Build.cs";
        List<string> Roots = new List<string>();
        Roots.Add(Path.Combine(EngineDirectory, "Source"));
        Roots.Add(Path.Combine(EngineDirectory, "Plugins"));
        string ProjectDir = ProjectDirOrNull(Target);
        if (ProjectDir != null)
        {
            Roots.Add(Path.Combine(ProjectDir, "Source"));
            Roots.Add(Path.Combine(ProjectDir, "Plugins"));
        }

        foreach (string Root in Roots)
        {
            if (!Directory.Exists(Root)) continue;
            try
            {
                string[] Matches = Directory.GetFiles(Root, RuleFile, SearchOption.AllDirectories);
                if (Matches != null && Matches.Length > 0) return true;
            }
            catch
            {
                // Some launcher installs contain restricted directories. Treat
                // them as "not found" rather than failing the entire build.
            }
        }
        return false;
    }

    private bool HasDefinitionPrefix(string Prefix)
    {
        foreach (string Definition in PublicDefinitions)
        {
            if (Definition.StartsWith(Prefix)) return true;
        }
        return false;
    }

    private void SetDefinition(string Define, bool bEnabled)
    {
        string Prefix = Define + "=";
        for (int i = PublicDefinitions.Count - 1; i >= 0; --i)
        {
            if (PublicDefinitions[i].StartsWith(Prefix))
            {
                PublicDefinitions.RemoveAt(i);
            }
        }
        PublicDefinitions.Add(Prefix + (bEnabled ? "1" : "0"));
    }

    private void AddOptionalModuleGate(ReadOnlyTargetRules Target, string ModuleName, bool bEditorOnly)
    {
        string Define = "WITH_" + SanitizeModuleDefineKey(ModuleName) + "_MCP";
        bool bFound = ModuleRuleExists(Target, ModuleName);
        bool bEnabledForTarget = bFound && (!bEditorOnly || Target.bBuildEditor);
        SetDefinition(Define, bEnabledForTarget);
        if (bEnabledForTarget)
        {
            AddDepSafe(ModuleName);
        }
    }

    private void AddIssue70PerModuleGates(ReadOnlyTargetRules Target)
    {
        // Wave 3: Chaos Physics
        string[] RuntimeChaos = new string[] { "Chaos", "ChaosSolverEngine", "GeometryCollectionEngine", "ChaosCloth", "ChaosVehicles", "FieldSystemEngine", "ClusterUnion" };
        foreach (string ModuleName in RuntimeChaos) AddOptionalModuleGate(Target, ModuleName, false);

        // Wave 3: Foliage / PCG / Water
        string[] RuntimeWorld = new string[] { "Foliage", "PCG", "PCGGeometryScriptInterop", "Water" };
        foreach (string ModuleName in RuntimeWorld) AddOptionalModuleGate(Target, ModuleName, false);
        string[] EditorWorld = new string[] { "FoliageEdit", "PCGEditor", "WaterEditor" };
        foreach (string ModuleName in EditorWorld) AddOptionalModuleGate(Target, ModuleName, true);

        // Wave 1: Niagara
        string[] RuntimeNiagara = new string[] { "Niagara", "NiagaraCore" };
        foreach (string ModuleName in RuntimeNiagara) AddOptionalModuleGate(Target, ModuleName, false);
        AddOptionalModuleGate(Target, "NiagaraEditor", true);

        // Wave 4: Movie Render Queue / Movie Graph
        string[] RuntimeMoviePipeline = new string[] { "MovieRenderPipelineCore", "MovieRenderPipelineSettings", "MovieRenderPipelineRenderPasses", "MoviePipelineMaskRenderPass", "MovieGraph", "MovieGraphCore" };
        foreach (string ModuleName in RuntimeMoviePipeline) AddOptionalModuleGate(Target, ModuleName, false);
        AddOptionalModuleGate(Target, "MovieRenderPipelineEditor", true);

        // Wave 4: Networking
        string[] RuntimeNetworking = new string[] { "OnlineSubsystem", "OnlineSubsystemUtils", "NetCore", "ReplicationGraph", "Iris", "IrisCore", "Voice", "VoiceChat" };
        foreach (string ModuleName in RuntimeNetworking) AddOptionalModuleGate(Target, ModuleName, false);

        // Wave 4: Localization / Source Control
        string[] RuntimeLocalization = new string[] { "Localization", "Internationalization", "LocalizationService" };
        foreach (string ModuleName in RuntimeLocalization) AddOptionalModuleGate(Target, ModuleName, false);
        AddOptionalModuleGate(Target, "LocalizationCommandletExecution", true);
        AddOptionalModuleGate(Target, "SourceControl", true);
        AddOptionalModuleGate(Target, "SourceControlWindows", true);

        // Wave 5: MetaSound / XR / Mobile / Testing
        string[] RuntimeMetaSound = new string[] { "MetasoundEngine", "MetasoundFrontend", "MetasoundGenerator", "MetasoundGraphCore" };
        foreach (string ModuleName in RuntimeMetaSound) AddOptionalModuleGate(Target, ModuleName, false);
        AddOptionalModuleGate(Target, "MetasoundEditor", true);
        string[] RuntimeXr = new string[] { "XRBase", "HeadMountedDisplay", "OpenXRHMD", "OpenXRInput" };
        foreach (string ModuleName in RuntimeXr) AddOptionalModuleGate(Target, ModuleName, false);
        if (Target.Platform == UnrealTargetPlatform.Android)
        {
            AddOptionalModuleGate(Target, "AndroidPermission", false);
            AddOptionalModuleGate(Target, "AndroidDeviceProfileSelector", false);
        }
        if (Target.Platform == UnrealTargetPlatform.IOS)
        {
            AddOptionalModuleGate(Target, "IOSDeviceProfileSelector", false);
        }
        string[] TestingModules = new string[] { "AutomationTest", "DataValidation", "EditorValidator", "FunctionalTesting" };
        foreach (string ModuleName in TestingModules) AddOptionalModuleGate(Target, ModuleName, true);
        AddOptionalModuleGate(Target, "AutomationController", true);

        // Wave 2: Gameplay / AI / Sequencer
        string[] RuntimeGameplay = new string[] { "GameplayAbilities", "GameplayTags", "GameplayTasks", "MassEntity", "StateTreeModule" };
        foreach (string ModuleName in RuntimeGameplay) AddOptionalModuleGate(Target, ModuleName, false);
        string[] EditorGameplay = new string[] { "StateTreeEditorModule", "BehaviorTreeEditor", "EnvironmentQueryEditor" };
        foreach (string ModuleName in EditorGameplay) AddOptionalModuleGate(Target, ModuleName, true);
        string[] RuntimeSequencer = new string[] { "MovieScene", "MovieSceneTracks", "LevelSequence", "SequencerCore" };
        foreach (string ModuleName in RuntimeSequencer) AddOptionalModuleGate(Target, ModuleName, false);
        string[] EditorSequencer = new string[] { "MovieSceneTools", "LevelSequenceEditor", "Sequencer" };
        foreach (string ModuleName in EditorSequencer) AddOptionalModuleGate(Target, ModuleName, true);

        // Wave 1: Animation Rigging / Landscape
        string[] RuntimeAnimRig = new string[] { "ControlRig", "ControlRigDeveloper", "IKRig", "RigVMDeveloper", "AnimGraphRuntime" };
        foreach (string ModuleName in RuntimeAnimRig) AddOptionalModuleGate(Target, ModuleName, false);
        string[] EditorAnimRig = new string[] { "ControlRigEditor", "IKRigEditor", "AnimGraph" };
        foreach (string ModuleName in EditorAnimRig) AddOptionalModuleGate(Target, ModuleName, true);
        AddOptionalModuleGate(Target, "LandscapeEditor", true);
        AddOptionalModuleGate(Target, "LandscapeEditorUtilities", true);
        AddOptionalModuleGate(Target, "LandscapeEditMode", true);
    }
    private void AddOptionalModuleGates(ReadOnlyTargetRules Target)
    {
        // -- Cesium (legacy, kept for back-compat) --
        bool bCesiumFound = ProbeExists(PluginProbes(Target, "CesiumForUnreal", "CesiumForUnreal.uplugin"));
        AddGate("CESIUM_LEGACY", bCesiumFound, new string[] { "CesiumRuntime" }, null, Target);
        PublicDefinitions.Add("WITH_CESIUM=" + (bCesiumFound ? "1" : "0"));

        // -- Niagara --
        bool bNiagara = ProbeExists(PluginProbes(Target, Path.Combine("FX", "Niagara"), "Niagara.uplugin"));
        AddGate("NIAGARA", bNiagara,
            new string[] { "Niagara", "NiagaraCore" },
            new string[] { "NiagaraEditor" },
            Target);

        // -- Landscape --
        bool bLandscape = File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Landscape", "Classes", "Landscape.h"));
        AddGate("LANDSCAPE", bLandscape,
            new string[] { "Landscape" },
            new string[] { "LandscapeEditor", "LandscapeEditorUtilities" },
            Target);

        // -- Foliage --
        bool bFoliage = File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Foliage", "Public", "FoliageType.h"));
        AddGate("FOLIAGE", bFoliage,
            new string[] { "Foliage" },
            new string[] { "FoliageEdit" },
            Target);

        // -- Chaos --
        bool bChaos = File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Experimental", "Chaos", "Public", "Chaos", "Real.h"))
                   || File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Experimental", "ChaosSolverEngine", "Public", "ChaosSolverEngineDefinitions.h"));
        AddGate("CHAOS", bChaos,
            new string[] { "Chaos", "ChaosSolverEngine", "GeometryCollectionEngine", "FieldSystemEngine" },
            new string[] { },
            Target);

        bool bChaosCloth = ProbeExists(PluginProbes(Target, "ChaosCloth", "ChaosCloth.uplugin"))
                       || ProbeExists(PluginProbes(Target, Path.Combine("Experimental", "ChaosClothAsset"), "ChaosClothAsset.uplugin"));
        AddGate("CHAOSCLOTH", bChaosCloth, new string[] { }, new string[] { }, Target);

        bool bChaosVehicles = ProbeExists(PluginProbes(Target, "ChaosVehiclesPlugin", "ChaosVehiclesPlugin.uplugin"))
                          || ProbeExists(PluginProbes(Target, "ChaosVehicles", "ChaosVehicles.uplugin"));
        AddGate("CHAOSVEHICLES", bChaosVehicles, new string[] { }, new string[] { }, Target);

        // -- PCG --
        bool bPcg = ProbeExists(PluginProbes(Target, "PCG", "PCG.uplugin"));
        AddGate("PCG", bPcg, new string[] { }, new string[] { }, Target);
        if (bPcg)
        {
            AddDepSafe("PCG");
            if (Target.bBuildEditor) AddDepSafe("PCGEditor");
        }

        // -- Water --
        bool bWater = ProbeExists(PluginProbes(Target, "Water", "Water.uplugin"));
        AddGate("WATER", bWater, new string[] { }, new string[] { }, Target);
        if (bWater)
        {
            AddDepSafe("Water");
            if (Target.bBuildEditor) AddDepSafe("WaterEditor");
        }

        // -- Movie Render Queue / Graph --
        bool bMrq = ProbeExists(PluginProbes(Target, "MovieRenderPipeline", "MovieRenderPipeline.uplugin"));
        AddGate("MRQ", bMrq, new string[] { }, new string[] { }, Target);
        if (bMrq)
        {
            AddDepSafe("MovieRenderPipelineCore");
            AddDepSafe("MovieRenderPipelineSettings");
            AddDepSafe("MovieRenderPipelineRenderPasses");
            if (Target.bBuildEditor) AddDepSafe("MovieRenderPipelineEditor");
        }

        // -- Networking / OnlineSubsystem --
        bool bOnline = File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Online", "OnlineSubsystem", "Public", "OnlineSubsystem.h"));
        AddGate("ONLINE", bOnline,
            new string[] { "OnlineSubsystem", "OnlineSubsystemUtils" },
            new string[] { },
            Target);

        // -- Iris replication --
        bool bIris = File.Exists(Path.Combine(EngineDirectory, "Plugins", "Runtime", "Iris", "Iris", "Iris.uplugin"))
                  || File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "Experimental", "Iris", "Core", "Public", "Iris", "Core", "IrisCoreInit.h"));
        AddGate("IRIS", bIris, new string[] { }, new string[] { }, Target);

        // -- Localization --
        AddGate("LOCALIZATION", true, null, new string[] { "Localization" }, Target);
        bool bLocEditor = File.Exists(Path.Combine(EngineDirectory, "Source", "Editor", "LocalizationCommandletExecution", "Public", "LocalizationCommandletExecution.h"));
        AddGate("LOCALIZATION_EDITOR", bLocEditor, new string[] { }, new string[] { "LocalizationCommandletExecution" }, Target);
        AddOptionalModuleGate(Target, "LocalizationDashboard", true);

        // -- Source Control --
        bool bScm = File.Exists(Path.Combine(EngineDirectory, "Source", "Developer", "SourceControl", "Public", "ISourceControlModule.h"));
        AddGate("SOURCECONTROL", bScm, new string[] { }, new string[] { "SourceControlWindows" }, Target);

        // -- MetaSound --
        bool bMetasound = ProbeExists(PluginProbes(Target, "MetaSound", "MetaSound.uplugin"))
                      || ProbeExists(PluginProbes(Target, Path.Combine("Runtime", "MetaSound"), "MetaSound.uplugin"));
        AddGate("METASOUND", bMetasound, new string[] { }, new string[] { }, Target);
        if (bMetasound)
        {
            AddDepSafe("MetasoundEngine");
            AddDepSafe("MetasoundFrontend");
            if (Target.bBuildEditor) AddDepSafe("MetasoundEditor");
        }

        // -- XR / OpenXR / Mobile permissions --
        bool bXr = File.Exists(Path.Combine(EngineDirectory, "Source", "Runtime", "HeadMountedDisplay", "Public", "IHeadMountedDisplayModule.h"));
        bool bOpenXr = ProbeExists(PluginProbes(Target, Path.Combine("Runtime", "OpenXR"), "OpenXR.uplugin"));
        AddGate("XR", bXr, new string[] { "HeadMountedDisplay" }, new string[] { }, Target);
        AddGate("OPENXR", bOpenXr, new string[] { }, new string[] { }, Target);

        bool bAndroidPerm = ProbeExists(PluginProbes(Target, "AndroidPermission", "AndroidPermission.uplugin"));
        AddGate("ANDROIDPERMISSION", bAndroidPerm, new string[] { }, new string[] { }, Target);

        // -- Automation / DataValidation --
        bool bAutomation = File.Exists(Path.Combine(EngineDirectory, "Source", "Developer", "AutomationController", "Public", "AutomationControllerModule.h"));
        AddGate("AUTOMATION", bAutomation, new string[] { }, new string[] { "AutomationController" }, Target);

        bool bDataValidation = File.Exists(Path.Combine(EngineDirectory, "Plugins", "Developer", "DataValidation", "DataValidation.uplugin"))
                          || File.Exists(Path.Combine(EngineDirectory, "Source", "Editor", "DataValidation", "Public", "EditorValidatorSubsystem.h"));
        AddGate("DATAVALIDATION", bDataValidation, new string[] { }, new string[] { }, Target);

        // -- GAS --
        bool bGas = ProbeExists(PluginProbes(Target, "GameplayAbilities", "GameplayAbilities.uplugin"));
        AddGate("GAS", bGas, new string[] { }, new string[] { }, Target);
        if (bGas)
        {
            AddDepSafe("GameplayAbilities");
            AddDepSafe("GameplayTasks");
        }

        // -- StateTree --
        bool bStateTree = ProbeExists(PluginProbes(Target, Path.Combine("Runtime", "StateTree"), "StateTree.uplugin"))
                      || File.Exists(Path.Combine(EngineDirectory, "Plugins", "Runtime", "StateTree", "StateTree.uplugin"));
        AddGate("STATETREE", bStateTree, new string[] { }, new string[] { }, Target);

        // -- Animation rigging (ControlRig / IKRig) --
        bool bControlRig = ProbeExists(PluginProbes(Target, Path.Combine("Animation", "ControlRig"), "ControlRig.uplugin"));
        bool bIkRig      = ProbeExists(PluginProbes(Target, Path.Combine("Animation", "IKRig"), "IKRig.uplugin"));
        AddGate("ANIM_RIGGING", bControlRig || bIkRig, new string[] { }, new string[] { }, Target);

        // Issue #70 exact checklist: per-module optional gates for every
        // module named by the Wave 1-5 category issues.
        AddIssue70PerModuleGates(Target);

        // -- Live Coding (Win64 editor only) --
        bool bLiveCoding = false;
        if (Target.bBuildEditor && Target.Platform == UnrealTargetPlatform.Win64)
        {
            string LiveCodingProbe = Path.Combine(EngineDirectory, "Source", "Developer", "Windows", "LiveCoding", "Public", "ILiveCodingModule.h");
            if (File.Exists(LiveCodingProbe))
            {
                bLiveCoding = true;
            }
        }
        if (bLiveCoding)
        {
            PublicDefinitions.Add("WITH_LIVE_CODING=1");
            AddDepSafe("LiveCoding");
        }
        else
        {
            PublicDefinitions.Add("WITH_LIVE_CODING=0");
        }
    }
}



