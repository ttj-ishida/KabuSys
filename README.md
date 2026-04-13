KabuSys — README
=================

概要
----
KabuSys は日本株を対象とした自動売買・研究・監視用の Python パッケージです。本コードベースは以下の主要機能を含みます。

- 注文発行・管理（Execution Engine / OrderManager / Reconciler）
- リスク管理（ドローダウン監視、ポジション上限など）
- 監視基盤（System/Trade/Risk Monitor、監視 DB、LINE 通知、kill flag）
- ポートフォリオ構築（候補選定、重み付け、株数計算、セクター制限）
- リサーチ（ファクター計算、特徴量探索、IC 計算、将来リターン）
- AI 補助機能（ニュース NLP によるセンチメント計算、レジーム判定）
- 運用支援ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な設計方針
- DuckDB/SQLite を用いたローカルデータ操作（外部の実口座とは明確に分離）
- レジーム判定やニュース解析で OpenAI API を利用（明示的に API キーを要求）
- ランタイム設定は環境変数／.env ファイルで柔軟に切替
- フェイルセーフを多用し、API 失敗やデータ欠損時は安全側にフォールバック

機能一覧
--------
- monitoring
  - SystemMonitor: CPU/メモリ/ディスク、実行プロセスの生存確認、株価データ鮮度チェック
  - TradeMonitor: 滞留注文チェック、約定異常価格チェック
  - RiskMonitor: ドローダウン監視、ポジション上限監視、ダッシュボード更新、リスクイベント記録
  - AlertManager: LINE Push による通知（クールダウン管理あり）
  - KillSwitch: 条件に応じて kill.flag を書き込み ExecutionEngine を停止させる
  - MonitoringDB: SQLite に監視ログ・注文ログ・ポジション等を永続化
  - Streamlit ダッシュボード（監視結果の可視化）
- execution
  - OrderManager / OrderRepository / Reconciler / ExecutionEngine（起動スクリプトあり）
  - Broker クライアントを抽象化し、paper_trading 環境では MockBroker を利用して本番 DB と分離
- portfolio
  - 候補選定、等重・スコア重み、リスク調整（セクターキャップ、レジーム乗数）、株数計算（単元丸め、aggregate cap）
- research
  - ファクター計算（Momentum / Volatility / Value）／将来リターン／IC 計算／統計サマリー
- ai
  - news_nlp.score_news: ニュース記事を LLM でセンチメント化して ai_scores に書き込み
  - regime_detector.score_regime: ETF (1321) の MA200 とマクロセンチメントを合成してレジーム判定
- tools
  - paper_verification_report: Paper Trading の検証レポート生成（成功率、稼働率、P95 レイテンシ等）

前提・依存
-----------
- Python 3.10+
- 主要ライブラリ（インストール例は次節参照）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- DB:
  - DuckDB ファイル: data/kabusys.duckdb（デフォルト）
  - SQLite 監視 DB: data/monitoring.db（デフォルト）
  - Paper Trading 用 SQLite: data/paper_trading.db（KABUSYS_ENV=paper_trading 時のデフォルト）

セットアップ手順
----------------
1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .venv\Scripts\activate     (Windows)

3. パッケージ依存をインストール
   - pip install -r requirements.txt
   - requirements.txt が無い場合の最低限（例）:
     - pip install duckdb psutil requests openai streamlit

4. 環境変数 / .env の準備
   - プロジェクトルートに .env（または .env.local）を置くと自動で読み込まれます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 例 .env（最低限）:
     - KABUSYS_ENV=development          # development | paper_trading | live
     - JQUANTS_REFRESH_TOKEN=xxx
     - KABU_API_PASSWORD=xxx
     - OPENAI_API_KEY=sk-...
     - LINE_CHANNEL_ACCESS_TOKEN=xxx
     - LINE_USER_ID=Uxxxxxxxxxxxxxxxxx
     - PAPER_FILL_MODE=instant         # paper_trading の約定動作: instant|partial|never|reject
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - LOG_LEVEL=INFO

   - 注意: Settings クラスは必須変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）が未設定だと ValueError を投げます。動作させるモジュールに応じて必要な変数を設定してください。

5. データディレクトリの作成
   - mkdir -p data

基本的な使い方
--------------
- 実行（Execution Engine）
  - 実口座/模擬口座切替: KABUSYS_ENV を指定します。
    - 本番（live）: KABUSYS_ENV=live
    - Paper Trading（分離された DB を使用）: KABUSYS_ENV=paper_trading
    - 開発: KABUSYS_ENV=development
  - 実行コマンド:
    - python -m kabusys.run_execution
      - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
  - 起動時にプロセス優先度を高く設定し、監視テーブルの初期化を行います。

- 監視プロセス
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルトは 60 秒。0 以下や不正な値はデフォルトにフォールバック。
    - 監視モジュールは（実行環境にかかわらず）本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
    - PID ファイル（Settings.pid_file_path）を参照して ExecutionEngine の存否を確認します。

- Streamlit ダッシュボード（監視）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で SQLite を open します。MonitoringEngine を稼働させてデータが入っている状態で閲覧してください。

