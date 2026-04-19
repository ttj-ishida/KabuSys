KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株の自動売買・研究・監視を想定した小〜中規模の Python コードベースです。  
主な機能群は発注実行（ExecutionEngine）、監視（Monitoring）、ファクター計算・リサーチ（Research）、ポートフォリオ構築、およびニュース NLP / レジーム判定（AI）です。  
実運用・ペーパートレード・開発の各モードを想定しており、SQLite / DuckDB をデータ永続化に利用します。

主な特徴
--------
- Execution（発注）エンジン
  - 本番（live）／ペーパートレード（paper_trading）に対応
  - paper_trading 時は MockBrokerClient を使用し、本番 DB と分離（data/paper_trading.db）
  - PID ファイル / 停止フラグ（data/stop_requested.flag / data/kill.flag）によるプロセス制御
- Monitoring（監視）
  - システム稼働・CPU/メモリ/ディスク・データ鮮度・注文状況・リスク（ドローダウン・保有数）を定期チェック
  - Kill Switch により閾値超過時に ExecutionEngine 停止のための flag を作成
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に保存
- Research（調査）
  - DuckDB 上でファクター（Momentum / Volatility / Value など）や将来リターン、IC を計算
- AI（ニュース NLP / レジーム判定）
  - OpenAI（gpt-4o-mini）を用いたニュースのセンチメント集計・市場レジーム判定（APIキー必須）
  - レスポンスのバリデーション・リトライ・書き込み処理を備え、フェイルセーフ実装
- ユーティリティ
  - 環境設定ウィザード（.env 生成）、設定検証 CLI、ログ設定ユーティリティ、プロセス優先度設定 等
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可能）

セットアップ
-----------
1. 必要な Python バージョン
   - Python 3.10 以上を推奨（型注釈に | を使用）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - 任意で: pip install pyyaml  （config/.yaml の検証を有効にする場合）
   - （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. プロジェクトルート確認
   - 本リポジトリのルートに .git または pyproject.toml があれば、config モジュールは自動で .env / .env.local を読み込みます。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

環境設定 (.env)
----------------
- まず対話式ウィザードで .env を作るのが簡単です:

  python -m kabusys.config_setup

- 重要な環境変数（例）
  - JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
  - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
  - KABUSYS_ENV: execution モード（development / paper_trading / live）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
  - LOG_LEVEL / LOG_DIR 等

- .env の自動ロード
  - OS 環境変数 > .env.local > .env の優先順で読み込まれます。
  - OS 環境変数を保護するため .env.local は上書き可能ですが OS のキーは上書きされません。

設定確認
--------
- 設定検証 CLI:

  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  (警告もエラー扱いにする)

起動 / 使い方
------------

1. Execution（発注エンジン）を起動
   - 本番 / ペーパーの挙動は KABUSYS_ENV に依存
   - 起動:

     python -m kabusys.run_execution

   - 特記:
     - paper_trading の場合は MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
     - 実行開始前に data/stop_requested.flag が存在すると起動せず終了します。
     - 実行中は data/execution.pid に PID（設定により path 変更可）を書き込みます。
     - 停止は data/stop_requested.flag の作成（手動でフラグを作る）やプロセスの SIGINT などで行えます。

2. Monitoring（監視）を起動
   - 起動:

     python -m kabusys.run_monitoring

   - オプション / 環境変数:
     - MONITOR_POLL_INTERVAL: ポーリング間隔（秒、デフォルト 60）
   - 動作:
     - 監視は Settings.sqlite_path（monitoring は常に本番 sqlite_path を参照）にログを書きます。
     - data/stop_requested.flag を検知すると監視ループを終了します。

3. Paper Trading レポート生成
   - ローカルのペーパートレード DB から検証レポートを作成:

     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     # DB パスを指定する場合:
     python -m kabusys.tools.paper_verification_report --db path/to/db.sqlite

4. AI / レジーム判定・ニューススコアリング
   - OpenAI API キー（OPENAI_API_KEY）を環境変数で設定してください。
   - news_nlp.score_news や regime_detector.score_regime を直接呼び出して利用できます（DuckDB 接続と target_date を渡す）。

