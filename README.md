README
=====

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤ライブラリです。本リポジトリは以下を含むモジュール群を提供します。

- 注文実行エンジン起動スクリプト（ExecutionEngine）
- 監視（Monitoring）コンポーネント（プロセス死活、データ鮮度、リスク監視、Kill Switch 等）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定、セクター制限）
- リサーチ（ファクター計算・特徴量解析）
- AI 補助（ニュース NLP／レジーム判定：OpenAI を利用）
- 運用用ユーティリティ（.env ウィザード、設定検証、レポート生成、ログ設定 等）

特徴
----
- 明確に分離された本番 / ペーパー（paper_trading）モード（DB も分離）
- DuckDB を用いたリサーチ向け高速分析、SQLite を監視・トレードログ用に使用
- OpenAI を使ったニュースセンチメント評価（AI スコアのバッチ処理・フェイルセーフ実装）
- Kill Switch（data/kill.flag）により外部から安全に ExecutionEngine を停止可能
- ログ出力はコンソールと日次ローテーションファイル（logs/）で統一管理
- 設定ウィザード（.env の対話作成）と起動前検証 CLI を備える

必要条件（推奨）
--------------
- Python 3.10+
- 推奨パッケージ（実行環境に応じてインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- （任意）SQLite / DuckDB ファイルはローカルディレクトリに作成されます

環境変数（主なもの）
-------------------
主要な環境変数とデフォルト値（.env で設定）:

