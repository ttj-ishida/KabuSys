KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向け自動売買システム（KabuSys）のコアライブラリと運用ユーティリティ群を含みます。
ここに含まれるのは監視（Monitoring）・Execution エンジン、ポートフォリオ構築、研究用ファクター計算、AI を使ったニュース解析等のモジュールです。

主な機能
--------
- ExecutionEngine 起動用スクリプト（本番 / ペーパートレード切替対応）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録（本番 DB と分離）
- Monitoring（System / Trade / Risk）ポーリングとアラート発行（kill.flag による停止シグナル）
- .env 環境設定ウィザード（対話式）
- 設定検証ツール（.env と config/*.yaml の事前チェック）
- Research モジュール（ファクター計算、将来リターン、IC 計算など） — DuckDB 経由でデータを参照
- AI モジュール
  - news_nlp: OpenAI を使ったニュースのセンチメント付与（ai_scores テーブルへ書込）
  - regime_detector: ETF（1321）MA とマクロニュースの LLM 評価を合成して市場レジーム判定
- Paper Trading 検証レポート生成スクリプト

前提 / 依存
-----------
主な Python ライブラリ（抜粋）:
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config YAML の中身検証に任意）
- SQLite（標準ライブラリ経由で使用）
- その他標準ライブラリ

インストール（例）
-----------------
1. 仮想環境作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （運用時は requirements.txt を用意している場合は pip install -r requirements.txt）

セットアップ手順
---------------
1. プロジェクトルートへ移動（README と同じ階層に src/ がある想定）

2. 初期 .env を作成（対話ウィザード）
   - python -m kabusys.config_setup
   - 対話に従って必須項目（J-Quants トークン、kabu API パスワード等）を入力し .env を保存します。

3. 設定検証
   - python -m kabusys.validate_config
   - 必要に応じて --strict オプションで警告も FAIL 扱いにできます。

4. データディレクトリの作成（logs, data 等）
   - mkdir -p data logs

5. （AI 機能を使う場合）
   - 環境変数 OPENAI_API_KEY を設定するか、score_news/score_regime に api_key を引数で渡してください。

環境変数の主な一覧
------------------
（.env の key と対応。デフォルト値は code 内コメント参照）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading 用
- KABUSYS_ENV (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL (DEBUG/INFO/...)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意・本番でのアラート用）
- KILL_FLAG_CLEAR_ON_START (0/1) — Execution 起動時に kill.flag を自動クリアするか

主要スクリプト使い方
-------------------

1. Execution エンジン起動
- python -m kabusys.run_execution
  - 起動時に KABUSYS_ENV に従って DB を選択します（paper_trading は paper DB を使用）。
  - data/execution.pid に PID が書き込まれ、 data/stop_requested.flag により停止できます。
  - 停止シグナル（外部）: data/stop_requested.flag を配置すると起動中スレッドは停止します。
  - Kill Switch: monitoring 側の kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）が書かれると ExecutionEngine 停止を促します。

2. Monitoring（SystemMonitor のポーリング）
- python -m kabusys.run_monitoring
  - デフォルト 60 秒間隔で監視ループを実行します（環境変数 MONITOR_POLL_INTERVAL で秒指定可）。
  - 監視は常に本番 sqlite_path（SQLITE_PATH）を使用し、monitoring テーブル群を初期化します。
  - 停止には data/stop_requested.flag を作成します。

3. 設定ウィザード
- python -m kabusys.config_setup

4. 設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告がある場合も exit(1) で失敗扱いになります。

5. Paper Trading 検証レポート生成
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB パスは 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db。

AI 関連の使い方
---------------
- ニュース NLP（銘柄別センチメント付与）
  - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または api_key 引数）。
  - ai_scores テーブルへ書き込みします。失敗時は安全にスキップして継続する実装です。

- レジーム判定
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の MA200 とマクロニュースの LLM スコアを合成して market_regime テーブルに書き込みます。

ログ設定
--------
- 共通ロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
  - stdout（StreamHandler）と日次ローテートファイル（logs/<app_name>.log）を設定します。
  - LOG_DIR 環境変数または引数でログディレクトリを指定できます。

Kill Switch / Stop フラグ
-------------------------
- Execution 停止要求: data/stop_requested.flag（run_execution/run_monitoring はこれを監視）
- Kill Switch（致命的アラート）: data/kill.flag（KillSwitch が書き込み、Execution 側で検出されると停止する挙動）
- 起動時に KILL_FLAG_CLEAR_ON_START=1 にすると自動クリア（本番では 0 推奨）

ディレクトリ構成（主要ファイル）
------------------------------
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数・設定読み込みロジック（.env 自動ロード）
    config_setup.py                # .env 対話式ウィザード
    validate_config.py             # 設定検証 CLI
    run_execution.py               # ExecutionEngine 起動スクリプト
    run_monitoring.py              # SystemMonitor ポーリング起動スクリプト

    execution/                      # 発注・注文管理関連（ファクトリ等）
      (Engine, OrderManager, RiskManager 等)

    monitoring/
      monitoring_db.py             # SQLite ベースの永続化層
      system_monitor.py            # システム状態・データ鮮度監視
      trade_monitor.py             # 注文滞留・約定異常監視（存在）
      risk_monitor.py              # ドローダウン・ポジション上限監視
      kill_switch.py               # kill.flag 書き込みユーティリティ
      monitoring_engine.py         # 各 Monitor を束ねるエンジン
      alert_manager.py             # アラート送信（LINE など） — 実装ファイル参照

    portfolio/
      portfolio_builder.py         # 候補選定・重み計算
      position_sizing.py           # 株数決定・スケールダウンロジック
      risk_adjustment.py           # セクターキャップ・レジーム乗数

    research/
      factor_research.py           # Momentum / Volatility / Value 等のファクター計算
      feature_exploration.py       # 将来リターン・IC・統計サマリ

    ai/
      news_nlp.py                  # ニュースの LLM によるセンチメント評価
      regime_detector.py           # 市場レジーム判定（MA200 + マクロNNL）

    data/                           # 実行時データファイル（logs, sqlite 等）を想定
    logs/                           # ログ出力先

注意事項 / 運用上のポイント
--------------------------
- デフォルトでは .env 自動読み込みが有効です（プロジェクトルートが .git または pyproject.toml を基準に検出できる場合）。
  テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番環境（KABUSYS_ENV=live）では LINE の通知設定や Kill Switch の設定を十分確認してください。
- paper_trading モードは本番 DB と分離されています。ペーパートレード用 DB は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使用します。
- AI を使う機能は OpenAI API の料金・利用規約に注意し、API キーは安全に管理してください。
- ログディレクトリ作成に失敗した際はコンソール出力のみで継続する設計です。

トラブルシューティング
-----------------------
- config/ 以下の YAML を検証したいが PyYAML がないとき:
  - pip install PyYAML
  - validate_config は PyYAML が無ければ YAML 検証をスキップします（警告を出します）。

- SQLite / DuckDB のパスに関する警告:
  - validate_config はパスの親ディレクトリ存在をチェックします。起動時には多くの場合自動作成されますが、権限などで失敗する場合があります。

- プロセス優先度の設定に失敗することがあります（権限不足や OS 非対応）。その場合は警告を出してスキップします。

貢献・拡張案
-------------
- BrokerClient の追加・実装（実口座接続・認証）
- strategy モジュールの追加（シグナル生成→Execution への連携）
- アラート送信先（LINE 以外）の追加
- 単体テストと CI（各モジュールのユニットテスト）
- requirements.txt / poetry / pipenv で依存管理ファイルを追加

ライセンス
---------
明示されていない場合はリポジトリ管理者の指示に従ってください。

---
この README はコードベースの主要な使い方・構成をまとめたものです。具体的な関数の引数や戻り値、詳細な実装は各ソースファイルの docstring / コメントを参照してください。必要なら README に使い方の短い実例（コマンドのサンプル）を追加します。どの部分を重点的に補足しましょうか？