ロギング
--------
- 全起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼んで統一的にログを出力します。
- デフォルトは stdout と logs/<app_name>.log（日次ローテーション、30日保持）。
- LOG_LEVEL / LOG_DIR は環境変数で調整可能。

停止フラグ / Kill Switch
----------------------
- 実行制御:
  - data/stop_requested.flag: run_monitoring / run_execution が監視している外部停止フラグ（停止要求）
  - data/kill.flag: KillSwitch が書き込むファイルで、ExecutionEngine を停止するトリガー
- KillSwitch はリスク（ドローダウン・ポジション上限など）を監視して基準を満たすと kill.flag を書き込みます。

ディレクトリ構成（主要ファイル）
-------------------------------
以下は src/kabusys 以下の主要モジュールと役割の概観です。

- src/kabusys/
  - __init__.py            : パッケージ定義（__version__ 等）
  - config.py              : 環境変数 / 設定読み込み（.env 自動ロード・Settings クラス）
  - config_setup.py        : .env の対話式ウィザード（python -m kabusys.config_setup）
  - validate_config.py     : 設定検証 CLI
  - run_execution.py       : ExecutionEngine 起動スクリプト
  - run_monitoring.py      : SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py     : 監視データの SQLite 永続化層
    - system_monitor.py    : システム / データ鮮度監視
    - trade_monitor.py     : （注文・約定）監視（該当ファイルあり）
    - risk_monitor.py      : ドローダウン・ポジション上限監視
    - kill_switch.py       : Kill Switch 実装（kill.flag 書き込み）
    - monitoring_engine.py : 各 Monitor の統合実行
    - alert_manager.py     : アラート送信ロジック（LINE 等、実装ファイル参照）
  - execution/
    - execution_engine.py  : 発注エンジン本体（EngineConfig / ExecutionEngine）
    - broker_factory.py    : ブローカークライアント生成（Mock / 実ブローカー）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py  : 候補選定・重み付け
    - position_sizing.py    : 株数決定・全体キャップ調整
    - risk_adjustment.py    : セクターキャップ・レジーム乗数
  - research/
    - factor_research.py    : ファクター計算（momentum / volatility / value）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/
    - news_nlp.py           : ニュース NLP（センチメント -> ai_scores）
    - regime_detector.py    : マクロ + ETF MA を合成したレジーム判定
  - data/                  : デフォルトデータ格納ディレクトリ（DB, PID, flag 等）
  - logs/                  : デフォルトログ出力先（作成は自動）

開発上の注意 / ベストプラクティス
---------------------------------
- 本番（live）実行時は .env の設定を十分確認してください（validate_config を実行）。
- .env は決してリポジトリにコミットしないでください（config_setup.py も README の注意に従います）。
- AI 機能は OpenAI API へのコスト発生・API レート制限に注意してください。リトライ・バックオフ実装はありますが運用設計は必要です。
- DB（DuckDB / SQLite）はファイル単位で扱うため、バックアップやファイルパス運用に注意してください。
- process priority / CPU affinity 設定は psutil を使います。権限不足で警告が出ることがありますが安全にフォールバックします。

よく使うコマンド一覧
-------------------
- .env 作成（対話式）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- Execution 起動
  python -m kabusys.run_execution

- Monitoring 起動（デフォルト 60 秒間隔）
  python -m kabusys.run_monitoring
  # 間隔を上書き:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

サポート / 拡張
----------------
- DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）を整備することで research / ai 機能が動作します。
- ブローカークライアントや注文ロジックは BrokerClientFactory などを拡張して追加できます。
- アラート送信先（LINE 等）は AlertManager を実装して統合してください。

ライセンス / 貢献
-----------------
- 本 README にはライセンスは含めていません（リポジトリの LICENSE を参照してください）。
- バグ報告・機能追加は PR / Issue を通してお願いします。

以上。必要であれば各モジュール（ExecutionEngine、Monitoring の内部 API、AI の詳細な実行例など）を追記して README を拡張します。どの箇所を詳しく書くか指定してください。