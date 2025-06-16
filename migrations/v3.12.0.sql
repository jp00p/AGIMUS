INSERT INTO crystal_types (name, rarity_rank, icon, effect, description) VALUES
-- Common
("Palladium", 1, "palladium.png", "white_tint", "A gleaming white metal used in isolinear relays. Cool to the touch."),
("Boronite", 1, "boronite.png", "cerulean_tint", "Rare ore use in molecule synthesis. High-energy potential."),
("Ryetalyn", 1, "ryetalyn.png", "crimson_purple_gradient", "The only known cure for Rigelian fever. Got a fever.. and the only cure is, Ryetalyn."),
("Gallicite", 1, "gallicite.png", "teal_yellow_gradient", "Electrically reactive mineral, might be useful for shielding."),
("Topaline", 1, "topaline.png", "blue_gold_gradient", "Found in abundance on Capella IV. Can be used to disrupt sens-oars."),
("Zenite", 1, "zenite.png", "purple_silver_gradient", "Extracted from Ardana. Careful around the gas, might cause brain rot."),
("High Quality Copper", 1, "high_quality_copper.png", "hq_copper", "Only the finest copper from Ur. No complaints here!"),
-- Uncommon
("M.T.D.", 2, "mtd.png", "mirror_mirror", "Multi-dimensional Transporter Device. Something to reflect upon..."),
("Neutronium Soup", 2, "neutronium_soup.png", "neutral_glow", "This is heavy Doc! So dense that even light hesitates to leave it."),
("Hexaferrite", 2, "hexaferrite.png", "cyan_hex_glow", "Crystalline iron with strong magnetic resonance. Hex marks the spot."),
-- Rare
("Sector 001 Beacon", 3, "sector_001_beacon.png", "earth_orbit", "Emits homing signal for Sol-bound ships. Launch a buoy when ready."),
("Transwarp Circuit", 3, "transwarp_circuit.png", "transwarp_streaks", "Borg-Tech for Transwarp Conduits. I'm sure nothing will go wrong."),
("Denorios Plasma", 3, "denorios_plasma.png", "wormhole_interior", "Raw plasma from near Bajor. Might cause visions."),
-- Legendary
('Fluidic Droplet', 4, 'fluidic_droplet.png', 'fluidic_ripple', "An itty bit of Fluidic Space. Ripples through local reality."),
('Inertial Compensator', 4, 'inertial_compensator.png', 'spin_tumble', "Provides stabilization at high warp. Looks a bit damaged though..."),
('Disruptor Coil', 4, 'disruptor_coil.png', 'disruptor_burn', "Rapidly burns and destabilizes molecular cohesion. Looks painful!"),
-- Mythic
('Photon Torpedo Core', 5, 'photon_torpedo_core.png', 'big_banger', "Matter/Anti-Matter in a Magno-Photon Field. Wall to wall bangers!"),
('Continuum Essence', 5, 'continuum_essence.png', 'q_snap', "Transcends human comprehension. Oh snap!"),
-- Unobtanium
('Anaphasic Flame', 6, 'anaphasic_flame.png', 'horny_smoke', "Housed in a curious-looking candle holder. It's beeaaauuutiful!");

ALTER TABLE badge_tags MODIFY COLUMN tag_name VARCHAR(47) NOT NULL;

CREATE TABLE IF NOT EXISTS wishlist_match_opt_outs (
  user_discord_id VARCHAR(64) NOT NULL,
  prestige_level   INT NOT NULL,
  PRIMARY KEY (user_discord_id, prestige_level),
  FOREIGN KEY (user_discord_id)
    REFERENCES users(discord_id)
    ON DELETE CASCADE
);