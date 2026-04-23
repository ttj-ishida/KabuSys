# KabuSys

日本株自動売買システムのコアライブラリ／ランタイム群です。  
実行エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ用ファクター計算、AI を使ったニュース分析などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を組み合わせて、自動売買のワークフローを実行／監視／評価するためのライブラリ群です。

- 実売買（live）およびペーパートレード（paper_trading）に対応した ExecutionEngine
- システム稼働状況・注文状況・リスク監視を行う MonitoringEngine（Kill Switch を備える）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、セクター制限）
- リサーチ用のファクター計算（モメンタム、ボラティリティ、バリュー等）および特徴量解析ユーティリティ
- OpenAI を利用したニュースセンチメントスコアリング / 市場レジーム判定
- 環境設定ウィザード（.env 生成）や設定検証ツール、Paper Trading 検証レポート生成スクリプト
- ロギング・プロセス優先度設定などのユーティリティ

---

## 主な機能一覧

- Execution
  - ExecutionEngine: BrokerClient 抽象を介した発注処理（KABU API / MockBroker）
  - Paper trading 用に本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス死活・データ鮮度監視
  - TradeMonitor / RiskMonitor: 注文の滞留・約定異常・ドローダウン/ポジション上限監視
  - KillSwitch: ルールに応じて data/kill.flag を書き込み ExecutionEngine を停止
  - MonitoringEngine: 複数モニタの統合ポーリングおよびアラート通知トリガ
- Portfolio
  - 候補選定（スコア順）、等金額・スコア加重、リスクベースのポジション算出
  - セクター集中制限、レジームに応じた投入資金乗数
- Research
  - DuckDB 経由で prices_daily / raw_financials からファクター計算（モメンタム / ATR / PER 等）
  - 将来リターン計算、IC（スピアマン）や統計サマリ
- AI
  - news_nlp: OpenAI（gpt-4o-mini 等）でニュースを銘柄ごとにスコア化して ai_scores に書き込み
  - regime_detector: ETF (1321) の MA 乖離 + マクロニュースセンチメントで market_regime を判定
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## 前提 / 必要要件

- Python 3.10+
- 必要パッケージ（一例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（Python 標準ライブラリ経由で使用）
- ネットワークアクセス（kabuステーション API / OpenAI 等を使う場合）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```
※ requirements.txt がある場合は `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。

2. .env を作成する（推奨: ウィザードを利用）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を対話的に生成します。生成後は必ず `python -m kabusys.validate_config` で検証してください。

3. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗扱いにする場合:
   ```
   python -m kabusys.validate_config --strict
   ```

4. （必要に応じて）データディレクトリ作成
   - デフォルトの DB / ログパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 多くは起動時に自動作成されますが、ファイルパーミッション等を事前に確認してください。

---

## 環境変数（主なもの）

- 必須 / 重要
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 実行環境
  - KABUSYS_ENV — 実行環境: development | paper_trading | live
    - paper_trading の場合は MockBrokerClient が使用され、DB は data/paper_trading.db に記録される
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
- ログ
  - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
  - LOG_DIR (defaults to logs/)
- AI
  - OPENAI_API_KEY — news_nlp / regime_detector で使用
- Paper trading
  - PAPER_FILL_MODE — instant | partial | never | reject
- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

---

## 使い方（主なコマンド）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine を起動
  - デフォルト（設定に従う）
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker が使用され、ペーパートレード DB に記録されます。

  - 停止方法:
    - 外部から停止するにはプロジェクトルートの `data/stop_requested.flag` を作成してください（run_execution/run_monitoring はこのファイルを検知して安全停止します）。
    - KillSwitch によって `data/kill.flag` が書き込まれると ExecutionEngine 側で停止処理が走ります。

- Monitoring を起動
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
  - 監視は常に本番 sqlite_path を使用する点に注意（環境にかかわらず監視 DB は monitoring.db）。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB: data/paper_trading.db。別 DB を使う場合は `--db /path/to/db` または環境変数 PAPER_TRADING_SQLITE_PATH を設定。

- AI スコアリング / レジーム判定（プログラム呼び出し）
  - DuckDB 接続を渡して利用:
    ```py
    from kabusys.ai.news_nlp import score_news
    # conn: duckdb connection, target_date: datetime.date, api_key: str|None
    written = score_news(conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定:
    ```py
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```

---

## 停止 / フラグ

- data/stop_requested.flag
  - run_execution と run_monitoring が起動ループ中にこのファイルを検知すると安全に終了します。
- data/kill.flag
  - KillSwitch がルールに応じて書き込むファイル。ExecutionEngine 起動中にこのファイルがあると起動を阻止または停止トリガになります。
- PID ファイル
  - data/execution.pid（設定により変更可能）

---

## ログ

- ロギングは共通ユーティリティで設定されます（kabusys.utils.logging_setup）。
- 出力先:
  - コンソール（stdout）
  - 日次ローテートされたファイル: logs/<app_name>.log（30日分保持）
- ログレベルは環境変数 LOG_LEVEL または引数で指定できます。

---

## 主要ディレクトリ構成

（リポジトリの src/kabusys 以下を想定）

- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定の読み込みロジック（.env 自動ロード）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 起動前の設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - execution/ — 発注・オーダー管理系コンポーネント（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager など）
  - monitoring/
    - monitoring_db.py — SQLite ベースの永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム稼働・データ鮮度監視
    - trade_monitor.py — 注文／約定の健全性チェック（実装ファイル群）
    - risk_monitor.py — ドローダウン・ポジション数監視
    - kill_switch.py — 停止フラグ管理
    - monitoring_engine.py — 複数モニタの統合ループ
    - alert_manager.py — アラート送信（LINE 等）を管理（実装想定）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 発注数量計算（単元丸め・リスク制限）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM スコアリング
    - regime_detector.py — レジーム判定ロジック
  - tools/
    - paper_verification_report.py — ペーパートレードの検証レポート生成スクリプト
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発上の注意 / 補足

- .env は決して Git にコミットしないでください（config_setup でも注記あり）。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml を探索）で実行されます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- Paper trading（KABUSYS_ENV=paper_trading）の DB は本番と分離されています（data/paper_trading.db）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しは冪等性・リトライ要件が組み込まれていますが、API 失敗時はフェイルセーフでスキップやデフォルト値で継続する設計になっています。
- run_monitoring / run_execution は起動時にプロセス優先度を高めに設定しようとします（権限不足で失敗することあり）。この動作は utils.process_priority が担います。
- PyYAML が無ければ validate_config の YAML 検証はスキップされます（警告表示）。

---

必要であれば、README に含めるサンプル .env テンプレートや詳細な API 仕様（ExecutionEngine / BrokerClient のインターフェース等）、モジュールごとの API リファレンスも作成します。どの情報を追加したいか教えてください。