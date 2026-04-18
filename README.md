README
======

概要
----
KabuSys は日本株の自動売買システム（リサーチ・ポートフォリオ構築・実行・監視・ツール群）向けの Python パッケージです。本リポジトリは以下の主要機能を持つモジュール群を含みます。

- データ分析／ファクター計算（DuckDB を利用）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算）
- ExecutionEngine（発注・リスク管理・リコンシリエーション）
- 監視（System / Trade / Risk モニタ、Kill Switch）
- AI 補助（OpenAI を使ったニュース NLP / 市場レジーム判定）
- 開発支援ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

主な特徴
--------
- モジュール化された純粋関数群（ポートフォリオ構築・リスク調整等）は副作用がなくテスト容易
- DuckDB を使った高速なオンメモリ分析（prices_daily / raw_financials 等を参照）
- 発注ロジックと監視ロジックの明確な分離（監視は常に本番監視 DB を使用）
- Paper Trading モード（KABUSYS_ENV=paper_trading）で本番 DB と分離された専用 SQLite を使用
- OpenAI を用いたニュースセンチメント処理（retry/backoff、レスポンス検証実装済）
- 実行・監視プロセスのログは stdout と logs/<app>.log（日次ローテーション）へ出力

前提 / 依存ライブラリ
--------------------
主に以下のパッケージが必要です（Python 標準ライブラリに加えて）:

- duckdb
- psutil
- openai
- PyYAML（config 検証で任意）
- （SQLite は標準組込み）

インストールはプロジェクトの requirements.txt を用意している場合は pip install -r requirements.txt を推奨します。なければ手動でインストールしてください。
例:
    python -m venv .venv
    source .venv/bin/activate
    pip install duckdb psutil openai PyYAML

セットアップ手順
--------------
1. リポジトリをクローンしワーク環境を作成
    git clone <repo>
    cd <repo>
    python -m venv .venv
    source .venv/bin/activate
    pip install -U pip
    pip install duckdb psutil openai PyYAML

2. ディレクトリ作成（data / logs）
    mkdir -p data logs

3. .env を作成（対話式ウィザード推奨）
    python -m kabusys.config_setup
   ウィザードは .env を生成します。必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）を入力してください。

   あるいは .env を手動で編集:
   例（最低限）:
       JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
       KABU_API_PASSWORD=your_kabu_password
       KABUSYS_ENV=development
       DUCKDB_PATH=data/kabusys.duckdb
       SQLITE_PATH=data/monitoring.db
       LOG_LEVEL=INFO

   自動読み込みについて:
   - 起動時に .env / .env.local を自動で読み込みます（OS 環境変数が優先）。
   - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証
    python -m kabusys.validate_config
    必要なら --strict を付けて警告もエラー扱いにできます。

5. （任意）OpenAI API キー設定
    OPENAI_API_KEY を .env に設定すると ai.news_nlp / ai.regime_detector が利用可能になります。

使い方
------
主要エントリポイント（実行はパッケージモード）:

- 監視プロセスを起動（SystemMonitor のポーリングループ）
    python -m kabusys.run_monitoring

    環境変数:
    - MONITOR_POLL_INTERVAL: ポーリング間隔（秒）。デフォルト 60 秒。
    監視は KABUSYS_ENV にかかわらず監視用 sqlite_path（Settings.sqlite_path）を使用します。
    停止フラグ: data/stop_requested.flag を作成するとループは停止します。

- ExecutionEngine を起動（発注エンジン）
    python -m kabusys.run_execution

    動作モード:
    - KABUSYS_ENV=paper_trading: MockBrokerClient が使用され、Paper Trading 用 DB（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）へ記録します。
    - KABUSYS_ENV=live: 本番設定での実行（kabuステーションに接続）— 十分な注意と検証が必要です。

    停止制御:
    - data/stop_requested.flag を作成するとエンジンに停止要求を送れます。
    - Kill Switch（監視側）で条件を満たすと data/kill.flag を作成して ExecutionEngine の自動停止トリガーとして使います。

