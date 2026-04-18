# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]


## [0.1.0] - 2026-04-18
初回リリース

### Added
- 基本アプリケーション構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を追加。
- 設定管理
  - 環境変数 / .env 自動ロード機能を実装（`kabusys.config`）。
    - プロジェクトルートを `.git` または `pyproject.toml` から特定して .env を読み込む。
    - `.env` / `.env.local` の読み込み順をサポート。OS 環境変数を保護するための上書き制御あり。
    - 複数の .env フォーマット（`export KEY=val` / クォート / インラインコメント）に対応するパーサを実装。
  - 設定ラッパー `Settings` を提供。J-Quants / kabu API / DB パス / 監視閾値など主要設定をプロパティ経由で取得可能。
  - Paper Trading 用設定（`paper_sqlite_path`、`paper_fill_mode`）と環境モード判定（development/paper_trading/live）を導入。
- 対話式環境設定ウィザード
  - `kabusys.config_setup` により `.env` の初期作成・更新を対話的に行う CLI を追加。
  - デフォルト値・選択肢表示・シークレット入力・既存値再利用機能をサポート。
- 設定検証 CLI
  - `kabusys.validate_config` により、起動前に必須環境変数・DB パス・config/*.yaml 等の妥当性を検証するツールを追加。
  - `--strict` オプションで警告を失敗として扱うモードをサポート。
  - PyYAML 未インストール時は YAML 検証をスキップして警告を出す挙動を実装。
- 起動スクリプト
  - 監視プロセス起動: `kabusys.run_monitoring`
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 常に本番用の sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）検出、KeyboardInterrupt への対応、DuckDB/SQLite のクローズ処理を実装。
  - 実行エンジン起動: `kabusys.run_execution`
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite を使用して本番 DB と分離。
    - Broker クライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 等の組み立て、デーモン スレッドでの実行制御を実装。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし既に停止要求がある場合は起動を回避。
    - 実行中に停止フラグ検出で安全に engine.stop() を呼び出す仕組みを実装。
- ロギング・ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と日次ローテート（TimedRotatingFileHandler, 30日保持）をルートロガーに設定。
    - `LOG_DIR` / `LOG_LEVEL` 環境変数と引数による上書きをサポート。
    - ログディレクトリ作成失敗時はファイル出力を無効にしてコンソール出力のみ継続。
- プロセス優先度ユーティリティ
  - `kabusys.utils.process_priority.set_process_priority` と `set_cpu_affinity` を実装。
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。
    - アクセス権限不足などで失敗した場合は警告を出してスキップ。
- Portfolio 構成モジュール（純粋関数群）
  - 候補選定・重み計算: `kabusys.portfolio.portfolio_builder`
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を実装。
  - セクター制限・レジーム乗数: `kabusys.portfolio.risk_adjustment`
    - `apply_sector_cap`（既存保有比率に基づく候補除外）
    - `calc_regime_multiplier`（"bull"/"neutral"/"bear" マッピング）を実装。
  - ポジションサイジング: `kabusys.portfolio.position_sizing`
    - `calc_position_sizes` を実装。risk_based / equal / score 向けの株数計算、lot_size 単位丸め、aggregate cap のスケーリングロジック、cost_buffer を考慮した保守的見積りなどをサポート。
- 研究（リサーチ）モジュール
  - `kabusys.research.factor_research` におけるモメンタム等ファクター計算の下地を追加（DuckDB 参照想定、パラメータ定義あり）。
- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`
    - ペーパートレード SQLite（`PAPER_TRADING_SQLITE_PATH`）からシステム稼働率・注文成功率・送信率・レイテンシ等を集計し、PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、欠損テーブルに対するフォールバック処理を実装。
- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db`（monitoring パッケージ内）を起動スクリプトから呼び出し、監視用テーブルの存在を冪等に保証。

### Changed
- N/A（初回リリースのため過去変更なし）

### Fixed
- N/A（初回リリースのため過去修正なし）

### Notes / Implementation details
- Paper Trading と本番 DB は明確に分離される設計（config の `is_paper` 判定により sqlite パスを切り替え）。
- `.env` の自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途のため）。
- `apply_sector_cap` はセクターが "unknown" の場合セクター上限の対象外とする挙動を採用（欠損データ時に不要に除外しないため）。
- Logging は stdout を使用する設計（cron / タスクスケジューラ等でのリダイレクト運用を想定）。
- `position_sizing.calc_position_sizes` は将来的な拡張（銘柄別 lot_size 等）を考慮したコメント・ TODO を含む。

<!--
参考: Keep a Changelog 形式に準拠。
必要に応じて今後の変更（バグ修正・機能追加）を Unreleased セクションに追加してください。
-->