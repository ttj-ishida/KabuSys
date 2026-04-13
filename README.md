# KabuSys

日本株向け自動売買システムのコンポーネント群（ライブラリ + 実行スクリプト / ツール群）

概要、監視、発注、ポートフォリオ構築、リサーチ、AI（ニュース NLP / レジーム判定）などの主要ロジックを含むモジュール設計になっています。README はこのリポジトリの一部機能の使い方とセットアップ手順をまとめたものです。

---
## プロジェクト概要
- 目的：日本株の自動売買のためのコアライブラリと、実際の発注／監視／レポート生成を行うランタイムスクリプト群を提供します。
- 設計方針：
  - ビジネスロジック（発注／リスク・監視／ポジション計算等）を純粋関数や明確なクラスに分離
  - DuckDB（時系列・リサーチデータ）と SQLite（監視・トレードログ・注文DB）を使い分け
  - Paper trading 環境は本番 DB と分離（data/paper_trading.db）
  - OpenAI を用いたニュースセンチメントやマクロセンチメントをオプションで利用可能

---
## 主な機能一覧
- 実行（Execution）
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化 / MockBroker による paper_trading 分離
  - 起動時のリコンシリエーション（Reconciler）
  - OrderManager / OrderRepository による注文ライフサイクル管理

- 監視（Monitoring）
  - SystemMonitor（CPU・メモリ・ディスク・プロセス監視・データ鮮度）
  - TradeMonitor（滞留注文・約定異常の検出）
  - RiskMonitor（ドローダウン・ポジション数上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine 停止）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データ可視化）
  - monitoring DB の初期化・永続化層（monitoring_db）

- ポートフォリオ構築（Portfolio）
  - 候補選定、重み付け（等配分・スコア加重）
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、リスクベース配分、集約キャップ）

- リサーチ（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン算出、IC（Information Coefficient）計算、統計サマリー

- AI
  - ニュース NLP による銘柄単位センチメント生成（OpenAI）
  - 市場レジーム判定（ETF MA200 とマクロセンチメントの合成）
  - エクスポート可能な関数群（score_news, score_regime）

- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

---
## 要件（主要ランタイム依存）
- Python 3.10+
- pip パッケージ（例）
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード利用時）
- SQLite は標準ライブラリで利用
- ネットワーク（OpenAI / LINE API を利用する場合）
- （任意）.env ファイルの読み込みのため環境変数設定

---
## 環境変数（代表的なもの）
Settings クラスで読み込む主要な環境変数と意味（.env で設定可能）：

- KABUSYS_ENV: 起動環境（development / paper_trading / live）
  - paper_trading の場合、paper 用専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須で使う機能がある場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須で使う場合）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite パス（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH: ExecutionEngine 用 PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch 用フラグファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

注意:
- Settings モジュールは自動でプロジェクトルートの .env と .env.local を読み込みます（OS 環境変数を優先）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---
## セットアップ手順（ローカル開発向け・簡易）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

3. データディレクトリ作成（必要に応じて）
   - mkdir -p data

4. 必要な環境変数を .env に設定（例）
   - KABUSYS_ENV=development
   - OPENAI_API_KEY=your_openai_key
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

5. DB 初期化
   - monitoring 用 SQLite は各起動スクリプトが init_monitoring_db を呼びます。最初はスクリプトを起動するだけでテーブルが作成されます。

---
## 使い方（主要スクリプト）
- 実行エンジン起動（本番 / paper_trading）
  - python -m kabusys.run_execution
  - 実行時: プロセス優先度を "high" に設定する試みを行います（権限により失敗する場合があります）。
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、別 DB（PAPER_TRADING_SQLITE_PATH）を用います。

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します。

