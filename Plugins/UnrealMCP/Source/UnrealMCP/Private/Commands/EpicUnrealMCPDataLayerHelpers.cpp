// =====================================================================
// EpicUnrealMCPDataLayerHelpers
//
// Shared utility for WP DataLayer asset/instance creation, color and
// runtime-state application, and degrades to actor tags when WP is not
// available (e.g. non-WorldPartition levels).
//
// Targets Unreal Engine 5.7 API:
//   - UDataLayerEditorSubsystem::GetDataLayerInstance
//   - UDataLayerEditorSubsystem::CreateDataLayerInstance
//   - FDataLayerCreationParameters
//   - UDataLayerInstance::SetDebugColor / SetInitialRuntimeState
// =====================================================================

#include "Commands/EpicUnrealMCPDataLayerHelpers.h"

#include "Editor.h"
#include "GameFramework/Actor.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "AssetRegistry/IAssetRegistry.h"
#include "EditorAssetLibrary.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/SoftObjectPtr.h"
#include "WorldPartition/DataLayer/DataLayerAsset.h"
#include "WorldPartition/DataLayer/DataLayerInstance.h"
#include "DataLayer/DataLayerEditorSubsystem.h"

namespace
{
    FString MakeSafeAssetName(const FString& Raw)
    {
        FString Safe = Raw;
        Safe.ReplaceInline(TEXT(" "), TEXT("_"));
        Safe.ReplaceInline(TEXT("/"), TEXT("_"));
        Safe.ReplaceInline(TEXT("\\"), TEXT("_"));
        Safe.ReplaceInline(TEXT(":"), TEXT("_"));
        return Safe;
    }

    FString GetDataLayerAssetPath(const FString& DataLayerName)
    {
        return FString::Printf(TEXT("/Game/DataLayers/%s"), *MakeSafeAssetName(DataLayerName));
    }

    UDataLayerAsset* FindDataLayerAssetByName(const FString& DataLayerName)
    {
        const FString SafeName = MakeSafeAssetName(DataLayerName);
        const FString DirectObjectPath = FString::Printf(TEXT("/Game/DataLayers/%s.%s"), *SafeName, *SafeName);
        if (UDataLayerAsset* LoadedAsset = LoadObject<UDataLayerAsset>(nullptr, *DirectObjectPath))
        {
            return LoadedAsset;
        }

        FAssetRegistryModule& AssetRegistryModule = FModuleManager::LoadModuleChecked<FAssetRegistryModule>(TEXT("AssetRegistry"));
        IAssetRegistry& AssetRegistry = AssetRegistryModule.Get();
        TArray<FAssetData> Assets;
        AssetRegistry.GetAssetsByClass(UDataLayerAsset::StaticClass()->GetClassPathName(), Assets, true);
        for (const FAssetData& Asset : Assets)
        {
            if (Asset.AssetName.ToString() == DataLayerName || Asset.AssetName.ToString() == SafeName)
            {
                return Cast<UDataLayerAsset>(Asset.GetAsset());
            }
        }

        return nullptr;
    }

    bool TryParseHexColor(const FString& HexIn, FColor& OutColor)
    {
        FString Hex = HexIn;
        Hex.TrimStartAndEndInline();
        if (Hex.Len() == 0)
        {
            return false;
        }
        if (Hex[0] == TCHAR('#'))
        {
            Hex.RightChopInline(1);
        }
        if (Hex.Len() != 6 && Hex.Len() != 8)
        {
            return false;
        }

        uint32 Value = 0;
        for (int32 i = 0; i < Hex.Len(); ++i)
        {
            TCHAR C = Hex[i];
            uint32 Digit = 0;
            if (C >= TCHAR('0') && C <= TCHAR('9'))
            {
                Digit = static_cast<uint32>(C - TCHAR('0'));
            }
            else if (C >= TCHAR('a') && C <= TCHAR('f'))
            {
                Digit = 10 + static_cast<uint32>(C - TCHAR('a'));
            }
            else if (C >= TCHAR('A') && C <= TCHAR('F'))
            {
                Digit = 10 + static_cast<uint32>(C - TCHAR('A'));
            }
            else
            {
                return false;
            }
            Value = (Value << 4) | Digit;
        }

        const bool bHasAlpha = (Hex.Len() == 8);
        const uint8 A = bHasAlpha ? static_cast<uint8>((Value >> 24) & 0xFF) : 0xFF;
        const uint8 R = static_cast<uint8>((Value >> (bHasAlpha ? 16 : 16)) & 0xFF);
        const uint8 G = static_cast<uint8>((Value >> 8) & 0xFF);
        const uint8 B = static_cast<uint8>(Value & 0xFF);
        OutColor = FColor(R, G, B, A);
        return true;
    }
}

bool FEpicUnrealMCPDataLayerHelpers::IsDataLayerSubsystemAvailable()
{
    if (!GEditor)
    {
        return false;
    }
    return GEditor->GetEditorSubsystem<UDataLayerEditorSubsystem>() != nullptr;
}