- Paper Trading 検証レポート
  - 実行例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可能
  - 出力: 稼働率、注文成功率、送信率、P95 レイテンシなどの要約と PASS/FAIL 判定

- AI モジュール（OpenAI）
  - news_nlp.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを参照/更新します。
    - api_key 指定がない場合は環境変数 OPENAI_API_KEY を参照します（未設定時は例外）。
    - 1 銘柄あたりの文字数制限やバッチ処理、リトライを実装済みで、取得に成功したスコアのみ部分的に書き込みます。
  - regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF 1321 の MA200 乖離とマクロニュースのセンチメントを合成して market_regime テーブルへ冪等書込みを行います。

設定・運用上のポイント
--------------------
- 環境管理
  - 設定は主に環境変数で操作します。プロジェクトルートの .env / .env.local が自動ロードされます（ただし OS 環境変数の上書きを .env.local で許す仕様）。
- KABUSYS_ENV
  - 値: development | paper_trading | live
  - paper_trading では MockBroker を使い、Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）へログを残します。本番 DB と分離されるよう設計されています。
- プロセス優先度
  - run_monitoring/run_execution は起動時に set_process_priority("high") を呼びます。アクセス権がない場合は警告ログを出してスキップします。
- kill.flag
  - KillSwitch はリスク条件により kill.flag（デフォルト data/kill.flag）を書き込み、ExecutionEngine 側でこれを検出して安全に停止する想定です。
  - ExecutionEngine 側は起動時に kill.flag をクリアするオプション（Settings.kill_flag_clear_on_start）を持っています（必要に応じて設定してください）。
- 監視 DB マイグレーション
  - init_monitoring_db() は冪等でテーブル作成・簡易マイグレーション（カラム追加）を行います。スクリプト起動時に自動で呼ばれます。

ディレクトリ構成（抜粋）
--------------------
src/kabusys/
- __init__.py                     — パッケージ定義、バージョン
- config.py                       — Settings（環境変数/.env 管理）
- run_execution.py                — ExecutionEngine 起動スクリプト
- run_monitoring.py               — SystemMonitor ポーリング起動スクリプト

src/kabusys/monitoring/
- monitoring_db.py                — SQLite による監視ログ層（初期化・永続化 API）
- system_monitor.py               — CPU/メモリ/ディスク/プロセス/データ鮮度監視
- trade_monitor.py                — 注文滞留・約定異常監視
- risk_monitor.py                 — ドローダウン・ポジション上限監視
- monitoring_engine.py            — 各 Monitor を束ねる実行ループ
- alert_manager.py                — LINE 通知ラッパー
- kill_switch.py                  — フラグファイルによる停止トリガ
- streamlit_dashboard.py          — Streamlit ベースの監視ダッシュボード

src/kabusys/execution/
- order_manager.py
- reconciler.py
- ...（broker 抽象化、order_repository 等）

src/kabusys/portfolio/
- portfolio_builder.py            — 候補選定・重み計算
- position_sizing.py              — 株数計算・aggregate cap
- risk_adjustment.py              — セクター制限・レジーム乗数

src/kabusys/research/
- factor_research.py              — Momentum/Volatility/Value のファクター計算
- feature_exploration.py          — 将来リターン・IC・統計サマリー

src/kabusys/ai/
- news_nlp.py                     — ニュースセンチメント化（OpenAI）
- regime_detector.py              — 市場レジーム判定（MA200 + マクロセンチメント）

src/kabusys/tools/
- paper_verification_report.py    — Paper Trading 用検証レポートジェネレータ

運用例（よく使うコマンド）
------------------------
- 監視プロセスを起動（デフォルト 60 秒間隔）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- ExecutionEngine を起動（Paper Trading モード）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サンプルコード（AI モジュールを直接呼び出す）
---------------------------------------
- Python REPL / スクリプト内で DuckDB 接続を作り、日付を指定して呼び出す例:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  score_news(conn, date(2026, 4, 10), api_key="sk-...")

テスト・開発時のヒント
---------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。パッケージ配布後も __file__ を基準に探索するため、CWD に依存しません。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを無効化できます（ユニットテスト等で便利）。
- OpenAI 呼び出しはリトライやフェイルオープン処理を行いますが、API キーが設定されていない場合は明示的な例外を投げます。
- psutil によるプロセス優先度設定や CPU affinity 設定は権限やプラットフォームに依存します。失敗した場合は警告ログでスキップされます。

ライセンス・貢献
----------------
- 本 README に含めるライセンス情報はリポジトリの LICENSE を参照してください。
- 機能追加・バグ修正は Pull Request にて歓迎します。README の改善点も随時受け付けます。

最後に
------
この README はソースコードの現状（提供されたモジュール群）に基づく概要と運用ガイドです。詳細な設計や追加の実行オプションは各モジュールの docstring を参照してください（例: kabusys/config.py, monitoring/*, ai/*）。必要であればデプロイ手順や systemd/プロセスマネージャ用のユニットファイルのテンプレートも別途作成できます。