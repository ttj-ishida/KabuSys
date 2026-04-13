# KabuSys

日本株向け自動売買システムの一部（ライブラリ / 実行スクリプト / モニタリング / 研究用ユーティリティ群）です。  
このリポジトリは取引実行、監視、ポートフォリオ構築、ファクター計算、LLM を用いたニュース解析等のコンポーネントで構成されています。

以下はこのコードベースの概要、機能、セットアップ、実行方法、およびディレクトリ構成です。

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群を含みます：
- execution: ブローカーへの発注、注文状態管理、再同期間処理（Reconciler）
- monitoring: システム状態・注文・リスクの監視、アラート送信（LINE）、ダッシュボード
- portfolio: 候補選定、重み算出、ポジションサイズ計算、リスク調整
- research: ファクター計算・特徴量探索（DuckDB を使ったオンプレミス解析）
- ai: OpenAI を用いたニュースのセンチメント解析・レジーム判定
- tools: ペーパートレード検証レポートなどのユーティリティ

設定は環境変数（またはプロジェクトルートの `.env` / `.env.local`）を通じて読み込まれ、`kabusys.config.Settings` 経由で参照します。

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して発注ループを実行（run_execution.py）
  - Paper trading モード（KABUSYS_ENV=paper_trading）をサポートし、専用の SQLite DB に記録
  - ブローカークライアント抽象化（Mock or 実ブローカー）

- Monitoring
  - SystemMonitor：CPU/Mem/Disk / PID / データ鮮度を監視しログ化
  - TradeMonitor：滞留注文・約定価格異常を検出
  - RiskMonitor：ドローダウンやポジション上限を監視しリスクログへ記録
  - KillSwitch：条件に応じてフラグファイルを書いて Execution を停止
  - AlertManager：LINE Push による通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用モード）

- Portfolio
  - シグナル選定（スコア降順）、等分配 / スコア重み配分
  - セクター集中制限、レジーム乗数、ポジションサイズ計算（単元株丸め、利用可能現金でスケール）

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ

- AI
  - ニュースを LLM（gpt-4o-mini 等）でスコアリングして ai_scores テーブルに保存
  - マクロニュース + ETF MA200 を組み合わせて市場レジーム判定（bull/neutral/bear）

- Tools
  - Paper Trading 検証レポート生成スクリプト（成功率 / レイテンシ / 稼働率 等を評価）

---

## セットアップ手順

前提：
- Python 3.9+（コードは型ヒントに合わせた互換性を想定）
- SQLite は標準ライブラリで利用
- DuckDB、psutil、requests、openai、streamlit 等の外部パッケージが必要

推奨的なインストール例（仮想環境を使用）:

1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit

（プロジェクトによっては追加の依存がある場合があります。requirements.txt があればそちらを使用してください。）

3. 環境変数 (.env)
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先）。
   - 自動読み込みを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数（デフォルト値や説明）：
- KABUSYS_ENV: 起動環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime_detector で必要）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート送信用（未設定時は送信をスキップ）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の注文約定挙動（instant / partial / never / reject。デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: Kill スイッチフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring ポーリング間隔（秒、default 60）

---

## 使い方（実行方法）

いくつかの主要スクリプトの実行例を示します。各スクリプトはパッケージ内のモジュールとして実行できます。

- 監視ループを起動（SystemMonitor を単独で回す簡易起動スクリプト）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 注意: Monitoring は常に本番用の sqlite_path を使用します（環境にかかわらず）。

- ExecutionEngine を起動（発注ループ）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、Paper Trading DB（PAPER_TRADING_SQLITE_PATH）に記録します。
  - 起動時にプロセス優先度を "high" に設定します（プラットフォーム依存でスキップされる場合あり）。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- Streamlit ダッシュボード（監視データ閲覧）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは読み取り専用モードで SQLite を URI 経由で read-only で開きます。

