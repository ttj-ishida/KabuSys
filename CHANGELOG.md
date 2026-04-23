# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-23

初回リリース — KabuSys 基盤機能を実装しました。主な追加内容は以下の通りです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` に設定。

- 実行エントリ／ランナー
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計。
    - 停止制御はプロジェクト内 `data/stop_requested.flag` ファイルで行う。
    - duckdb / sqlite 接続の初期化とクローズを実装。
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合はペーパートレード用 SQLite（`data/paper_trading.db` または環境変数で上書き）を使用し、本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Paper と Live を切り替え）。
    - 実行エンジンはデーモンスレッドで実行、停止フラグ検知時に安全停止。
    - 実行用 PID ファイルのサポート。

- 環境設定／検証用ユーティリティ
  - config.py: 環境変数管理クラス `Settings` を実装。
    - .env 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。`.env` → `.env.local` の優先度。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロード無効化が可能。
    - 必須環境変数取得用 `_require()`、各種パス／フラグ／閾値プロパティ（duckdb/sqlite パス、PID/kill flag、閾値など）を提供。
    - Paper トレード用設定（`PAPER_FILL_MODE`）と専用 DB パス（`PAPER_TRADING_SQLITE_PATH`）をサポート。無効値検出で例外を送出。
  - config_setup.py: 対話式 .env 作成・更新ウィザードを実装。
    - シークレット入力のマスク、既存 .env の読み込み、確認後に .env を安全に書き込む。
  - validate_config.py: 設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ロギングレベル、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在／パース検証（PyYAML 未インストール時は警告）。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番（live）向けの追加ガード（LINE 通知設定の未設定や Kill Flag 自動クリア設定の警告）。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティ。
    - stdout StreamHandler と日次ローテート（TimedRotatingFileHandler）をルートロガーにセット。
    - ログディレクトリ自動作成（失敗時はファイル出力を無効化してコンソール出力のみ継続）。
    - ログレベル・ログディレクトリの解決順を実装。
  - utils/process_priority.py: プロセス優先度（および CPU affinity）設定ユーティリティ。
    - Windows と POSIX 系（Linux/Mac/FreeBSD）を吸収して `set_process_priority(level)` を提供（"high"/"normal"/"low"）。
    - `set_cpu_affinity(cpu_count)` によるコア固定機能。
    - 権限不足など失敗時は警告ログでスキップする安全設計。

- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 select_candidates（スコア昇順・タイブレークルール）と重み計算 calc_equal_weights / calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮、売却予定は除外、"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（"bull"=1.0/ "neutral"=0.7/ "bear"=0.3）。未知レジームは警告の上 1.0 にフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数計算（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超過した場合のスケールダウン）や cost_buffer を用いた保守的コスト見積り、余り配分ロジックを実装。

- Paper Trading 検証レポート
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite の集計レポートを生成する CLI を追加。
    - システム安定性（稼働率・エラー数）、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（平均/最大/P95）を算出。
    - パス／レポート期間の指定オプション（--from/--to/--db）をサポート。
    - 判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を実装。

- データベース連携
  - sqlite3 と DuckDB の両方を利用する設計を採用（monitoring と execution の両起動スクリプトで接続・初期化・クローズを行う）。
  - 監視テーブル初期化のための init_monitoring_db 関数（モジュールから利用）。

- 研究／ファクター計算基盤
  - research/factor_research.py（ファクター計算の骨子）
    - モメンタム／MA／ATR／流動性等、StrategyModel に基づくファクター設計を開始。
    - DuckDB 接続を受け取る設計、モメンタム計算のための定数とインターフェースを定義（実装の継続を想定）。

### Changed
- （実装フェーズのため、既存機能の仕様変更はなし。各モジュールは新規追加として提供。）

### Fixed
- 環境変数パースの堅牢化（config._parse_env_line）
  - export 形式のサポート、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱い、コメント判定ルールの明確化。

### Security
- .env の扱いについて明記（config_setup にて .env を生成する際は Git にコミットしない旨の注意を追加）。

### Known limitations / Notes
- research/factor_research.py はモメンタム計算などの骨組みが含まれますが（ファイル末尾が途中で切れているため）一部関数は実装継続を要します。
- position_sizing の lot_size は現状固定（全銘柄共通）であり、将来的に銘柄ごとの単元対応を検討する旨の TODO コメントあり。
- process_priority / cpu_affinity は権限や OS に依存するため、失敗時はスキップして warning を出す設計です。
- monitoring は設計上「環境にかかわらず本番 sqlite_path を使用」するため、運用時は意図した DB パス設定に注意してください。

---

今後の予定（例）
- factor_research の完全実装（Momentum / Volatility / Value / Liquidity の完成）
- ExecutionEngine / BrokerClient の統合テスト、Paper 実行系のエンドツーエンド検証
- 銘柄毎 lot_size のサポート、スリッページ/手数料モデルの拡張

（詳細な変更点やチケットはリポジトリのコミット履歴を参照してください。）