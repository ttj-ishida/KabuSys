# KabuSys

KabuSys は日本株向けの自動売買基盤のコードベースです。本リポジトリは発注や監視、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）など、運用に必要な主要コンポーネントを含んでいます。

以下はこのコードベースの概要、セットアップ、使い方、ディレクトリ構成の説明です。

注意: 本 README はソースコード（src/kabusys 以下）を参照して作成しています。実運用前に .env ファイルや API キー、DB の配置などを適切に設定してください。

---

## プロジェクト概要

- 日本株自動売買システムのコアコンポーネント群を収めています。
- 主要機能:
  - ExecutionEngine（発注・注文管理・再同期）
  - Monitoring（システム監視、注文監視、リスク監視、アラート）
  - Portfolio construction（候補選定、重み計算、ポジション算出）
  - Research（ファクター計算、将来リターン、IC、統計）
  - AI モジュール（ニュースのセンチメントスコアリング、レジーム判定）
  - ツール（Paper Trading 検証レポート、Streamlit ダッシュボードなど）
- 永続ストア:
  - SQLite（監視ログ / paper trading DB）
  - DuckDB（時系列株価・ファクターデータ等の分析向け）

---

## 機能一覧（主要コンポーネント）

- execution/
  - ExecutionEngine（発注実行、リスク制御、オーダー管理）
  - OrderManager, OrderRepository, Reconciler（再同期）
- monitoring/
  - SystemMonitor（CPU/メモリ/ディスク・プロセスPID・データ鮮度監視）
  - TradeMonitor（滞留注文・約定異常検出）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - KillSwitch（条件に応じて停止フラグを作成）
  - AlertManager（LINE による通知）
  - MonitoringDB（SQLite テーブル定義・永続化 API）
  - MonitoringEngine（各 Monitor をまとめてポーリング）
  - Streamlit ダッシュボード（監視情報の可視化）
- portfolio/
  - 候補選定、等配分／スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め、資金制約）
- research/
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC 計算、統計サマリ
- ai/
  - news_nlp: OpenAI を使ったニュースセンチメント集計と ai_scores への書込み
  - regime_detector: ETF ma200 とマクロニュースの LLM 評価で日次レジーム判定
- tools/
  - paper_verification_report: Paper Trading の検証レポート生成

---

## 前提条件 / 依存関係

- Python 3.10 以上（typing の | 記法等に依存）
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit（ダッシュボード利用時）
- SQLite は標準ライブラリで利用可能
- 実ブローカー接続を行う場合は kabuステーション 等の情報（パスワード / API）を環境変数で設定

requirements.txt がある場合はそれを使用してください。ない場合は手動でインストール例:
- pip install duckdb psutil openai requests streamlit

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境 ("development" | "paper_trading" | "live") — デフォルト: development  
  - paper_trading の場合、MockBroker を用い paper_trading 用 DB に書き込む（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabu API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- SQLITE_PATH: 監視用 SQLite DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper trading のフィルモード（instant|partial|never|reject、デフォルト "instant"）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（INFO 等）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視関連設定

.env 自動ロード:
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- .env のパースは独自実装で export 形式やクォート、コメントを考慮します。

必須環境変数が未設定の場合、Settings._require により起動時に例外が発生します。 .env.example を参考に .env を準備してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローン・チェックアウト
2. Python 3.10 以上の仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Linux/macOS) または .venv\Scripts\activate (Windows)
3. 依存パッケージをインストール
   - pip install -r requirements.txt  （requirements.txt がなければ個別に）
   - 例: pip install duckdb psutil openai requests streamlit
4. 環境変数を設定（.env を作成）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - AI モジュールを使うなら OPENAI_API_KEY を設定
   - 任意: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH, KABUSYS_ENV 等
5. data/ ディレクトリを作成（DB を置く場合など）
   - mkdir -p data
6. （初回）Monitoring DB 等はスクリプトが自動で初期化します（init_monitoring_db を呼び出します）。

---

## 使い方

以下は主要スクリプトの起動方法と使い方の例です。

- 実行エンジン（Execution）
  - 起動:
    - python -m kabusys.run_execution
    - 実行中に data/stop_requested.flag が作成されると安全にエンジン停止処理を行います。
  - KABUSYS_ENV=paper_trading の場合:
    - MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録されます。
  - 注意:
    - 実行前に kill.flag の自動クリア設定（Settings.kill_flag_clear_on_start）を確認してください。
    - Execution 起動中に stop 要求を送るには stop_requested.flag を作成します（または KillSwitch が条件に応じて kill.flag を書くことがあります）。

