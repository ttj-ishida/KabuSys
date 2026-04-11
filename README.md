KabuSys — 日本株自動売買システム
=================================

このリポジトリは、教育/研究用の日本株自動売買フレームワーク「KabuSys」のコア実装（取引実行、監視、ポートフォリオ構築、ファクター研究、LLM を用いたニュース解析など）を含みます。README はコードベースの主要コンポーネントと使い方をまとめた日本語ドキュメントです。

主な特徴
--------
- ExecutionEngine：Signal Queue ベースの発注エンジン（発注ゲート／リスク管理／リコンシリエーション）
- Broker 抽象化：本番ブローカー / Paper Trading（モック）切替
- Monitoring：システム稼働監視、注文滞留・約定異常・ドローダウン監視、LINE 通知、kill.flag による外部停止
- DB 層：DuckDB（時系列・ファクター・ニュース等）と SQLite（監視ログ・オーダー管理）
- Portfolio：候補選定、重み付け、ポジションサイズ計算、セクター制約・レジーム調整
- Research：ファクター計算（モメンタム/ボラティリティ/バリュー）、前方リターン・IC・統計サマリ
- AI：OpenAI（gpt-4o-mini）を使ったニュースセンチメント付与・市場レジーム判定（フェイルセーフ実装）
- Streamlit ダッシュボード：監視情報・ポジション・注文ログの可視化

セットアップ（開発環境）
---------------------
前提
- Python 3.10 以上（型注釈の表現や pathlib の利用に依存）
- git

推奨手順（UNIX 系）
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

3. 必要パッケージをインストール
   必要となる主要パッケージ（コード中の import を参照）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   例:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

4. PYTHONPATH を通す（ローカル実行時）
   - export PYTHONPATH=$(pwd)/src
   もしくはパッケージとしてインストール:
   - pip install -e .

環境変数（主要）
-----------------
Settings（src/kabusys/config.py）で管理される主要な環境変数（一部）：

必須（実際の運用で使用する場合）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）

任意 / 推奨
- OPENAI_API_KEY — OpenAI API キー（AI 機能を利用する場合）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。paper_trading はモックブローカーを使用
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_FILL_MODE — paper_trading の成行挙動: instant | partial | never | reject（デフォルト: instant）
- PID_FILE_PATH, KILL_FLAG_PATH — 実行プロセスの PID / kill フラグファイル
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒; デフォルト 60）
- LOG_LEVEL — ログレベル

.env の自動読み込み
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

使い方（起動例）
----------------

1) 実行エンジン（Execution）
- 目的：当日のシグナルに基づく発注・WebSocket ドレイン・実行ループを起動します。
- 実行方法（ソース直下から）:
  - PYTHONPATH を通した状態で:
    - python src/kabusys/run_execution.py
  - またはインストール済みパッケージとして:
    - python -m kabusys.run_execution
- 挙動:
  - 起動直後にプロセス優先度を high に設定（psutil に依存、権限により失敗する場合あり）
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（data/paper_trading.db 等）を使用して本番 DB と分離
  - 実行中は pid ファイルを書き込み、kill.flag による停止シグナルをチェック

2) 監視ループ（Monitoring）
- purpose：システム稼働状況、データ鮮度、注文滞留、リスクイベント等を定期的にチェックし、DB にログ・必要に応じて通知／kill.flag を書きます。
- 実行方法:
  - python src/kabusys/run_monitoring.py
  - 環境変数 MONITOR_POLL_INTERVAL でループ間隔を秒単位で上書き（デフォルト 60 秒）
- 挙動:
  - Monitoring は常に「本番用」sqlite_path（Settings.sqlite_path）を使用して監視用 DB を記録します
  - システム監視（CPU/Mem/Disk/プロセス）、注文監視、ドローダウン監視、KillSwitch 判定、LINE 通知などを実行

3) Streamlit ダッシュボード（監視可視化）
- 起動例:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明: monitoring DB を read-only で開き、Overview / Positions / Orders / System タブを提供します