- AI 関連
  - kabusys.ai.score_news（関数 API）：DuckDB 接続と target_date（date）を渡してスコアを生成します。実行には OPENAI_API_KEY が必要です。
  - kabusys.ai.regime_detector.score_regime も同様に使用します。

- その他
  - 各モジュールはライブラリとしてインポート可能です。研究用関数（kabusys.research.*）は DuckDB 接続を引数に取り、SQL と Python で分析を行います。

---

## 注意点 / 実運用上の仕様

- Settings は `.env` / `.env.local` を自動的に読み込みますが OS の環境変数が優先されます。自動ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Paper trading（KABUSYS_ENV=paper_trading）は本番の発注 DB と分離して `PAPER_TRADING_SQLITE_PATH` を使うように設計されています。
- Process 優先度や CPU affinity の設定は psutil を用いて行いますが、権限不足や未対応 OS の場合は警告を出してスキップします。
- OpenAI 呼び出しはリトライロジックやレスポンス検証を組み込んでいます。API キー漏れや 5xx 等はフェイルセーフ（スコア 0.0 やスキップ）で処理される箇所がありますが、適切な監視を行ってください。
- Monitoring の DB 初期化は `init_monitoring_db` で冪等に行われます。既存スキーマに足りないカラムがある場合は簡単なマイグレーション（ALTER）を行います。

---

## ディレクトリ構成（主なファイルと説明）

（src/kabusys 以下）

- __init__.py
  - パッケージメタ情報（__version__ 等）

- config.py
  - 環境変数 / .env 読み込みロジック、Settings クラス

- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）

- run_execution.py
  - ExecutionEngine 起動スクリプト（紙トレードは MockBroker を使用）

- ai/
  - news_nlp.py: ニュースを OpenAI でセンチメント評価して ai_scores に格納
  - regime_detector.py: マクロニュース + ETF MA200 を統合して market_regime を決定
  - __init__.py

- monitoring/
  - monitoring_db.py: SQLite による監視ログ永続化層（テーブル作成・読み書き）
  - system_monitor.py: CPU/メモリ/Disk/PID/データ鮮度監視
  - trade_monitor.py: 滞留注文・約定価格異常検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: フラグファイルで ExecutionEngine 停止指示
  - alert_manager.py: LINE プッシュ通知（クールダウン管理）
  - monitoring_engine.py: 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
  - __init__.py

- execution/
  - order_manager.py: 注文の作成・送信・状態管理（Order State Machine の外向き API）
  - reconciler.py: 起動時の注文/ポジション再同期間処理
  - （その他の broker_factory、order_repository 等の実装が想定される）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算（等分配・スコア加重）
  - position_sizing.py: 単元株丸めを含む発注株数決定ロジック
  - risk_adjustment.py: セクターキャップ・レジーム乗数
  - __init__.py

- research/
  - factor_research.py: Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリ等
  - __init__.py

- tools/
  - paper_verification_report.py: Paper Trading の検証レポート生成 CLI
  - __init__.py

- utils/
  - process_priority.py: プロセス優先度・CPU affinity 設定ラッパー
  - __init__.py

データファイル（デフォルトパス）
- data/kabusys.duckdb    (DuckDB)
- data/monitoring.db      (監視用 SQLite)
- data/paper_trading.db   (ペーパートレード用 SQLite)
- data/execution.pid      (ExecutionEngine の PID)
- data/kill.flag          (KillSwitch が書き込む停止フラグ)

---

## よくある操作例（短い一覧）

- 開発環境で監視を起動
  - KABUSYS_ENV=development python -m kabusys.run_monitoring

- Paper trading 実行（Mock broker）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper 検証レポート（過去期間）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード起動（ローカル）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要に応じて README の特定セクション（例: 環境変数一覧のフォーマット変更、Docker/コンテナ化手順、CI 設定、各モジュールの API 仕様詳細化）を追加できます。どの情報を詳しく追加したいか指示をください。