- Streamlit ダッシュボード（監視画面）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを表示します。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI モジュール（プログラム内呼び出し例）
  - ニューススコア（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は DuckDB 接続と target_date を与えて呼び出します。OpenAI API キーは引数または OPENAI_API_KEY 環境変数で渡します。
  - 例（簡易）:
    - python -c "import duckdb, datetime; from kabusys.ai.regime_detector import score_regime; conn=duckdb.connect('data/kabusys.duckdb'); print(score_regime(conn, datetime.date(2026,4,1), api_key=None))"

---
## 動作上の注意・トラブルシュート
- プロセス優先度設定・CPU affinity 設定は psutil を用いています。権限不足で設定に失敗すると警告が出ますが処理自体は継続します。
- run_execution は起動時に PID ファイルを生成（Settings.pid_file_path）し、run_monitoring の SystemMonitor はその PID をチェックします。PID ファイルの権限・パスに注意してください。
- OpenAI API 呼び出しはリトライ(safe backoff) を実装していますが、API キー・レート制限に注意してください。失敗時はフェイルセーフとしてスコアをスキップまたは中立扱いにします。
- DuckDB / SQLite のパスは Settings で指定可能（デフォルトは data 以下）。データファイルの読み書き権限に注意してください。
- monitoring は環境にかかわらず本番の SQLITE_PATH を参照します。paper_trading 用データは PAPER_TRADING_SQLITE_PATH を使う設計です（安全のため、paper_trading 時は別 DB を使用してください）。

---
## ディレクトリ構成（src/kabusys の主要ファイルと簡単な説明）
- __init__.py
  - パッケージの基本情報（__version__ 等）
- config.py
  - 環境変数/.env の自動読み込みと Settings クラス
- run_execution.py
  - ExecutionEngine 起動スクリプト（KABUSYS_ENV に応じ paper_trading を切替）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL）
- execution/
  - order_manager.py: 注文の作成・送信などの外向け API（OrderManager）
  - reconciler.py: 再起動時の注文・ポジション同期処理
  - その他（broker_factory, execution_engine, order_repository などが存在）
- monitoring/
  - monitoring_db.py: SQLite による永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/Disk/process/data freshness の監視
  - trade_monitor.py: 滞留注文・約定価格異常の検出
  - risk_monitor.py: ドローダウン・ポジション上限監視
  - kill_switch.py: kill.flag による Execution 停止指令生成
  - alert_manager.py: LINE 通知用ユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねるループ（テスト用 run_once と本番 run を提供）
  - streamlit_dashboard.py: Streamlit ベースの監視ダッシュボード
- portfolio/
  - portfolio_builder.py: 候補選定・重み付け
  - position_sizing.py: 株数（lot 単位）決定ロジック
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- research/
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン / IC / 統計サマリー等
- ai/
  - news_nlp.py: raw_news→OpenAI→銘柄別センチメントを生成して ai_scores に書込
  - regime_detector.py: ETF MA200 とマクロニュースセンチメントを合成して market_regime を書込
- tools/
  - paper_verification_report.py: Paper Trading 検証用の集計レポート生成スクリプト
- utils/
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

（上記は主要ファイルの抜粋です。細かなモジュールや補助ユーティリティはソースツリーを参照してください。）

---
## 開発メモ / ベストプラクティス
- 環境による挙動差異を小さくするため Settings は .env 自動読み込みを行います。CI やテスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使ってください。
- DuckDB のクエリは時系列データを直接 SQL で処理する設計なので、大規模データを扱う際はインデックス・パーティショニング（ファイル管理）に注意してください。
- AI API の呼び出しは外部依存・コスト・レイテンシの面で影響大です。production ではキー管理、呼び出し頻度の制限、タイムアウト設定を慎重に設計してください。
- Paper Trading を使うときは PAPER_TRADING_SQLITE_PATH を必ず分離して設定すると本番データとの混在を避けられます。

---
必要であれば、README に .env.example の具体例、より詳細な起動引数一覧、Docker / systemd サービスユニット例などを追記できます。どの情報を追加希望か教えてください。