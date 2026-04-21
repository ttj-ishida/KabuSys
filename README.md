プロジェクト: KabuSys — 日本株自動売買システム
================================================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視を目的としたモジュール群です。
主に以下の機能を持ちます。

- 実行エンジン（ExecutionEngine）: 発注・注文管理・リスク管理・約定照合を行う。
- 監視（Monitoring）: システム状態、注文の滞留、ドローダウンやポジション上限を監視し、
  必要時に Kill Switch（停止フラグ）を発動。
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算、セクターキャップ等。
- リサーチ: DuckDB 上の時系列データからファクター（モメンタム・バリュー・ボラティリティ）を計算。
- AI 支援: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定。
- ユーティリティ: ロギング設定、プロセス優先度設定、設定ウィザード、設定検証ツール 等。
- 運用ツール: ペーパートレード結果の検証レポート生成スクリプト等。

主要な特徴
---------
- 設定は .env または環境変数で管理（config.Settings クラスで集約）。
- Paper Trading と Live を明確に分離（paper_trading 時は MockBroker を使用し専用 DB に記録）。
- DuckDB を分析用途に使用、SQLite を監視／注文履歴用に使用。
- モジュール設計でテストや再利用がしやすい純粋関数（portfolio 等）と DB 永続化層を分離。
- OpenAI 呼び出しは堅牢にリトライ/バリデーションを実装（LLM の不安定さを考慮）。

前提（推奨環境）
---------------
- Python 3.10+
- SQLite（標準ライブラリで同梱）
- 推奨／必須ライブラリ（pip でインストール）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML 検証を行う場合）
- その他: ネットワーク接続（kabuAPI / OpenAI を使う場合）

セットアップ手順
----------------
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそれを使用してください。）

3. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
     → J-Quants トークン、kabu API パスワード、KABUSYS_ENV などを設定します。
   - 自動ロードはデフォルトで有効です（プロジェクトルートに .env/.env.local があれば読み込まれます）。
     無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. 設定検証（起動前推奨）
   - python -m kabusys.validate_config
   - 警告を厳格に扱う場合は --strict を付けます。

環境変数（代表的なもの）
------------------------
以下は代表的な環境変数（Settings クラスで参照される）。.env に設定してください。

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBroker を使い data/paper_trading.db に記録します
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（AI モジュールを使う場合に必要）
- LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR（ログ保存ディレクトリ、デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止推奨。1 で自動クリア）

主要なコマンド / 使い方
---------------------

- 設定ウィザード（.env 作成）:
  - python -m kabusys.config_setup

- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）:
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使用し、paper_trading DB に記録します。
  - 既に data/stop_requested.flag が存在するとエンジンは起動せず終了します。
  - 実行時は data/execution.pid に PID を書きます（pid ファイルパスは Settings で変更可）。

- 監視プロセス起動（Monitoring）:
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書きできます（デフォルト 60 秒）。
  - 監視は本番 sqlite_path を常に参照します（環境にかかわらず監視 DB は本番用）。
  - 停止は data/stop_requested.flag を作成することで行えます（起動スクリプトはこのフラグを監視）。

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 関連（ニューススコアリング、レジーム判定）:
  - 呼び出し関数:
    - kabusys.ai.score_news (DuckDB 接続・target_date・api_key)
    - kabusys.ai.regime_detector.score_regime (DuckDB 接続・target_date・api_key)
  - OPENAI_API_KEY の設定が必要（引数で直接渡すことも可能）。

運用上のポイント / 注意点
------------------------
- Kill Switch:
  - RiskMonitor → KillSwitch により条件（ドローダウン超過、ポジション上限超過等）で data/kill.flag を作成し、
    ExecutionEngine に停止シグナルを送ります。flag は既存なら上書きしません（冪等）。
  - 本番で KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag が自動クリアされますが危険なので注意。

- stop_requested.flag / execution.pid:
  - 起動スクリプトは data/stop_requested.flag を監視して優雅に終了します。運用時はこのファイルの作成で停止できます。

- ロギング:
  - kabusys.utils.logging_setup.setup_logging を各起動スクリプトが呼び出します。ログは stdout と
    日次ローテートされたファイル（logs/<app_name>.log）に出力されます。LOG_DIR や LOG_LEVEL で制御可能。

- Paper Trading:
  - paper_trading 環境では MockBrokerClient を使用し、本番 DB とは分離された PAPER_TRADING_SQLITE_PATH に記録します。
  - PAPER_FILL_MODE（instant/partial/never/reject）で約定の挙動を制御できます。

- OpenAI 呼び出し:
  - API エラーやレートリミットに対して指数バックオフ・リトライを実装していますが、API キーの制限に注意してください。
  - LLM レスポンスは厳密にバリデートしてから DB 書き込みします。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義、バージョン情報
- config.py — 環境変数 / 設定の読み込み・Settings クラス（.env 自動ロード含む）
- config_setup.py — .env 作成用対話式ウィザード
- validate_config.py — 起動前設定チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

サブパッケージ（概要）
- execution/ — ブローカーファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler、OrderRepository など（発注処理）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化と DB 操作ラッパー
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・実行プロセス監視
  - trade_monitor.py — （注文滞留や約定異常の監視、ソース内に存在）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag の作成/クリアロジック
  - monitoring_engine.py — 各モニタを束ねるエンジン
- portfolio/ — 銘柄選定、重み計算、リスク調整、ポジションサイズ算出（純粋関数）
- research/ — factor_research.py（モメンタム/バリュー/ボラティリティ）、feature_exploration.py（IC 等）
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングし ai_scores に書き込む
  - regime_detector.py — マクロセンチメントと MA 乖離から市場レジーム判定
- utils/
  - logging_setup.py — 統一的なロギング設定
  - process_priority.py — プロセス優先度 / CPU affinity 設定
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

開発向けヒント
--------------
- DuckDB のテーブル（prices_daily, raw_financials, raw_news 等）はリサーチ・AI モジュールで参照されます。分析用データロードスクリプトを用意してください（本リポジトリ本体にはデータロード部分は含まれていません）。
- unit test 時は OpenAI / psutil の外部呼び出しをモックする設計になっています（内部で _call_openai_api 等を分離実装）。
- SQLite / DuckDB のパスは .env で設定できるため、テストでは一時ファイルを指定して本番データを汚さないようにできます。

付録: よく使うコマンド例
-----------------------
- .env を作成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- Execution 起動 (paper_trading):
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Monitoring 起動:
  - python -m kabusys.run_monitoring
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

以上が README の要点です。必要であれば、.env.example のサンプル内容や systemd / supervisor 用のサービス定義例、ログローテーション設定サンプルなどの追加ドキュメントも作成できます。どの部分を詳しく出力しますか？