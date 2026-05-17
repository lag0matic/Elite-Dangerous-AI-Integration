# COVAS:NEXT Reaction Inventory

Extracted from current upstream source after reset.

- Backend defaults: `src/lib/Config.py` `game_events`
- UI categories: `ui/src/app/components/character-settings/game-event-categories.ts`
- State meaning: `on` = React, `off` = Aware/no-react, `hidden` = not sent to the model

Total backend defaults: 298

## System

| Event | Default |
|---|---|
| `Cargo` | UI category only |
| `ClearSavedGame` | UI category only |
| `LoadGame` | React |
| `Shutdown` | React |
| `NewCommander` | React |
| `Materials` | UI category only |
| `Missions` | UI category only |
| `Progress` | UI category only |
| `Powerplay` | UI category only |
| `Rank` | UI category only |
| `Reputation` | UI category only |
| `Statistics` | UI category only |
| `SquadronStartup` | UI category only |
| `EngineerProgress` | UI category only |

## Combat

| Event | Default |
|---|---|
| `Died` | React |
| `Resurrect` | React |
| `InDanger` | Aware / no-react |
| `OutOfDanger` | Aware / no-react |
| `CombatEntered` | React |
| `CombatExited` | React |
| `LegalStateChanged` | React |
| `CommitCrime` | Aware / no-react |
| `Bounty` | Aware / no-react |
| `CapShipBond` | Aware / no-react |
| `Interdiction` | Aware / no-react |
| `Interdicted` | Aware / no-react |
| `BeingInterdicted` | React |
| `EscapeInterdiction` | Aware / no-react |
| `FactionKillBond` | Aware / no-react |
| `FighterDestroyed` | React |
| `HeatDamage` | React |
| `HeatWarning` | Aware / no-react |
| `HullDamage` | Aware / no-react |
| `PVPKill` | React |
| `ShieldState` | React |
| `ShipTargeted` | Aware / no-react |
| `BountyScanned` | Aware / no-react |
| `UnderAttack` | Aware / no-react |
| `CockpitBreached` | React |
| `CrimeVictim` | React |
| `SystemsShutdown` | React |
| `SelfDestruct` | React |

## Trading

| Event | Default |
|---|---|
| `BuyTradeData` | Aware / no-react |
| `CollectCargo` | Aware / no-react |
| `EjectCargo` | React |
| `MarketBuy` | Aware / no-react |
| `MarketSell` | Aware / no-react |
| `CargoTransfer` | Aware / no-react |
| `Market` | Aware / no-react |

## Mining

| Event | Default |
|---|---|
| `AsteroidCracked` | Aware / no-react |
| `MiningRefined` | Aware / no-react |
| `ProspectedAsteroid` | React |
| `LaunchDrone` | Aware / no-react |
| `RememberLimpets` | React |

## Ship Updates

| Event | Default |
|---|---|
| `FSDJump` | Aware / no-react |
| `FSDTarget` | Aware / no-react |
| `StartJump` | Aware / no-react |
| `FsdCharging` | React |
| `SupercruiseEntry` | React |
| `SupercruiseExit` | React |
| `ApproachSettlement` | React |
| `InDockingRange` | React |
| `GlideModeExited` | Aware / no-react |
| `GlideModeEntered` | Aware / no-react |
| `Docked` | React |
| `Undocked` | React |
| `DockingCanceled` | Aware / no-react |
| `DockingDenied` | React |
| `DockingGranted` | Aware / no-react |
| `DockingRequested` | Aware / no-react |
| `DockingTimeout` | React |
| `DockingComputerDocking` | Aware / no-react |
| `DockingComputerUndocking` | Aware / no-react |
| `DockingComputerDeactivated` | Aware / no-react |
| `NavRoute` | Aware / no-react |
| `NavRouteClear` | Aware / no-react |
| `CrewLaunchFighter` | React |
| `VehicleSwitch` | Aware / no-react |
| `LaunchFighter` | React |
| `DockFighter` | React |
| `FighterRebuilt` | React |
| `FuelScoop` | Aware / no-react |
| `RebootRepair` | React |
| `RepairDrone` | Aware / no-react |
| `AfmuRepairs` | Aware / no-react |
| `ModuleInfo` | Aware / no-react |
| `Synthesis` | Aware / no-react |
| `JetConeBoost` | Aware / no-react |
| `JetConeDamage` | Aware / no-react |
| `LandingGearUp` | Aware / no-react |
| `LandingGearDown` | Aware / no-react |
| `HudSwitchedToAnalysisMode` | Aware / no-react |
| `HudSwitchedToCombatMode` | Aware / no-react |
| `FlightAssistOn` | Aware / no-react |
| `FlightAssistOff` | Aware / no-react |
| `HardpointsRetracted` | Aware / no-react |
| `HardpointsDeployed` | Aware / no-react |
| `LightsOff` | Aware / no-react |
| `LightsOn` | Aware / no-react |
| `CargoScoopRetracted` | Aware / no-react |
| `CargoScoopDeployed` | Aware / no-react |
| `SilentRunningOff` | Aware / no-react |
| `SilentRunningOn` | Aware / no-react |
| `FuelScoopStarted` | Aware / no-react |
| `FuelScoopEnded` | Aware / no-react |
| `FsdMassLockEscaped` | Aware / no-react |
| `FsdMassLocked` | Aware / no-react |
| `LowFuelWarningCleared` | React |
| `LowFuelWarning` | React |
| `HighGravityWarning` | React |
| `NightVisionOff` | Aware / no-react |
| `NightVisionOn` | Aware / no-react |
| `SupercruiseDestinationDrop` | Aware / no-react |

