# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
ソフトウェアはセマンティックバージョニングに従います。

## [Unreleased]


## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初回リリース。
- 実行/監視用のエントリポイントを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading の分離、専用 SQLite を使用、停止フラグ / pid ファイル管理）。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL によるポーリング間隔上書き、停止フラグ検知）。
- 環境設定管理:
  - config.py — Settings クラス、.env 自動読み込み（.env / .env.local）、環境変数の取得・バリデーション、デフォルトパスの定義（DUCKDB_PATH, SQLITE_PATH など）。
  - config_setup.py — 対話式 .env ウィザード（.env の初期作成・更新を支援）。
  - validate_config.py — 起動前設定検証 CLI（必須環境変数、KABUSYS_ENV の妥当性、パス存在チェック、config/*.yaml の存在／パース確認、ライブ環境向けガード）。
- Paper Trading 向けツール:
  - tools/paper_verification_report.py — ペーパートレード検証レポート生成スクリプト（稼働率、注文成功率、送信率、レイテンシ(P95)等の集計と PASS/FAIL 判定）。
- ポートフォリオ構築関連（純粋関数群、DB 参照なし）:
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights（スコア正規化／等分配など）。
  - portfolio.position_sizing: calc_position_sizes（risk_based / equal / score の各配分方式、単元株丸め、aggregate cap によるスケール調整、cost_buffer を考慮した保守的見積り）。
  - portfolio.risk_adjustment: apply_sector_cap（セクター集中制限）、calc_regime_multiplier（市場レジーム乗数）。
- リサーチ（ファクター計算）:
  - research.factor_research: モメンタム／ボラティリティ等のファクター計算関数（calc_momentum, calc_volatility 等）。DuckDB 接続を受け取り prices_daily テーブルを参照して計算する設計。
- ユーティリティ:
  - utils.process_priority: set_process_priority / set_cpu_affinity（Windows / POSIX の差を吸収しプロセス優先度と CPU affinity を設定、失敗時は警告ログで安全にフォールバック）。
- パッケージ初期化:
  - __init__.py にバージョン情報 __version__ = "0.1.0" を追加。

### Changed
- （初回リリースのため特になし）

### Fixed / Improved
- .env パーサの改善（config._parse_env_line）:
  - export プレフィックス対応（export KEY=val）。
  - シングル/ダブルクォート内でのバックスラッシュエスケープ処理をサポートし、適切にクォート閉じを検出。
  - クォートなし値に対するインラインコメント解析（直前が空白／タブの場合に # をコメントとみなす）を実装。
  - .env 読み込みロジックで OS 環境変数を保護する protected オプションを導入（.env.local は上書き可能だが OS 環境変数は守る）。
- run_monitoring / run_execution:
  - 停止フラグ（data/stop_requested.flag）による安全停止の実装。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する挙動を明示。
  - ExecutionEngine は paper_trading 環境時に paper_sqlite_path を使用して本番 DB と切り離し。
- position_sizing のロジック改善:
  - 単元株（lot_size）での丸め処理、per-position 上限、aggregate cap によるスケールダウン、残差（fractional remainder）に基づく優先配分を実装。
  - price が欠損（0 または None）の場合はスキップして安全に処理。
- risk_adjustment の挙動:
  - apply_sector_cap: "unknown" セクターは上限適用対象外とする仕様を明示。
  - calc_regime_multiplier: 未知レジームでのフォールバック（1.0）と警告ログの追加。
- process_priority と affinity は権限不足やプラットフォーム未サポート時に例外を捕捉して警告にフォールバックするように安全化。

### Notes / Known limitations
- Portfolio / position_sizing:
  - price が欠損（0.0）だとエクスポージャーや target_shares の算出が不正確になる旨を TODO コメントで残しています。将来的に前日終値や取得原価でのフォールバックを検討。
  - lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map を受け取る拡張を想定。
- research.factor_research の volatility 関数は内部で長めのスキャン範囲・NULL 制御を行う設計になっており、利用時は prices_daily テーブルの品質に依存します。
- tools/paper_verification_report の判定基準（稼働率 99% 等）はハードコードされています。運用要件に応じて調整してください。
- set_process_priority や set_cpu_affinity は環境によっては権限不足（Linux の nice を下げる等）で失敗するため、その場合はログ警告が出て設定はスキップされます。

### Security
- （初回リリースのため特になし）

---

開発者向け補足:
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化できます（テスト時に便利）。
- validate_config は PyYAML が未インストールでも実行可能ですが、YAML 検証はスキップされ警告が出ます。