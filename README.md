# KabuSys

日本株自動売買システムのコードベース（抜粋）。この README はプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成をまとめたものです。

注意: このリポジトリには複数のコンポーネント（ExecutionEngine / Monitoring / Research / AI 等）が含まれます。実行には Python 環境の他、DuckDB、SQLite、外部 API（OpenAI、kabuステーション、J-Quants など）の設定が必要です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を想定したモジュール群です。主に以下の責務を持ちます。

- 発注・注文状態管理（ExecutionEngine / OrderManager / Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築とポジションサイズ決定（portfolio パッケージ）
- リサーチ用ファクター計算 / 特徴量探索（research パッケージ）
- ニュース NLP によるセンチメントスコアリング、レジーム判定（ai パッケージ）
- 検証用ツール（paper trading レポート生成、Streamlit ダッシュボード）

設計方針の一部:
- DB は SQLite（監視）と DuckDB（時系列データ・成分表等）を併用
- Paper trading（検証）用 DB は本番 DB と分離可能
- LLM / 外部 API 呼び出しはフェイルセーフ（失敗時は安全側にフォールバック）
- 自動ロードされる .env の扱い（config モジュール）によりローカル設定が可能

---

## 主な機能一覧

- Execution
  - ExecutionEngine（起動・セッション管理）
  - BrokerClientFactory（本番/モック切替）
  - OrderManager（Order State Machine の外向き API）
  - Reconciler（起動時のリコンシリエーション）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク / プロセス監視 / データ鮮度）
  - TradeMonitor（滞留注文・約定異常価格検出）
  - RiskMonitor（ドローダウン / ポジション上限監視）
  - KillSwitch（条件に応じて停止フラグを書き込み）
  - AlertManager（LINE push による通知）
  - MonitoringEngine（上記監視のポーリングループ）
  - Streamlit ダッシュボード（監視結果表示）
- Portfolio
  - 銘柄選定、等分／スコア加重配分、リスク調整、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC、統計サマリ
- AI
  - news_nlp: raw_news -> OpenAI による銘柄別センチメント化 → ai_scores へ書き込み
  - regime_detector: ma200 とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成

---

## 必要条件（推奨）

- Python 3.10+
- duckdb
- psutil
- requests
- openai (LLM 機能を使う場合)
- streamlit（ダッシュボードを使う場合）
- SQLite（OS 標準で利用可能）
- pipenv / venv 等で仮想環境利用を推奨

インストール例（例示）:
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit

（requirements.txt がある場合はそれを使用してください）

---

## 環境変数と .env

config.py は環境変数を読み込みます。.env / .env.local がプロジェクトルートにあれば自動で読み込まれます（OS 環境変数が優先）。

自動ロードを無効化する場合:
KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な環境変数（代表例）:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（ai 機能で必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（research 等で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（ブローカー接続）
- PAPER_FILL_MODE: paper trading の約定挙動（instant | partial | never | reject）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH: ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で参照。デフォルト 60）

シンプルな .env の例:
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
PAPER_FILL_MODE=instant

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
3. 必要パッケージをインストール
   pip install duckdb psutil requests openai streamlit
4. data ディレクトリ等の作成（必要に応じて）
   mkdir -p data
5. .env を作成（.env.example を参照できる場合はそれをコピー）
6. DuckDB / SQLite に必要なテーブル等は初回実行時に多くの初期化処理で自動作成されます（例: init_monitoring_db）。

注意:
- OpenAI を使う機能を使う場合は OPENAI_API_KEY をセットしてください。
- Paper trading を行う場合は KABUSYS_ENV=paper_trading を設定すると、run_execution は paper 用 DB を使用します（settings.is_paper に依存）。ただし Monitoring はドキュメントにある通り環境にかかわらず本番 sqlite_path を使うため注意してください（run_monitoring のコメント）。

---

## 使い方（代表コマンド）

プロジェクトのルート（pyproject.toml または .git があるディレクトリ）をカレントにして実行してください。

- 監視ループを起動（ポーリングして監視ログ書き込み）
  python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）。
  - 停止は data/stop_requested.flag ファイルを作成することで優雅に停止できます。

- Execution エンジンを起動
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（デフォルト data/paper_trading.db）にデータを記録します。
  - 停止は data/stop_requested.flag を作成するとエンジンが検知して停止します。
  - 起動時に kill_flag（Settings.kill_flag_path）を検出すると起動を中止します。

