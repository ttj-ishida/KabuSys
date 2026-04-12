# KabuSys — README (日本語)

このリポジトリは日本株向け自動売買システム「KabuSys」の一部実装です。本書はコードベースに含まれる主要コンポーネント・起動方法・設定・利用方法・ディレクトリ構成を日本語でまとめた README.md です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（起動／コマンド）
- 主要環境変数（.env）
- 補足: 動作や注意点
- ディレクトリ構成

--------------------
プロジェクト概要
--------------------
KabuSys は日本株向けの自動売買・研究・監視を行うシステムのコードベースです。本リポジトリには以下の主要領域が含まれます：
- execution: 発注・オーダーライフサイクル、リコンシリエーション、リスク管理
- monitoring: システム稼働監視、注文監視、リスク監視、アラート送信、監視DB
- research: ファクター計算・特徴量探索（DuckDB を利用）
- portfolio: 候補選定、重み算出、ポジションサイズ計算、セクター制限
- ai: ニュースの NLP によるスコアリング、レジーム検出（OpenAI を利用）
- tools: 検証レポート生成などのユーティリティスクリプト

設計上のポイント：
- DuckDB / SQLite を組み合わせてオンメモリ + 永続化を実現
- 環境に応じて paper_trading（モックブローカー）と live を切替可能
- .env / .env.local による環境管理（自動読み込みはプロジェクトルート発見に基づく）

--------------------
機能一覧
--------------------
主な機能（抜粋）：
- ExecutionEngine 起動スクリプト（run_execution.py）
  - live / paper_trading 切替（paper_trading は data/paper_trading.db に記録）
  - ブローカーファクトリによる実ブローカー or モックの選択
  - OrderManager / RiskManager / Reconciler の組み立てと実行
- Monitoring（監視）
  - SystemMonitor：CPU/メモリ/ディスク、PID ファイル、データ鮮度のチェック
  - TradeMonitor：滞留注文チェック、約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション上限の監視
  - KillSwitch：条件達成時に kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - AlertManager：LINE Push による通知（設定があれば送信）
  - Streamlit ダッシュボード（監視データ表示）
- Research（ファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター算出（DuckDB）
  - 将来リターン・IC・統計サマリーなど
- AI（OpenAI）
  - news_nlp.score_news: ニュース記事をバッチで LLM に送り銘柄別スコアを ai_scores テーブルへ保存
  - regime_detector.score_regime: ma200 とマクロニュースを合成して日次の市場レジーム判定
- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ計算
  - セクター集中制限・レジームに応じた乗数
- Tools
  - paper_verification_report: Paper Trading DB を集計して PASS/FAIL 判定付きレポート生成

--------------------
セットアップ手順
--------------------
前提
- Python 3.10 以上（型注釈で | を使用しているため）
- DuckDB, SQLite は Python パッケージ / 標準で動作
- ネットワークアクセス（OpenAI / LINE）を使う場合は API キー等を設定

基本手順（開発環境向け）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要パッケージ例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数設定（.env の配置推奨）
   - プロジェクトルート（.git か pyproject.toml のある場所）に .env または .env.local を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

--------------------
主要環境変数（.env）
--------------------
設定は Settings クラス（kabusys.config）で読み込まれます。主なキー：

必須（利用機能により必須になるもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（research 等で必要）
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注に必要）

任意 / デフォルトあり
- KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
  - paper_trading にすると run_execution が mock ブローカーを使い data/paper_trading.db に記録
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY — OpenAI API キー（ai モジュールを使う場合必須）
- PAPER_FILL_MODE — paper_trading のモック約定モード: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の PID 保存パス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch の flag ファイルパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）

例（.env の簡易例）
    KABUSYS_ENV=development
    OPENAI_API_KEY=sk-xxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    JQUANTS_REFRESH_TOKEN=your_jquants_token
    DUCKDB_PATH=data/kabusys.duckdb
    SQLITE_PATH=data/monitoring.db

