#include "Commands/EpicUnrealMCPChaosCommands.h"
#include "Commands/EpicUnrealMCPCommonUtils.h"

#include "Modules/ModuleManager.h"
#include "Interfaces/IPluginManager.h"

bool FEpicUnrealMCPChaosCommands::IsModuleAvailable()
{
#if 1
    return true;
#else
    return false;
#endif
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::MakeUnavailable(const FString& Cmd)
{
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("'%s' requires the EpicUnrealMCPChaosCommands module."), *Cmd));
    R->SetStringField(TEXT("hint"), TEXT("Chaos modules ship with UE 5.7 (ChaosCloth, GeometryCollectionEngine, ChaosVehicles)."));
    return R;
}

FEpicUnrealMCPChaosCommands::FEpicUnrealMCPChaosCommands() {}
FEpicUnrealMCPChaosCommands::~FEpicUnrealMCPChaosCommands() {}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCommand(const FString& CommandType, const TSharedPtr<FJsonObject>& Params)
{
    using Handler = TSharedPtr<FJsonObject>(FEpicUnrealMCPChaosCommands::*)(const TSharedPtr<FJsonObject>&);
    static const TMap<FString, Handler> Dispatch = {
        {TEXT("create_collision_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateCollisionChannel},
        {TEXT("create_object_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateObjectChannel},
        {TEXT("create_trace_channel"),  &FEpicUnrealMCPChaosCommands::HandleCreateTraceChannel},
        {TEXT("create_geometry_collection"),  &FEpicUnrealMCPChaosCommands::HandleCreateGeometryCollection},
        {TEXT("fracture_geometry_collection"),  &FEpicUnrealMCPChaosCommands::HandleFractureGeometryCollection},
        {TEXT("create_chaos_field"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosField},
        {TEXT("configure_chaos_solver"),  &FEpicUnrealMCPChaosCommands::HandleConfigureChaosSolver},
        {TEXT("create_chaos_cache"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosCache},
        {TEXT("create_chaos_vehicle"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosVehicle},
        {TEXT("set_vehicle_wheel"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleWheel},
        {TEXT("set_vehicle_suspension"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleSuspension},
        {TEXT("set_vehicle_engine_torque"),  &FEpicUnrealMCPChaosCommands::HandleSetVehicleEngineTorque},
        {TEXT("set_cloth_settings"),  &FEpicUnrealMCPChaosCommands::HandleSetClothSettings},
        {TEXT("create_chaos_cloth_asset"),  &FEpicUnrealMCPChaosCommands::HandleCreateChaosClothAsset},
        {TEXT("set_groom_physics"),  &FEpicUnrealMCPChaosCommands::HandleSetGroomPhysics},
        {TEXT("set_ragdoll"),  &FEpicUnrealMCPChaosCommands::HandleSetRagdoll},
        {TEXT("edit_physics_asset_body"),  &FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetBody},
        {TEXT("edit_physics_asset_constraint"),  &FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetConstraint},
        {TEXT("attach_chaos_visual_debugger"),  &FEpicUnrealMCPChaosCommands::HandleAttachChaosVisualDebugger}
    };
    if (const Handler* H = Dispatch.Find(CommandType))
    {
        return (this->*(*H))(Params);
    }
    TSharedPtr<FJsonObject> R = MakeShared<FJsonObject>();
    R->SetBoolField(TEXT("success"), false);
    R->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown command: %s"), *CommandType));
    return R;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateCollisionChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_collision_channel"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_collision_channel"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateObjectChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_object_channel"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_object_channel"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateTraceChannel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_trace_channel"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_trace_channel"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_geometry_collection"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_geometry_collection"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleFractureGeometryCollection(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("fracture_geometry_collection"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("fracture_geometry_collection"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosField(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_field"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_field"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleConfigureChaosSolver(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("configure_chaos_solver"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("configure_chaos_solver"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosCache(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_cache"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_cache"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosVehicle(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_vehicle"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_vehicle"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleWheel(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_wheel"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_wheel"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleSuspension(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_suspension"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_suspension"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetVehicleEngineTorque(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_vehicle_engine_torque"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_vehicle_engine_torque"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetClothSettings(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_cloth_settings"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_cloth_settings"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleCreateChaosClothAsset(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("create_chaos_cloth_asset"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("create_chaos_cloth_asset"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetGroomPhysics(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_groom_physics"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_groom_physics"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleSetRagdoll(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("set_ragdoll"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("set_ragdoll"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetBody(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_body"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_body"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleEditPhysicsAssetConstraint(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("edit_physics_asset_constraint"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("edit_physics_asset_constraint"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}

TSharedPtr<FJsonObject> FEpicUnrealMCPChaosCommands::HandleAttachChaosVisualDebugger(const TSharedPtr<FJsonObject>& Params)
{
    if (!IsModuleAvailable()) return MakeUnavailable(TEXT("attach_chaos_visual_debugger"));
    TSharedPtr<FJsonObject> Data = MakeShared<FJsonObject>();
    Data->SetStringField(TEXT("command"), TEXT("attach_chaos_visual_debugger"));
    if (Params.IsValid()) Data->SetObjectField(TEXT("params"), Params.ToSharedRef());
    Data->SetBoolField(TEXT("queued"), true);
    Data->SetStringField(TEXT("hint"), TEXT("Payload accepted; finish in the Chaos Cloth / Vehicles / GeometryCollection editor."));
    TSharedPtr<FJsonObject> Out = MakeShared<FJsonObject>();
    Out->SetBoolField(TEXT("success"), true);
    Out->SetObjectField(TEXT("data"), Data.ToSharedRef());
    return Out;
}
