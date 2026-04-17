# Changelog

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
このファイルはコードベースから推測される変更点・機能群を基に作成しています。

## [Unreleased]

### Added
- 全体
  - パッケージ初期リリース相当の機能群を追加。
  - バージョンは `kabusys.__version__ = "0.1.0"`。

- 実行用スクリプト
  - run_execution.py: 実運用／ペーパートレーディング用の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV に応じて Paper Trading を分離（Paper Trading 時は専用 SQLite DB を使用）。
    - 起動前に停止フラグ（data/stop_requested.flag）をチェックし、既に立っていれば起動をスキップする処理を実装。
    - エンジンは別スレッドで起動し、停止フラグ検知時に engine.stop() で安全終了を試みる。
    - エンジンの PID を data/execution.pid に書く（設定可能）。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値は警告を出してデフォルトにフォールバック。
    - 監視は KABUSYS_ENV にかかわらず本番の `sqlite_path` を使用して起動（意図的な設計）。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。

- 設定・環境変数管理
  - config.py: 強化された .env ファイルパーサと自動読み込みロジックを追加。
    - .env/.env.local の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
    - export 付き行、クォート文字列、エスケープ、インラインコメント、保護された OS 環境変数の扱いに対応する堅牢なパーサを実装。
    - Settings クラスを提供し、多数の設定プロパティ（DB パス、API トークン、監視閾値、環境種別バリデーション等）を定義。
    - 設定値に対する入力検証を追加（例: KABUSYS_ENV の有効値チェック、PAPER_FILL_MODE の有効値チェック、LOG_LEVEL の検証など）。

- データベース・モニタリング
  - monitoring/ 初期化ロジック（init_monitoring_db）を呼び出して監視テーブルの存在を保証するフローを導入。
  - duckdb を併用する設計（duckdb_path 設定）。

- Execution / Risk / Order 管理（骨組み）
  - BrokerClientFactory によるブローカークライアント生成（Paper Trading 時に Mock を想定）。
  - OrderRepository, OrderManager, Reconciler, RiskManager, ExecutionEngine 等のコンポーネント組み立て処理を run_execution.py に統合。
  - RiskManager 既定値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定し、初期 portfolio value を broker.get_available_cash() で取得して利用。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定ユーティリティを提供（set_process_priority）。
    - CPU affinity 設定ユーティリティを提供（set_cpu_affinity）。
    - Windows と POSIX の差を吸収し、サポートされない OS や権限不足時は警告を出してスキップする実装。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。スコア全0時は等金額にフォールバック。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を追加。
    - 未知のレジームや unknown セクターの取り扱いに関するフォールバックとログを実装。
  - portfolio/position_sizing.py:
    - allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash を超えた場合のスケールダウン）を実装。
    - cost_buffer を考慮した保守的見積り、スケール後の残差処理（lot 単位での配分）を実装。

- リサーチ／ファクター
  - research/factor_research.py:
    - Momentum、Volatility、Value ファクター計算関数を実装（DuckDB を用いた SQL ベース処理）。
    - 実装では過去データのウィンドウ、欠損値処理、必要行数チェック（MA200、ATR など）を行う。
  - research/feature_exploration.py:
    - 将来リターン（calc_forward_returns）、IC（calc_ic）計算、ファクター統計サマリ（factor_summary）、ランク変換ユーティリティを実装。
    - 外部依存を使わず標準ライブラリと DuckDB のみで動作する設計。
  - research/__init__.py による公開 API を整備（zscore_normalize を data.stats から再公開）。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシ等の指標を算出し、閾値に基づく PASS/FAIL 判定を行う。
    - デフォルト DB パスは `data/paper_trading.db`。コマンドラインで期間と DB を指定可能。
    - デフォルト閾値を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200 ms）。

- AI ニュース NLP（下書き）
  - ai/news_nlp.py:
    - raw_news を OpenAI API（gpt-4o-mini）でセンチメント解析して ai_scores テーブルへ書き込むモジュールの骨格を追加。
    - 処理方針（タイムウィンドウ定義、記事集約、バッチ送信、リトライ戦略、JSON の厳密検証、スコアクリップ、部分更新戦略等）を実装予定。
    - API キー未指定時の ValueError、ウィンドウ計算ユーティリティ calc_news_window、定数（バッチサイズ・モデル名・最大記事数等）を定義。

### Changed
- 設定ロジック
  - .env の自動読み込みルールを明確化し、OS 環境変数を保護する挙動に変更（.env.local は override=True で上書き可能だが OS 環境変数は保護）。
  - Settings の各プロパティはデフォルト値と検証を持つように整理（例: path は Path に変換して expanduser を適用）。

### Fixed
- エラーハンドリング
  - run_monitoring のポーリングループで monitor.check_once() が例外を投げてもループを継続するように例外捕捉とログ出力を追加。
  - 各種 DB クエリでデータ不足やテーブル未存在時に安全に扱うための try/except を tools/paper_verification_report.py に追加（OperationalError を捕捉してデフォルト値を返す）。

### Deprecated
- なし（初期リリース相当のため未設定）。

### Removed
- なし。

### Security
- なし特記。

## [0.1.0] - 2026-04-17

Initial public-ish release: 上記「Added」に記載の機能群をパッケージ化して公開（推定リリース日を現在日付に設定しました）。  
注: 実際のリリース日／バージョンはソース管理履歴に合わせて更新してください。

Breaking changes / Migration notes
- run_monitoring は KABUSYS_ENV にかかわらず本番用の sqlite_path を使用する設計になっています。環境に応じて監視 DB を分離したい場合は設定・コードの調整が必要です。
- .env の自動読み込みを行うため、開発環境で環境変数の上書きを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- PAPER_TRADING の DB は `PAPER_TRADING_SQLITE_PATH` で上書き可能。デフォルトは `data/paper_trading.db`（run_execution.py / tools で利用）。
- Settings のプロパティは不正値で ValueError を送出する場合があります（例: invalid KABUSYS_ENV, invalid PAPER_FILL_MODE, invalid LOG_LEVEL）。起動前に環境変数の整合性を確認してください。

Known issues / Work in progress
- ai/news_nlp.py は処理設計・構成が詳細に書かれているものの、ファイル末尾で処理が中断（トランケート）しているように見えます。OpenAI API 呼び出し周りの実装や記事フェッチ (_fetch_articles 等) が未完の可能性があります。運用前に実装完了とテストが必要です。
- portfolio.position_sizing の price の欠損（0.0）に関する TODO コメントあり。現状は price が欠損するとエクスポージャーが過少見積もられ、ブロックが外れることがあり得ます。前日終値や取得原価をフォールバックする拡張が推奨されています。
- CPU affinity / process priority 設定は権限不足や未対応プラットフォームでスキップされ、警告ログのみ出ます。期待動作を得るには適切な権限とプラットフォームで実行してください。

参考: 主要な環境変数（抜粋）
- KABUSYS_ENV (development | paper_trading | live) — 環境種別（必須／デフォルト: development）
- SQLITE_PATH / DUCKDB_PATH — 監視 DB / DuckDB のパス
- PAPER_TRADING_SQLITE_PATH — Paper Trading 専用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視用のファイルパス制御
- PAPER_FILL_MODE — Paper Trading の mock fill 挙動（instant|partial|never|reject）
- OPENAI_API_KEY — ai/news_nlp の API キー（未実装部分あり）

---

もし実際のコミット履歴やリリース日が存在する場合、上記の「0.1.0 - 2026-04-17」はそれに合わせて更新してください。必要であれば各ファイルごとの詳細な変更点（行単位の差分推定）や、リリースノート向けに短いサマリ版を作成します。