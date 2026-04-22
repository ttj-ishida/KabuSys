KabuSys
=======

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）です。  
このドキュメントはリポジトリ内のコード構成と基本的なセットアップ／運用方法をまとめたものです。

プロジェクト概要
---------------
KabuSys は日本株向けの自動売買フレームワークです。  
主要機能は次のとおりです。

- 注文実行エンジン（ExecutionEngine）
  - 本番 / ペーパートレード切替対応（KABUSYS_ENV）
  - ブローカークライアント抽象化（MockBrokerClient を用いたペーパートレード）
  - リスク管理（RiskManager）、注文管理（OrderManager）などを備える
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag による安全停止（Kill Switch）
  - SQLite（monitoring DB）へ各種ログを永続化
- ポートフォリオ構築
  - 候補選定、重み付け、ポジションサイズ計算、セクター上限適用など純粋関数群
- リサーチ（Research）
  - DuckDB を用いたファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索、IC 計算など分析ユーティリティ
- AI 支援モジュール（OpenAI）
  - ニュースセンチメント算出（news_nlp）
  - 市場レジーム判定（regime_detector）
- ユーティリティ／ツール
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - ペーパートレード検証レポート生成（tools.paper_verification_report）

主な特徴
- 本番とペーパートレード用 DB を分離（PAPER_TRADING_SQLITE_PATH）
- DuckDB を分析用途に使用
- ログはコンソール＋ファイル（日次ローテーション）で統合管理
- プロセス優先度や CPU affinity の設定ユーティリティを内蔵
- OpenAI（gpt-4o-mini 相当）を用いたニュース NLP / マクロ情勢評価（任意）

動作要件（概略）
- Python 3.9+（ソースでは型ヒントに 3.10 以降の構文が一部ある可能性があるため、3.10+ を推奨）
- 必要ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml の内容検証を行う場合）
- SQLite は標準ライブラリで利用可

セットアップ手順
----------------
1. リポジトリを取得する
   - git clone … 等

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows の場合は .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ requirements.txt がない場合は少なくとも duckdb, psutil, openai をインストールしてください。

4. .env ファイルの作成（対話式）
   - python -m kabusys.config_setup
   - 各項目は対話形式で設定されます。J-Quants トークン、kabu API パスワード、KABUSYS_ENV（development / paper_trading / live）などを入力します。
   - 生成された .env を絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - 問題がある場合は出力を確認し修正。厳格モード:
     - python -m kabusys.validate_config --strict

6. データディレクトリの準備（任意）
   - デフォルトでは data/ 以下に SQLite / PID / flag ファイルを置きます。必要に応じて環境変数で上書きしてください（例: SQLITE_PATH, DUCKDB_PATH, PAPER_TRADING_SQLITE_PATH）。

主な環境変数（抜粋）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒。デフォルト 60）

基本的な使い方
--------------
実行エンジン（ExecutionEngine）起動
- 本番（または設定された KABUSYS_ENV に従う）:
  - python -m kabusys.run_execution
- 特記事項:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
  - 実行中は data/execution.pid に PID 書き込みを行います。
  - Execution 起動時に kill.flag を自動でクリアする挙動は KILL_FLAG_CLEAR_ON_START によって制御できます（本番では無効推奨）。

監視プロセス（Monitoring）起動
- python -m kabusys.run_monitoring
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒数で上書き可能（デフォルト 60 秒）。
- 監視は常に本番用の sqlite_path（Settings.sqlite_path）を参照します（環境にかかわらず）。
- 監視は system_status / trade_logs / risk_logs / dashboard などのテーブルを生成・更新します。
- 監視側から KillSwitch を通じて data/kill.flag を書くことで ExecutionEngine に停止を要求できます。

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
- オプション:
  - --from YYYY-MM-DD
  - --to YYYY-MM-DD
  - --db PATH（PAPER_TRADING_SQLITE_PATH を上書き）
- 出力: 稼働率・注文成功率・送信率・レイテンシ等の集計と PASS/FAIL 判定

AI モジュール（ニュース NLP / レジーム判定）
- OpenAI API キーが必要（環境変数 OPENAI_API_KEY または引数で指定）
- ニューススコア算出:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - DuckDB 接続（conn）を渡して実行。ai_scores テーブルへ書き込みます。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - market_regime テーブルへ冪等書き込みします。

ログ
- ロギング設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution" など)
- デフォルトで logs/<app_name>.log に日次ローテーションで出力（30日保持）。コンソール（stdout）にも出力されます。
- ログディレクトリは環境変数 LOG_DIR、ログレベルは LOG_LEVEL で変更可能。

停止・Kill Switch・フラグ
- 停止要求: data/stop_requested.flag （run_execution / run_monitoring が監視している）
- 強制停止（Execution 側に処理停止を要求）: data/kill.flag（KillSwitch が書き込む）
- kill.flag は Settings.kill_flag_clear_on_start が 1 の場合、Execution 起動時にクリアされることがあります（本番では 0 推奨）。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 以下の主要ファイル・モジュールです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定管理（.env 自動ロード等）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト

- src/kabusys/execution/     — 発注実行関連（Engine, OrderManager, RiskManager 等）
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - broker_factory.py
  - ...

- src/kabusys/monitoring/    — 監視系コンポーネント
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_db.py
  - alert_manager.py

- src/kabusys/portfolio/     — ポートフォリオ構築
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/      — リサーチ／ファクター計算
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/            — AI 関連
  - news_nlp.py
  - regime_detector.py

- src/kabusys/tools/
  - paper_verification_report.py

- src/kabusys/utils/
  - logging_setup.py
  - process_priority.py
  - ほかユーティリティ群

運用上の注意
-------------
- .env は秘匿情報を含むため絶対にコミットしないでください。
- KABUSYS_ENV=live の際は特に注意（実際の発注が行われます）。validate_config で live 向けガード（LINE 通知設定など）を確認してください。
- paper_trading は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。
- OpenAI を用いる機能は API 使用料が発生します。試験運用では API 呼び出しをモックすることを推奨します。
- ログディレクトリの作成に失敗するとファイル出力は無効化され、コンソール出力のみになります。

開発／テストのヒント
--------------------
- unit テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env の自動読み込みを無効化できます。
- AI モジュールの外部呼び出しは _call_openai_api を patch / mock してテストできます（実装で想定）。
- DuckDB / SQLite によるローカルデータを用いれば実際のブローカーにアクセスせずに挙動検証が可能です。

付録：よく使うコマンド例
----------------------
- .env ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- Execution 起動:
  - python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

最後に
------
この README はコードベースの主要機能と運用上のポイントをまとめたものです。  
各モジュール（execution/*, monitoring/*, ai/*, research/*）には詳細なドキュメントコメントが含まれているので、実装や拡張時はソースの docstring を参照してください。質問や補足が必要であれば教えてください。