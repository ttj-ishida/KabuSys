# KabuSys

日本株向けの自動売買 / リサーチ基盤ライブラリ群および起動スクリプト群です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ファクター計算やポートフォリオ構築、AI ベースのニュース解析などの主要コンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つモジュール群で構成されています。

- 発注ロジック（ExecutionEngine） — 実際の or ペーパートレードの発注処理
- 監視（Monitoring） — システム状態・注文状態・リスク監視、Kill Switch
- ポートフォリオ構築（Portfolio） — 候補選定、重み付け、ポジションサイズ計算
- リサーチ（Research） — ファクター計算・特徴量探索・IC 評価
- AI（AI） — ニュースのセンチメント解析や市場レジーム判定（OpenAI）
- ツール（Tools） — Paper Trading の検証レポートなど
- ユーティリティ（Utils） — ログ設定・プロセス優先度設定、設定読み込み等

設計上の注意点：
- .env（環境変数）から設定を読み込みます（自動ロード機能あり）。.env は絶対にコミットしないでください。
- Paper Trading（KABUSYS_ENV=paper_trading）の場合、発注はモッククライアントへ送られ、専用 SQLite（data/paper_trading.db）が使用され、本番データとは分離されます。
- 監視コンポーネントは環境に関わらず本番用の sqlite_path を参照して監視ログを書きます（monitoring は常に production DB パスを使う実装）。

---

## 主な機能一覧

- Execution
  - ExecutionEngine によるセッション実行（実発注 / ペーパートレード対応）
  - ブローカークライアントのファクトリ（実運用/モック切替）
  - リスクマネージャ（ポジション上限・ドローダウン等）
  - OrderRepository / OrderManager / Reconciler 等

- Monitoring
  - SystemMonitor: CPU/メモリ/Disk/プロセス生存チェック、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs 監視）
  - RiskMonitor: ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch: 条件で data/kill.flag を書き込むことで ExecutionEngine を停止可能
  - MonitoringEngine: 上記モニタを束ねたポーリングループ

- Portfolio
  - 候補選定（スコア降順）
  - 等重・スコア加重の重み計算
  - セクターキャップ適用
  - ポジションサイジング（リスクベース / 等配分など）、単元株丸め、aggregate cap

- Research
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を利用）
  - 将来リターン・IC（Spearman）・統計サマリ

- AI
  - ニュースセンチメント評価（OpenAI を用いた LLM 呼び出し、スコアを ai_scores に保存）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）

- Tools
  - Paper Trading 検証レポート生成スクリプト（成功率・レイテンシ・稼働率等を評価）

