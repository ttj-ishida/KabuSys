README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。本リポジトリは以下の機能をモジュール化して提供します。

- 注文発行・管理（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視・アラート（SystemMonitor / TradeMonitor / AlertManager）
- ポートフォリオ構築（候補選定・重み算出・ポジションサイズ計算）
- リサーチ用ファクター計算（momentum / value / volatility 等）
- ニュースの NLP スコアリング（OpenAI を利用）
- Paper Trading 用の検証レポート生成ツール
- Streamlit を使った監視ダッシュボード

特徴
----
- 明確に分離されたモジュール設計（execution / monitoring / portfolio / research / ai / tools）
- DuckDB / SQLite を利用したローカルデータアクセス（DuckDB は時系列ファクター集計、SQLite は監視ログや注文ログ）
- 本番（live） / 検証（paper_trading） / 開発（development）の環境切替
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント・市場レジーム判定の統合（オプション）
- フェイルセーフ設計（DB マイグレーション、部分失敗時の冪等処理、リトライ／バックオフ等）

セットアップ
----------
1. Python 環境を作成
   - 推奨: Python 3.10+ で仮想環境を作成してください。
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要な依存（プロジェクトに requirements.txt がない場合の例）:
     - pip install duckdb psutil openai requests streamlit
   - 実行環境に合わせて追加パッケージが必要になる場合があります。

3. ソースの import 解決
   - 開発時はプロジェクトルートから PYTHONPATH に src を追加するか、editable インストールします。
     - export PYTHONPATH=$(pwd)/src
     - あるいは: pip install -e .

4. 環境変数 / .env
   - 設定は環境変数、またはプロジェクトルートの .env / .env.local から自動ロードされます（自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 重要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（ai 機能を使う場合）
     - KABUSYS_ENV: 実行環境（development / paper_trading / live）
     - PAPER_FILL_MODE: paper_trading 時の約定挙動（instant | partial | never | reject）（デフォルト: instant）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID ファイル・kill.flag のパス
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

使い方
-----

基本起動
- 実行（Monitoring）
  - 簡易（開発環境）:
    - 環境変数と PYTHONPATH を設定した上で:
      - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数で監視ポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を定期的に呼び出し、SQLite にログを書き、条件に応じて kill.flag を書き込むなどのアクションを行います。
    - 監視は KABUSYS_ENV に関係なくデフォルトの（本番）SQLite パスを使用します（Settings.sqlite_path）。

- 実行（ExecutionEngine）
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - Settings.env によって挙動が分岐します。
      - KABUSYS_ENV=paper_trading の場合: MockBrokerClient を利用し、Paper Trading 用の SQLite（PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離します。
      - live の場合は実ブローカーを使用（環境変数で API 情報設定が必要）。
    - プロセス優先度を高（High）へ設定してから起動します（psutil を使用）。

監視ダッシュボード（Streamlit）
- 起動コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 機能:
  - ダッシュボード集計、保有ポジション一覧、直近注文、最新システムステータス、Recent Risk Events を表示します（SQLite を read-only で開きます）。

Paper Trading 検証レポート
- 実行:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD（開始日）
    - --to YYYY-MM-DD（終了日）
    - --db PATH（DB ファイルの上書き）
- 出力:
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などの指標と PASS/FAIL 判定を標準出力へ出力します。

AI（ニュース NLP / レジーム判定）
- ニューススコアリング:
  - kabusys.ai.news_nlp.score_news を呼び出して raw_news から銘柄ごとのセンチメントを ai_scores テーブルへ書き込みます。
  - OpenAI API キー（OPENAI_API_KEY または引数）必須。
  - 大量 API 呼び出しはバッチ（最大 20 銘柄）で行い、429 / タイムアウト / 5xx は指数バックオフでリトライします。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime を呼び出すと、ETF(1321) の MA 偏差とマクロニュースの LLM スコアを合成して market_regime テーブルへ冪等書き込みします。
  - OpenAI API キーが必要。失敗時は安全にフォールバック（macro_sentiment=0.0）します。

設定と動作のポイント
- 環境モード: KABUSYS_ENV は development / paper_trading / live のいずれか
  - paper_trading は発注や DB を本番と分離して検証ができます。
