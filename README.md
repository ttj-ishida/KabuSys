# KabuSys

KabuSys は日本株の自動売買システムの骨格ライブラリです。発注エンジン、監視（モニタリング）、ポートフォリオ構築、研究用ファクター計算、ニュース NLP（LLM ベースのセンチメント）などを含みます。このリポジトリは本番運用・Paper Trading（検証）・研究用途のコンポーネントを分離して実装しています。

---

## 主要な特徴（機能一覧）

- 実行（Execution）
  - ExecutionEngine：発注セッションの実行
  - OrderManager / OrderRepository：注文の状態管理と永続化
  - Reconciler：再起動時の注文・ポジション整合性回復
  - RiskManager：発注リスク制御（ポジション上限・利用率・ドローダウン等）
  - BrokerClientFactory：環境に応じたブローカークライアント生成（paper_trading では MockBroker）

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常の検出
  - RiskMonitor：ドローダウン・ポジション上限の監視とアラート記録
  - KillSwitch：条件により ExecutionEngine 停止のためのフラグファイルを書き込む
  - AlertManager：LINE Push でアラート通知
  - MonitoringEngine：上記モニタを束ねるポーリングループ
  - Streamlit ダッシュボード（監視用 UI）

- ポートフォリオ構築（Portfolio）
  - 候補選定、重み算出（等金額 / スコア加重）
  - セクターキャップ適用、レジーム乗数
  - ポジションサイジング（ロット単位丸め・aggregate cap）

- 研究（Research）
  - ファクター計算（Momentum, Volatility, Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ

- AI（LLM）連携
  - news_nlp.score_news：ニュース記事を集約して OpenAI（gpt-4o-mini など）で銘柄別センチメントを算出・保存
  - regime_detector.score_regime：ETF の MA とマクロニュースセンチメントを合成して日次レジーム判定を行い永続化

- ツール
  - paper_verification_report：Paper Trading DB を集計して検証レポートを生成
  - Streamlit ベースの監視ダッシュボード

---

## 動作環境・前提

- Python 3.10+
- 必要な主な外部ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit (ダッシュボード利用時)
- SQLite（組み込みモジュールとして提供されます）

（requirements.txt が別途ある場合はそれを使ってください）

---

## セットアップ手順（ローカル）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係をインストール
   - pip install duckdb psutil openai requests streamlit

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt`）

3. データディレクトリを作成
   - mkdir -p data

4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（読み込みは OS 環境 > .env.local > .env の順。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必要な主要環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (LLM 機能を使う場合)
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（アラート送信）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（研究データ DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定モード: instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH（ExecutionEngine 用 pid ファイル、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、デフォルト: 60）

   サンプル .env:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

---

## 使い方

※ 下記はプロジェクトのルートから実行することを想定しています。

### 監視ループの起動
SystemMonitor をポーリングする簡易スクリプト:
- python -m kabusys.run_monitoring

挙動:
- プロセス優先度を "high" に試みて設定します（psutil を利用）。
- SQLite（monitoring DB）と DuckDB に接続し、監視テーブルを自動で初期化します。
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
- 監視は常に本番用 sqlite_path を使用（KABUSYS_ENV に依らず）。

### ExecutionEngine（発注エンジン）の起動
- python -m kabusys.run_execution

挙動:
- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。本番 DB と分離されます。
- ブローカークライアント、OrderRepository、RiskManager、Reconciler を組み立てて ExecutionEngine を起動します。
- Process priority を "high" に設定します。

### Streamlit ダッシュボード（監視 UI）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

オプション:
- --db で監視 DB のパスを指定可能（デフォルト: data/monitoring.db）
- 読み取り専用で DB を開きます（存在しない場合はエラー表示）。

### Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 期間指定例:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- DB 指定:
  - --db を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

出力内容:
- 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを表示し、 PASS/FAIL で判定します。

### AI（ニュースセンチメント）機能の呼び出し（プログラムから）
- kabusys.ai.score_news(conn, target_date, api_key=None)
  - conn: duckdb.DuckDBPyConnection（prices_daily, raw_news, news_symbols, ai_scores テーブルが前提）
  - target_date: date 型（スコア対象日）
  - api_key: None の場合は環境変数 OPENAI_API_KEY を参照
  - 戻り値: 書き込んだ銘柄数

- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）MA とマクロセンチメントを合成して market_regime テーブルへ保存します

注意:
- OpenAI API 呼び出しを行うため、OPENAI_API_KEY を設定してください。
- API エラーやタイムアウト時のリトライ・フェイルセーフ処理は実装されていますが、API 使用はコストに注意してください。

---

## 重要な振る舞い・運用上のポイント

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

- Paper Trading 分離
  - KABUSYS_ENV=paper_trading の場合、実際の発注処理はモック化され、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録されます（本番 DB と完全分離）。

- モニタリング DB の自動初期化・マイグレーション
  - init_monitoring_db() が存在しないテーブル／カラムを作成し、古い DB には必要なカラムを追加するマイグレーションを行います（冪等）。

- Kill Switch
  - RiskMonitor がドローダウンやポジション上限を検出すると KillSwitch が kill.flag を書き込みます。ExecutionEngine はこのフラグの存在を見て安全停止できます（フラグのクリアは設定次第で実行時に行われます）。

- プロセス優先度
  - 起動スクリプトは set_process_priority("high") を呼び出します。実行環境によっては権限不足で設定できない場合があります（警告ログのみ）。

---

## 主要なディレクトリ構成（抜粋）

（プロジェクトルート /src/kabusys 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py                         — 環境変数読み込み・Settings
  - run_monitoring.py                 — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                  — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py             — プロセス優先度・CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py                — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py          — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - (その他ブローカー・注文関連モジュール)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/ (想定されるデータ格納場所)
    - monitoring.db (SQLite)
    - kabusys.duckdb (DuckDB)
    - paper_trading.db (Paper Trading 用 SQLite)
  - tools/
    - __init__.py
    - paper_verification_report.py

（上記は主要ファイルのみを抜粋しています）

---

## 開発・拡張時のヒント

- DuckDB は分析用データ（prices_daily, raw_financials, raw_news など）を格納する想定です。research モジュールは DuckDB 接続を受け取り SQL＋Python で計算します。
- モジュールは単体テストしやすいように外部依存を注入する設計（DB 接続や API クライアントを引数で受け取る）になっています。LLM 呼び出し部分はテスト時に差し替え可能です。
- Paper Trading の検証レポートや監視ログ（monitoring_db）は本番 DB と分離して利用してください。

---

問題・質問や README に追加してほしい項目があれば教えてください。運用例（systemd / Docker / CI 用の設定例）やサンプル .env、requirements.txt のテンプレート作成も対応します。