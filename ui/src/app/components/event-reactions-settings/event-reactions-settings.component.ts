import { Component, OnDestroy } from "@angular/core";
import { CommonModule, KeyValue } from "@angular/common";
import { FormsModule } from "@angular/forms";
import {
    MatFormField,
    MatFormFieldModule,
    MatHint,
    MatLabel,
} from "@angular/material/form-field";
import { MatInputModule } from "@angular/material/input";
import { MatIcon } from "@angular/material/icon";
import { MatSlideToggle } from "@angular/material/slide-toggle";
import { MatSelect, MatOption } from "@angular/material/select";
import {
    MatAccordion,
    MatExpansionPanel,
    MatExpansionPanelHeader,
    MatExpansionPanelTitle,
    MatExpansionPanelDescription,
} from "@angular/material/expansion";
import { MatTooltipModule } from "@angular/material/tooltip";
import { MatButtonModule } from "@angular/material/button";
import { MatButtonToggleModule } from "@angular/material/button-toggle";
import { Subscription } from "rxjs";
import {
    Character,
    CharacterService,
    EventReactionState,
    FocusProfileName,
} from "../../services/character.service";
import {
    Config,
    ConfigService,
} from "../../services/config.service.js";
import { MatSnackBar } from "@angular/material/snack-bar";
import { ConfirmationDialogService } from "../../services/confirmation-dialog.service.js";
import { GameEventTooltips } from "../character-settings/game-event-tooltips.js";
import { GameEventCategories } from "../character-settings/game-event-categories.js";

@Component({
    selector: "app-event-reactions-settings",
    standalone: true,
    imports: [
        CommonModule,
        FormsModule,
        MatFormFieldModule,
        MatFormField,
        MatLabel,
        MatHint,
        MatInputModule,
        MatIcon,
        MatSlideToggle,
        MatSelect,
        MatOption,
        MatAccordion,
        MatExpansionPanel,
        MatExpansionPanelHeader,
        MatExpansionPanelTitle,
        MatExpansionPanelDescription,
        MatTooltipModule,
        MatButtonModule,
        MatButtonToggleModule,
    ],
    templateUrl: "./event-reactions-settings.component.html",
    styleUrl: "./event-reactions-settings.component.scss",
})
export class EventReactionsSettingsComponent implements OnDestroy {
    activeCharacter: Character | null = null;
    activeCharacterIndex: number | null = null;
    characterList: Character[] = [];
    filteredEventReactions: Record<string, Record<string, EventReactionState>> = {};
    eventSearchQuery: string = "";
    expandedSection: string | null = null;
    selectedFocusProfile: "global" | FocusProfileName = "global";
    focusProfiles: Array<{ value: "global" | FocusProfileName; label: string; description: string }> = [
        { value: "global", label: "Global defaults", description: "Base reaction settings used outside focus-profile overrides." },
        { value: "combat-focus", label: "Combat focus", description: "Overrides while combat focus is active." },
        { value: "mining", label: "Mining", description: "Overrides while mining focus is active." },
        { value: "travel-docking-exploration", label: "Travel / Docking / Exploration", description: "Overrides for travel, docking, navigation, and exploration." },
        { value: "commerce", label: "Commerce", description: "Overrides for market, sale, repair, refuel, and merits events." },
        { value: "quiet", label: "Quiet", description: "Overrides for low-chatter mode." },
        { value: "full-context", label: "Full context", description: "Overrides while broad awareness is active." },
        { value: "normal", label: "Normal", description: "Overrides while normal focus is active." },
    ];
    public GameEventTooltips = GameEventTooltips;
    gameEventCategories = GameEventCategories;
    showImportSelector = false;
    selectedImportIndex: number | null = null;

    private configSubscription?: Subscription;
    private characterSubscription?: Subscription;
    private characterListSubscription?: Subscription;

    constructor(
        private configService: ConfigService,
        private characterService: CharacterService,
        private snackBar: MatSnackBar,
        private confirmationDialog: ConfirmationDialogService,
    ) {
        this.configSubscription = this.configService.config$
            .subscribe((config: Config | null) => {
                this.activeCharacterIndex =
                    config?.active_character_index ?? null;
                this.filterEvents(this.eventSearchQuery);
            });

        this.characterSubscription = this.characterService.character$
            .subscribe((character) => {
                this.activeCharacter = character;
                this.filterEvents(this.eventSearchQuery);
            });

        this.characterListSubscription = this.characterService.characterList$
            .subscribe((list) => {
                this.characterList = list || [];
            });
    }