4) AI / リサーチ機能（個別実行）
- ニューススコア付与:
  - kabusys.ai.score_news(conn, target_date, api_key=...)
  - DuckDB 接続を渡して、raw_news から銘柄別センチメントを生成し ai_scores テーブルに書き込みます
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
- 研究用関数:
  - kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic 等

運用上の注意
------------
- psutil によるプロセス優先度設定や cpu_affinity は OS と権限に依存します。失敗しても警告を出して継続します。
- OpenAI 呼び出しは外部 API を伴うため、API キーの管理とレート制限・エラーハンドリングに留意してください。コードにはリトライ・フォールバックの仕組みがあります（失敗時はスコアを省略またはデフォルト処理）。
- Paper Trading モード（KABUSYS_ENV=paper_trading）は本番 DB とは独立した paper_sqlite_path を使用する設計です。テスト用途で利用してください。
- kill.flag による停止は冪等に扱われます（既に存在する場合は再書き込みしない）。ExecutionEngine 起動時にフラグをクリアしたい場合は設定で制御してください（Settings.kill_flag_clear_on_start）。

ディレクトリ構成（概要）
---------------------
（主要ファイル / モジュールのみ抜粋）

- src/kabusys/
  - __init__.py                      — パッケージ定義
  - config.py                        — 環境変数 / Settings 管理（.env 自動読み込み機能含む）
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor ポーリングスクリプト
  - utils/
    - process_priority.py            — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - execution_engine.py            — ExecutionEngine（発注ループ・プッシュ処理）
    - order_manager.py               — OrderManager（発注 API 抽象）
    - reconciler.py                  — 起動時リコンシリエーション
    - order_repository.py            — DB レイヤ（Orders）
    - broker_factory.py              — BrokerClient の生成（実・モック切替）
    - ...                            — broker_api / order_record 等（コードベースに依存）
  - monitoring/
    - monitoring_db.py               — SQLite 監視 DB スキーマ & ラッパー
    - system_monitor.py              — システム稼働・データ鮮度チェック
    - trade_monitor.py               — 注文滞留・約定異常チェック
    - risk_monitor.py                — ドローダウン・ポジション上限チェック
    - kill_switch.py                 — kill.flag 管理
    - alert_manager.py               — LINE 通知送信
    - monitoring_engine.py           — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py         — Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py           — 候補選定・スコア順ソート
    - position_sizing.py             — 発注株数計算（リスクベース／重みベース）
    - risk_adjustment.py             — セクター上限・レジーム乗数
  - research/
    - factor_research.py             — ファクター計算（momentum / volatility / value）
    - feature_exploration.py         — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py                    — LLM を用いたニュースセンチメント付与
    - regime_detector.py             — MA + マクロセンチメントでレジーム判定
  - data/                             — データファイル配置想定（data/kabusys.duckdb, data/monitoring.db など）

サンプル .env（例）
------------------
以下は最低限の例（実際の運用では秘密情報は安全に管理する）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
SQLITE_PATH=data/monitoring.db
DUCKDB_PATH=data/kabusys.duckdb
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=

テスト & 開発
--------------
- 単体関数群（portfolio/*.py、research/*.py、monitoring/* の run_once 系）を切り出してユニットテストを作成しやすい設計です。
- OpenAI や外部 API 呼び出しは内部で分離されているため、テスト時はモック化（unittest.mock.patch）してください。

補足
----
- ここに記載の多くの動作（ブローカー API、データパイプライン、DuckDB のテーブル群など）は別モジュール／データ準備が前提です（例えば prices_daily/raw_financials/raw_news 等のテーブルはデータ取り込み処理で作成される想定）。
- ライセンスや運用ルール（リアルマネーでの利用可否等）は本 README に含まれていません。実運用する場合は法令・取引所規定・ブローカー規約を遵守してください。

---

不明点や README に追加したい具体的な手順（例：初期データ投入スクリプトや mock broker の使い方、CI 実行方法など）があれば教えてください。必要に応じてサンプル .env.example や requirements.txt のテンプレートも作成します。