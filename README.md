KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買・研究・監視ツール群（KabuSys）の Python コード群です。  
本 README は、プロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成をまとめたものです。

プロジェクト概要
----------------
KabuSys は以下の機能を持つモジュール群から構成される自動売買基盤です。

- Execution: 発注エンジン（本番 / ペーパートレード切り替え可）
- Monitoring: システム稼働状況・注文状況・リスク監視・Kill Switch
- Portfolio: 銘柄選定・配分・ポジションサイズ計算
- Research: ファクター計算・特徴量探索・IC 計算など
- AI 支援: ニュースを LLM でスコアリング（OpenAI）
- Tools: レポート生成などユーティリティスクリプト
- Utils: ロギング設定、プロセス優先度設定など共通ユーティリティ

主要な設計方針（抜粋）
- .env / 環境変数ベースの設定管理（config モジュール）
- DuckDB / SQLite をデータ格納に使用（分析用と監視用で分離）
- 本番 / ペーパートレードの DB 分離（ペーパートレード時は data/paper_trading.db を使用）
- OpenAI を使った NLP 処理は API キー必須。API 失敗時はフェイルセーフで継続

主な機能一覧
--------------
- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine を起動する run_execution（発注制御・リスク管理含む）
- System / Trade / Risk 各種監視と Kill Switch（run_monitoring）
- Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）
- ファクター計算（momentum、volatility、value）
- ニュース NLP スコアリング（OpenAI を用いた銘柄ごとのセンチメント）
- ログの統一設定（ログファイルは logs/<app_name>.log に日次ローテーション）

セットアップ手順
----------------

1. Python 環境
   - Python 3.9+ 互換を想定（実際の互換性はプロジェクト要件に合わせてください）。
   - 仮想環境の作成と有効化を推奨（venv / conda 等）。

2. 必要パッケージのインストール（例）
   - 以下は最低限必要となるパッケージ例です。実際は requirements.txt を用意している場合はそれを利用してください。
     - duckdb
     - psutil
     - openai
     - PyYAML（config ファイル検証を行う場合）
   - pip 例:
     pip install duckdb psutil openai PyYAML

3. .env の初期作成（推奨）
   - 対話式ウィザードで .env を作成・更新できます:
     python -m kabusys.config_setup
   - ウィザード実行後、.env がプロジェクトルートに生成されます（Git にコミットしないでください）。

4. 設定検証
   - 作成した .env の内容や config/*.yaml の整合性をチェック:
     python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付与します。

5. データディレクトリの準備
   - デフォルトでは以下のパスが使われます（.env で変更可能）:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視用): data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db
   - ログは logs/ 以下に出力されます。起動時に自動作成されますが、権限に注意してください。

主要な環境変数（抜粋）
---------------------
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite (監視) パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、run_monitoring で上書き可、デフォルト 60）

使い方（主要スクリプト）
-----------------------

1. 環境ウィザード
   - .env を対話的に作る:
     python -m kabusys.config_setup

2. 設定検証
   - 設定チェック:
     python -m kabusys.validate_config
   - 厳格モード（警告も失敗）:
     python -m kabusys.validate_config --strict

3. ExecutionEngine の起動
   - 実行（モジュールとして）:
     python -m kabusys.run_execution
   - 指定した環境変数によりペーパートレード (/ 本番) が切り替わります:
     KABUSYS_ENV=paper_trading python -m kabusys.run_execution
   - 注意:
     - paper_trading の場合、MockBrokerClient を使用し paper_trading.db に記録します（本番 DB と分離）。
     - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
     - 実行中は data/execution.pid に PID が書き込まれます。

4. Monitoring の起動（SystemMonitor のポーリング）
   - 実行:
     python -m kabusys.run_monitoring
   - ポーリング間隔を環境変数で変更:
     MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   - 監視は Settings に基づき常に本番 sqlite_path を使用します（環境に依存しません）。
   - 停止: data/stop_requested.flag を作成するとループを終了します。

5. Paper Trading 検証レポート
   - レポート生成:
     python -m kabusys.tools.paper_verification_report
   - 期間指定例:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB 指定:
     python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

6. AI 機能（ニュース NLP / レジーム判定）
   - OpenAI API キー（OPENAI_API_KEY）を設定して利用します。
   - プログラム的に呼び出す場合:
     from kabusys.ai import score_news
     score_news(conn, target_date, api_key="...")

運用上の注意
-------------
- 本番環境では KABUSYS_ENV=live と設定され、validate_config で警告が増えます。LINE 通知等の設定漏れに注意してください。
- Kill Switch: kabusys.monitoring.kill_switch が条件に応じて data/kill.flag を作成します。ExecutionEngine は起動時にこのフラグを検出したら起動を控えます。
- ログ: logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリの作成に失敗するとコンソール出力のみで継続します。
- 権限: ファイル作成・ログ書き込み・プロセス優先度設定（psutil を利用）に権限が必要です。特にプロセス優先度の設定は OS 権限に依存します。

ディレクトリ構成
-----------------
（src/kabusys 以下の主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・.env 自動ロードと Settings クラス
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py           — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py    — 市場レジーム判定（AI + MA）
  - monitoring/
    - monitoring_db.py      — SQLite テーブル定義・永続化層
    - system_monitor.py     — システム状態・データ鮮度監視
    - trade_monitor.py      — （注文監視ロジック）
    - risk_monitor.py       — ドローダウン・ポジション上限監視
    - kill_switch.py        — Kill Switch ファイル操作
    - monitoring_engine.py  — 各 Monitor を束ねるエンジン
    - alert_manager.py      — （通知管理: LINE 等の抽象）
  - execution/              — 発注周りの実装（BrokerFactory, Engine, OrderManager 等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py    — momentum / volatility / value 等
    - feature_exploration.py
  - utils/
    - logging_setup.py      — ログ設定ユーティリティ
    - process_priority.py   — プロセス優先度 / CPU affinity 設定

補足・開発者向け情報
-------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml のある場所）を検出して .env/.env.local を自動ロードします。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- データベース初期化:
  - monitoring_db.init_monitoring_db はテーブル作成と簡単なマイグレーション（列追加）を行います。既存 DB に対して冪等です。
- テスト/モック:
  - paper_trading モードでは MockBrokerClient を使用し、発注結果は本番 DB と完全に分離されます。
- 依存パッケージ:
  - openai クライアントの挙動（例外クラス: RateLimitError 等）に対応したエラーハンドリングが実装されています。
  - PyYAML がない場合は validate_config が YAML 検証をスキップします（警告出力）。

トラブルシュート（よくある質問）
------------------------------
- 起動時に .env が読み込まれない:
  - プロジェクトルートが特定できない場合は自動ロードをスキップします。手動で .env をプロジェクトルートに配置してください。
- ログファイルが作成されない:
  - logs/ ディレクトリ作成に失敗するとファイル出力が無効になります。権限やパスを確認してください。
- OpenAI 関連が動作しない:
  - 環境変数 OPENAI_API_KEY を正しく設定してください。API エラー時は処理がスキップされる設計です（フェイルセーフ）。

ライセンス・貢献
----------------
（このリポジトリのライセンス情報や貢献手順があればここに追記してください）

おわりに
--------
この README はソースコードの注釈・設計意図に基づいて作成しています。実際の運用に合わせて .env、DB パス、ログ設定などを調整してください。必要であれば README に追加の運用手順（systemd / docker / cron など）や詳細な設定例を追記できます。