- PAPER_FILL_MODE:
  - instant / partial / never / reject のいずれか。paper_trading の MockBroker 動作を制御します。
- PID / Kill Flag:
  - 実行プロセスは PID を PID_FILE_PATH に書き、監視側が存在を確認します。KillSwitch は flag ファイル（KILL_FLAG_PATH）を作成して ExecutionEngine 停止を指示します。
- DB 初期化:
  - monitoring 側は init_monitoring_db(sqlite_conn) で監視用のテーブルとマイグレーション（冪等）を行います。run_monitoring / run_execution 起動時に内部で呼ばれます。

主要な環境変数（一覧）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API Key（ai 機能で必須）
- KABUSYS_ENV: execution 環境（development|paper_trading|live）
- PAPER_FILL_MODE: paper_trading の約定モード（instant|partial|never|reject）
- SQLITE_PATH: 監視用 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 DB（デフォルト data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- PID_FILE_PATH: PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

ディレクトリ構成
----------------
（src 配下がパッケージです。代表的なファイル/モジュールを列挙します）

- src/
  - kabusys/
    - __init__.py                — パッケージ定義
    - config.py                  — 環境変数／Settings 管理 (.env 自動ロード)
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py — Paper Trading 検証レポート生成ツール
    - ai/
      - __init__.py
      - news_nlp.py              — ニュースセンチメント（OpenAI 統合）
      - regime_detector.py       — 市場レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py        — SQLite の監視ログ永続化層（初期化・CRUD）
      - system_monitor.py       — CPU/メモリ/ディスク/プロセス/データ鮮度監視
      - trade_monitor.py        — 注文滞留・約定異常監視
      - risk_monitor.py         — ドローダウン・ポジション上限監視
      - kill_switch.py          — kill.flag 管理
      - alert_manager.py        — LINE 通知ラッパー
      - monitoring_engine.py    — 各モニタを束ねるエンジン
      - streamlit_dashboard.py  — Streamlit ベースの監視ダッシュボード
    - execution/
      - reconciler.py           — 起動時の自動リコンシリエーション
      - order_manager.py        — 注文状態管理（作成・送信・同期）
      - order_repository.py     — 注文 DB（SQLite）アクセス
      - ...                     — BrokerFactory / Engine / RiskManager 等（省略）
    - portfolio/
      - __init__.py
      - portfolio_builder.py    — シグナル選定・スコアソート
      - position_sizing.py      — 株数計算・単元丸め・集約制約
      - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - research/
      - __init__.py
      - factor_research.py      — momentum/value/volatility ファクター計算（DuckDB）
      - feature_exploration.py  — 将来リターン計算・IC・統計サマリ
    - data/
      - pipeline.py (参照されるユーティリティ等)  — DuckDB から最新日取得など
    - utils/
      - __init__.py
      - process_priority.py     — プロセス優先度 / CPU affinity 設定ユーティリティ

開発・デプロイの注意点
---------------------
- DB ファイル（data/ 以下）は適切にバックアップしてください。特に本番用の SQLite / DuckDB は重要です。
- OpenAI API を使う機能は API 呼び出しにコストがかかります。バッチ処理やリトライ戦略が実装されていますが注意してください。
- psutil を使用してプロセス優先度や CPU affinity を設定します。アクセス権の制約により設定に失敗することがあります（警告ログのみ）。
- .env パーサは一般的な export/quoted/コメント形式に対応します。.env.example を参考に .env を作成してください。
- Paper Trading と Live は DB を分離する設計です。検証データが本番 DB を汚染しないようにデフォルトで分けられています。

サンプル実行コマンド（まとめ）
-----------------------------
- 監視ループ起動:
  - export PYTHONPATH=$(pwd)/src
  - python -m kabusys.run_monitoring
  - （任意）MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Execution 起動:
  - export PYTHONPATH=$(pwd)/src
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

問い合わせ / 貢献
-----------------
- バグ修正や機能追加は Pull Request でお願いします。設計思想（フェイルセーフ、冪等性、ルックアヘッド回避）を尊重した実装を心がけてください。

以上が本コードベースの README（日本語）です。追加で「.env.example のテンプレート」や「requirements.txt の推奨リスト」などを用意する場合は、その内容も作成できます。必要なら教えてください。