- 監視ループ（Monitoring）
  - 起動:
    - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使います（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（監視 UI）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite を読み取り専用で参照します。監視プロセスが DB を更新していることが前提です。

- Paper Trading 検証レポート
  - 使い方:
    - python -m kabusys.tools.paper_verification_report
    - 指定期間:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - DB 指定:
      - --db PATH （または環境変数 PAPER_TRADING_SQLITE_PATH）
  - 出力: 標準出力に統計（稼働率・成功率・レイテンシ等）と PASS/FAIL 判定が表示されます。

- AI モジュール（ニューススコア / レジーム判定）
  - programmatic に利用する設計です（関数呼び出し）。
  - 例（Python REPL / スクリプト）:
    - from kabusys.ai.news_nlp import score_news
      import duckdb, datetime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, datetime.date(2026,4,10), api_key="YOUR_OPENAI_KEY")
    - from kabusys.ai.regime_detector import score_regime
      score_regime(conn, datetime.date(2026,4,10), api_key="YOUR_OPENAI_KEY")
  - OpenAI API のエラーやパース失敗はフェイルセーフで処理されます（多くは 0.0 をフォールバック）。

- 停止フラグとキルスイッチ
  - data/stop_requested.flag: 手動で監視・実行スクリプトを停止したい場合に作成します。run_monitoring / run_execution が存在をチェックします。
  - data/kill.flag: KillSwitch が条件を満たした場合に書き込む停止シグナル（ExecutionEngine 側でのチェックを想定）。Settings.kill_flag_path で場所を制御できます。
  - PID ファイル: 実行エンジンは pid ファイルを記述し、SystemMonitor はこの PID を確認してプロセスの生存判定を行います（stale PID の検出・削除）。

---

## ログ・監視・アラート

- ログレベルは LOG_LEVEL 環境変数で設定可能（INFO デフォルト）。
- AlertManager は LINE Messaging API へ push を投げます。channel token / user id が空の場合は送信せずログ出力のみ。
- MonitoringDB に監視ログ・リスクログ・trade_logs・positions・dashboard 等を保存します。init_monitoring_db によりテーブルは自動作成・必要なマイグレーションも実施されます。

---

## ディレクトリ構成（主なファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン等
  - config.py — 環境変数 / 設定読み込みロジック（.env 自動ロード、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI 経由）
    - regime_detector.py — 市場レジーム判定（ETF MA200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py — SQLite のテーブル定義・DB 操作ラッパー
    - system_monitor.py — CPU/メモリ/DISK・プロセス・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限の監視ロジック
    - kill_switch.py — kill.flag の作成・評価
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 各 Monitor を束ねてポーリング
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注フローの外向API
    - reconciler.py — 再同期 / リコンシリエーション
    - ...（BrokerFactory, EngineConfig, ExecutionEngine 等の実装ファイルが存在）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数・資金配分計算（単元丸め・スケール調整）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value ファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン, IC, 統計サマリ
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。実際のソースツリーにはさらに多くの補助モジュールが含まれます。）

---

## よくある操作例

- 監視を 30 秒間隔にする:
  - export MONITOR_POLL_INTERVAL=30
  - python -m kabusys.run_monitoring
- Paper Trading レポート（2026-04-01〜2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit ダッシュボード起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

## トラブルシューティング / 注意点

- Settings が必須キーを要求するため、JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD が未設定だと起動時に例外になります。
- OpenAI 呼び出し部分は外部 API に依存するため、API キーの不足やネットワーク障害があると AI 機能は部分的にフォールバックします（多くの場合スコア 0.0 またはスキップ）。
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルが前提です。これらのスキーマ・データは別途準備する必要があります。
- process_priority / cpu_affinity の設定は psutil を使用しており、権限不足で失敗する場合は警告を出してスキップします。
- デフォルトの DB パスは data/ 以下です。運用時は適切なパスやバックアップ戦略を検討してください。

---

必要に応じて README にサンプル .env（.env.example）の内容、詳細な API 使用例、ユニットテストの実行方法、CI/CD 設定などを追加できます。追加でそのような情報が必要でしたら教えてください。