## SRV Updates

| Event | Default |
|---|---|
| `LaunchSRV` | React |
| `DockSRV` | React |
| `SRVDestroyed` | React |
| `SrvHandbrakeOff` | Aware / no-react |
| `SrvHandbrakeOn` | Aware / no-react |
| `SrvTurretViewConnected` | Aware / no-react |
| `SrvTurretViewDisconnected` | Aware / no-react |
| `SrvDriveAssistOff` | Aware / no-react |
| `SrvDriveAssistOn` | Aware / no-react |

## On-Foot Updates

| Event | Default |
|---|---|
| `Disembark` | React |
| `Embark` | React |
| `BookDropship` | React |
| `BookTaxi` | React |
| `CancelDropship` | React |
| `CancelTaxi` | React |
| `CollectItems` | Aware / no-react |
| `DropItems` | Aware / no-react |
| `BackpackChange` | Aware / no-react |
| `BuyMicroResources` | Aware / no-react |
| `SellMicroResources` | Aware / no-react |
| `TransferMicroResources` | Aware / no-react |
| `TradeMicroResources` | Aware / no-react |
| `BuySuit` | React |
| `BuyWeapon` | React |
| `SellWeapon` | Aware / no-react |
| `UpgradeSuit` | Aware / no-react |
| `UpgradeWeapon` | Aware / no-react |
| `CreateSuitLoadout` | React |
| `DeleteSuitLoadout` | Aware / no-react |
| `RenameSuitLoadout` | React |
| `SwitchSuitLoadout` | React |
| `WeaponSelected` | Aware / no-react |
| `UseConsumable` | Aware / no-react |
| `FCMaterials` | Aware / no-react |
| `ScanOrganic` | React |
| `SellOrganicData` | React |
| `LowOxygenWarningCleared` | React |
| `LowOxygenWarning` | React |
| `LowHealthWarningCleared` | React |
| `LowHealthWarning` | React |
| `BreathableAtmosphereExited` | Aware / no-react |
| `BreathableAtmosphereEntered` | Aware / no-react |
| `DropShipDeploy` | Aware / no-react |

## Stations

| Event | Default |
|---|---|
| `StationServices` | Aware / no-react |
| `ShipyardBuy` | React |
| `ShipyardNew` | Aware / no-react |
| `ShipyardSell` | Aware / no-react |
| `ShipyardTransfer` | Aware / no-react |
| `ShipyardSwap` | Aware / no-react |
| `StoredShips` | Aware / no-react |
| `ModuleBuy` | Aware / no-react |
| `ModuleRetrieve` | Aware / no-react |
| `ModuleSell` | Aware / no-react |
| `ModuleSellRemote` | Aware / no-react |
| `ModuleStore` | Aware / no-react |
| `ModuleSwap` | Aware / no-react |
| `LoadoutEquipModule` | Aware / no-react |
| `LoadoutRemoveModule` | Aware / no-react |
| `Outfitting` | Aware / no-react |
| `BuyAmmo` | Aware / no-react |
| `BuyDrones` | Aware / no-react |
| `RefuelAll` | Aware / no-react |
| `RefuelPartial` | Aware / no-react |
| `Repair` | Aware / no-react |
| `RepairAll` | Aware / no-react |
| `RestockVehicle` | Aware / no-react |
| `FetchRemoteModule` | Aware / no-react |
| `MassModuleStore` | Aware / no-react |
| `ClearImpound` | React |
| `CargoDepot` | Aware / no-react |
| `CommunityGoal` | Aware / no-react |
| `CommunityGoalDiscard` | Aware / no-react |
| `CommunityGoalJoin` | Aware / no-react |
| `CommunityGoalReward` | Aware / no-react |
| `EngineerContribution` | Aware / no-react |
| `EngineerCraft` | Aware / no-react |
| `EngineerLegacyConvert` | Aware / no-react |
| `MaterialTrade` | Aware / no-react |
| `TechnologyBroker` | Aware / no-react |
| `PayBounties` | React |
| `PayFines` | React |
| `PayLegacyFines` | React |
| `RedeemVoucher` | React |
| `ScientificResearch` | Aware / no-react |
| `Shipyard` | Aware / no-react |
| `CarrierJump` | Aware / no-react |
| `CarrierBuy` | React |
| `CarrierStats` | Aware / no-react |
| `CarrierJumpRequest` | Aware / no-react |
| `CarrierDecommission` | React |
| `CarrierCancelDecommission` | React |
| `CarrierBankTransfer` | Aware / no-react |
| `CarrierDepositFuel` | Aware / no-react |
| `CarrierCrewServices` | Aware / no-react |
| `CarrierFinance` | Aware / no-react |
| `CarrierShipPack` | Aware / no-react |
| `CarrierModulePack` | Aware / no-react |
| `CarrierTradeOrder` | Aware / no-react |
| `CarrierDockingPermission` | Aware / no-react |
| `CarrierNameChanged` | React |
| `CarrierJumpCancelled` | React |
| `ColonisationConstructionDepot` | Aware / no-react |
| `FetchRemoteModuleCompleted` | Aware / no-react |
| `ShipyardTransferCompleted` | Aware / no-react |
| `CarrierJumpWarning` | React |
| `CarrierJumpArrived` | Aware / no-react |
| `CarrierJumpCooldownComplete` | React |

