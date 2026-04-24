KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株向けの自動売買（アルゴリズムトレーディング）向けライブラリ兼アプリケーション群です。
主な機能群は以下の通りです（モジュール化され、スクリプトから起動できます）:

- 注文実行エンジン（ExecutionEngine）
- 監視コンポーネント（System / Trade / Risk Monitor）
- Kill Switch（条件に応じた安全停止）
- ポートフォリオ構築（候補選定・重み・ポジションサイズ算出）
- リサーチ（ファクター計算・特徴量解析）
- AI 支援（ニュースセンチメント / 市場レジーム判定）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証など）
- ペーパートレード検証レポート生成ツール

特徴
----
- 環境変数ベースの設定 (.env/.env.local の自動読み込みをサポート)
- 本番／ペーパートレード環境を明確に分離（KABUSYS_ENV）
- DuckDB を用いたリサーチ・集計、SQLite を用いた監視・トレードログ永続化
- OpenAI（gpt-4o-mini）を利用したニュース NLP / レジーム判定（オプション）
- ログは標準出力＋日次ローテートファイルに一元化
- フェイルセーフ設計（API失敗時のバックオフ、部分失敗保護など）
- ユーティリティ CLI: .env ウィザード、設定検証、レポート生成

セットアップ手順
----------------

1. 前提
   - Python 3.10+
   - システムに sqlite3 が組み込まれている（標準ライブラリ）
   - 推奨パッケージ（後述）をインストール

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要ライブラリのインストール（例）
   - pip install duckdb psutil openai
   - PyYAML を入れると config/*.yaml の検証が可能: pip install pyyaml
   - （プロジェクト配布に合わせて requirements.txt があればそれを使用してください）

4. .env の準備（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - ウィザードは .env を生成・更新します（.env は Git にコミットしないでください）
   - 自動読み込み
     - プロジェクトルート（.git または pyproject.toml がある場所）から .env/.env.local を自動で読み込みます。
     - 自動読み込みを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告をエラー扱いにする: python -m kabusys.validate_config --strict

主要な環境変数（よく使うもの）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live) — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading 時に使用）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒, デフォルト 60）
- PAPER_FILL_MODE: ペーパーブローカのフィルモード（instant|partial|never|reject）

使い方（起動・ツール）
--------------------

1. ExecutionEngine（取引実行）の起動
   - 本番/開発/ペーパーは KABUSYS_ENV に依存します。
   - 実行:
     - python -m kabusys.run_execution
   - 注意:
     - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い data/paper_trading.db に記録し、本番 DB と分離されます。
     - 起動時に data/stop_requested.flag が存在するとエンジンは起動しません。
     - エンジンは data/execution.pid に PID を書きます。

2. Monitoring（監視ループ）の起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
   - 監視は常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（環境に依存せず本番 DB を参照）。
   - 停止: data/stop_requested.flag ファイルを作成するとループが終了します。

3. .env ウィザード
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱いになります

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - デフォルト DB: data/paper_trading.db または 環境変数 PAPER_TRADING_SQLITE_PATH

6. AI / リサーチ機能
   - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
     - OpenAI API キーが必要（引数または OPENAI_API_KEY 環境変数）
     - raw_news / news_symbols / ai_scores テーブルを使用
   - 市場レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
     - prices_daily / raw_news / market_regime を参照して market_regime テーブルへ書き込み

ログ
----
- 共通ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="execution")
- 出力:
  - コンソール（stdout）
  - 日次ローテーションファイル: LOG_DIR/<app_name>.log（デフォルト logs/<app_name>.log）
- LOG_LEVEL 環境変数でログレベルを制御

安全停止 / Kill Switch / 制御ファイル
----------------------------------
- data/kill.flag: Kill Switch が発動した際に書き込まれるフラグ。ExecutionEngine は起動時にこれを確認します（設定により起動時に自動クリアするオプションあり）。
- data/stop_requested.flag: run_execution / run_monitoring の外部停止トリガー。作成されると各ループは終了します。
- PID ファイル: data/execution.pid（ExecutionEngine が PID を書きます）

ディレクトリ構成（主要ファイル）
------------------------------
以下はこのリポジトリの主要なファイル／モジュール（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env の読み込み・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py         — Monitoring 起動スクリプト（メイン）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 株数決定・キャッシュスケーリング
    - risk_adjustment.py       — セクター上限・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum/value/volatility）
    - feature_exploration.py   — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py              — ニュース NLP スコア生成（OpenAI）
    - regime_detector.py       — 市場レジーム判定（OpenAI + MA200 等）
  - monitoring/
    - monitoring_db.py         — SQLite 監視 DB のスキーマ + ラッパー
    - system_monitor.py        — システム状態・データ鮮度監視
    - trade_monitor.py         — （発注・約定監視; ソース内参照）
    - risk_monitor.py          — ドローダウン・ポジション数監視
    - kill_switch.py           — Kill Switch 実装
    - monitoring_engine.py     — 複数モニタの連携ループ
  - utils/
    - logging_setup.py         — ログ初期化
    - process_priority.py      — プロセス優先度 / CPU affinity 設定
  - monitoring/*.py etc.      — 監視関連ユーティリティ
  - execution/*.py            — Execution 関連（BrokerFactory, Engine, OrderManager 等）
  - data/                     — デフォルトの DB / フラグファイル 等（実行時に生成）

依存関係（主要）
----------------
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（任意、config YAML 検証用）
- 標準ライブラリ: sqlite3, logging, threading, datetime, pathlib, os, json, math など

推奨ワークフロー（例）
--------------------
1. 仮想環境を作成して依存関係をインストール
2. python -m kabusys.config_setup で .env を作成
3. python -m kabusys.validate_config で設定検証
4. (開発) python -m kabusys.run_execution を起動
5. (監視) python -m kabusys.run_monitoring を別プロセスで起動
6. Paper トレードの結果検証 → python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD

注意事項・運用時のヒント
-----------------------
- 本番環境 (KABUSYS_ENV=live) では設定ミスにより実際の発注が行われます。validate_config をよく確認してください。
- .env は絶対にリポジトリにコミットしないでください。
- monitoring は常に Settings.sqlite_path（監視 DB）を使用します。ペーパートレードでも監視 DB は同じパスを参照するため運用上の注意が必要です（run_execution は paper_trading 時に paper_sqlite_path を使用）。
- OpenAI を使うモジュールは API コストとレイテンシを考慮してスケジュールしてください。
- logs/ ディレクトリのディスク容量とログローテーションの動作を監視してください。

ライセンス・貢献
----------------
- この README はコードベースの概要と使い方を説明するためのもので、実際のライセンスはリポジトリ内 LICENSE を参照してください。
- バグ報告・機能提案は issue を立ててください。

補足
----
詳細な設計方針やアルゴリズム（PortfolioConstruction.md / StrategyModel.md など）はリポジトリ内の設計ドキュメントやコメントを参照してください。必要であれば README に追加で「設計ドキュメント一覧」「実行例（env 内容のテンプレート）」なども追記できます。必要なら雛形の .env.example も用意しますのでお知らせください。