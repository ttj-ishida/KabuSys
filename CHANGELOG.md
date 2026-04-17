# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]

## [0.1.0] - 2026-04-17

### Added
- パッケージ初期実装を追加。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 実行・監視用エントリポイントスクリプトを追加。
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - 起動時にプロセス優先度を "high" に設定（`utils.process_priority.set_process_priority` を使用）。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合はペーパートレード専用 SQLite（`PAPER_TRADING_SQLITE_PATH` / デフォルト `data/paper_trading.db`）を使用して本番 DB と完全分離。
    - BrokerClientFactory により実行環境に応じたブローカークライアントを生成（モック/実ブローカー分岐）。
    - エンジンは別スレッドで起動し、プロジェクトルートの `data/stop_requested.flag` を検知すると安全に停止。
    - PID ファイル (`data/execution.pid`) をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトにフォールバックし、警告ログを出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用（監視データは本番 DB を想定）。

- 設定管理・支援ツールを追加。
  - config.py
    - 環境変数と .env の自動読み込みロジック（プロジェクトルートは `.git` または `pyproject.toml` を基準に特定）。
    - 複数の設定プロパティを提供（J-Quants, kabuAPI, DB パス, モニタ閾値など）。
    - `.env` の自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - `PAPER_FILL_MODE` など一部キーのバリデーション実装（許容値以外は例外）。
    - `Settings` クラスと `settings` シングルトンを提供。

  - config_setup.py
    - 対話式ウィザードで `.env` を初期作成・更新する CLI。
    - シークレット項目は入力時にマスク表示、保存テンプレートを生成。
    - 既存 `.env` の読み込みと Enter による再利用をサポート。

  - validate_config.py
    - 起動前に環境変数・config/*.yaml の妥当性を検査する CLI。
    - 必須/任意の環境変数チェック、KABUSYS_ENV・LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 利用）。
    - `--strict` オプションで警告も失敗扱いにできる。

- ポートフォリオ構築関連の純粋関数群（DB 参照なし）を追加。
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、売却予定銘柄は除外）。"unknown" セクターは上限除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームはフォールバックで 1.0）。
  - portfolio.position_sizing
    - calc_position_sizes: リスクベース / equal / score の割当方式に対応。単元株（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、コストバッファ反映、残差に基づく追加配分ロジックを実装。

- ユーティリティを追加。
  - utils.process_priority
    - Windows と POSIX の差を吸収してプロセス優先度を設定（high/normal/low）。
    - CPU affinity を最初の N コアに固定する機能を提供（権限や非対応 OS では警告ログを出力してスキップ）。

- リサーチ（ファクター計算）モジュールを追加（部分実装）。
  - research.factor_research
    - DuckDB 接続を受け取り、Momentum（1m/3m/6m、MA200乖離）や Volatility（ATR 等）を計算する関数を提供。
    - prices_daily / raw_financials テーブルを参照し、営業日ベースのウィンドウ計算を行う設計。

- ペーパートレード検証用ツールを追加。
  - tools.paper_verification_report
    - 指定期間の paper_trading SQLite DB を解析して検証レポートを生成。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ など。
    - 基準値（閾値）を定義して PASS/FAIL を判定。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。

- DB 初期化ユーティリティを起動箇所で呼び出し（冪等な監視テーブル初期化）。
  - run_execution/run_monitoring から `monitoring_db.init_monitoring_db` を呼び出し、監視テーブルが存在することを保証。

### Changed
- （初回リリースのため履歴なし）

### Fixed
- MONITOR_POLL_INTERVAL に不正な値が設定された場合、time.sleep に渡してエラーにならないようフォールバック処理と警告ログを追加（run_monitoring）。

### Notes / Migration
- .env の自動読み込みはデフォルトで有効。テストなどで自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper Trading を実行する際は、`KABUSYS_ENV=paper_trading` を設定すると専用 DB（`PAPER_TRADING_SQLITE_PATH`）が使用されるため、本番データと分離されます。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG の設定に注意してください。`validate_config` の `--strict` モードで事前チェックを推奨します。

### Security
- シークレット系環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は .env に平文で保存されるため、`.env` をリポジトリにコミットしないよう注意喚起をドキュメントに記載済み（config_setup の出力ヘッダ参照）。

---

今後のリリースでは、ExecutionEngine / SystemMonitor 本体やブローカークライアント実装、テストカバレッジ、エラーハンドリング強化、その他ドキュメントの追加を予定しています。