    ngOnDestroy(): void {
        if (this.configSubscription) {
            this.configSubscription.unsubscribe();
        }
        if (this.characterSubscription) {
            this.characterSubscription.unsubscribe();
        }
        if (this.characterListSubscription) {
            this.characterListSubscription.unsubscribe();
        }
    }

    orderByKey = (
        a: KeyValue<string, any>,
        b: KeyValue<string, any>,
    ): number => a.key.localeCompare(b.key);

    onSectionToggled(sectionName: string | null) {
        this.expandedSection = sectionName;
    }

    isSectionExpanded(sectionName: string): boolean {
        return this.expandedSection === sectionName;
    }

    async onEventConfigChange(
        section: string,
        event: string,
        state: "on" | "off" | "hidden",
    ) {
        if (!this.activeCharacter) return;

        if (this.selectedFocusProfile === "global") {
            await this.characterService.setCharacterEventProperty(
                event,
                state,
            );
            return;
        }

        await this.setFocusProfileEventState(this.selectedFocusProfile, event, state);
    }

    async resetGameEvents() {
        if (this.activeCharacterIndex === null) return;

        if (this.selectedFocusProfile !== "global") {
            await this.resetSelectedFocusProfileOverrides();
            return;
        }

        const dialogRef = this.confirmationDialog.openConfirmationDialog({
            title: "Reset Game Events",
            message:
                "This will reset all game event settings to their default values. Are you sure you want to continue?",
            confirmButtonText: "Reset",
            cancelButtonText: "Cancel",
        });

        dialogRef.subscribe(async (result: boolean) => {
            if (result) {
                await this.characterService.resetGameEvents(
                    this.activeCharacterIndex!,
                );
                this.snackBar.open("Game events reset to defaults", "OK", {
                    duration: 3000,
                });
            }
        });
    }

    getMaterialsArray(materials: string | undefined): string[] {
        if (!materials) return [];
        return materials.split(",").map((m) => m.trim()).filter((m) =>
            m.length > 0
        );
    }

    async onMaterialsChange(selectedMaterials: string[]) {
        const materialsString = selectedMaterials.join(", ");
        await this.setCharacterProperty("react_to_material", materialsString);
    }

    async setCharacterProperty<T extends keyof Character>(
        propName: T,
        value: Character[T],
    ): Promise<void> {
        await this.characterService.setCharacterProperty(propName, value);
    }

    private categorizeEvents(
        events: Record<string, EventReactionState>,
    ): Record<string, Record<string, EventReactionState>> {
        const categorizedEvents: Record<string, Record<string, EventReactionState>> = {};

        for (
            const [category, list] of Object.entries(this.gameEventCategories)
        ) {
            categorizedEvents[category] = {};
            for (const event of list) {
                const state = (events[event] || "off") as EventReactionState;
                categorizedEvents[category][event] = state;
            }
        }
        return categorizedEvents;
    }

    filterEvents(query: string) {
        if (!this.activeCharacter) {
            this.filteredEventReactions = {};
            return;
        }

        const eventReactions = this.getVisibleEventReactions();

        if (!query && this.eventSearchQuery) {
            this.eventSearchQuery = "";
            this.filteredEventReactions = this.categorizeEvents(eventReactions);
            this.expandedSection = null;
            return;
        }
        this.eventSearchQuery = query;

        if (query.length >= 3) {
            this.filteredEventReactions = {};
            const all_reactions = this.categorizeEvents(eventReactions);
            const searchTerm = query.toLowerCase();

            for (
                const [sectionKey, events] of Object.entries(all_reactions)
            ) {
                const matchingEvents: Record<string, EventReactionState> = {};
                for (const [eventKey, value] of Object.entries(events)) {
                    if (
                        eventKey.toLowerCase().includes(searchTerm) ||
                        sectionKey.toLowerCase().includes(searchTerm)
                    ) {
                        matchingEvents[eventKey] = value;
                    }
                }
                if (Object.keys(matchingEvents).length > 0) {
                    this.filteredEventReactions[sectionKey] = matchingEvents;
                }
            }
        } else {
            this.filteredEventReactions = this.categorizeEvents(eventReactions);
        }
    }

