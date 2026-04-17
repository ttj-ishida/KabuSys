# KabuSys

日本株向けの自動売買システムのコアライブラリ群です。戦略構築、ポートフォリオ構成、注文実行、監視、調査（リサーチ）、AI によるニュース解析などのコンポーネントを含みます。

以下はこのリポジトリの概要・機能・セットアップ・使い方・ディレクトリ構成の説明です。

注意: これはパッケージ内の主要なモジュール群を説明する README です。実際の運用では環境変数と DB ファイルの配置に注意してください。

---

## プロジェクト概要

KabuSys は次の責務を持つモジュール群で構成されます。

- execution: 注文作成・管理・ブローカー連携・再同期（Reconciler）
- monitoring: システム状態／注文状態／リスク監視、アラート送信、ダッシュボード
- portfolio: 銘柄選定・配分（等配分・スコア配分）、単元丸め、リスク調整
- research: ファクター計算（Momentum/Value/Volatility）、特徴量探索・IC 計算
- ai: ニュース NLP によるセンチメント付与、マクロレジーム判定
- utils: プロセス優先度設定などのユーティリティ
- tools: 検証用スクリプト（例: Paper Trading の検証レポート）

設計方針の一部:
- DuckDB/SQLite を用いたオンプレ DB でのデータ処理
- 外部 API 呼び出し（OpenAI など）は明示的にキーを渡す設計
- ルックアヘッドバイアス回避（date.today()/datetime.today() を直接参照しない設計）
- 冪等性・フェイルセーフ（部分失敗時でも安全に継続）を重視

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアント抽象化（本番 / Mock（paper_trading）切替）
  - OrderManager, OrderRepository による注文管理
  - Reconciler による起動時の自動復旧（Order 照合・ポジション差分検出）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 滞留注文・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag の生成）
  - MonitoringDB: SQLite による監視ログ永続化（schema 自動作成・簡易マイグレーションあり）
  - AlertManager: LINE Push による通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード（read-only 接続可能）

- Portfolio construction
  - 候補選定、等配分／スコア加重、セクター制限、ポジションサイジング、単元丸め、合計投下資金調整等

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー

- AI
  - ニュース記事を LLM に投げて銘柄ごとのスコアを ai_scores に書き込む（news_nlp.score_news）
  - マクロセンチメント＋ETF MA200 を合成して市場レジームを判定し market_regime テーブルへ書込む（regime_detector.score_regime）
  - OpenAI API 呼び出しのリトライ/検証ロジックあり

- Tools
  - paper_verification_report: Paper Trading の検証レポート生成（稼働率・注文成功率・レイテンシ等）

---

## システム要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（代表例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- sqlite3（標準ライブラリ）
- (オプション) LINE 通知を使う場合は LINE Messaging API のチャンネルアクセストークン

インストール例（仮）:
pip install duckdb psutil requests openai streamlit

---

## 環境変数（主なもの）

- KABUSYS_ENV: 起動環境（"development" | "paper_trading" | "live"） — デフォルト "development"
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN: LINE Push 用トークン（任意）
- LINE_USER_ID: LINE Push 宛先ユーザ ID（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定振る舞い（"instant" | "partial" | "never" | "reject"、デフォルト "instant"）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化（"1" で無効）

.env をプロジェクトルート（.git または pyproject.toml を検出する位置）に置くことで自動読み込みされます。
自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化（推奨）
3. 依存パッケージをインストール
   - 例: pip install duckdb psutil requests openai streamlit
4. .env ファイルを作成（.env.example に基づく）
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - ai 機能を使うなら OPENAI_API_KEY
   - LINE 通知を使うなら LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID
5. データディレクトリを作成
   - mkdir -p data
6. （必要に応じて）DuckDB / SQLite DB を初期化する（実行スクリプトが自動でテーブルを作成するため通常は不要）
   - 監視 DB は起動時に init_monitoring_db() によって作成されます

---

## 使い方（よく使うコマンド / 実行方法）

パッケージ形式で提供されているため、python -m を使ってモジュールとして起動できます。

- 実行エンジン（注文実行）を起動
  - 本番相当:
    KABUSYS_ENV=live python -m kabusys.run_execution
  - Paper Trading（MockBroker を使用し paper DB に分離）:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - PAPER_FILL_MODE 環境変数で約定モードを切替可能（instant/partial/never/reject）
  - 実行時に data/execution.pid（デフォルト）に PID が書き込まれます。停止は kill.flag を作成するか、プロセスに SIGINT を送るなど。

