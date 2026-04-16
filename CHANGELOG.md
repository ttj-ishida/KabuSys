# Changelog

すべての注目すべき変更を記載します。本ファイルは「Keep a Changelog」形式に準拠しています。  
日付およびバージョンはコードベースから推測して付与しています。必要に応じて調整してください。

## [0.1.0] - 2026-04-16
初回リリース（コードベースのスナップショットに基づく主要機能の導入）。

### Added
- 全体
  - パッケージ初期化とバージョン管理を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開のための __all__ エクスポートを整備。

- 設定・環境変数管理（kabusys.config）
  - .env / .env.local の自動読み込み機構を実装。プロジェクトルート（.git / pyproject.toml）を探索して自動ロードする。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
  - .env パーサーの実装（export プレフィックス、クォート値、インラインコメント対応）。
  - Settings クラスを追加し、各種設定をプロパティで提供（DBパス、Paper Trading 設定、監視閾値、環境種別バリデーション等）。
  - 必須環境変数未設定時に明確な例外を送出する _require() を実装。

- 実行ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) / set_cpu_affinity(cpu_count) を追加。Windows と POSIX の差分を吸収してプロセス優先度や CPU affinity を設定。
  - 権限不足や未対応環境での失敗はワーニングで安全にスキップ。

- 監視・起動スクリプト
  - run_monitoring.py を追加。SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数で間隔上書き、停止フラグ（data/stop_requested.flag）対応。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（注: 意図的/仕様的な点）。
  - run_execution.py を追加。ExecutionEngine の起動、PID ファイル管理、停止フラグ監視、スレッドでの実行制御を実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用して本番 DB と分離。

- 実行系（execution）
  - BrokerClientFactory / ExecutionEngine / OrderManager / OrderRepository / Reconciler / RiskManager 系の組み立て例をスクリプト内で示す（run_execution.py）。
  - デフォルトの RiskConfig を設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）。

- Portfolio（銘柄選定・配分・ポジション計算）
  - portfolio_builder: select_candidates(), calc_equal_weights(), calc_score_weights() を追加。スコアが全て 0 の場合のフォールバックあり。
  - risk_adjustment: apply_sector_cap(), calc_regime_multiplier() を追加。セクター上限フィルタ、レジームに応じた乗数（bull/neutral/bear）を実装。
  - position_sizing: calc_position_sizes() を追加。risk_based / equal / score 各方式、単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer（手数料/スリッページ見積り）対応。

- 研究・リサーチ（research）
  - factor_research: calc_momentum(), calc_volatility(), calc_value() を追加。DuckDB を用いた SQL ベースのファクター計算（MA200, ATR20, 各種モメンタム等）。
  - feature_exploration: calc_forward_returns(), calc_ic(), factor_summary(), rank() を追加。将来リターン、IC（Spearman）計算、基本統計量集計を実装。
  - research パッケージの __all__ を整備し、zscore_normalize（kabusys.data.stats 依存）などをエクスポート。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成 CLI を追加。
    - 稼働率・注文成功率・送信率・レイテンシ（P95）などを集計し、PASS/FAIL を判定する閾値を定義。
    - DB ファイル存在チェックや sqlite3.OperationalError の耐性を実装。
    - P95 計算や日付フィルタ機構を実装。

- AI / ニュース NLP（途中実装あり）
  - ai.news_nlp モジュールを追加（ニュース記事を OpenAI に送って銘柄別スコアを生成する設計）。
    - ニュースウィンドウ計算（JST → UTC 変換）、バッチ送信（最大20 銘柄）、スコアクリッピング、リトライ方針（429/5xx/タイムアウト）などを設計。
    - OpenAI API キー未指定時は明確なエラーを送出する安全設計。
    - （注）ファイル末尾で処理が途中で切れているため、書き込みロジック等は未完了箇所あり。

### Changed
- .env 読み込み順序・挙動
  - OS 環境変数 > .env.local > .env の優先順位を採用。既存 OS 環境変数は protected として上書きを防止。
- run_monitoring の挙動
  - 監視プロセスは KABUSYS_ENV に関わらず production の sqlite_path を参照する仕様。監視データは本番 DB に集約される想定。
- run_execution の挙動
  - paper_trading 環境では paper_sqlite_path を使用して DB を完全分離する挙動を導入。
- Settings: 各種バリデーション
  - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL の値を厳密に検証し、不正な値の場合は ValueError を送出するよう改善。

### Fixed
- .env パーサーの堅牢化
  - クォート内のバックスラッシュエスケープ、export 形式、インラインコメントの取り扱いを改善。無効行や key が空の行を除外。
- MONITOR_POLL_INTERVAL の取り扱い
  - 環境変数が不正（非整数や 0/負値）の場合は警告を出してデフォルト（60 秒）にフォールバック。time.sleep に渡す不正値を回避。
- process_priority の失敗耐性
  - 権限不足や未対応プラットフォームでの例外をキャッチしてワーニングに置き換え、安全にスキップするよう修正。
- calc_score_weights のフォールバック
  - 全銘柄スコアが 0 の場合は等金額配分にフォールバックし、WARNING を出力するよう修正。
- position_sizing の堅牢化
  - 価格未取得（None/0）銘柄はスキップするようにしてゼロ除算や不正計算を回避。
  - aggregate cap のスケーリングと残差処理（lot 単位での追加配分）を実装して、可用現金に応じた配分安定化を図った。
- research / SQL クエリの NULL/欠損ハンドリング
  - ATR / MA200 等のウィンドウで行数不足のときに NULL を返すなど、データ不足に対する安全策を明示的に実装。
- tools.paper_verification_report の耐障害性
  - テーブルが存在しない等の sqlite3.OperationalError を捕捉してレポート生成処理を継続可能にした。

### Security
- ai.news_nlp: OpenAI API キー（OPENAI_API_KEY）を必須とし、未設定時は ValueError を送出。API キーの取り扱いを明示。

### Notes / Usage hints
- 停止フラグ / PID
  - 実行スクリプトは data/stop_requested.flag ファイルで外部停止制御を行う設計。PID ファイルは data/execution.pid 等で管理。
- .env の読み込みを無効化したいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB / SQLite のパスは Settings で定義されており、環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）で上書き可能です。

---

この CHANGELOG は現行のソースコードから機能追加・修正・設計意図を推測して作成しています。必要であれば各変更に対応するコミットハッシュや実際の日付、責任者などのメタ情報を追記します。どのレベルまで詳細化するか指示をください。