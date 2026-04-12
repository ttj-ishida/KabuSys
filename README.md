# KabuSys

日本株自動売買システム KabuSys のリポジトリ向け README（日本語）。

この README はコードベース（src/kabusys 配下）を元に作成しています。各モジュールの設計意図や起動手順、主要な環境変数、ディレクトリ構成をまとめています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動 / 実行コマンド）
- 主要環境変数
- ディレクトリ構成（ファイル一覧と説明）
- 運用上の注意

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムです。  
主に以下の責務を持つモジュール群で構成されています：

- 注文生成・発注管理（OrderManager、ExecutionEngine、BrokerClient）
- リコンシリエーションと起動時の復旧処理（Reconciler）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイジング、リスク補正）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor、KillSwitch、AlertManager、Streamlit ダッシュボード）
- 研究（ファクター計算、特徴量探索、IC 計算）
- AI（OpenAI を使ったニュースセンチメント、レジーム検出）
- 運用ツール（Paper Trading 検証レポート等）

設計方針の一部：
- DuckDB / SQLite をデータストアとして使用（分析用は DuckDB、監視等は SQLite）
- Paper Trading と本番 DB を分離（paper_trading 環境では別 SQLite を使用）
- ルックアヘッドバイアスを避ける（日時参照に注意）
- API 呼び出しはフェイルセーフ（失敗時は安全にフォールバック）

---

## 主な機能一覧

- Execution
  - 注文の作成、送信、状態同期（OrderManager, OrderRepository）
  - Broker クライアントの抽象化（本番/モックの切り替え）
  - 起動時の自動リコンシリエーション（Reconciler）
- Monitoring
  - システムリソース・プロセス有無・データ鮮度監視（SystemMonitor）
  - 注文滞留・約定異常検出（TradeMonitor）
  - ドローダウンやポジション上限の監視（RiskMonitor）
  - Kill Switch（ルールに基づき ExecutionEngine 停止を指示するフラグファイル生成）
  - LINE によるアラート通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分・スコア重み配分
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、利用可能現金とのスケーリング）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）や統計サマリー
- AI
  - ニュース NLP による銘柄センチメント（OpenAI）
  - マクロニュース + ETF MA を使った市場レジーム判定（OpenAI）
- Tools
  - Paper Trading 検証レポート生成（data/paper_trading.db を参照）
  - その他 CLI / スクリプト

---

## セットアップ手順

前提：
- Python 3.9+（コードは型注釈等を利用しているため、3.9 以上を推奨）
- Git レポジトリのルートに .env / .env.local を置けること（自動ロード機能あり）

1. 仮想環境を準備
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt / poetry / pyproject.toml で依存管理してください。

3. 環境変数の設定
   - リポジトリルートに .env を作成するか、OS 環境変数で設定します。
   - 自動ロードはデフォルトで有効。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

4. データディレクトリの用意
   - data ディレクトリを作成し、必要なら DuckDB / SQLite の初期ファイルを置く。
   - Paper Trading 用 DB はデフォルトで data/paper_trading.db を使用します（KABUSYS_ENV=paper_trading の場合）。

注：psutil を使ったプロセス優先度 / CPU affinity 設定は権限が必要になる場合があります。Linux で high 優先度を設定する場合は権限に注意してください。

---

## 使い方

ここでは主要な起動コマンドと環境変数の例を示します。パッケージをインストール済み、カレントディレクトリがプロジェクトルート（src を含む）であることを前提とします。

- ExecutionEngine を起動（本番 / paper_trading 切り替え）
  - 簡易起動：
    - export KABUSYS_ENV=development
    - python -m kabusys.run_execution
  - Paper Trading（ブローカーは Mock、DBは data/paper_trading.db）
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution

  実行フロー（run_execution.py）：
  1. プロセス優先度を high に設定（psutil を使用）
  2. SQLite（paper_trading 時は専用 DB）と DuckDB に接続
  3. Broker クライアント生成（設定により Mock/実ブローカー）
  4. OrderRepository / OrderManager / RiskManager / Reconciler 等を組み立て ExecutionEngine を run_session() で開始

- Monitoring を起動（常駐ポーリング）
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可（デフォルト 60 秒）
  - python -m kabusys.run_monitoring

  実行フロー（run_monitoring.py）：
  1. プロセス優先度を high に設定
  2. monitoring 用 DB（環境に関係なく本番 sqlite_path を使用）を開きテーブルを初期化
  3. SystemMonitor を初期化して check_once() をポーリング

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - あるいはパッケージ経由で run する場合は DB のパスを指定してください。

- Paper Trading 検証レポート（CLI）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite パスを指定できる（環境変数 PAPER_TRADING_SQLITE_PATH でも指定可）

