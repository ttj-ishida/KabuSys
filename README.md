# KabuSys

日本株向け自動売買システムの一部コードベース（監視 / 実行 / ポートフォリオ構築 / リサーチ / AI 補助など）。このリポジトリには実運用に必要な監視・ログ永続化・リスクガードや、バックテスト・リサーチ用のファクター計算ユーティリティ、OpenAI を使ったニュース NLP モジュールなどが含まれます。

以下はこのコードベースの概要、機能、セットアップ手順、使い方、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。本リポジトリ内の主な役割：

- ExecutionEngine（発注・注文管理・リスク管理・リコンシリエーション）
- Monitoring（プロセス監視・注文滞留・リスク監視・アラート）
- Portfolio construction（候補選定・重み計算・ポジションサイズ計算・セクター制約）
- Research（ファクター計算・将来リターン・IC 計算・統計サマリー）
- AI（ニュースの NLP スコアリング、マーケットレジーム判定）
- ツール類（Paper Trading 検証レポート、Streamlit ダッシュボード起動等）

設計方針の例：
- DuckDB / SQLite を用いたデータアクセス
- .env ファイルおよび環境変数による設定
- 本番と paper_trading の分離（paper_trading は専用 DB を使用）
- OpenAI API 呼び出しはフェイルセーフなリトライ実装とレスポンス検証あり

---

## 主な機能一覧

- 監視（Monitoring）
  - システムリソース監視（CPU / メモリ / ディスク）
  - 実行プロセスの存在チェック（PIDファイル）
  - データ鮮度チェック（DuckDB の prices_daily 参照）
  - 注文滞留（stale orders）検出、約定異常価格検出
  - ドローダウン／ポジション上限の自動検出（kill flag 作成）
  - LINE プッシュ通知によるアラート（AlertManager）
  - Streamlit ダッシュボード（監視情報表示）
- 実行（Execution）
  - Broker クライアント抽象化（本番 / モックの切替）
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による起動時リコンシリエーション（注文・ポジションの同期）
  - RiskManager による各種制約（設定に基づく）
- ポートフォリオ構築（Portfolio）
  - シグナルから候補選定、等重／スコア重み計算
  - セクター集中制限の適用
  - ポジションサイズ計算（リスクベース、等分配等）、単元株考慮、aggregate cap
- リサーチ（Research）
  - Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 併用）
  - 将来リターン計算、IC（スピアマン）算出、ファクター統計サマリー
- AI（OpenAI）
  - ニュース記事を集約して LLM による銘柄ごとのセンチメントスコア化（ai_scores へ保存）
  - マクロタイトルを元に市場レジーム（bull/neutral/bear）判定し DB へ保存
  - API 呼び出しは JSON モード・バッチ送信・リトライ・レスポンス検証を行う
- ツール
  - paper_verification_report: paper_trading 用 DB から検証レポート作成（稼働率、成功率、レイテンシ等）
  - streamlit_dashboard: 監視 DB を読み取り UI 表示

---

## 前提条件

- Python 3.10+（コード内で型 `X | Y` を使用しているため）
- システム依存ライブラリ（概ね以下が必要）
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
  - （その他プロジェクトによっては追加の依存がある可能性）

requirements.txt がない場合は最低限以下をインストールしてください（例）:
pip install duckdb psutil openai requests streamlit

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows では .venv\Scripts\activate)
3. 必要パッケージのインストール
   - pip install duckdb psutil openai requests streamlit
   - （もし requirements.txt があれば pip install -r requirements.txt）
4. .env ファイルを作成
   - プロジェクトルートに `.env` や `.env.local` を置くと自動で読み込まれます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 例として最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN=...  （必須）
     - KABU_API_PASSWORD=...      （必須）
     - OPENAI_API_KEY=...         （AI 機能を使う場合必須）
     - KABUSYS_ENV=development|paper_trading|live  （デフォルト development）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  （paper_trading 時に使用）
     - SQLITE_PATH=data/monitoring.db  （監視 DB のデフォルト）
     - DUCKDB_PATH=data/kabusys.duckdb
     - LINE_CHANNEL_ACCESS_TOKEN=... / LINE_USER_ID=...（LINE 通知を使う場合）
     - MONITOR_POLL_INTERVAL=60  （監視ループの間隔（秒））
     - PAPER_FILL_MODE=instant|partial|never|reject  （paper_trading の約定挙動）
   - .env のパースはシェル風の記述（コメント、クォート、export 対応）をサポートします。

5. データディレクトリ作成
   - デフォルトの SQLite / DuckDB ファイルを書き込めるよう data/ ディレクトリを作成してください。
   - 例: mkdir -p data

---

## 使い方

