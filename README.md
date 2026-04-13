# KabuSys

KabuSys は日本株の自動売買システム向けユーティリティ群（ポートフォリオ構築、発注/実行管理、監視、研究、AI ベースのニュース評価など）を集めた Python パッケージです。本リポジトリには、本番／ペーパー取引を分離して扱う実行エンジン、監視エンジン、研究用ファクター計算、ニュース NLP、監視ダッシュボードなどのモジュールが含まれます。

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動方法・コマンド）
- 環境変数（主要項目）
- ディレクトリ構成

---

## プロジェクト概要
- 設計方針のハイライト
  - 発注と監視を分離：ExecutionEngine（発注）とMonitoringEngine（監視）は独立して動作。
  - 本番データとペーパー取引の明確な分離：KABUSYS_ENV に応じて paper_trading 用 DB を使用する仕組みを持つ。
  - データ分析・研究は DuckDB を利用して高速な SQL/列指向処理を実行。
  - OpenAI（LLM）を利用したニュースセンチメント評価・市場レジーム判定をサポート（APIキー必須）。
  - プロセス優先度や CPU affinity 設定をユーティリティで吸収（psutil を使用）。

---

## 主な機能
- Execution（発注）関連
  - 注文管理（OrderManager）
  - 発注リコンシリエーション（Reconciler）
  - Risk/Position 管理（RiskManager 等） — 実行エンジン実装は execution パッケージ内
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し、データは data/paper_trading.db に記録

- Monitoring（監視）関連
  - SystemMonitor（CPU/メモリ/Disk/プロセス PID/データ鮮度の監視）
  - TradeMonitor（滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション上限の監視）
  - KillSwitch（閾値超過時に flag ファイルを書いて ExecutionEngine を停止）
  - AlertManager（LINE Push による通知）
  - monitoring DB の永続化（SQLite）と Streamlit ダッシュボード

- Portfolio（配分・サイズ計算）
  - 候補選定、等分配/スコア加重、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元株丸め、aggregate cap）

- Research（研究）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（情報係数）計算、統計サマリー
  - DuckDB を用いた処理（prices_daily / raw_financials テーブルを前提）

- AI（OpenAI）連携
  - ニュース NLP：raw_news から銘柄毎に記事を集約して LLM でセンチメントスコアを生成し ai_scores に格納
  - Regime Detector：ETF（1321）の MA とマクロニュースを組合せて日次レジーム判定を実施

- ツール
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等の集計）

---

## セットアップ手順（ローカル開発向け）

前提：Python 3.9+（DuckDB / psutil / openai 等が動作するバージョンを推奨）

1. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（代表例）
   - pip install duckdb psutil requests openai streamlit

   ※プロジェクトに requirements.txt がない場合は上記パッケージを手動で揃えてください。
   - 他に必要なパッケージがあれば適宜追加してください（例: typing-extensions 等）。

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定
   - プロジェクトルートに .env を作成して主要な環境変数を設定できます（自動ロード機構あり）。
   - 主要な環境変数については次節を参照してください。

---

## 使い方（起動例・コマンド）

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 動作モード: KABUSYS_ENV によって挙動が変わります。
    - KABUSYS_ENV=paper_trading: MockBrokerClient を使用、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に保存。
    - KABUSYS_ENV=live: 本番モード（実ブローカー連携）
    - KABUSYS_ENV=development: 開発向け
  - 起動時にプロセス優先度を "high" に設定します（psutil を利用）。
  - ExecutionEngine は pid ファイル（Settings.pid_file_path）を使用します。

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔: 60 秒
  - ポーリング間隔を環境変数で変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視用 DB は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します。

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - データベース指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）

- AI 関連（ニューススコアリング / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または各関数へ api_key 引数で渡す）
  - 使い方（コードから直接呼び出し）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

---

## 主要な環境変数（Settings から抜粋）
- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants API 用
- KABU_API_PASSWORD: （必須）kabu API 用
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う際に必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知に使用
- DUCKDB_PATH: DuckDB データベースパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパー取引の約定モード（instant | partial | never | reject）デフォルト: instant
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアするか（"1" で有効）
- MONITOR_POLL_INTERVAL: run_monitoring 実行時のポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

注意: Settings クラスは自動でプロジェクトルートの .env / .env.local を読み込みます（OS 環境変数が優先）。自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 重要な実装上の挙動（運用メモ）
- Monitoring は常に（KABUSYS_ENV に関わらず）Settings.sqlite_path（監視 DB）を使用します。つまり監視ログは本番 DB パスに書き込まれます。
- Paper Trading モードでは Execution 用 DB が paper_sqlite_path に切り替わり、本番発注 DB と分離されます。
- run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定しようとします（権限不足時は警告でスキップ）。
- KillSwitch は data/kill.flag を作成して ExecutionEngine 停止を促します（既存の場合は再書き込みしない、冪等）。
- monitoring_db.init_monitoring_db は冪等であり、マイグレーション（カラム追加）も簡易的に行います。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理（Settings）
  - run_execution.py           — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - utils/
    - process_priority.py      — プロセス優先度 / CPU affinity ユーティリティ
  - execution/
    - order_manager.py
    - reconciler.py
    - ...                      — 発注関連ロジック（OrderRepository 等は発注サブパッケージ内）
  - monitoring/
    - monitoring_db.py         — SQLite の永続化レイヤ
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - tools/
    - paper_verification_report.py

注: 上記は主要ファイルの抜粋です。細部実装や追加モジュールはパッケージ内に存在します。

---

## 備考 / 注意事項
- OpenAI API を利用する機能はネットワーク/レート制限およびコストを伴います。API キーの管理や呼び出し頻度には注意してください（ログ・リトライ設計あり）。
- 本システムは実際の発注を行う可能性があるため、live モードでの実行は十分に注意のうえで行ってください。Paper trading モードで十分に検証してください。
- SQLite / DuckDB ファイルはローカルファイルで管理されます。バックアップや排他制御に注意してください（複数プロセスで同一ファイルを同時書き込みする運用は避けるか適切なロックを検討してください）。
- 必要に応じて各モジュールのロギングレベルや設定を調整してください（LOG_LEVEL 環境変数等）。

---

この README はコードベースの主要点をまとめた概要です。各モジュールの詳細や API 利用方法は該当ファイルの docstring / 関数ドキュメントを参照してください。必要であれば、特定モジュール（例: ニュース NLP / ポジションサイズ計算 / Reconciler）の詳しい使用例や設計ドキュメントも作成できます。