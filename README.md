# KabuSys

日本株向けの自動売買システム（ライブラリ/ツール群）の簡易ドキュメントです。  
このリポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などを含むモジュール群から構成されています。

## プロジェクト概要
KabuSys は以下の機能を持つモジュール群を含む Python ベースの自動売買プラットフォームです。

- 実行エンジン（ExecutionEngine）: ブローカーへの発注、注文状態管理、リコンシリエーション
- 監視（Monitoring）: システム稼働状態、注文滞留、約定異常、リスク（ドローダウン・ポジション上限）検出、Kill Switch（停止フラグ）
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ決定、セクター制約・レジーム補正
- リサーチ: ファクター計算（Momentum / Value / Volatility 等）と特徴量解析（IC 等）
- AI モジュール: ニュースのセンチメントスコア（OpenAI）や市場レジーム判定
- 運用ツール: ペーパートレード検証レポート出力、Streamlit ベースの監視ダッシュボード

設計上のポイント:
- DuckDB（時系列・ファクターデータ）と SQLite（監視ログ / 注文ログ等）を併用
- Paper trading は本番 DB と完全分離（専用 SQLite）
- LLM 呼び出しはフェイルセーフに設計（リトライ、フォールバック値）

## 機能一覧
主な機能（抜粋）:

- run_monitoring.py — SystemMonitor ポーリングループ起動。MONITOR_POLL_INTERVAL でポーリング間隔変更可。
- run_execution.py — ExecutionEngine 起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper DB に記録。
- monitoring モジュール
  - MonitoringDB: SQLite スキーマ初期化 / read/write API
  - SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, AlertManager
  - MonitoringEngine: 各種モニタを束ねポーリング／通知
  - Streamlit ダッシュボード（監視用）
- execution モジュール
  - OrderManager、Reconciler 等（注文状態管理、再起動時の同期）
- portfolio モジュール
  - 候補選定、スコア加重／等重配分、ポジションサイズ計算、セクターキャップ、レジーム乗数
- research モジュール
  - ファクター計算（momentum, value, volatility）、forward returns、IC、summary 等
- ai モジュール
  - news_nlp.score_news（OpenAI を用いたニュースセンチメント）
  - regime_detector.score_regime（MA とマクロ NLP 合成による日次レジーム判定）
- tools
  - paper_verification_report.py：Paper Trading の検証レポート生成（稼働率 / 注文成功率 / レイテンシ等）

## セットアップ手順（ローカル開発向け）
以下は一般的な準備手順です。プロジェクトに requirements.txt がない場合は下記の主要依存をインストールしてください。

1. リポジトリをチェックアウト
   - git clone <repo-url>
2. 仮想環境を作成して有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests streamlit openai
   - （開発用に pip install -e . が使える場合は適宜）
4. 環境変数を設定（.env / .env.local をプロジェクトルートに置くか、環境変数をエクスポート）
   - 自動読み込みはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
   - 主な環境変数（主要なもののみ）:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: Monitoring SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知（AlertManager）用
     - PID_FILE_PATH, KILL_FLAG_PATH: 実行 / 停止フラグ用パス
5. データディレクトリ作成
   - mkdir -p data

注意: 実行前に DuckDB / prices_daily や raw_financials 等のテーブルを準備する必要があります（データ投入は別途）。

## 使い方（主要スクリプト・コマンド）
以下は代表的な起動方法とオプション例です。

- 監視ループを起動
  - 環境変数でポーリング間隔を上書き可能（秒単位）
    - export MONITOR_POLL_INTERVAL=30
  - 起動:
    - python -m kabusys.run_monitoring
  - 説明:
    - SQLite（settings.sqlite_path）に接続し監視テーブルを初期化してポーリングを開始します。
    - MONITOR は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します。

- 実行エンジンを起動（取引用）
  - 本番:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパートレード（MockBroker・別 DB を使用）:
    - export KABUSYS_ENV=paper_trading
    - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
    - python -m kabusys.run_execution

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション --db で DB パスを指定可（環境変数 PAPER_TRADING_SQLITE_PATH と同様の優先度）

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（DB が存在しない場合は MonitoringEngine を先に起動してください）。

- AI 機能（プログラム呼び出し）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key が None なら OPENAI_API_KEY を使う
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

注意点:
- OpenAI 呼び出しは API キー必須。エラー時はフェイルセーフ（既定値やスキップ）で継続する設計です。
- run_execution 内で RiskConfig の初期_portfolio_value は broker.get_available_cash() を使用して決定します。

## 環境変数（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使用する場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行 PID / 停止フラグのパス
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager による LINE 通知用
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

Settings クラスは .env / .env.local を自動読み込みします（プロジェクトルートは .git または pyproject.toml を基準に探索）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

## 重要な設計・運用ノート
- Paper trading は本番 DB と完全に分離されています（別 SQLite）。安全に検証できます。
- Monitoring の DB 初期化（テーブル作成・マイグレーション）は init_monitoring_db() により冪等に実行されます。run_monitoring/run_execution は起動時にこれを呼び出します。
- Kill Switch は data/kill.flag を作成して ExecutionEngine に停止指示を出します。Kill ファイルは既存なら上書きせず冪等に動作します。
- Process 優先度 / CPU affinity 設定ユーティリティ（psutil ベース）はプラットフォーム差分を吸収しますが、権限不足時は警告のみでスキップします。
- AI によるスコアリングは JSON 出力の妥当性検証・スコアクリップ・リトライ等の耐障害策を備えています。

## ディレクトリ構成
主要ファイル・ディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — Settings / .env 読み込みロジック
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他 execution 関連モジュール: broker_factory, order_repository 等)
  - utils/
    - process_priority.py

data/ 配下（推奨）
- data/kabusys.duckdb         — DuckDB（時系列・ファクターデータ）
- data/monitoring.db          — 監視ログ SQLite（デフォルト）
- data/paper_trading.db       — ペーパートレード用 SQLite（paper_trading モード）
- data/execution.pid          — 実行 PID ファイル
- data/kill.flag              — Kill Switch フラグファイル

## 開発・拡張のヒント
- DuckDB 上のテーブル（prices_daily, raw_financials, raw_news 等）が想定どおりに整備されていることを確認してください。research / ai モジュールはこれらのテーブルを前提に動作します。
- AI 関連のユニットテストでは OpenAI 呼び出し関数をモックする設計になっています（_call_openai_api を patch するなど）。
- position_sizing 等の純粋関数は DB 参照を行わないため単体テストが容易です。
- run_execution の起動時にリコンシリエーション（Reconciler）を実行することでクラッシュ後の自動復旧が行われます。

---

問題や追加で README に載せたい内容（例: CI 手順、詳細な環境変数一覧、データスキーマ定義など）があれば教えてください。必要に応じてサンプル .env.example も作成します。