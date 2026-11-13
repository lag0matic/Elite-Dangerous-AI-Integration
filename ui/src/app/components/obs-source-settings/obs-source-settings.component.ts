import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { TauriService } from '../../services/tauri.service';

@Component({selector:'app-obs-source-settings',standalone:true,
  imports:[FormsModule,MatSlideToggleModule,MatFormFieldModule,MatInputModule,MatButtonModule,MatIconModule,MatTooltipModule],
  template:`
    <div class="obs-row">
      <mat-slide-toggle [ngModel]="state.enabled" (ngModelChange)="setEnabled($event)" [disabled]="busy">OBS Browser Source</mat-slide-toggle>
      <span>1920 × 1080</span>
      <mat-form-field class="port"><mat-label>Port</mat-label><input matInput type="number" min="1024" max="65535"
        [(ngModel)]="port" (focus)="editingPort=true" (blur)="editingPort=false;apply()" [disabled]="busy"></mat-form-field>
    </div>
    @if (state.url) {
      <div class="obs-row"><mat-form-field class="url"><mat-label>Browser Source URL</mat-label>
        <input matInput readonly [value]="state.url" aria-label="OBS Browser Source URL"></mat-form-field>
        <button mat-icon-button type="button" matTooltip="Copy source URL" aria-label="Copy OBS source URL" (click)="copy()"><mat-icon>content_copy</mat-icon></button>
      </div>
    }
    @if (error || state.error) {<p class="error" role="alert">{{ error || state.error }}</p>}
  `,
  styles:[`:host{display:block;border-top:1px solid #555;margin-top:16px;padding-top:16px}
    .obs-row{display:flex;align-items:center;gap:16px;flex-wrap:wrap;min-width:0}
    .port{width:110px}.url{flex:1;min-width:180px}.error{color:#ff8a80;margin:4px 0 12px}
    input{letter-spacing:0}`]
})
export class ObsSourceSettingsComponent implements OnInit,OnDestroy {
  state: {enabled:boolean;url?:string|null;error?:string|null;port?:number} = {enabled:false};
  port=4049; busy=false; editingPort=false; error=''; private timer?:ReturnType<typeof setInterval>; private destroyed=false;
  constructor(private tauri:TauriService) {}
  ngOnInit() {void this.refresh();this.timer=setInterval(() => {if(!this.busy)void this.refresh();},1500);}
  ngOnDestroy() {this.destroyed=true;if(this.timer)clearInterval(this.timer);}
  private async refresh() {
    try {const state=await this.tauri.getObsSourceState();if(state&&!this.destroyed){this.state=state;if(!this.editingPort)this.port=state.port;}}
    catch(e){this.error=String(e);}
  }
  async setEnabled(enabled:boolean) {this.state={...this.state,enabled};await this.apply();}
  async apply() {
    if(!Number.isInteger(this.port)||this.port<1024||this.port>65535){this.error='Port must be between 1024 and 65535.';return;}
    this.busy=true;this.error='';
    try {this.state=await this.tauri.configureObsSource(this.state.enabled,this.port);}
    catch(e){this.error=String(e);}finally{this.busy=false;}
  }
  async copy() {await this.tauri.copyObsSourceUrl();}
}