- .env ウィザード（対話式）
    python -m kabusys.config_setup

- 設定検証
    python -m kabusys.validate_config
    python -m kabusys.validate_config --strict

- ペーパートレード検証レポート生成
    python -m kabusys.tools.paper_verification_report
    オプション:
      --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
    DB パスの優先順: --db > PAPER_TRADING_SQLITE_PATH 環境変数 > デフォルト data/paper_trading.db

- AI スコアリング（プログラムから呼び出す）
    例（Python スクリプト内）:
        from datetime import date
        import duckdb
        from kabusys.ai.news_nlp import score_news
        conn = duckdb.connect("data/kabusys.duckdb")
        n = score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
        print("書き込み銘柄数:", n)

    同様に regime_detector の score_regime も programmatic に利用できます。

重要な環境変数（主なもの）
------------------------
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite（デフォルト data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- MONITOR_POLL_INTERVAL: 監視ポーリング秒数（run_monitoring 用）

ログと DB
---------
- ログ: logs/<app_name>.log に日次ローテーションで出力（stdout も同時出力）
- 監視 DB: デフォルト data/monitoring.db（MonitoringDB が使用）
- Paper Trading DB: data/paper_trading.db（paper_trading モード時）
- PID / フラグ:
  - data/execution.pid（ExecutionEngine の PID）
  - data/stop_requested.flag（外部からプロセス停止を要求する簡易フラグ）
  - data/kill.flag（Kill Switch による自動停止フラグ）

ディレクトリ構成（抜粋）
----------------------
src/kabusys/
- __init__.py
- config.py                  — 環境変数読み込み・Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト

サブパッケージ（主要）
- ai/
  - news_nlp.py              — ニュース NLP（OpenAI 連携）
  - regime_detector.py      — 市場レジーム判定（OpenAI 連携）
- monitoring/
  - monitoring_db.py         — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- execution/                 — 発注エンジン関連（broker_factory, engine, order_manager 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py         — ログ設定ユーティリティ
  - process_priority.py      — プロセス優先度設定ユーティリティ
- tools/
  - paper_verification_report.py

補足（運用に関する注意）
----------------------
- 本番（KABUSYS_ENV=live）での稼働時は .env と設定ファイルを慎重に管理し、LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）等を確認してください。
- validate_config の警告は運用リスクに繋がるため --strict モードで事前検証を推奨します。
- OpenAI API を利用する機能は API キーの利用料・レート制限に注意してください。API 呼び出しはリトライやバックオフ処理を実装していますが、料金とレートは別途管理してください。
- logs および data ディレクトリのパーミッション（書き込み権限）やディスク容量には注意してください。

トラブルシューティング
----------------------
- ログが出力されない / ファイルハンドラ作成失敗:
  logs ディレクトリの作成権限を確認してください。logging_setup はディレクトリ作成に失敗した場合でもコンソール出力は継続します。
- OpenAI 関連エラー:
  OPENAI_API_KEY が正しく設定されているか、API のレート制限・ネットワーク接続を確認してください。
- DB ファイルが見つからない:
  環境変数（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を確認、必要ならファイルを生成・パス修正してください。
- 停止／再起動:
  data/stop_requested.flag を作成すると run_monitoring / run_execution のループはそれを検知して安全に終了します。kill.flag は KillSwitch による自動停止用途です。

開発・拡張の指針
----------------
- portfolio, research, ai モジュールは副作用を持たない関数群として実装されているためユニットテストが書きやすい設計です。
- OpenAI 呼び出し部分はテストで差し替え可能（モジュール内の _call_openai_api を patch することでモック可能）。
- DuckDB を利用するリサーチロジックは SQL と Python の混在で記述されており、大規模データセットに対しても比較的高速に集計できます。

ライセンス / コントリビューション
--------------------------------
（リポジトリに合わせてライセンス情報を追記してください。）

以上。README に記載の手順や環境変数はコード中の Settings / 各スクリプトの仕様に基づきます。追加の操作や詳細な実行例が必要であれば教えてください。