    clearEventSearch() {
        const eventReactions = this.getVisibleEventReactions();
        this.eventSearchQuery = "";
        this.filteredEventReactions = this.categorizeEvents(eventReactions);
        this.expandedSection = null;
    }

    getCharacterProperty<T extends keyof Character>(
        propName: T,
        defaultValue: Character[T],
    ): Character[T] {
        if (!this.activeCharacter) return defaultValue;
        return this.activeCharacter[propName] ?? defaultValue;
    }

    async setCategoryState(categoryName: string, state: EventReactionState) {
        if (!this.activeCharacter) return;

        const eventsInCategory = this.gameEventCategories[categoryName] || [];

        if (this.selectedFocusProfile === "global") {
            const currentEventReactions = { ...(this.activeCharacter.event_reactions || {}) };
            for (const eventName of eventsInCategory) {
                currentEventReactions[eventName] = state;
            }

            await this.characterService.setCharacterProperty(
                "event_reactions",
                currentEventReactions,
            );
            return;
        }

        const focusReactions = this.getFocusProfileReactions(this.selectedFocusProfile);
        for (const eventName of eventsInCategory) {
            focusReactions[eventName] = state;
        }
        await this.setFocusProfileReactions(this.selectedFocusProfile, focusReactions);
    }

    getEventState(eventName: string): "on" | "off" | "hidden" {
        if (!this.activeCharacter) return "off";
        if (this.selectedFocusProfile === "global") {
            return this.activeCharacter.event_reactions?.[eventName] ?? "off";
        }
        return this.getFocusProfileReactions(this.selectedFocusProfile)[eventName]
            ?? this.activeCharacter.event_reactions?.[eventName]
            ?? "off";
    }

    getEventStateSource(eventName: string): "profile" | "global" {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return "global";
        const focusReactions = this.getFocusProfileReactions(this.selectedFocusProfile);
        return Object.prototype.hasOwnProperty.call(focusReactions, eventName) ? "profile" : "global";
    }

    getGlobalEventState(eventName: string): EventReactionState {
        if (!this.activeCharacter) return "off";
        return this.activeCharacter.event_reactions?.[eventName] ?? "off";
    }

    formatReactionState(state: EventReactionState): string {
        switch (state) {
            case "on":
                return "React";
            case "hidden":
                return "Hidden";
            case "off":
            default:
                return "See";
        }
    }

    getEventOverrideTooltip(eventName: string): string {
        if (this.getEventStateSource(eventName) === "profile") {
            return `Profile override. Global is ${this.formatReactionState(this.getGlobalEventState(eventName))}. Click reset to inherit global.`;
        }
        return `Inherited from global: ${this.formatReactionState(this.getGlobalEventState(eventName))}.`;
    }

    async clearEventOverride(eventName: string) {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return;
        const focusReactions = this.getFocusProfileReactions(this.selectedFocusProfile);
        delete focusReactions[eventName];
        await this.setFocusProfileReactions(this.selectedFocusProfile, focusReactions);
    }

    getEventIcon(state: "on" | "off" | "hidden"): string {
        switch (state) {
            case "on":
                return "volume_up";
            case "hidden":
                return "close";
            case "off":
            default:
                return "visibility";
        }
    }

    getEventDescription(eventName: string): string {
        return this.GameEventTooltips[eventName] ?? `${eventName} game event.`;
    }

    getCategoryCounts(categoryKey: string): { on: number; off: number; hidden: number } {
        const section = this.filteredEventReactions[categoryKey];
        const initial = { on: 0, off: 0, hidden: 0 };
        if (!section) return initial;

        return Object.values(section).reduce((acc, state) => {
            if (state === "on") acc.on += 1;
            else if (state === "hidden") acc.hidden += 1;
            else acc.off += 1;
            return acc;
        }, initial);
    }

    getCategoryOverrideCount(categoryKey: string): number {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return 0;
        const section = this.filteredEventReactions[categoryKey];
        if (!section) return 0;
        const focusReactions = this.getFocusProfileReactions(this.selectedFocusProfile);
        return Object.keys(section).filter((eventName) =>
            Object.prototype.hasOwnProperty.call(focusReactions, eventName)
        ).length;
    }

    getSelectedProfileOverrideCount(): number {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return 0;
        return Object.keys(this.getFocusProfileReactions(this.selectedFocusProfile)).length;
    }

