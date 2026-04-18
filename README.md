README
=====

概要
----
KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした小規模なフレームワークです。  
このリポジトリは、以下のような機能群を持つモジュール群で構成されています。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象化（paper/live 切替）
- 監視サブシステム（システム稼働率・データ鮮度・注文ログ・リスク監視）
- ポートフォリオ構築ユーティリティ（銘柄選定・重み計算・ポジションサイズ計算）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- ニュース NLP / レジーム判定（OpenAI を使ったセンチメント計算）
- 各種 CLI ユーティリティ（.env ウィザード、設定検証、紙トレード検証レポート）

主な設計方針として、外部 API 呼び出し・発注ロジックは抽象化されており、paper_trading 環境では MockBroker を使って本番 DB と分離できるようになっています。

機能一覧
--------
- 実行管理
  - run_execution.py：ExecutionEngine を起動（スレッド実行、停止フラグ監視）
  - paper_trading 時は専用 SQLite（data/paper_trading.db）へ記録
- 監視
  - run_monitoring.py：SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔指定可）
  - MonitoringDB：system_status / trade_logs / positions / risk_logs / dashboard の永続化
  - MonitoringEngine：System / Trade / Risk の監視をまとめて実行、Kill Switch 判定とアラート連携
- ポートフォリオ関連（純粋関数）
  - 候補選定・等重/スコア重み計算
  - セクターキャップ適用、レジーム乗数計算
  - 株数決定（単元処理・リスク制限・aggregate cap）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI / NLP
  - news_nlp.score_news：raw_news から銘柄別センチメントを生成し ai_scores テーブルへ書込
  - regime_detector.score_regime：ETF の MA200 とマクロニュースを合成して market_regime を書込
  - OpenAI 呼び出しに対するリトライや出力バリデーションを実装
- ツール
  - config_setup.py：.env を対話形式で作成・更新
  - validate_config.py：環境変数・config/*.yaml の存在・基本妥当性検査
  - tools/paper_verification_report.py：ペーパートレード DB を集計して検証レポート出力

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境の準備（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合に必要）
   - インストール例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がない場合は上記を個別にインストールしてください。

4. .env を作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに .env を直接作成してください（.env.example を参照）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨設定:
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（DEBUG/INFO/...）
     - LOG_DIR（ログ出力先、デフォルト: logs/）

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 追加で --strict を付けると警告も FAIL 扱いになります

6. ディレクトリ作成（自動で作られますが念のため）
   - mkdir -p data logs

使い方
------
基本的にモジュールは CLI/スクリプトから起動します。

- 監視ループを起動
  - 環境変数でポーリング間隔を変更:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - 起動:
    - python -m kabusys.run_monitoring
  - 備考:
    - run_monitoring は Monitoring の SQLite（settings.sqlite_path）を使用します（環境にかかわらず本番 sqlite_path を参照する設計）。
    - stop: プロジェクトルートの data/stop_requested.flag を作成すると停止ループが検出して終了します。

- ExecutionEngine（発注エンジン）を起動
  - paper_trading モードで起動（MockBroker を使用、DB は data/paper_trading.db）
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - live / development でも同様に KABUSYS_ENV を設定して起動できます
  - 停止方法:
    - data/stop_requested.flag を作成すると実行中のループが検出して安全に停止します
    - Kill Switch（監視側で条件を満たした場合）は data/kill.flag を書き込んで Engine 側へ停止要求を送ります
  - PID ファイル:
    - 実行中は settings.pid_file_path（デフォルト: data/execution.pid）へ PID を書きます

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH を指定するか、環境変数 PAPER_TRADING_SQLITE_PATH を設定します

- AI / NLP 機能（プログラム的に呼ぶ場合）
  - news_nlp（銘柄別ニューススコア付与）
    - Python から:
      from datetime import date
      import duckdb
      from kabusys.ai.news_nlp import score_news
      conn = duckdb.connect("data/kabusys.duckdb")
      score_news(conn, date(2026, 4, 1), api_key="sk-...")

  - regime_detector（市場レジーム判定）
    - Python から:
      from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, date(2026, 4, 1), api_key="sk-...")

環境変数一覧（主要）
-------------------
- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ / パス
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckb）
  - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 DB（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH: 実行 PID ファイル（デフォルト: data/execution.pid）
  - LOG_LEVEL: ログレベル（デフォルト: INFO）
  - LOG_DIR: ログディレクトリ（デフォルト: logs/）

- AI
  - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
  - PAPER_FILL_MODE: paper_trading 時の約定モデル（instant|partial|never|reject、デフォルト: instant）

- 監視関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動で削除するか（0/1、デフォルト: 0）

運用上の注意
------------
- run_monitoring は「監視」プロセスとして本番の monitoring.sqlite（settings.sqlite_path）を参照する設計です。paper_trading だからといって監視 DB が切り替わるわけではない点に注意してください（実装上の意図による）。
- kill.flag による ExecutionEngine の停止は意図的な「Kill Switch」です。本番環境で KILL_FLAG_CLEAR_ON_START=1 を設定するのは危険です（validate_config でも警告が出ます）。
- ログはデフォルトで logs/<app_name>.log に日次でローテートされます。LOG_DIR の作成に失敗した場合はコンソール出力のみになります。
- OpenAI 呼び出しはリトライを実装していますが、APIキーの管理には注意してください。テスト時は該当関数をモックすることを推奨します。

ディレクトリ構成（抜粋）
---------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings 管理
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — SystemMonitor ポーリング起動スクリプト

- ai/
  - __init__.py
  - news_nlp.py             — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py      — 市場レジーム判定（MA + LLM）

- monitoring/
  - monitoring_db.py        — SQLite 永続化層（schema/migrations）
  - system_monitor.py       — システム状態 / データ鮮度チェック
  - trade_monitor.py        — （注文監視ロジック）
  - risk_monitor.py         — ドローダウン / ポジション上限監視
  - kill_switch.py          — kill.flag 書込みロジック
  - monitoring_engine.py    — 各 Monitor を束ねる

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - logging_setup.py        — 共通ログ設定
  - process_priority.py     — プロセス優先度 / CPU affinity 設定
  - __init__.py

補足（開発者向け）
-----------------
- SQL テーブルスキーマは monitoring/monitoring_db.py の init_monitoring_db() に記載されています。既存 DB に対する簡単なマイグレーション（カラム追加）処理も含まれています。
- AI 呼び出しや外部接続はモジュール内で分離されているため、単体テスト時は OpenAI クライアント呼び出し部分をモックしてください（モジュール内で _call_openai_api を分離している箇所が多くあります）。
- logger は必ず kabusys.utils.logging_setup.setup_logging() を使って初期化してください（スクリプト内ですでに呼ばれています）。

ライセンス
---------
（この README にはライセンス情報は含めていません。プロジェクトに適切な LICENSE ファイルを追加してください。）

以上。README に不足があれば、対象箇所（例えば実際の ExecutionEngine の起動オプションや broker 実装）を教えてください。必要に応じて使用例やトラブルシュート項目を追加します。