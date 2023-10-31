-- Ce programme est régi par la licence CeCILL soumise au droit français et
-- respectant les principes de diffusion des logiciels libres. Vous pouvez
-- utiliser, modifier et/ou redistribuer ce programme sous les conditions
-- de la licence CeCILL diffusée sur le site "http://www.cecill.info".

CREATE TABLE IF NOT EXISTS `wormholes` (
  `id` INTEGER PRIMARY KEY AUTOINCREMENT,
  `name` TEXT NOT NULL,
  `sync_threads` BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX IF NOT EXISTS idx_wormholes ON `wormholes` (`id`);

CREATE TABLE IF NOT EXISTS `wormhole_admins` (
  `wormhole_id` TEXT NOT NULL,
  `user_id` BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wormhole_admins ON `wormhole_admins` (`wormhole_id`);

CREATE TABLE IF NOT EXISTS `wormhole_channels` (
    `wormhole_id` TEXT NOT NULL,
    `channel_id` BIGINT NOT NULL,
    `can_read` BIGINT NOT NULL DEFAULT true,
    `can_write` BIGINT NOT NULL DEFAULT true,
    `webhook_id` BIGINT NOT NULL,
    `webhook_token` TEXT NOT NULL,
    `webhook_name` TEXT NOT NULL DEFAULT '{user}',
    `webhook_avatar` TEXT NOT NULL DEFAULT 'user'
);
CREATE INDEX IF NOT EXISTS idx_wormhole_channels ON `wormhole_channels` (`wormhole_id`);
