README
=====

概要
---
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主に以下の機能群を含みます。

- 自動発注エンジン（ExecutionEngine）
- 監視サービス（Monitoring）
- ポートフォリオ構築・ポジションサイズ計算（Portfolio モジュール）
- ファクター計算・研究ユーティリティ（Research モジュール）
- ニュースを用いた LLM ベースのセンチメント（AI モジュール）
- 各種ユーティリティ（ログ設定・プロセス優先度など）
- ペーパートレード検証用レポート生成ツール

特徴
---
- 環境変数 / .env による柔軟な設定管理（config_setup による対話式ウィザードを提供）
- Paper Trading と Live を分離（Paper は専用 SQLite DB に記録）
- DuckDB を用いた時系列データ処理・ファクター計算
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（任意）
- 監視（CPU/メモリ/ディスク、プロセス生存、注文/リスク異常）と Kill Switch の実装
- ログは stdout と日次ローテートファイルに出力（logs/<app>.log）

セットアップ手順
---
前提
- Python 3.9+（ソースは typing 機能を多用しています）
- SQLite（Python 標準ライブラリで使用可能）
- 推奨ライブラリ: duckdb, psutil, openai, pyyaml（YAML 検証用、任意）

インストール（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt がある場合）
   - pip install -r requirements.txt

設定 (.env)
1. 対話式ウィザードで初期 .env を作成:
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークン、kabu API パスワード、DB パス、実行環境（KABUSYS_ENV）等を設定します。

2. 自動検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります。

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の専用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI 機能を使う場合）
- LOG_LEVEL（例: INFO、DEBUG）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔 秒、default 60）
- PAPER_FILL_MODE（paper_trading の注文応答モード: instant|partial|never|reject）

使い方
---
基本的な実行コマンド

1. 設定ウィザード（.env生成・更新）
   - python -m kabusys.config_setup

2. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

3. 監視サービス起動（ポーリング）
   - MONITOR_POLL_INTERVAL 環境変数で間隔を変更できます（秒）
   - python -m kabusys.run_monitoring

   注意:
   - 監視プロセスは Monitoring DB（sqlite_path）へ書き込みします（環境に関係なく production sqlite_path を使用）。

4. ExecutionEngine 起動（注文エンジン）
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
   - python -m kabusys.run_execution

   停止方法:
   - data/stop_requested.flag を作成するとループが検出して安全に停止します。
   - Kill Switch (kill.flag) は監視側が書き込むことで ExecutionEngine に停止シグナルを送ります。

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report
   - 期間指定:
     - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     - --db PATH を使うか、環境変数 PAPER_TRADING_SQLITE_PATH を設定

6. AI / ニュース NLP（プログラム的利用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
     - DuckDB 接続と target_date（datetime.date）を渡す。api_key が指定なければ OPENAI_API_KEY を参照。
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - 市場レジーム判定を行い、結果を market_regime テーブルへ書き込みます。

ロギング
- setup_logging により stdout と logs/<app>.log（日次ローテート、30 日保持）に出力されます。
- LOG_DIR 環境変数でログ保存先を指定可能。作成できない場合はファイル出力はスキップされます。

停止・Kill Switch
- 監視および実行ループはプロジェクトルートの data/stop_requested.flag による停止要求を確認します。
- 監視は条件に応じて data/kill.flag を作成（Kill Switch）し、ExecutionEngine 側がこれを検出して停止します。
- ExecutionEngine の PID ファイル: data/execution.pid（PID 書き込みに使用）

ディレクトリ構成（主なファイルと役割）
---
src/kabusys/
- __init__.py
  - パッケージ初期化。バージョン情報等。
- config.py
  - 設定管理クラス Settings（環境変数/.env 読み取り、自動ロード機能）
- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）
- validate_config.py
  - 起動前チェック CLI（python -m kabusys.validate_config）
- run_monitoring.py
  - SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔設定）
- run_execution.py
  - ExecutionEngine 起動スクリプト（paper_trading 時は専用 DB を使用）

サブパッケージ / モジュール
- ai/
  - news_nlp.py: ニュースから LLM を使って銘柄別センチメントを算出し ai_scores へ書き込む
  - regime_detector.py: 市場レジーム判定（ETF ma200 + マクロセンチメントで判定）
- monitoring/
  - monitoring_db.py: SQLite テーブルの初期化・CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py: （取引関連の監視ロジック）
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - kill_switch.py: kill.flag の管理
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py: アラート送信（LINE 等）用（実装に依存）
- execution/
  - execution_engine.py: ExecutionEngine 本体（注文実行ループ）
  - broker_factory.py: BrokerClient の生成（実ブローカー or Mock）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py 等
- portfolio/
  - portfolio_builder.py: 候補選定、重み計算
  - position_sizing.py: 発注株数計算、エクスポージャー制限・単元丸め
  - risk_adjustment.py: セクター上限、レジーム乗数
- research/
  - factor_research.py: モメンタム／ボラティリティ／バリュー等ファクター計算（DuckDB）
  - feature_exploration.py: 将来リターン、IC、統計サマリー等
- data/ (実行時に作成される想定)
  - monitoring.db（SQLITE_PATH default）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH default）
  - kabusys.duckdb（DUCKDB_PATH default）
  - kill.flag / stop_requested.flag / execution.pid など
- utils/
  - logging_setup.py: 共通ログ設定
  - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ

よくある注意点 / トラブルシュート
---
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存します。CWD に依存せずモジュール位置から探す設計です。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効化できます。
- PyYAML がインストールされていないと config/*.yaml の検証はスキップされます（validate_config が警告を出します）。
- OpenAI を使う機能は OPENAI_API_KEY が必須です。未設定だと score_news / score_regime は例外を送出します（呼び出し元で捕捉してください）。
- Monitoring は常に settings.sqlite_path（監視 DB）を使用します。Execution は KABUSYS_ENV によって paper_trading 用 DB を使うかどうかを切り替えます。
- MONITOR_POLL_INTERVAL は正の整数（秒）で指定してください。無効値はデフォルト 60 秒にフォールバックします。
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソールのみで出力されます。

開発者向けメモ
---
- DuckDB を用いたクエリは conn.execute(...).fetchall() で結果を取得する設計です。テーブル名（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等）が前提となっています。
- LLM 呼び出し部分（news_nlp._call_openai_api, regime_detector._call_openai_api）はユニットテスト時にモックしやすいよう分離されています。
- monitoring_db.init_monitoring_db は既存 DB へのマイグレーション（カラム追加）を行うため、冪等に実行できます。

ライセンスや貢献
---
（このリポジトリのライセンス情報や貢献方法があればここに追記してください）

問い合わせ
---
実装や使い方に関する質問はリポジトリの issue を作成してください。