    async clearCategoryOverrides(categoryKey: string) {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return;
        const eventsInCategory = this.gameEventCategories[categoryKey] || [];
        const focusReactions = this.getFocusProfileReactions(this.selectedFocusProfile);
        for (const eventName of eventsInCategory) {
            delete focusReactions[eventName];
        }
        await this.setFocusProfileReactions(this.selectedFocusProfile, focusReactions);
    }

    async resetSelectedFocusProfileOverrides() {
        if (!this.activeCharacter || this.selectedFocusProfile === "global") return;
        const profile = this.selectedFocusProfile;
        const label = this.focusProfiles.find((p) => p.value === profile)?.label ?? profile;
        const dialogRef = this.confirmationDialog.openConfirmationDialog({
            title: "Reset Focus Profile",
            message:
                `This will clear all overrides for ${label}. Events will fall back to the global defaults. Are you sure you want to continue?`,
            confirmButtonText: "Reset",
            cancelButtonText: "Cancel",
        });

        dialogRef.subscribe(async (result: boolean) => {
            if (!result || !this.activeCharacter) return;
            const next = { ...(this.activeCharacter.focus_profile_reactions || {}) };
            delete next[profile];
            await this.characterService.setCharacterProperty("focus_profile_reactions", next);
            this.filterEvents(this.eventSearchQuery);
            this.snackBar.open(`${label} overrides reset`, "OK", {
                duration: 3000,
            });
        });
    }

    onFocusProfileChange(profile: "global" | FocusProfileName) {
        this.selectedFocusProfile = profile;
        this.filterEvents(this.eventSearchQuery);
    }

    getSelectedFocusProfileDescription(): string {
        return this.focusProfiles.find((profile) => profile.value === this.selectedFocusProfile)?.description ?? "";
    }

    private getVisibleEventReactions(): Record<string, EventReactionState> {
        if (!this.activeCharacter) return {};
        if (this.selectedFocusProfile === "global") {
            return this.activeCharacter.event_reactions || {};
        }
        return {
            ...(this.activeCharacter.event_reactions || {}),
            ...this.getFocusProfileReactions(this.selectedFocusProfile),
        };
    }

    private getFocusProfileReactions(profile: FocusProfileName): Record<string, EventReactionState> {
        if (!this.activeCharacter) return {};
        return { ...(this.activeCharacter.focus_profile_reactions?.[profile] || {}) };
    }

    private async setFocusProfileEventState(
        profile: FocusProfileName,
        eventName: string,
        state: EventReactionState,
    ) {
        const focusReactions = this.getFocusProfileReactions(profile);
        focusReactions[eventName] = state;
        await this.setFocusProfileReactions(profile, focusReactions);
    }

    private async setFocusProfileReactions(
        profile: FocusProfileName,
        reactions: Record<string, EventReactionState>,
    ) {
        if (!this.activeCharacter) return;
        const next = {
            ...(this.activeCharacter.focus_profile_reactions || {}),
            [profile]: reactions,
        };
        await this.characterService.setCharacterProperty("focus_profile_reactions", next);
    }

    getCategoryAggregateState(categoryKey: string): EventReactionState | null {
        const counts = this.getCategoryCounts(categoryKey);
        const total = counts.on + counts.off + counts.hidden;
        if (total === 0) return null;
        if (counts.on === total) return "on";
        if (counts.off === total) return "off";
        if (counts.hidden === total) return "hidden";
        return null;
    }

    getImportCandidates(): Array<{ index: number; name: string }> {
        const candidates: Array<{ index: number; name: string }> = [];
        this.characterList.forEach((c, idx) => {
            if (idx !== this.activeCharacterIndex) {
                candidates.push({ index: idx, name: c.name || `Character ${idx + 1}` });
            }
        });
        return candidates;
    }

    startImportSelection() {
        this.showImportSelector = true;
        this.selectedImportIndex = null;
    }

    cancelImportSelection() {
        this.showImportSelector = false;
        this.selectedImportIndex = null;
    }

    async performImportFromCharacter() {
        if (this.selectedImportIndex === null) return;
        const source = this.characterList[this.selectedImportIndex];
        if (!source || !source.event_reactions) return;

        await this.characterService.setCharacterProperty(
            "event_reactions",
            { ...source.event_reactions },
        );

        this.snackBar.open("Event reactions imported from selected character", "OK", {
            duration: 3000,
        });

        this.cancelImportSelection();
    }
}
