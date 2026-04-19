# CHANGELOG

All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠します。  

---

## [0.1.0] - 2026-04-19

### Added
- 基本アプリケーションパッケージ `kabusys` を追加（バージョン 0.1.0）。
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 `sqlite_path` を使用。
    - プロジェクトルート配下の `data/stop_requested.flag` を監視して停止する仕組みを実装。
    - duckdb 接続を併用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は専用の paper DB（`data/paper_trading.db` がデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory により本番/モックのブローカークライアントを生成。
    - 停止フラグと PID ファイルによる制御。
- 設定周り
  - config.py: 環境変数／.env の読み込み・ラッパー `Settings` を追加。
    - プロジェクトルート自動検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み（`.env` → `.env.local`、OS 環境変数は保護）。
    - .env の行パーサを実装（`export` プレフィックス、クォート／バックスラッシュエスケープ、コメント処理に対応）。
    - 各種プロパティを追加（J-Quants / kabu API / DuckDB/SQLite パス / paper_trading 用設定 / 監視閾値 / ログ等）。
    - `paper_fill_mode` のバリデーション（有効値チェック）。
- 設定ユーティリティ CLI
  - config_setup.py: 対話式 .env ウィザードを追加（.env の初期作成・更新を支援）。
  - validate_config.py: 設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV 検証、DB パス/ファイル存在確認、YAML パース検証、live 環境向け追加ガード）。
    - `--strict` オプションで警告も失敗扱いにできる。
- ポートフォリオ構築（pure functions）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコアで選別。
    - calc_equal_weights, calc_score_weights: 等配分・スコア加重の重み計算（スコア全て 0 の場合はフォールバックして等配分）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score に対応した株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を考慮した保守的見積り、残余の再配分アルゴリズムを実装。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有を基に上限超過セクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数を実装（bull/neutral/bear、未知レジームは 1.0 でフォールバック）。
- ユーティリティ
  - utils/logging_setup.py: ルートロガーの統一セットアップを追加（stdout StreamHandler + 日次ローテートファイルハンドラ、ログディレクトリ自動作成とフォールバック）。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加（Windows / POSIX の差分吸収、失敗時は警告を出してスキップ）。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを集計して PASS/FAIL 判定を行う。
    - デフォルト DB パスは `data/paper_trading.db`。コマンドライン引数で期間・DB を指定可。
    - P95 計算ユーティリティと閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。

### Changed
- ルーティングや API 実装変更などは本リリースではなし（初期リリース）。

### Fixed
- config の自動ロードは OS 環境変数を保護する仕組みを導入（.env.local が OS 環境を誤って上書きしないよう保護）。
- logging_setup: 既存ハンドラがある場合は一度 flush/close してから再設定することで二重登録を回避。

### Security
- .env ファイルの取り扱いに関する注意書きを config_setup の生成ファイルに明記（.env を絶対に Git にコミットしない旨）。

---

未記載の内部実装詳細や将来の変更点はリリースノートに逐次追加予定です。