- AI / レジーム検出・ニューススコア
  - OpenAI API を呼び出す機能（kabusys.ai.news_nlp / kabusys.ai.regime_detector）は OPENAI_API_KEY 環境変数（または関数引数）を必要とします。
  - API 呼び出しは retry/backoff を備えており、失敗時は安全側のデフォルト値（0.0 等）でフォールバックします。

---

## 主要環境変数

必須（少なくとも開発や一部機能で必要）：
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（Settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API 用パスワード（Settings.kabu_api_password）

運用 / オプション：
- KABUSYS_ENV — 起動環境（development | paper_trading | live）。デフォルト: development
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）。デフォルト: INFO
- DUCKDB_PATH — DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視用 SQLite パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — Paper Trading における注文の約定挙動（instant|partial|never|reject）
- PID_FILE_PATH — ExecutionEngine PID ファイルのパス（kill / stale PID チェック）
- KILL_FLAG_PATH — Kill Switch のフラグファイル（デフォルト: data/kill.flag）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化

.env ファイルはリポジトリルート（.git や pyproject.toml のあるディレクトリ）から自動で読み込まれます。.env.local は上書き（override）されます。テスト時や特殊な状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化してください。

---

## ディレクトリ構成（主要ファイルの説明）

以下は src/kabusys 配下の主要モジュールと簡単な説明です（リポジトリの全ファイルを網羅）。実際のファイル構成はこの README のとおりでない場合がありますが、コードベースに基づいた説明です。

- src/kabusys/__init__.py
  - パッケージ定義、バージョン（__version__ = "0.1.0"）
- src/kabusys/config.py
  - 環境変数読み込み・設定管理（Settings クラス）
  - .env 自動ロード、各種デフォルトパスやバリデーション
- src/kabusys/run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV による paper_trading 切替）
- src/kabusys/run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- src/kabusys/tools/
  - paper_verification_report.py：Paper Trading の検証レポート生成 CLI
- src/kabusys/portfolio/
  - portfolio_builder.py：候補選定、等重／スコア重み計算
  - position_sizing.py：株数決定、単元丸め、利用可能現金でのスケーリング
  - risk_adjustment.py：セクター上限、レジーム乗数計算
- src/kabusys/monitoring/
  - monitoring_db.py：SQLite による監視テーブル定義 と MonitoringDB ラッパー
  - system_monitor.py：CPU/メモリ/ディスク、プロセス存在、データ鮮度の監視
  - trade_monitor.py：滞留注文・約定異常検出
  - risk_monitor.py：ドローダウン・ポジション上限監視
  - kill_switch.py：kill.flag 書き込みロジック
  - alert_manager.py：LINE Push 通知（クールダウン管理あり）
  - monitoring_engine.py：複数モニタを束ねるポーリングエンジン
  - streamlit_dashboard.py：監視ダッシュボード（Streamlit）
- src/kabusys/execution/
  - order_manager.py：注文状態遷移・発注ワークフロー
  - reconciler.py：起動時の自動復旧・ブローカー照合
  - ※ ExecutionEngine / broker_factory などは別ファイルに存在（run_execution から参照）
- src/kabusys/research/
  - factor_research.py：Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - feature_exploration.py：将来リターン、IC、統計サマリー
- src/kabusys/ai/
  - news_nlp.py：ニュース記事をまとめ OpenAI でセンチメント評価 → ai_scores へ書込
  - regime_detector.py：ETF MA + LLM マクロセンチメントを合成して market_regime を算出
- src/kabusys/utils/
  - process_priority.py：プラットフォーム差を吸収したプロセス優先度 / CPU affinity 設定ユーティリティ

注：実運用ではさらに data / logs / config などのディレクトリが存在することを想定しています。

---

## 運用上の注意（重要）

- Paper Trading と本番 DB は分離してください。KABUSYS_ENV=paper_trading を利用すると paper_sqlite_path に記録されます。
- OpenAI を使う機能は API コストとレート制限に注意してください。コードはリトライとバックオフを備えていますが、キーや使用方針は慎重に管理してください。
- プロセス優先度（high）へ変更するために psutil を利用しています。一部環境では権限不足で設定が失敗する場合があります（警告ログが出ますが処理は継続されます）。
- kill.flag による停止は冪等に実装されていますが、運用上は手動での確認フローを整えてください。
- DuckDB / SQLite のファイルパスは Settings により容易に変更できます。バックアップやパーミッション管理を怠らないでください。
- .env の解析はシンプルなシェル形式に対応していますが、特殊な文字列や複雑な構成は想定外の挙動になる場合があります。

---

必要であれば以下を追加で提供できます：
- サンプル .env.example（推奨環境変数のテンプレート）
- requirements.txt / pyproject.toml の推奨内容
- より詳細な運用手順（デプロイ / systemd / docker コンテナ化 など）

ご希望があれば、上記いずれかを作成します。