- KABUSYS_ENV: 実行環境 (development, paper_trading, live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

セットアップ手順
----------------
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （requirements.txt がある場合）pip install -r requirements.txt

4. 環境変数 (.env) を作成
   - 対話式ウィザードを使用:
     - python -m kabusys.config_setup
     - これによりプロジェクトルートに .env を作成できます（.env は絶対に Git にコミットしないでください）
   - もしくは手動で .env を作成（.env.example を参考）

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 問題がある場合は出力を確認して修正。--strict を付けると警告も失敗扱いになります。

使い方（主要スクリプト）
------------------------

- 実行エンジン（Execution）
  - 概要: 注文実行エンジンを起動します。KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録されます（本番 DB と分離）。
  - 起動:
    - python -m kabusys.run_execution
  - 挙動:
    - プロセス優先度を high に設定
    - SQLite (settings.sqlite_path または paper_sqlite_path) と DuckDB に接続
    - Broker クライアント生成 → ExecutionEngine をスレッドで起動
    - data/stop_requested.flag を検知すると安全に停止

- 監視（Monitoring）
  - 概要: SystemMonitor をポーリングしてシステム状態、データ鮮度、トレード状態、リスクを監視し、Kill Switch やアラートに連携します。
  - 起動:
    - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL を省略するとデフォルト 60 秒
  - 挙動:
    - 本モジュールは常に production（settings.sqlite_path）を監視 DB として使用
    - data/stop_requested.flag を検知するとループを終了

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH を優先）

AI / リサーチの呼び出し（ライブラリ用途）
-------------------------------------
- ニュース NLP（ai.score_news）
  - Python から:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key は省略可（環境変数 OPENAI_API_KEY を利用）
- レジーム判定（ai.regime_detector.score_regime）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(duckdb_conn, target_date, api_key="...")

注意: OpenAI 使用時は OPENAI_API_KEY を環境変数に設定するか、関数に api_key を渡してください。

運用上のポイント
-----------------
- Kill Switch:
  - data/kill.flag を作成すると ExecutionEngine に停止指示を送ることができます（KillSwitch モジュールがフラグの作成・判定を行います）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動クリアされますが、本番では 0 を推奨します（安全のため）。
- ペーパー/本番 DB の分離:
  - KABUSYS_ENV=paper_trading の場合、実行は paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全に分離されます。
- ログ:
  - setup_logging が共通のログ設定を提供します。ログは stdout と logs/<app_name>.log（毎日ローテーション）に出力されます。
- プロセス優先度:
  - 起動スクリプトは set_process_priority("high") を呼びます（psutil による OS 関数を使用）。権限不足等で設定できない場合は警告に留まります。

ディレクトリ構成（主要ファイル）
------------------------------
以下はソースツリー（src/kabusys）内の主要なモジュール・ファイルの一覧です（抜粋）:

- kabusys/
  - __init__.py
  - config.py              # 環境変数読み込み・Settings 定義（.env 自動ロード機能含む）
  - config_setup.py        # .env 対話ウィザード
  - validate_config.py     # 起動前設定検証 CLI
  - run_execution.py       # ExecutionEngine 起動スクリプト
  - run_monitoring.py      # Monitoring ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py     # 共通ログ設定
    - process_priority.py  # プロセス優先度・CPU affinity
  - monitoring/
    - monitoring_db.py     # SQLite 用永続化層（テーブル定義・CRUD）
    - system_monitor.py    # システム状態・データ鮮度監視
    - trade_monitor.py     # （トレード監視ロジック）
    - risk_monitor.py      # ドローダウン等のリスク監視
    - kill_switch.py       # kill.flag の書き込み・評価
    - monitoring_engine.py # 複数モニターを束ねるエンジン
    - alert_manager.py     # （通知管理）
  - execution/             # Execution エンジン関連（OrderManager 等）
  - portfolio/
    - portfolio_builder.py # 候補選定・重み計算
    - risk_adjustment.py   # セクター制限・レジーム係数
    - position_sizing.py   # 発注株数計算（単元丸め等）
  - research/
    - factor_research.py   # Momentum/Value/Volatility ファクター計算（DuckDB）
    - feature_exploration.py # 将来リターン/IC/統計サマリー
  - ai/
    - news_nlp.py          # ニュース NLP スコアリング（OpenAI）
    - regime_detector.py   # レジーム判定（MA + LLM）
  - tools/
    - paper_verification_report.py  # ペーパートレードの検証レポート生成

- data/   # デフォルトで使われるデータ格納先（DB, pid, フラグファイル 等）
- logs/   # ログ出力先（デフォルト）

テスト・開発
------------
- 設定ウィザード（config_setup.py）で .env を作成 → validate_config で検証してから起動するワークフローを推奨します。
- AI モジュールの API 呼び出しはネットワークに依存するため、ユニットテスト時は _call_openai_api をモックしてテストしてください（コード内でもその旨がコメントされています）。
- DuckDB を用いたリサーチ関数群は副作用を持たない純粋関数設計が基本で、リプレイしやすくユニットテスト可能です。

ライセンス・貢献
----------------
- 本リポジトリのライセンス表記（LICENSE）がプロジェクトルートに存在する想定です。貢献ガイドライン（CONTRIBUTING.md）があればそちらに従ってください。

補足（よくある質問）
--------------------
- Q: 監視はどの DB を参照しますか？
  - A: Monitoring は常に Settings.sqlite_path（production 用監視 DB）を利用します。Execution は KABUSYS_ENV により production / paper_trading を切り替えます（DB も分離）。

- Q: 実行中に外部から安全に止めたい
  - A: data/stop_requested.flag（または Kill Switch により data/kill.flag）を使って安全に停止できます。run_execution/run_monitoring はフラグを確認して停止処理を行います。

- Q: MONITOR_POLL_INTERVAL はどこで設定？
  - A: 環境変数 MONITOR_POLL_INTERVAL で秒数を指定（例: MONITOR_POLL_INTERVAL=30）。不正値や 0 以下はデフォルト 60 秒にフォールバックします。

最後に
-----
この README はコードベースの主要な使い方と構成を要約したものです。各モジュールの詳細な仕様や引数・定数の説明は各ソースファイル（src/kabusys 以下）内のドキュメント文字列（docstring）を参照してください。問題や不明点があれば、実行ログを確認してから該当モジュールのソースを参照するとトラブルシュートが容易です。