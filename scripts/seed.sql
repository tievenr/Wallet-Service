-- Seed data for asset types
INSERT INTO asset_types (code, display_name, is_active) VALUES
('COIN', 'Gold Coins', 1),
('GEM', 'Premium Gems', 1),
('GOLD', 'Gold Bars', 1);

-- System wallets for COIN (asset_type_id = 1)
INSERT INTO wallets (user_id, asset_type_id, balance, is_system_wallet, system_wallet_type) VALUES
(-1, 1, 1000000.00000000, 1, 'TREASURY'),
(-2, 1, 1000000.00000000, 1, 'MARKETING'),
(-3, 1, 0.00000000, 1, 'REVENUE');

-- System wallets for GEM (asset_type_id = 2)
INSERT INTO wallets (user_id, asset_type_id, balance, is_system_wallet, system_wallet_type) VALUES
(-1, 2, 1000000.00000000, 1, 'TREASURY'),
(-2, 2, 1000000.00000000, 1, 'MARKETING'),
(-3, 2, 0.00000000, 1, 'REVENUE');

-- System wallets for GOLD (asset_type_id = 3)
INSERT INTO wallets (user_id, asset_type_id, balance, is_system_wallet, system_wallet_type) VALUES
(-1, 3, 1000000.00000000, 1, 'TREASURY'),
(-2, 3, 1000000.00000000, 1, 'MARKETING'),
(-3, 3, 0.00000000, 1, 'REVENUE');

-- Test user wallets
INSERT INTO wallets (user_id, asset_type_id, balance, is_system_wallet) VALUES
(1, 1, 100.00000000, 0),
(1, 2, 50.00000000, 0),
(2, 1, 200.00000000, 0);