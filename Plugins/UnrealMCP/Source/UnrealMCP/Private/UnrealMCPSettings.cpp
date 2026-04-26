#include "UnrealMCPSettings.h"

UUnrealMCPSettings::UUnrealMCPSettings()
	: Host(TEXT("127.0.0.1"))
	, Port(55557)
	, bAllowRemoteConnections(false)
{
}

FName UUnrealMCPSettings::GetCategoryName() const
{
	return TEXT("Plugins");
}