UDataLayerAsset* FEpicUnrealMCPDataLayerHelpers::FindOrCreateDataLayerAsset(const FString& DataLayerName, FString* OutAssetPath)
{
    const FString AssetPath = GetDataLayerAssetPath(DataLayerName);
    if (OutAssetPath)
    {
        *OutAssetPath = AssetPath;
    }

    if (UDataLayerAsset* ExistingAsset = FindDataLayerAssetByName(DataLayerName))
    {
        return ExistingAsset;
    }

    UEditorAssetLibrary::MakeDirectory(TEXT("/Game/DataLayers"));
    UPackage* Package = CreatePackage(*AssetPath);
    if (!Package)
    {
        return nullptr;
    }

    const FString AssetName = FPackageName::GetLongPackageAssetName(AssetPath);
    UDataLayerAsset* DataLayerAsset = NewObject<UDataLayerAsset>(Package, FName(*AssetName), RF_Public | RF_Standalone);
    if (!DataLayerAsset)
    {
        return nullptr;
    }

    FAssetRegistryModule::AssetCreated(DataLayerAsset);
    Package->MarkPackageDirty();
    UEditorAssetLibrary::SaveLoadedAsset(DataLayerAsset, false);
    return DataLayerAsset;
}

UDataLayerInstance* FEpicUnrealMCPDataLayerHelpers::FindOrCreateDataLayerInstance(const FString& DataLayerName, UDataLayerAsset* DataLayerAsset)
{
    if (!GEditor || !DataLayerAsset)
    {
        return nullptr;
    }

    UDataLayerEditorSubsystem* DataLayerSubsystem = GEditor->GetEditorSubsystem<UDataLayerEditorSubsystem>();
    if (!DataLayerSubsystem)
    {
        return nullptr;
    }

    if (UDataLayerInstance* ExistingInstance = DataLayerSubsystem->GetDataLayerInstance(DataLayerAsset))
    {
        return ExistingInstance;
    }
    if (UDataLayerInstance* ExistingInstance = DataLayerSubsystem->GetDataLayerInstance(FName(*DataLayerName)))
    {
        return ExistingInstance;
    }

    FDataLayerCreationParameters CreationParameters;
    CreationParameters.DataLayerAsset = DataLayerAsset;
    return DataLayerSubsystem->CreateDataLayerInstance(CreationParameters);
}

int32 FEpicUnrealMCPDataLayerHelpers::AddActorsToInstance(const TArray<AActor*>& Actors, UDataLayerInstance* Instance)
{
    if (!Instance || !GEditor)
    {
        return 0;
    }
    UDataLayerEditorSubsystem* DataLayerSubsystem = GEditor->GetEditorSubsystem<UDataLayerEditorSubsystem>();
    if (!DataLayerSubsystem)
    {
        return 0;
    }

    int32 ModifiedCount = 0;
    for (AActor* Actor : Actors)
    {
        if (!Actor)
        {
            continue;
        }
        if (DataLayerSubsystem->AddActorToDataLayer(Actor, Instance))
        {
            ++ModifiedCount;
        }
    }
    return ModifiedCount;
}

bool FEpicUnrealMCPDataLayerHelpers::ApplyDebugColor(UDataLayerInstance* Instance, const FString& ColorHex)
{
    if (!Instance || ColorHex.IsEmpty())
    {
        return false;
    }

    FColor Color;
    if (!TryParseHexColor(ColorHex, Color))
    {
        return false;
    }

    // UDataLayerInstance exposes DebugColor as an FColor in the Editor
    // category. The property is settable directly in 5.7.
    FProperty* Prop = Instance->GetClass()->FindPropertyByName(FName(TEXT("DebugColor")));
    if (Prop && Prop->IsA<FStructProperty>())
    {
        FStructProperty* StructProp = CastField<FStructProperty>(Prop);
        if (StructProp->Struct == TBaseStructure<FColor>::Get())
        {
            void* PropPtr = StructProp->ContainerPtrToValuePtr<void>(Instance);
            *static_cast<FColor*>(PropPtr) = Color;
            Instance->Modify();
            return true;
        }
    }
    return false;
}

bool FEpicUnrealMCPDataLayerHelpers::ApplyInitialRuntimeState(UDataLayerInstance* Instance, const FString& StateName)
{
    if (!Instance || StateName.IsEmpty())
    {
        return false;
    }

    // The runtime state enum is EDataLayerRuntimeState (Unloaded/Loaded/Activated).
    // The property name on UDataLayerInstance is InitialRuntimeState.
    FProperty* Prop = Instance->GetClass()->FindPropertyByName(FName(TEXT("InitialRuntimeState")));
    if (!Prop || !Prop->IsA<FByteProperty>())
    {
        // In recent UE versions the enum is wrapped in an FEnumProperty.
        FEnumProperty* EnumProp = CastField<FEnumProperty>(Prop);
        if (!EnumProp)
        {
            return false;
        }

        UEnum* Enum = EnumProp->GetEnum();
        if (!Enum)
        {
            return false;
        }
        const int64 Value = Enum->GetValueByNameString(StateName);
        if (Value == INDEX_NONE)
        {
            return false;
        }
        void* PropPtr = EnumProp->ContainerPtrToValuePtr<void>(Instance);
        EnumProp->GetUnderlyingProperty()->SetIntPropertyValue(PropPtr, Value);
        Instance->Modify();
        return true;
    }

    FByteProperty* ByteProp = CastField<FByteProperty>(Prop);
    UEnum* Enum = ByteProp->Enum;
    if (!Enum)
    {
        return false;
    }
    const int64 Value = Enum->GetValueByNameString(StateName);
    if (Value == INDEX_NONE)
    {
        return false;
    }
    void* PropPtr = ByteProp->ContainerPtrToValuePtr<void>(Instance);
    ByteProp->SetIntPropertyValue(PropPtr, Value);
    Instance->Modify();
    return true;
}
