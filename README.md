# KabuSys

KabuSys は日本株向けの自動売買・研究・監視ツール群です。本リポジトリは以下を含みます：注文発行と実行エンジン、監視（モニタリング）コンポーネント、ポートフォリオ構築ユーティリティ、ファクター計算 / 研究ツール、LLM ベースのニュース NLP / レジーム判定機能、および付帯ツール（検証レポート・Streamlit ダッシュボード等）。

注意：本 README はソースコード（src/kabusys 以下）からのドキュメント化です。実運用にあたっては環境変数や API キーの管理、DB のバックアップ、API コスト管理など運用上の注意を必ず行ってください。

## 主な機能一覧
- Execution（発注・実行）
  - ExecutionEngine 起動スクリプト（run_execution）
  - Broker クライアント抽象化と Mock（paper_trading 用）
  - OrderManager / OrderRepository / Reconciler による起動時リコンシリエーション
  - リスク管理コンポーネント（RiskManager 設定例あり）
- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite に監視ログを永続化する monitoring_db
  - KillSwitch（フラグファイル書き込みで ExecutionEngine 停止指示）
  - AlertManager（LINE Notification 経由のプッシュ通知）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア加重の重み計算
  - セクター制限、レジーム乗数の適用
  - ポジションサイズ計算（単元株丸め・aggregate cap 対応）
- Research（研究用）
  - Momentum / Volatility / Value 等のファクター計算（DuckDB 経由）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI（LLM 利用）
  - ニュースのセンチメント算出（OpenAI Chat API / gpt-4o-mini を想定）
  - マクロニュース + ETF MA200 による市場レジーム判定
  - バッチ・リトライ・レスポンス検証・スコアクリッピング等の実装
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）
  - Streamlit ダッシュボード（監視情報の可視化）

---

## セットアップ手順（開発環境向け / ローカル実行）
以下は基本的なセットアップ例です。必要パッケージは環境によって増減します。

1. Python 3.10+ を用意（コードは型ヒントに union 型等を使用）。
2. 仮想環境を作成して有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（最低限の例）:
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt が無ければ上記を参考に追加してください）
4. .env ファイル（プロジェクトルート）に環境変数を設定（下の「環境変数」参照）。
   - 自動ロードは Settings モジュールで .env / .env.local をプロジェクトルートから読み込みます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
5. データディレクトリの初期化（必要に応じて）:
   - data/ ディレクトリを作成
   - 実行時に SQLite / DuckDB ファイルが自動作成されます（ファイルパスは Settings のデフォルトを使用）。

---

## 主要な環境変数（Settings）
Settings クラスは .env または環境変数から設定を読み込みます。主なキー：

- 必須（運用により必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API 用パスワード

- OpenAI 関連
  - OPENAI_API_KEY — LLM 呼び出しに使用

- 運用環境
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading の場合、MockBrokerClient が使用され、paper 用 SQLite（data/paper_trading.db）へ記録される
  - LOG_LEVEL — ログレベル（"DEBUG"/"INFO"/...）

- DB / ファイルパス
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine 用 pid ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — KillSwitch 用フラグファイル（デフォルト: data/kill.flag）

- Paper Trading
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）

- 監視閾値
  - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT （% 値）

- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID

その他、MONITOR_POLL_INTERVAL（監視ポーリング間隔・秒）をプロセス実行時に環境変数で上書きできます。

Settings はプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込みます。プロジェクトルートが見つからない場合は自動ロードをスキップします。

---

## 使い方（主要コマンド）

- 監視ループの起動（Monitoring）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で変更可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）にログを残します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 実行エンジン起動（Execution）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します（本番 DB と分離）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH（あるいは環境変数 PAPER_TRADING_SQLITE_PATH）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで可視化（read-only 接続推奨）。MonitoringEngine が先に監視 DB を作成・更新している必要があります。

