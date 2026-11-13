export function migrateOverlayConfig(config) {
  const mode = config.overlay_mode;
  return {...config,overlay_mode:mode === 'both' ? 'vr' : ['standalone','screen'].includes(mode) ? 'desktop' :
    ['disabled','desktop','vr'].includes(mode) ? mode : 'desktop',
  overlay_obs_enabled:config.overlay_obs_enabled ?? mode === 'both',overlay_obs_port:config.overlay_obs_port ?? 4049};
}