- Utilities
  - ログ設定（コンソール + 日次ローテーションファイル）
  - プロセス優先度 / CPU affinity 設定
  - 設定ウィザード（.env の対話的生成）
  - 設定検証 CLI（config/*.yaml の存在チェック, 必須環境変数チェック）

---

## セットアップ手順

1. Python 環境準備
   - 推奨: Python 3.10+
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（必要なもの）
   - duckdb
   - psutil
   - openai  (AI 機能を使う場合)
   - PyYAML (config 検証で YAML 内容チェックをする場合に必要)
   - （実運用で J-Quants 等のクライアントが必要であれば別途）
   - 例:
     - pip install duckdb psutil openai pyyaml

   ※ requirements.txt がない場合は上記を手動でインストールしてください。

3. .env の作成
   - 対話式ウィザードを使う:
     - python -m kabusys.config_setup
   - あるいは .env を自分で作成（.env.example を参考に）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - PAPER_FILL_MODE（ペーパートレードの約定モード: instant | partial | never | reject、デフォルト: instant）
     - LOG_LEVEL（DEBUG/INFO/...）

   - .env は絶対にリポジトリへコミットしないでください。

4. 設定検証（起動前のチェック）
   - python -m kabusys.validate_config
   - 問題があればメッセージが出ます。警告も FAIL 扱いにしたい場合は --strict を付けてください。

5. データディレクトリ / ログディレクトリ自動作成
   - デフォルトでは data/ と logs/ を使用します。必要に応じて手動作成しても OK。

---

## 使い方（起動 & CLI）

主なエントリポイント（モジュールとして実行）:

- ExecutionEngine を起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
    - 起動時に data/stop_requested.flag が存在すると起動を中止します。
    - 実行中は data/execution.pid に PID を書き込みます。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。
  - 監視は settings.sqlite_path（デフォルト: data/monitoring.db）を使用してログを保存します（環境に関係なく本番パスを使用する挙動）。
  - 停止には data/stop_requested.flag を作成するか KeyboardInterrupt。

- 設定ウィザード（.env 生成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict をつけると警告があると exit 1 になります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で PAPER_TRADING_SQLITE_PATH を明示的に指定可能

- AI 関連（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を与えてニューススコアを ai_scores テーブルへ書き込みます。
    - OPENAI_API_KEY または api_key を必須で設定してください。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジームを計算して market_regime テーブルへ書き込みます。

--- 

## 停止 / Kill Switch / フラグファイル

- 停止フラグ（外部からの停止要求）:
  - data/stop_requested.flag — run_execution, run_monitoring などが起動時/ループ中に参照します。存在すると起動を止める/ループを抜けます（run_monitoring, run_execution が利用）。
  - data/kill.flag — KillSwitch が書き込むファイル。ExecutionEngine に停止シグナルを与えるために監視が書き込みます。ExecutionEngine 起動時に KILL_FLAG_CLEAR_ON_START の設定により自動でクリアすることができます（本番では 0 推奨）。

- PID ファイル:
  - data/execution.pid — ExecutionEngine が書き込みます（監視が stale PID を検出するロジックあり）。

注意: フラグファイルを作成/削除する際は適切な操作手順を守ってください（特に本番環境では自動クリアは避けること）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV — execution モード: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY — OpenAI を使う場合に必要
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant | partial | never | reject）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL — monitoring のポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動でクリアするか（"1" でクリア、デフォルト "0"）

---

## ログと DB の場所（デフォルト）

- ログ: logs/<app_name>.log（app_name は "execution" や "monitoring" 等）
- DuckDB: data/kabusys.duckdb
- 監視 SQLite: data/monitoring.db
- Paper Trading SQLite: data/paper_trading.db
- フラグ & PID: data/kill.flag, data/stop_requested.flag, data/execution.pid

ログは kabusys.utils.logging_setup.setup_logging により stdout と日次ローテーションファイルへ出力されます。

---

## ディレクトリ構成（要約）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings
- config_setup.py — .env 作成ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュース NLP（OpenAI 利用）
  - regime_detector.py — 市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite 永続化層
  - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py (等)
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py (等)
- portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research/
  - factor_research.py, feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py, process_priority.py
- data/ (実行時に作成される想定)
- logs/ (ログ出力先)

（上記は主要ファイルの抜粋です。すべての実装ファイルは src/kabusys 以下に配置されています。）

---

## 開発・運用上の注意

- .env をリポジトリにコミットしないでください。
- 本番環境（KABUSYS_ENV=live）では LINE 通知設定などを必ず確認してください（validate_config で警告が出ます）。
- OpenAI API を使用する処理は外部 API 依存であり、API レート制限や可用性に注意してください。失敗時は多くの箇所でフェイルセーフ（0 戻し等）を持っていますが、運用監視を推奨します。
- Monitoring は監視ログテーブルの作成・マイグレーション処理を行います。DB のスキーマ互換に注意してください。
- process_priority 設定は psutil を使って OS に依存した操作を行います。権限不足により警告が出る場合があります。

---

## 参考コマンド集

- .env 作成（ウィザード）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動
  - python -m kabusys.run_execution
- Monitoring 起動
  - python -m kabusys.run_monitoring
- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

---

README はここまでです。必要であれば以下の追加情報を作成できます:
- 具体的な .env.example（テンプレート）
- systemd / Supervisor 用の起動ユニット例
- 開発用のテスト手順 / 単体テストの説明

どれを追加しますか？