- AI / 研究機能（プログラム的利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores を参照してニューススコアを生成・書き込み
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 とマクロニュースを組み合わせたレジーム判定を market_regime テーブルへ書き込み
  - kabusys.research.calc_momentum / calc_volatility / calc_value などは DuckDB 接続を渡して利用します

注意：OpenAI を利用する機能は API キーが必要です。API 呼び出しは料金が発生するため、本番実行前にコスト・呼び出し頻度を確認してください。API の失敗時はフェイルセーフ（スコア 0 へのフォールバックなど）実装がありますが、運用ルールを検討してください。

---

## 実行時の挙動・重要ポイント
- run_monitoring と run_execution は起動時にプロセス優先度を "high" にセットしようとします（psutil を利用）。権限がない場合は警告ログを出してスキップします。
- Monitoring DB 初期化は init_monitoring_db により冪等的に行われ、既存スキーマに列がない場合のマイグレーション処理も一部含みます（例: trade_logs.latency_ms, dashboard.peak_value）。
- RiskMonitor は dashboard の peak_value をハイウォーターマークとして管理し、ドローダウンやポジション上限アラートを risk_logs に記録・kill.flag の作成トリガーにできます。
- TradeMonitor は order_repository の list_active() を参照して滞留注文・約定異常を判定します（OrderRepository を必要とするため、監視用 DB と注文 DB が分離されている設計を想定）。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番の DB と完全分離された SQLite を用いるよう設計されています。

---

## ディレクトリ構成（src/kabusys）
以下はリポジトリ中の主なファイル・モジュールと簡単な説明です。

- kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数・設定読み込み（.env 自動読み込みロジックを含む）
  - run_monitoring.py — SystemMonitor をポーリングで実行する起点スクリプト
  - run_execution.py — ExecutionEngine を起動するスクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成 CLI
  - monitoring/
    - monitoring_db.py — SQLite を用いた監視ログ永続化層（init / MonitoringDB）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス PID チェック
    - trade_monitor.py — 注文滞留・約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag を書いて ExecutionEngine 停止を指示
    - alert_manager.py — LINE push 通知（クールダウン管理付き）
    - monitoring_engine.py — Monitor 群を束ねるループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py — 発注フロー（作成 → 送信 → ブローカー同期等）
    - reconciler.py — 起動時の注文/ポジション再同期ロジック
    - ...（broker_factory, execution_engine, order_repository 等が存在想定）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数決定・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - ai/
    - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py — マクロセンチメント + MA200 でレジーム判定
  - data/ （実行時に生成される想定）
    - kabusys.duckdb (default)
    - monitoring.db (default)
    - paper_trading.db (paper_trading 時)

（上記は主要モジュールの抜粋です。実際のファイル一覧は src/kabusys 以下を参照してください）

---

## 開発・デバッグのヒント
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストなどで自動ロードを抑止したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で調整可能です（0 や負の数はデフォルトにフォールバックします）。
- OpenAI 呼び出し部分はリトライ / バックオフを実装していますが、ローカルテストでは API 呼び出しをモック（unittest.mock.patch）することを推奨します。
- Streamlit をローカルで使う際、DB を別プロセスから read-only で開くために streamlit の起動引数で --db を指定できます（デフォルトは data/monitoring.db）。

---

## ライセンス・注意事項
- 本コードはテンプレート・参考実装として提供されている想定です。実運用（実資金投入）前に入念なテストと監査を行ってください。
- OpenAI 等外部 API の利用には料金が発生します。API キーは安全に管理してください。
- 金融取引に係る法令・規制・リスクについては専門家の助言を得たうえで運用してください。

---

必要であれば、README に以下の追加情報を追記します：
- requirements.txt の例（pip freeze ベース）
- 典型的な .env.example（キーのテンプレート）
- 実行フロー図（簡易シーケンス）
- 各モジュールの API（関数・クラスの詳細ドキュメント）

どれを追加しますか？