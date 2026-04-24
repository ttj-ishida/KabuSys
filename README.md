README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買 / リサーチ / 監視のための小規模フレームワークです。本リポジトリには以下の主要機能が含まれます。

- 発注実行エンジン（ExecutionEngine）: 本番 / ペーパートレード両対応
- 監視コンポーネント（Monitoring）: システム稼働状況・注文の監視、Kill Switch
- ポートフォリオ構築ユーティリティ: 候補選定、重み計算、ポジションサイズ決定など
- リサーチ機能: ファクター計算、特徴量探索
- AI 統合: ニュース NLP（OpenAI）によるセンチメントスコア算出、レジーム判定
- ユーティリティ: 環境設定ウィザード、設定検証、ペーパートレード検証レポート 等

主要な設計方針:
- 環境変数/.env による設定管理
- DuckDB（分析用） + SQLite（監視 / ペーパートレード）を併用
- 本番とペーパートレードの DB を分離可能
- 実行スクリプトはプロセス優先度を上げて実行（可能な場合）
- 外部 API 呼び出し（OpenAI など）は明示的にキー指定または環境変数参照

機能一覧
--------
- run_execution.py
  - ExecutionEngine を起動して注文処理を行う
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、data/paper_trading.db を使用
  - プロセスの PID 管理、停止フラグ（data/stop_requested.flag）検出で安全停止

- run_monitoring.py
  - SystemMonitor のポーリングループを起動
  - MONITOR_POLL_INTERVAL でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視用の SQLite（monitoring.db）にログを永続化（監視は常に本番 sqlite_path を使用）

- monitoring モジュール
  - system_monitor: CPU/メモリ/ディスク・プロセス状態・データ鮮度をチェック
  - trade_monitor: 発注ログの監視（滞留注文、約定異常など）
  - risk_monitor: ドローダウン・ポジション上限などの監視とアラート記録
  - kill_switch: Kill 条件を満たしたら data/kill.flag を書き込み ExecutionEngine を停止させる
  - monitoring_engine: 各 Monitor を束ねたポーリングエンジン

- portfolio パッケージ
  - 銘柄選定、重み付け、セクターキャップ、ポジションサイズ計算など純粋関数群

- research パッケージ
  - ファクター計算（momentum/value/volatility）、将来リターン、IC 計算、統計サマリ

- ai パッケージ
  - news_nlp: OpenAI を使ってニュースを銘柄別にスコアリングし ai_scores テーブルへ書き込む
  - regime_detector: ma200 とマクロニュースセンチメントを組合せて日次レジーム判定を実行

- tools
  - paper_verification_report.py: ペーパートレード DB を解析して PASS/FAIL レポートを生成