- Paper Trading 検証レポート生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD  レポート開始日
    --to   YYYY-MM-DD  レポート終了日
    --db PATH           SQLite DB パス（環境変数 PAPER_TRADING_SQLITE_PATH を上書き）
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB（SQLite）を読み取り専用で開きます。

- AI 関連（スクリプトまたは REPL から呼出）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  これらは OpenAI API キー（引数または OPENAI_API_KEY 環境変数）を必要とします。

---

## プロセス制御 / フラグファイル

- 停止フラグ（run_execution / run_monitoring が監視する）
  - data/stop_requested.flag（存在を検出するとループを抜ける）
- KillSwitch（自動停止のために書き込まれる可能性がある）
  - data/kill.flag（KillSwitch が条件を満たすと書き込む）
- PID ファイル
  - data/execution.pid（ExecutionEngine が書き込むファイル。SystemMonitor はこれを確認してプロセスが生きているかチェック）

KillSwitch のトリガーは主に RiskMonitor（ドローダウン / ポジション上限）に基づきます。KillSwitch がフラグを書き込むと、実行系は起動を停止する / 停止を受け付けます。

---

## 主要ファイルとディレクトリ構成

以下は主要なファイルの抜粋です（src/kabusys 以下）。実際のリポジトリではさらに多くのファイルが存在する可能性があります。

- src/kabusys/
  - __init__.py (パッケージ定義, __version__=0.1.0)
  - config.py (環境変数と設定の読み込み / Settings クラス)
  - run_monitoring.py (SystemMonitor をポーリングして監視を行う起動スクリプト)
  - run_execution.py (ExecutionEngine を起動するスクリプト)
  - tools/
    - paper_verification_report.py (Paper Trading の検証レポート生成)
  - ai/
    - news_nlp.py (ニュースを OpenAI でスコアリングし ai_scores に書き込む)
    - regime_detector.py (市場レジーム判定)
  - monitoring/
    - monitoring_db.py (SQLite に対する読み書き層)
    - system_monitor.py (CPU/メモリ/ディスク/データ鮮度/プロセスの監視)
    - trade_monitor.py (滞留注文・約定異常検出)
    - risk_monitor.py (ドローダウン・ポジション上限監視)
    - kill_switch.py (停止フラグの作成/管理)
    - alert_manager.py (LINE Push を使った通知)
    - monitoring_engine.py (各 Monitor を束ねる)
    - streamlit_dashboard.py (監視ダッシュボード)
  - execution/
    - order_manager.py (Order 管理)
    - reconciler.py (リコンシリエーション)
    - ...（broker_factory / execution_engine / order_repository 等）
  - portfolio/
    - portfolio_builder.py (候補選定 / 等配分 / スコア配分)
    - position_sizing.py (株数決定 / キャップ / 単元丸め)
    - risk_adjustment.py (セクター制限 / レジーム乗数)
  - research/
    - factor_research.py (momentum, volatility, value)
    - feature_exploration.py (forward returns, IC, summary)
  - data/ (実行時に使用する SQLite / DuckDB ファイルやフラグファイルを置く想定)
    - monitoring.db (デフォルト: monitoring / system logs)
    - paper_trading.db (paper trading 用 DB)
    - kabusys.duckdb (DuckDB 用ファイル)
    - stop_requested.flag, kill.flag, execution.pid

---

## 開発・デバッグのヒント

- Settings クラスは .env と OS 環境変数を組み合わせて設定を解決します。テスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。
- Monitoring 側の DB 初期化は冪等（init_monitoring_db）。既存 DB に対して必要なマイグレーション（カラム追加など）を含む実装になっています。
- OpenAI を利用する処理はリトライやフェイルセーフの実装があるため、API キーの制限や一時的なエラーがあっても致命的にならない設計です。
- cpu/memory/affinity の設定は utils/process_priority.py にまとめられており、プラットフォーム差分（Windows / POSIX）を吸収します。

---

## ライセンス / 注意事項

- 本 README はコード内のドキュメント文字列に基づいて作成しています。実運用・実取引に用いる際は、各種 API の利用規約、証券取引に関する法令、リスク管理を十分に確認してください。
- 実トレードを行う場合は本番環境（KABUSYS_ENV=live）での動作確認、監視、通知経路の堅牢化、十分なテストを必ず行ってください。

---

この README はコードに含まれるコメントと docstring を基に作成しています。必要があれば、セットアップ手順の詳細化（requirements.txt、Dockerfile、CI 設定 等）や各モジュールの API ドキュメントを追加します。どの部分を優先して充実させるか指定してください。