.env の読み込みルール
- 自動読み込み順: OS 環境変数 > .env.local（上書き） > .env（初期セット）
- プロジェクトルートは __file__ を基点に .git または pyproject.toml を探索して決定
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能

--------------------
使い方（起動・コマンド）
--------------------

1) ExecutionEngine を起動（発注系）
- デフォルト（development / live の切替は KABUSYS_ENV）
  - python -m kabusys.run_execution
- paper_trading 環境で起動する例:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - この場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。

2) Monitoring（SystemMonitor のポーリング）を起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL でポーリング間隔(秒)を上書き可能（例: MONITOR_POLL_INTERVAL=30）
- 監視は monitoring DB（Settings.sqlite_path）へ書き込みを行います。run_monitoring は環境に関係なく本番 sqlite_path を使用します。

3) Streamlit ダッシュボード（監視表示）
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ブラウザで視覚的に監視ログ・ポジション・注文を確認できます（読み取り専用で DB を開きます）。

4) Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report
- 日付範囲を指定:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- --db オプションで DB パスを指定可能（デフォルト: data/paper_trading.db）

5) AI モジュール呼び出し（プログラム使用例）
- ニュースのスコア付け:
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key="sk-...")
- レジームスコア:
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key="sk-...")

6) その他
- kill.flag の存在は KillSwitch により ExecutionEngine 停止シグナルとして扱われます。通常 ExecutionEngine 側で定期チェックして停止します。

--------------------
補足・注意点
--------------------
- run_monitoring は監視 DB（monitoring DB）に対して書き込みを行います。監視は本番 sqlite_path を参照します（KABUSYS_ENV にかかわらず）。
- run_execution は KABUSYS_ENV に応じて本番 DB / paper_db を切り替えます（paper_trading は完全分離）。
- PID 管理: ExecutionEngine は Settings.pid_file_path に PID を書きます。SystemMonitor はこの PID を見てプロセス稼働を判定します（stale PID の削除も行います）。
- OpenAI 関連:
  - API の失敗はフェイルセーフ設計（部分失敗時はデフォルト値で継続）になっていますが、API キーが必須の処理を呼ぶ時は必ず設定してください。
  - レート制限や 5xx は指数バックオフでリトライします（コード内に実装）。
- DB migrations:
  - monitoring_db.init_monitoring_db は冪等でテーブルを作成し、既存テーブルにカラムが無い場合は ALTER による簡易マイグレーションを実行します。
- モジュール単体テストやユニットテストを書く際は .env 自動読み込みを KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化すると安全です。

--------------------
ディレクトリ構成（抜粋）
--------------------
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数読み込み・Settings
    run_execution.py               # ExecutionEngine 起動スクリプト
    run_monitoring.py              # SystemMonitor ポーリング起動スクリプト

    execution/
      order_manager.py
      reconciler.py
      order_repository.py
      execution_engine.py
      broker_factory.py
      broker_api.py
      order_record.py
      ... (発注周りの実装)

    monitoring/
      __init__.py
      monitoring_db.py             # SQLite の監視テーブル永続化層
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      ...

    portfolio/
      __init__.py
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py

    research/
      __init__.py
      factor_research.py
      feature_exploration.py

    ai/
      __init__.py
      news_nlp.py
      regime_detector.py

    data/
      (data パイプライン・DuckDB 関連のモジュールを想定)

    tools/
      __init__.py
      paper_verification_report.py

プロジェクトルート:
  .env.example (想定)
  pyproject.toml / setup.cfg（ある場合）
  data/ (SQLite / DuckDB のファイルを配置するディレクトリ）

--------------------
最後に
--------------------
本 README はコードベースから抽出した情報を基に作成しています。実際の運用時は環境変数や各モジュールのログ（LOG_LEVEL を DEBUG にして起動）を確認し、まずはローカルの paper_trading 環境で動作検証を行ってください。必要であれば README に追加したい具体的なコマンドや .env.example のテンプレートを教えてください。