## Social

| Event | Default |
|---|---|
| `Idle` | Hidden |
| `CrewAssign` | React |
| `CrewFire` | React |
| `CrewHire` | React |
| `ChangeCrewRole` | Aware / no-react |
| `CrewMemberJoins` | React |
| `CrewMemberQuits` | React |
| `CrewMemberRoleChange` | React |
| `EndCrewSession` | React |
| `JoinACrew` | React |
| `KickCrewMember` | React |
| `QuitACrew` | React |
| `NpcCrewRank` | Aware / no-react |
| `Promotion` | React |
| `Friends` | React |
| `WingAdd` | React |
| `WingInvite` | React |
| `WingJoin` | React |
| `WingLeave` | React |
| `SendText` | Aware / no-react |
| `ReceiveText` | Aware / no-react |
| `AppliedToSquadron` | React |
| `DisbandedSquadron` | React |
| `InvitedToSquadron` | React |
| `JoinedSquadron` | React |
| `KickedFromSquadron` | React |
| `LeftSquadron` | React |
| `SharedBookmarkToSquadron` | Aware / no-react |
| `SquadronCreated` | React |
| `SquadronDemotion` | React |
| `SquadronPromotion` | React |
| `WonATrophyForSquadron` | Aware / no-react |
| `PowerplayCollect` | Aware / no-react |
| `PowerplayDefect` | React |
| `PowerplayDeliver` | Aware / no-react |
| `PowerplayFastTrack` | Aware / no-react |
| `PowerplayJoin` | React |
| `PowerplayLeave` | React |
| `PowerplaySalary` | Aware / no-react |
| `PowerplayVote` | Aware / no-react |
| `PowerplayVoucher` | Aware / no-react |

## Exploration

| Event | Default |
|---|---|
| `CodexEntry` | Aware / no-react |
| `DiscoveryScan` | Aware / no-react |
| `Scan` | Aware / no-react |
| `FSSAllBodiesFound` | Aware / no-react |
| `FSSBodySignals` | Aware / no-react |
| `FSSBiologicalSignals` | React |
| `FSSDiscoveryScan` | Aware / no-react |
| `FirstPlayerSystemDiscovered` | Aware / no-react |
| `FleetCarrierDiscovered` | Aware / no-react |
| `ResourceExtractionDiscovered` | Aware / no-react |
| `InstallationDiscovered` | Aware / no-react |
| `NavBeaconDiscovered` | Aware / no-react |
| `TouristBeaconDiscovered` | Aware / no-react |
| `MegashipDiscovered` | Aware / no-react |
| `GenericDiscovered` | Aware / no-react |
| `OutpostDiscovered` | Aware / no-react |
| `CombatDiscovered` | Aware / no-react |
| `StationDiscovered` | Aware / no-react |
| `UnknownSignalDiscovered` | Aware / no-react |
| `MaterialCollected` | Aware / no-react |
| `MaterialDiscarded` | Aware / no-react |
| `MaterialDiscovered` | Aware / no-react |
| `MultiSellExplorationData` | Aware / no-react |
| `NavBeaconScan` | React |
| `BuyExplorationData` | Aware / no-react |
| `SAAScanComplete` | Aware / no-react |
| `SAASignalsFound` | Aware / no-react |
| `ScanBaryCentre` | Aware / no-react |
| `SellExplorationData` | Aware / no-react |
| `Screenshot` | React |
| `ApproachBody` | React |
| `LeaveBody` | React |
| `Liftoff` | React |
| `Touchdown` | React |
| `DatalinkScan` | Aware / no-react |
| `DatalinkVoucher` | Aware / no-react |
| `DataScanned` | React |
| `Scanned` | Aware / no-react |
| `USSDrop` | Aware / no-react |
| `NoScoopableStars` | React |
| `HGECandidateFound` | Aware / no-react |
| `HighValueLandmarksBody` | Aware / no-react |

## Backend Defaults Not Listed In UI Categories

| Event | Default |
|---|---|
| `MissionAbandoned` | React |
| `MissionAccepted` | React |
| `MissionCompleted` | React |
| `MissionFailed` | React |
| `MissionRedirected` | React |
| `quest` | React |
