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
        AddGate("LOCALIZATION", true, new string[] { "Internationalization" }, new string[] { "Localization" }, Target);
        bool bLocEditor = File.Exists(Path.Combine(EngineDirectory, "Source", "Editor", "LocalizationCommandletExecution", "Public", "LocalizationCommandletExecution.h"));
        AddGate("LOCALIZATION_EDITOR", bLocEditor, new string[] { }, new string[] { "LocalizationCommandletExecution" }, Target);

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
