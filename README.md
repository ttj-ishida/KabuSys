KabuSys — 日本株自動売買システム
=============================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした小規模なフレームワークです。  
このリポジトリには、注文実行エンジン（ExecutionEngine）、監視ループ（Monitoring）、ファクター計算・リサーチツール、ペーパートレード検証ツール、OpenAI を用いたニュース NLP / レジーム判定などのコンポーネントが含まれます。

主な特徴
--------
- ExecutionEngine（発注エンジン）
  - 実口座 / ペーパートレードを切り替え可能（KABUSYS_ENV=paper_trading）。
  - Paper Trading 時は MockBrokerClient を用いて data/paper_trading.db に記録。
  - 起動時に PID ファイルを生成し、stop/kill フラグにより安全に停止可能。
- Monitoring（監視）
  - システム状態、データ鮮度、注文ログ、リスク指標を定期的に記録。
  - Kill Switch（ドローダウンやポジション上限で自動停止）をサポート。
  - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
- 監査・永続化
  - SQLite（監視用）および DuckDB（リサーチ用）を使用。
  - monitoring_db モジュールにより監視用テーブルを冪等に初期化・マイグレーション。
- リサーチ / ポートフォリオ構築
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、将来リターン、IC 計算、ポジションサイズ算出、セクター制約など純粋関数群。
- AI モジュール
  - OpenAI を使ったニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
  - API キーは環境変数 OPENAI_API_KEY を使用。
- ツール
  - .env 対話ウィザード（config_setup）、設定検証 CLI（validate_config）、Paper Trading 検証レポート生成（paper_verification_report）等。

セットアップ手順
---------------
前提
- Python 3.10 以上（型ヒントの union 演算子 | を使用）
- SQLite は標準搭載、DuckDB/PyPI パッケージが必要

インストール（例）
1. 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai
   - （YAML 設定ファイルの検証を使う場合）pip install pyyaml

（注）requirements.txt がある場合は pip install -r requirements.txt を使用してください。

環境変数の初期化
1. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
   - 作成後、.env がプロジェクトルートに保存されます（Git 管理しないでください）。

必須環境変数（代表）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要（AI モジュール）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- DUCKDB_PATH / SQLITE_PATH（任意、デフォルトは data/kabusys.duckdb / data/monitoring.db）

設定検証
- python -m kabusys.validate_config
  - --strict を付けると警告も失敗（exit 1）扱いになります。

主要ファイル（実行系）
- 実行（本番 / ペーパートレード）
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB を使用（デフォルト data/paper_trading.db）。
    - 起動時に優先度を high に設定、execution.pid を作成、stop フラグ existence を監視。
- 監視（監視ループ）
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可（デフォルト 60 秒）。
    - data/stop_requested.flag を検知するとループを終了。

重要なフラグ / ファイル
- data/kill.flag: Kill Switch が書き込むファイル。ExecutionEngine 停止シグナル。
- data/stop_requested.flag: run_monitoring / run_execution が停止要求として参照するファイル。
- data/execution.pid: 実行プロセスの PID を記録するファイル。

使い方（コマンド例）
-----------------
環境設定
- python -m kabusys.config_setup
- python -m kabusys.validate_config
  - 問題がなければ exit 0 を返します。

起動
- 監視を開始する（常駐実行向け）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジンを起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

停止（手動）
- 実行エンジンを停止したい場合: data/kill.flag を作成（KillSwitch は書込み処理も行う）。monitoring が代わりに書く場合もある。
- 監視ループを止める: data/stop_requested.flag を作成するか、プロセスを SIGINT（Ctrl-C）で停止。

ペーパートレード検証レポート
- python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（デフォルトは環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

AI モジュール
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY 環境変数を使用する場合は api_key を省略可
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意事項
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API コールは課金対象になります。
- KABUSYS_ENV=live の場合は本番口座へ実際に発注が行われます。設定や資金管理に十分注意してください。
- .env ファイルは絶対に Git にコミットしないでください（機密情報を含みます）。
- ロギング: デフォルトで logs/ ディレクトリに日次ローテーションでログを残します。ログ出力が失敗しても標準出力には出力されます。

ディレクトリ構成（主要）
----------------------
（src/kabusys 以下）:

- __init__.py
- config.py
- config_setup.py        — .env 対話ウィザード
- validate_config.py     — 設定検証 CLI
- run_execution.py       — ExecutionEngine 起動スクリプト
- run_monitoring.py      — Monitoring 起動スクリプト

サブパッケージ
- ai/
  - news_nlp.py          — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py   — レジーム判定（MA + マクロセンチメント）
- monitoring/
  - monitoring_db.py     — SQLite 監視 DB 初期化・操作
  - system_monitor.py    — システム状態 / データ鮮度監視
  - risk_monitor.py      — ドローダウン・ポジション上限監視
  - trade_monitor.py     — （注文関連監視）※実装を参照
  - monitoring_engine.py — 各モニタを束ねるエンジン
  - kill_switch.py       — kill.flag 書込みユーティリティ
  - alert_manager.py     — （アラート管理）※実装参照
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - reconciler.py
  - risk_manager.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py     — ログ設定ユーティリティ
  - process_priority.py  — プロセス優先度 / CPU affinity 設定

（データ・ログ）
- data/                  — (デフォルト) DB・PID・フラグを置く場所
  - monitoring.db (SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - paper_trading.db
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/                  — ログ出力先（デフォルト）

開発・テスト向けヒント
---------------------
- 自動で .env を読み込む機構があり、プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込みます。テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- 設定検証（validate_config）は .env の基本的な不備や config/*.yaml の存在／パースをチェックします（PyYAML がインストールされていない場合は YAML 検証をスキップします）。
- AI モジュールの呼び出しは外部 API に依存するため、ユニットテストでは OpenAI クライアント呼び出しをモックしてください（コード内に差し替え用の関数が想定されています）。

ライセンス・バージョン
---------------------
- パッケージバージョン: __version__ = "0.1.0" （src/kabusys/__init__.py）
- ライセンス表記等はリポジトリのトップレベルファイルをご確認ください（ここでは記載がありません）。

付記（よくある質問）
-------------------
Q. MONITOR_POLL_INTERVAL の指定方法は？
A. 環境変数 MONITOR_POLL_INTERVAL を秒数で指定（例: MONITOR_POLL_INTERVAL=30）。無効な値はデフォルト 60 秒にフォールバックします。

Q. ペーパートレードと本番 DB は分離されていますか？
A. はい。KABUSYS_ENV=paper_trading の場合、Execution は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 monitoring.db とは分離されます。

Q. kill.flag は何に使いますか？
A. Kill Switch が閾値を超えた場合（例: ドローダウン）に kill.flag を書き、ExecutionEngine を停止させるために使用します。起動時に kill.flag を自動でクリアする設定（KILL_FLAG_CLEAR_ON_START）がありますが、本番では 0 を推奨します。

---
この README はコードベースの主要機能と運用上の注意をまとめたものです。実装の詳細や追加オプションは各モジュール内の docstring・コメントを参照してください。必要であれば、README に含めたい追加情報（例: systemd ユニット、docker-compose、CI 設定の例）を教えてください。