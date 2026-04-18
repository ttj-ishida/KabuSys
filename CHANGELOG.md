# Changelog

すべての notable な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。  

このプロジェクトはセマンティックバージョニングを採用します。

なお、本 CHANGELOG はコードベースから推測して作成しています（自動生成ではありません）。実装の意図・既定値・挙動などを説明的にまとめています。

## [Unreleased]
- 今後のリリースに向けた未確定の変更点をここに記載します。

## [0.1.0] - 2026-04-18

### Added
- 基本機能
  - KabuSys 自動売買システムの初期実装を追加。
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - プロセス優先度を高く設定する処理をサポート（utils.process_priority.set_process_priority を呼び出す）。
    - KABUSYS_ENV によって paper_trading 時は専用の SQLite DB（デフォルト: data/paper_trading.db）を使用する。
    - BrokerClientFactory によるブローカークライアント生成を行い、ExecutionEngine を起動する。
    - ExecutionEngine をデーモンスレッドで実行し、data/stop_requested.flag を検知して終了処理を行う。
    - PID 管理（data/execution.pid）に対応。

  - 監視ポーリング起動スクリプト `run_monitoring.py` を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path（デフォルト: data/monitoring.db）を参照して初期化する。
    - stop フラグ検知でループを終了し、例外発生時もログに残して次のポーリングへ回復する設計。

- 設定管理・CLI
  - `config.py`：.env 自動読み込み（プロジェクトルート検出）、環境変数のラッパー Settings クラスを提供。
    - 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 設定 / 監視閾値 / ログ等）。
    - PAPER_FILL_MODE（paper trading の fill 動作）や PAPER_TRADING_SQLITE_PATH をサポート。
    - env 値検証（KABUSYS_ENV や LOG_LEVEL など）を行う。
  - `config_setup.py`：.env を対話式に作成・更新するウィザードを追加。
    - 複数設定項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL 等）を対話的に入力可能。
    - .env ファイルに保存する機能と既存値の読み込みを提供。
  - `validate_config.py`：設定検証 CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の値検証、DB パスの親ディレクトリチェック、config/*.yaml の存在と（PyYAML があれば）パース検証を行う。
    - --strict オプションで警告もエラー扱いにできる。

- ロギング / プロセスユーティリティ
  - `utils/logging_setup.py`
    - 統一ロギング設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）をルートロガーに設定。
    - ログディレクトリ自動作成、失敗時のフォールバック（コンソールのみ）をサポート。
  - `utils/process_priority.py`
    - プロセス優先度設定（Windows / POSIX を吸収）を追加。
    - CPU affinity を最初の N コアに固定するユーティリティも提供。
    - アクセス権限不足などの例外は警告ログで安全に無視する。

- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定（score 降順、signal_rank によるタイブレーク）、等重配分、スコア重み配分を提供。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）を実装。既存保有のセクターエクスポージャを算出し、上限超過セクターの新規候補を除外する。
    - レジームに基づく投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear マッピングを提供、未知のレジームは 1.0 にフォールバック）。
  - `portfolio/position_sizing.py`
    - 発注株数計算ロジックを実装（allocation_method: risk_based / equal / score）。
    - lot_size（単元株）で丸め、max_position_pct、max_utilization、cost_buffer（スリッページ・手数料見積）を考慮した aggregate cap スケーリングを実装。
    - risk_based の場合は risk_pct と stop_loss_pct を使ったポジションサイズ算出。

- 研究用ファクター計算（断片的実装）
  - `research/factor_research.py`：DuckDB を使ったファクター計算モジュールを追加（モメンタム等の計算を行う設計）。（ファイル末尾が切れているため実装継続が想定される。）

- ツール
  - `tools/paper_verification_report.py`
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し、PASS/FAIL 判定（閾値はソース内で定義）を行う。
    - コマンドライン引数で期間指定（--from/--to）と DB パス（--db）を受け取る。

- DB 周り
  - duckdb のサポート（duckdb.connect を使用）。
  - 監視テーブルの初期化関数 init_monitoring_db を呼び出して冪等に監視テーブルを保証（実装箇所は monitoring/monitoring_db モジュールに存在）。

### Changed
- logging の挙動とデフォルト
  - ログは stdout に出力するように設計（stderr ではない）。cron / タスクスケジューラ実行時のリダイレクトを意識した仕様。

- 環境ファイルの読み込みロジック
  - .env のパースは export KEY=val 形式やクォート内のエスケープ対応を行う仕様に改良。
  - 自動ロード時の優先順位は OS 環境変数 > .env.local > .env（.env.local は override=true）。

### Fixed
- 不正な環境変数値への耐性強化
  - MONITOR_POLL_INTERVAL が不正（0 や負値や非数）の場合に警告を出しデフォルトにフォールバックするよう修正。
  - PAPER_FILL_MODE の値検証を追加し、不正値時は ValueError を発生させるように（有効値: instant/partial/never/reject）。
  - KABUSYS_ENV / LOG_LEVEL の不正値検出と明示的なエラー・警告出力を追加。

### Notes / Migration
- .env ファイルは絶対に Git にコミットしないでください（config_setup のヘッダにも注記あり）。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config による注意喚起が行われます。
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（デフォルト: data/monitoring.db）を使用するため、本番データ取り扱いに注意してください。
- Paper Trading はデータベースを完全に分離（デフォルト: data/paper_trading.db）しているため、テスト用に paper_trading モードを利用可能です。

---

以上が本コードベースから推測して作成した初回リリース向け CHANGELOG です。必要であればリリースノートの文言調整（より詳細な API/関数仕様、既知の制限、TODO など）を追記します。