- 監視（SystemMonitor 単体）を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き（デフォルト 60）
  - 監視は常に本番の sqlite_path を使用して monitoring DB に書き込みます（環境にかかわらず）

- Paper Trading 検証レポート生成（コマンドライン）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで SQLite パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH を優先）

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 起動時に読み取り専用 (URI ?mode=ro) で接続するため、監視中の DB を参照できます

- AI モジュールの利用（Python API）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")  # conn は DuckDB 接続
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  どちらも OPENAI_API_KEY が必要（api_key を渡すか環境変数を設定）。

---

## 停止 / フラグファイル（運用）

- 停止要求（run_monitoring / run_execution）は data/stop_requested.flag をチェックしており、該当ファイルが存在するとループを抜けます。
- ExecutionEngine の強制停止トリガ（Kill Switch）は data/kill.flag に理由文を記述して作成します。KillSwitch はリスクアラート（ドローダウン・ポジション数超過）でフラグを書き込みます。
- PID ファイル:
  - ExecutionEngine は起動時に PID を data/execution.pid に書き込みます。SystemMonitor はこのファイルを見てプロセスの存否を監視し、stale PID を検出したら削除します。

---

## 主要なコードモジュール（簡単な説明）

- kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト。BrokerFactory によるブローカー選定、OrderManager/RiskManager/Reconciler の組み立て、スレッドで engine.run_session を実行。

- kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を設定可能。

- kabusys/config.py
  - 環境変数の読み込み・解析。プロジェクトルート基準で .env/.env.local を自動ロード（無効化可）。
  - Settings クラスに主要設定をまとめる。

- kabusys/monitoring/
  - monitoring_db.py: SQLite テーブル定義・簡易マイグレーション・読み書きラッパー（MonitoringDB）
  - system_monitor.py, trade_monitor.py, risk_monitor.py: 各種チェックロジック
  - monitoring_engine.py: 各 Monitor を束ねてポーリング、AlertManager と KillSwitch の連携
  - alert_manager.py: LINE Push 実装
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）

- kabusys/execution/
  - order_manager.py, order_repository.py, order_record.py, reconciler.py, execution_engine.py 等: 注文管理・同期・リコン・実行ロジック（Engine 実装は完全にはここに無いファイルもありますが主要パターンを含む）

- kabusys/portfolio/
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py: 候補選定・重み計算・サイズ決定・セクター制限

- kabusys/research/
  - factor_research.py: Momentum/Volatility/Value の計算
  - feature_exploration.py: 将来リターン・IC・統計サマリー

- kabusys/ai/
  - news_nlp.py: ニュースを LLM で評価して ai_scores に書き込む
  - regime_detector.py: ETF MA200 と LLM マクロセンチメントを合成して市場レジーム判定

- kabusys/utils/
  - process_priority.py: プロセス優先度 / CPU affinity の設定ユーティリティ

---

## ディレクトリ構成

（src/kabusys 以下を抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_execution.py
    - run_monitoring.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
      - streamlit_dashboard.py
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - (その他 execution 関連モジュール)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py
      - __init__.py
    - data/ (ランタイムで使用するディレクトリ: DB/flag/pid 等を配置)

---

## 開発上の注意 / ヒント

- 環境変数は .env/.env.local に記載しておくと便利。自動ロードはプロジェクトルートを .git か pyproject.toml を基準に検出します。
- Paper Trading モードは本番 DB とは分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI を使う機能は API 呼び出しに対して堅牢性（リトライ・パース検証）を組み込んでいますが、API キー管理・レート制限には注意してください。
- DuckDB を用いる調査モジュールは prices_daily / raw_financials 等のテーブル構造を前提としています。実データ投入とテーブル整備が必要です。
- テスト目的で自動環境変数ロードを抑制するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

必要に応じて README に実運用サンプル（systemd ユニットファイル、Dockerfile、CI スクリプトなど）を追加できます。README の補足や特定モジュールの詳細ドキュメント化（Engine の実行フロー、OrderState 遷移図など）も対応可能です。どの部分をより詳しく記載したいか教えてください。