以下は主要なコマンド例です。いずれのスクリプトも package モードで実行できます（python -m kabusys.…）。

- 監視ループ起動（Monitoring）
  - 簡単起動:
    - python -m kabusys.run_monitoring
  - 環境変数でポーリング間隔を変更:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 動作:
    - PID ファイルをチェックし、システムリソース・データ鮮度・注文状態を定期的に評価し、monitoring SQLite DB にログを残します。
    - KABUSYS_ENV に関係なく monitoring は本番の sqlite_path を使用します（デフォルト data/monitoring.db）。

- 実行エンジン起動（Execution）
  - 本番モード（デフォルト development / live に合わせて Broker を切替）:
    - python -m kabusys.run_execution
  - Paper trading モード（MockBrokerClient を使用し paper_trading 用 DB に記録）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Paper trading 用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。

- Streamlit ダッシュボード起動（監視 DB の表示）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り表示します（read-only モードで開くため DB ロックを避けます）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 機能（プログラム呼び出し）
  - ニュース NLP スコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key は環境変数 OPENAI_API_KEY でも可
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- Kill Switch / kill.flag
  - リスク条件（ドローダウン等）により監視モジュールが data/kill.flag を書き込むと ExecutionEngine に停止信号を送ります。
  - Kill flag のパスは Settings.kill_flag_path（デフォルト data/kill.flag）で指定。

- PID 管理
  - ExecutionEngine は起動時に PID ファイル（Settings.pid_file_path）を書き、SystemMonitor はその PID ファイルを参照してプロセス生存を判断します。

---

## 重要な環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- JQUANTS_REFRESH_TOKEN:（必須）J-Quants API 用トークン
- KABU_API_PASSWORD:（必須）kabuステーション API のパスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必須）
- SQLITE_PATH: 監視用 SQLite DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の注文約定挙動）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知利用時に設定

---

## ディレクトリ構成（抜粋）

以下は主要パッケージとファイルの構成です（提供されたコードに基づく抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / .env ロード、Settings クラス
  - run_monitoring.py                — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py   — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py               — monitoring SQLite の初期化とラッパー（MonitoringDB）
    - system_monitor.py              — システム／データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常検出
    - risk_monitor.py                — ドローダウン・ポジション上限監視
    - kill_switch.py                 — kill.flag の作成/管理
    - alert_manager.py               — LINE へ通知（クールダウン付き）
    - monitoring_engine.py           — 複数モニタを束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - execution/
    - order_manager.py               — 発注ハイレベル API
    - reconciler.py                  — 起動時のリコンシリエーション
    - (その他: broker_factory, execution_engine, order_repository, risk_manager など)
  - portfolio/
    - portfolio_builder.py           — 候補選定、重み計算
    - position_sizing.py             — 株数決定・スケーリング
    - risk_adjustment.py             — セクターキャップ、レジーム乗数
    - __init__.py
  - research/
    - factor_research.py             — Momentum/Volatility/Value の計算（DuckDB）
    - feature_exploration.py         — 将来リターン、IC、統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py                    — ニュース集約→OpenAI で銘柄ごとにスコア生成
    - regime_detector.py             — ETF MA + マクロニュースでレジーム判定
    - __init__.py
  - utils/
    - process_priority.py            — プラットフォーム横断的なプロセス優先度 / affinity 設定
    - __init__.py
  - (その他) data/, strategy/ 等（プロジェクト全体の他モジュール）

---

## 開発時の注意・運用上のポイント

- Settings クラスは起動時に .env / .env.local を自動ロードします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効化できます。
- Monitoring の DB 初期化（init_monitoring_db）は起動スクリプトで呼ばれるため通常は手動で準備不要です。ただし DuckDB 用のデータ（prices_daily / raw_financials / raw_news など）は別途用意する必要があります。
- OpenAI の呼び出しは API キーが必要。API 呼び出しに失敗した場合はフェイルセーフで継続しますが、AI 機能は結果の信頼性を保証しないため運用時に注意してください。
- PID ファイル / kill.flag の扱いに注意：プロセスが正常終了しない場合に stale PID が残ると SystemMonitor が検出して削除するロジックが入っています。
- Paper trading モードは本番データと完全に分離して動作するように設計されています（別 DB を使用）。

---

## よくある操作例

- 監視だけを起動（デフォルト間隔 60 秒）:
  - python -m kabusys.run_monitoring

- Paper trading で Execution を実行:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading レポート（過去期間）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード（監視 DB を指定）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

README ではリポジトリの主要構成と実行方法、設定項目の概要を示しました。実際の運用や開発にあたっては、各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、サンプル .env.example や requirements.txt、起動用 systemd ユニット例などの追加ドキュメントも作成できます。希望があればその点も作成します。