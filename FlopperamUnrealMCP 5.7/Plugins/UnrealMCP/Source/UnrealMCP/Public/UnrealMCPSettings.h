#pragma once

#include "CoreMinimal.h"
#include "Engine/DeveloperSettings.h"
#include "UnrealMCPSettings.generated.h"

UCLASS(config=Game, defaultconfig, meta=(DisplayName="Unreal MCP"))
class UNREALMCP_API UUnrealMCPSettings : public UDeveloperSettings
{
	GENERATED_BODY()

public:
	UUnrealMCPSettings();

	UPROPERTY(config, EditAnywhere, Category="Server")
	FString Host;

	UPROPERTY(config, EditAnywhere, Category="Server", meta=(ClampMin="1", ClampMax="65535"))
	int32 Port;

	UPROPERTY(config, EditAnywhere, Category="Security")
	FString AuthToken;

	UPROPERTY(config, EditAnywhere, Category="Security")
	bool bAllowRemoteConnections;

	virtual FName GetCategoryName() const override;
};