- 設定支援
  - config_setup.py: 対話式ウィザードで .env を作成/更新
  - validate_config.py: .env と config/*.yaml の整合性チェック

セットアップ手順
----------------
前提:
- Python 3.9+（コードは型ヒント等を使っているため比較的新しい Python を想定）
- Git（ソース取得）
- システムにより追加ネイティブ依存があるパッケージあり（例: psutil）

推奨手順（ローカル開発）:
1. リポジトリをクローンして作業ディレクトリへ移動
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 代表的な依存パッケージ:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証をする場合に必要）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合は pip install -r requirements.txt を使用してください。

4. .env の用意
   - python -m kabusys.config_setup を実行して対話的に .env を作成/更新することを推奨
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 参考: .env.example（存在する場合）を参照

5. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit code=1）

6. DB / ディレクトリ確認
   - デフォルトの DB/ログディレクトリはプロジェクト内の data/ と logs/
   - 必要に応じて .env で DUCKDB_PATH、SQLITE_PATH、PAPER_TRADING_SQLITE_PATH、LOG_DIR を指定

使い方
------
環境変数の主要な説明:
- KABUSYS_ENV: execution の動作モード（development / paper_trading / live）
  - paper_trading: 発注はモック、データベースは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - live: 実際にブローカー API に発注
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能（ai/*.py）に必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant/partial/never/reject）

起動例:
- ExecutionEngine を起動（通常）
  - python -m kabusys.run_execution
  - 起動時に data/stop_requested.flag が存在する場合は起動せず終了します
  - 実行中は data/execution.pid（PID ファイル）を利用

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL を秒数で指定するとポーリング間隔を変更できます:
    - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

ログ:
- setup_logging により標準出力（stdout）と日次ローテートされたログファイル（logs/<app_name>.log）へ出力します
- LOG_DIR 環境変数や setup_logging の引数でログディレクトリを変更可能

停止・Kill
- 実行中のエンジンを停止する手段:
  - data/stop_requested.flag を作成すると run_execution / run_monitoring が検出して停止します
  - Kill Switch（監視側）により data/kill.flag が書き込まれると ExecutionEngine は停止を受けるよう設計されています

注意点 / 運用メモ
- Monitoring の初期化 (init_monitoring_db) は run_monitoring および run_execution で呼ばれます。monitoring 用のテーブルは冪等的に作成されます。
- run_monitoring は監視ログ用の sqlite_path を環境にかかわらず本番 sqlite_path（Settings.sqlite_path）で開きます（監視データは常に一元管理する想定）。
- run_execution は KABUSYS_ENV=paper_trading の場合 PAPER_TRADING_SQLITE_PATH を使用して本番 DB と分離します。
- OpenAI を使用するモジュール（ai/*.py）は OPENAI_API_KEY を要求します。API エラー時はフェイルセーフとして 0 相当で続行する設計が多く採用されていますが、API キー未指定時は例外を投げる関数もあります（呼び出し前にキーを設定してください）。

ディレクトリ構成
----------------
プロジェクトの主要ファイル・ディレクトリ（src/kabusys 以下を中心に一部抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数/.env 読み込み・Settings
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（ma200 + マクロセンチメント）
    - monitoring/
      - monitoring_db.py       — 監視用 SQLite テーブル定義と簡易 DAO
      - system_monitor.py      — システム稼働・データ鮮度監視
      - trade_monitor.py       — 発注ログ監視（滞留注文など）
      - risk_monitor.py        — ドローダウン・ポジション数監視
      - kill_switch.py         — Kill Switch 実装
      - monitoring_engine.py   — 各モニタを束ねる
      - alert_manager.py       — アラート送信（LINE 等、実装に依存）
    - execution/
      - execution_engine.py    — ExecutionEngine（発注ループ）
      - broker_factory.py      — ブローカークライアント生成（本番/モック切替）
      - order_manager.py       — 注文管理ロジック
      - order_repository.py    — 発注履歴の永続化（SQLite 等）
      - reconciler.py          — 注文状態差分解消ロジック
      - risk_manager.py        — 発注時のリスク判定
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - data/
      - pipeline.py            — データパイプライン補助（prices_daily 取得等）
      - stats.py               — zscore_normalize 等
    - utils/
      - logging_setup.py       — 共通ロギング初期化
      - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
    - (その他モジュールが含まれます)

開発・拡張のヒント
------------------
- 設定検証（validate_config）は PyYAML があると config/*.yaml の構文検査を行います。インストールされていない場合は YAML 検証をスキップします。
- OpenAI 呼び出し部分は内部でリトライやレスポンス検証を行うよう作られており、テスト時は _call_openai_api をモック可能です。
- DuckDB を利用したリサーチ関数は SQL を含む実装なので、大量データの分析に適しています。
- ログ設定は setup_logging 経由で統一しています。ログ出力先やレベルを変えたい場合は環境変数（LOG_DIR / LOG_LEVEL）か該当処理での呼び出し時に引数を渡してください。

ライセンス / 貢献
-----------------
本 README はコードベースに基づくドキュメントです。リポジトリの LICENSE ファイルを参照してください。バグ報告や機能追加は Issue / Pull Request を通じてお願いします。

最後に
------
この README はコードスニペットから抽出した概要です。実際の運用では .env の設定と validate_config による検証、ローカルでの小規模な動作確認（paper_trading モード）を推奨します。必要であれば各モジュール（execution, monitoring, ai, research）の詳細な使い方ドキュメントも追加できますので、希望の範囲を教えてください。