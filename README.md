README
======

概要
----
KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量な Python コードベースです。本リポジトリは主に以下の機能群で構成されています。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注・約定のリコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- システム監視（SystemMonitor / MonitoringEngine）
- 監視データの永続化（SQLite）と分析用 DuckDB
- ポートフォリオ構築・ポジションサイズ計算
- ファクター計算 / 特徴量探索（Research）
- ニュースを用いた LLM ベースの NLP スコアリング（OpenAI）
- Streamlit による監視ダッシュボード

特徴（機能一覧）
----------------
- Execution
  - Signal Queue 型の発注エンジン（シグナル期間の Gate チェック、WebSocket push ドレイン）
  - ブローカー API 抽象化（実運用 / モック切替可、paper_trading モード）
  - 再起動後の自動リコンシリエーション（OrderSent の復旧、ポジション差分検出）
- Monitoring
  - システム状態（CPU/Memory/Disk/プロセス）とデータ鮮度監視
  - 注文滞留 / 約定価格異常の検出
  - ドローダウン・ポジション上限の監視と kill.flag による外部停止シグナル
  - LINE Push 経由のアラート（AlertManager）
  - Streamlit ダッシュボードで監視状況を可視化
- Portfolio
  - 候補選定、等額配分・スコア加重配分、ポジションサイズ計算（単位株丸め・aggregate cap）
  - セクター集中制限、レジームに応じた投下資金乗数
- Research
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB ベース）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- AI
  - ニュース記事をまとめて LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - 市場レジーム判定（ETF の MA200 とマクロニュースセンチメントの合成）
- Utilities
  - 環境変数/.env の読み込み・Settings 管理
  - プロセス優先度 / CPU affinity 設定ユーティリティ

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の union 型表記などを使用）
- SQLite（標準ライブラリ）
- システムに DuckDB と psutil をインストール可能であること

手順（推奨）
1. ソースを取得
   - git clone でリポジトリを取得します。

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   例:
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を個別にインストールしてください。）

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 主な環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須機能を使う場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト: INFO）
   - .env の書式はシェル互換（export KEY=val など）に対応しています。

5. データディレクトリの作成
   - mkdir -p data

使い方
------
実行エントリ（スクリプト）
- 監視ループを起動
  - 簡易: python src/kabusys/run_monitoring.py
  - モジュール実行: python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）。1 未満や不正値は無視されデフォルト使用。

- 発注エンジン（ExecutionEngine）
  - python src/kabusys/run_execution.py
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）に分離して記録します:
    - 例: KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボード（監視 UI）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - デフォルトで data/monitoring.db（読み取り専用）を開きます。MonitoringEngine を先に起動してデータを作成してください。

AI（OpenAI）関連
- ニューススコアリング:
  - Python API: from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
  - api_key を与えない場合は環境変数 OPENAI_API_KEY を参照します。
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key=None)
- 注意: API 呼び出し失敗時はフェイルセーフ（多くの場合 0.0 にフォールバック）しますが、OPENAI_API_KEY が未設定の場合は例外が出ます。

監視 DB 初期化
- run_monitoring.py / run_execution.py は起動時に init_monitoring_db() を呼び出して SQLite テーブル群を冪等に作成します。手動で初期化したい場合は MonitoringDB の init_monitoring_db 関数を使用してください。

設定（Settings）
- 設定は kabusys.config.Settings クラス経由で取得できます。自動的に .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から読み込みます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要な場合）
- KABU_API_PASSWORD: kabu API パスワード
- OPENAI_API_KEY: OpenAI API キー（AI 機能）
- DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
- SQLITE_PATH: data/monitoring.db（デフォルト）
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading の fill 動作）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセス監視 / kill フラグのパス
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）

ディレクトリ構成（主なファイル）
------------------------------
src/
  kabusys/
    __init__.py                # パッケージ定義（__version__）
    config.py                  # 環境変数 / Settings
    run_monitoring.py          # SystemMonitor のポーリング起動スクリプト
    run_execution.py           # ExecutionEngine 起動スクリプト

    execution/
      execution_engine.py      # ExecutionEngine（シグナル処理・push ドレイン）
      order_manager.py         # OrderManager（DB + Broker 統合）
      order_repository.py      # (存在する) Orders DB アクセス層
      reconciler.py            # リコンシリエーション（再起動復旧）
      risk_manager.py          # Risk 管理ロジック
      broker_api.py            # Broker API 抽象定義（実装に応じて concrete クラスを用意）
      ...                      # その他 execution 関連

    monitoring/
      monitoring_db.py         # SQLite による監視テーブルと MonitoringDB ラッパー
      system_monitor.py        # システム状態・データ鮮度監視
      trade_monitor.py         # 注文滞留・約定価格異常検出
      risk_monitor.py          # ドローダウン・ポジション上限監視
      kill_switch.py           # kill.flag 書き込み / 管理
      alert_manager.py         # LINE Push 通知
      monitoring_engine.py     # 各 Monitor を束ねるポーリングエンジン
      streamlit_dashboard.py   # Streamlit 監視ダッシュボード

    portfolio/
      portfolio_builder.py     # 候補選定・重み計算
      position_sizing.py       # 株数計算・aggregate cap
      risk_adjustment.py       # セクターキャップ・レジーム乗数
      __init__.py

    research/
      factor_research.py       # モメンタム/ボラatility/バリュー計算
      feature_exploration.py   # 将来リターン / IC / 統計サマリー
      __init__.py

    ai/
      news_nlp.py              # ニュース集約 → OpenAI 呼び出し → ai_scores 書込み
      regime_detector.py       # マクロ + MA200 でレジーム判定
      __init__.py

    utils/
      process_priority.py      # プロセス優先度 / CPU affinity ユーティリティ
      __init__.py

データファイル（デフォルト）
- data/kabusys.duckdb        (DuckDB、prices_daily/raw_financials 等を格納)
- data/monitoring.db         (監視ログ、trade_logs / positions / risk_logs / dashboard)
- data/paper_trading.db      (paper_trading モードの分離 DB)
- data/execution.pid         (ExecutionEngine の PID ファイル)
- data/kill.flag             (KillSwitch による停止フラグ)

運用上の注意
--------------
- KABUSYS_ENV=paper_trading にすると発注はモック化され、本番 SQLite と分離した DB（PAPER_TRADING_SQLITE_PATH）に記録されます。実運用時は KABUSYS_ENV=live を使用してください。
- run_execution / run_monitoring の最初にプロセス優先度を上げる処理を行います（権限不足で失敗することがあります）。
- OpenAI を利用する AI 機能は API 呼び出しの料金やレート制限に注意してください。429 等は内部でリトライロジックがありますが、運用時は適切なキーと制限管理を推奨します。
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。CI / テストで不要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- sqlite / duckdb のパスを環境変数で明示的に指定すると、複数環境（ローカル・ステージング・本番）を分離できます。

開発・拡張
-----------
- ブローカー実装は BrokerAPIProtocol を実装する形で差し替え可能です（実運用用実装 / テスト用 Mock）。
- DuckDB のテーブル（prices_daily, raw_financials, raw_news, news_symbols など）にデータをロードすると Research / AI モジュールが利用可能になります。
- Streamlit ダッシュボードは読み取り専用で SQLite DB にアクセスします。監視プロセスは常にモニタリング DB を更新するようにしてください。

お問い合わせ / 貢献
------------------
バグ報告や機能追加は Issue を立ててください。README に書かれていない運用上の質問や実装の詳細解説が必要であれば、具体的な目的を添えて問い合わせてください。

--- End of README ---