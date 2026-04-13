KabuSys — 日本株自動売買プラットフォーム
========================================

概要
----
KabuSys は日本株向けの自動売買システムのコードベースです。  
主な機能は以下の通りです:

- 注文作成・送信・状態管理を行う Execution Engine（ブローカー抽象化あり）
- システム状態・注文状況・リスクを監視する Monitoring（SQLite 保存）
- ポートフォリオ構築（候補選定・重み付け・株数決定・セクター制約など）
- リサーチ用モジュール（ファクター計算、将来リターン・IC 計算）
- AI を利用したニュースセンチメント（OpenAI）および市場レジーム判定
- Paper Trading 用の分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

特徴
----
- 明確に分離されたコンポーネント設計（execution / monitoring / research / ai / portfolio）
- DuckDB を使った時系列データ分析（prices_daily / raw_financials 等）
- SQLite に監視ログや発注ログを永続化（冪等なスキーマ初期化を提供）
- Paper Trading と Live を環境で分離（PAPER_TRADING_SQLITE_PATH）
- OpenAI（gpt-4o-mini）を用いたニュース NLP とレジーム判定（API 呼び出しのリトライ/フォールバック実装）
- process priority / cpu affinity のユーティリティ（psutil 利用）
- CLI / モジュール両方から利用可能な設計

前提・主要依存ライブラリ
-----------------------
（プロジェクトに添付される requirements.txt があればそちらを使用してください）
- Python 3.9+
- duckdb
- psutil
- openai
- requests
- streamlit (ダッシュボード利用時)

セットアップ
------------
1. リポジトリをチェックアウト
   - git clone … && cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも以下を入れてください:
     - pip install duckdb psutil openai requests streamlit

4. 環境変数 / .env の準備
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 最低限設定が必要なキー:
     - JQUANTS_REFRESH_TOKEN : J-Quants API 用トークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
     - OPENAI_API_KEY        : OpenAI 呼び出しに必要（AI 機能を使う場合）
   - 任意/重要なキー（デフォルト値あり）:
     - KABUSYS_ENV (development / paper_trading / live). デフォルト: development
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
     - PAPER_FILL_MODE (instant / partial / never / reject) — paper_trading の約定モード
     - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL など

   例 (.env)
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=yyyyy
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリの作成
   - mkdir -p data

初期化
------
- 監視用 SQLite スキーマはコード内の init_monitoring_db() により自動作成・マイグレーションされます。実行スクリプトを起動すると必要なテーブルが作られます。

使い方
------

1. 実行エンジン（ExecutionEngine）の起動
   - Paper Trading を使う場合は KABUSYS_ENV=paper_trading を設定してください（専用の paper DB を使用）。
   - 起動例:
     - python -m kabusys.run_execution
   - 動作:
     - プロセス優先度を "high" にセット（set_process_priority）
     - SQLite / DuckDB に接続
     - BrokerClientFactory を通じて実際のブローカーまたはモックを作成
     - ExecutionEngine.run_session() を実行

2. 監視ループの起動（SystemMonitor 単体）
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト: 60
     - 例: export MONITOR_POLL_INTERVAL=30
   - 監視は常に本番用の sqlite_path を使います（KABUSYS_ENV にかかわらず）。

3. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report \
       --from 2026-04-01 --to 2026-04-11 \
       --db data/paper_trading.db
   - デフォルト DB は data/paper_trading.db（PAPER_TRADING_SQLITE_PATH で上書き可）
   - 検証指標: 稼働率、注文成功率、送信率、P95 レイテンシ 等

4. AI ニューススコアリング（プログラムから）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - conn は DuckDB 接続（prices_daily/raw_news/news_symbols/ai_scores を参照）
     - api_key を None にすると OPENAI_API_KEY 環境変数を参照

5. 市場レジーム判定（プログラムから）
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - DuckDB の prices_daily / raw_news / market_regime を参照。結果を market_regime テーブルへ冪等に書き込む

6. Streamlit ダッシュボード（監視用）
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - read-only モードで SQLite を開いてダッシュボードを表示します

運用に関するポイント
-------------------
- Paper Trading と Live は DB を分離（paper_trading は data/paper_trading.db を使用）しているため、誤って本番資金を操作するリスクを低減しています。
- ExecutionEngine と Monitoring は PID ファイル（デフォルト data/execution.pid）および kill.flag（デフォルト data/kill.flag）で連携します。監視側は kill.flag の書き込みにより ExecutionEngine に停止シグナルを発行します。
- OpenAI API 呼び出しはレート制限や一時的エラーに対してエクスポネンシャルバックオフのリトライ実装があります。失敗時はフェイルセーフで継続します（必要に応じてログを確認してください）。
- process priority の設定は psutil に依存し、アクセス権の制約により設定できない場合は警告が出ますが起動は継続します。

主要ディレクトリ構成
-------------------
（src/kabusys をルートとした代表的なファイル一覧と説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env ロード・Settings クラス（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABUSYS_ENV, DUCKDB_PATH など）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（KABUSYS_ENV=paper_trading に対応）
  - run_monitoring.py
    - SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, ...
    - 発注・リコンシリエーション・リスク管理に関する実装
  - monitoring/
    - monitoring_db.py
      - SQLite による監視テーブル定義・永続化ロジック
    - system_monitor.py, trade_monitor.py, risk_monitor.py
      - 監視ロジック（システム状態、受注/約定、ドローダウン等）
    - monitoring_engine.py
      - 各 Monitor を束ねてポーリング/アラート判定を行う
    - alert_manager.py
      - LINE へのプッシュ通知ユーティリティ
    - kill_switch.py
      - kill.flag を書くロジック
    - streamlit_dashboard.py
      - Streamlit ベースの監視ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - 銘柄選定・重み計算・株数決定・セクター制約などの純粋関数群
  - research/
    - factor_research.py, feature_exploration.py
    - DuckDB を使ったファクター計算・IC 計算 等
  - ai/
    - news_nlp.py, regime_detector.py
    - OpenAI を利用したニュース NLP と市場レジーム判定
  - data/
    - （DuckDB / SQLite のデータファイルを置く想定: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db）
  - utils/
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）
  - monitoring/monitoring_db.py, ... (上記に詳述)

開発者向けメモ
--------------
- .env の自動読み込みは config.py によりプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。テスト時などで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB クエリは多くの場合 target_date ベースでルックアヘッドを避ける実装になっています（backtesting / リサーチでのバイアス防止）。
- monitoring_db.init_monitoring_db() は冪等にテーブルとインデックスを作成し、必要なマイグレーション（カラム追加）も含みます。

トラブルシューティング
---------------------
- OpenAI API キーがない場合、AI 機能呼び出しは ValueError を投げます。環境変数 OPENAI_API_KEY を設定してください。
- psutil の優先度設定が権限不足で失敗する場合は警告ログが出ますが処理は続行されます。
- Streamlit で SQLite を読み込めない場合は "Database not found or cannot open" のエラーが表示されます。MonitoringEngine が稼働してデータベースが生成されているか確認してください。

ライセンス
----------
- （必要に応じてプロジェクトのライセンス情報をここに記載してください）

以上がこのコードベースの概要と基本的な利用方法です。必要であれば、各モジュールの API 使用例やより詳細な運用手順（デプロイ / systemd 単位ファイル / コンテナ化 など）を追記します。どの部分の詳細が必要か教えてください。