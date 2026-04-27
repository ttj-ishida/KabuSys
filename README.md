KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買用ライブラリ / 実行ツール群です。  
本 README はコードベース（src/kabusys 以下）を元に、導入・実行方法、主要機能、ディレクトリ構成を日本語でまとめたものです。

概要
----
KabuSys は次のような機能を持つ自動売買プラットフォームのコンポーネント群です。

- 実行エンジン（ExecutionEngine）: ブローカークライアントと連携して発注ループを実行
- 監視（SystemMonitor）: 定期的なヘルスチェック・監視データ収集
- 起動時・朝の判定レポート（Pre-Market / Execution Startup / Night Batch）
- ポートフォリオ構築・ポジションサイズ計算（等重配分・スコア加重・リスクベース）
- 研究用モジュール（ファクター計算・特徴量探索）
- ニュースNLP ベースの銘柄センチメント（OpenAI API を用いた ai_score）
- 各種ユーティリティ（ログ設定、プロセス優先度設定、設定ウィザード、設定検証）

主な機能一覧
--------------
- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動。KABUSYS_ENV=paper_trading 時は MockBroker を使用し、ペーパートレード用 DB（data/paper_trading.db）へ記録
  - run_monitoring.py — SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL 環境変数で間隔上書き可能）
  - run_pre_market_report.py — Pre-Market レポートを生成（--save, --json オプション）
- 設定・検証ツール
  - config_setup.py — .env の初期作成 / 対話式更新ウィザード
  - validate_config.py — .env と config/*.yaml の起動前検証（--strict モードあり）
- レポート / 検証ツール
  - tools/paper_verification_report.py — ペーパートレード結果の検証レポート生成
- ポートフォリオ構築
  - portfolio_builder, position_sizing, risk_adjustment 等：候補選定、重み付け、株数算出、セクター上限やレジーム補正
- 研究用
  - research モジュール：momentum/volatility/value ファクター計算、forward returns、IC（情報係数）等
- AI / NLP
  - ai/news_nlp.py：raw_news から銘柄別センチメントを OpenAI に問い合わせて ai_scores を生成
- 共通ユーティリティ
  - utils.logging_setup — 一貫したログ設定（Console + 日次ローテーションファイル）
  - utils.process_priority — プロセス優先度 / CPU affinity 設定

セットアップ手順
----------------
前提:
- Python 3.10 以上（型ヒントに `X | Y` 形式を使用）
- SQLite（標準ライブラリ）、その他以下 Python パッケージ

推奨インストール（例）
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール（requirements.txt がある場合はそれを利用）
   - pip install duckdb pyyaml psutil openai
   - 追加で必要なら requests 等をインストールしてください

3. 環境変数の設定
   - プロジェクトルートに .env を作成するか、環境変数を直接設定します。
   - 対話式ウィザードで .env を作る:
     - python -m kabusys.config_setup
   - 自動ロード:
     - config.py はプロジェクトルート（.git または pyproject.toml を基準）を検出して .env/.env.local を自動読み込みします。
     - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください

必要な主な環境変数（最低限）
- JQUANTS_REFRESH_TOKEN（必須）
- JQUANTS_BULK_API_KEY（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV（development | paper_trading | live） — デフォルト: development
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（ペーパートレード専用 DB、デフォルト: data/paper_trading.db）
- OPENAI_API_KEY（ai/news_nlp を実行する場合）

重要な運用系環境変数（抜粋）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE — MockBroker の約定モード（instant / partial / never / reject）
- LOG_LEVEL, LOG_DIR — ログレベル・ログ格納先
- KILL_FLAG_CLEAR_ON_START — 本番での自動クリアは危険（デフォルト 0 推奨）

使い方（主要コマンド）
--------------------

- 設定ウィザード（.env 作成／更新）
  - python -m kabusys.config_setup

- 設定検証（起動前チェック）
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict  # 警告もエラー扱いにする

- 実行エンジン起動
  - python -m kabusys.run_execution
  - 挙動:
    - settings.env が paper_trading の場合は MockBroker を使用し、PAPER_TRADING_SQLITE_PATH に書き込む
    - 起動時にブローカーから資産を取得しリコンシリエーションを実行
    - 起動サマリ（Execution Startup Summary）を標準出力/artifacts に保存

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で指定可能（例: MONITOR_POLL_INTERVAL=30）
  - 停止はプロジェクトルート/data/stop_requested.flag を作成することで行える

- Pre-Market レポート生成
  - python -m kabusys.run_pre_market_report
  - オプション:
    - --save : artifacts/pre_market/<date>/ に保存
    - --json : JSON 形式で出力

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 日付フィルタや DB パス指定のオプションあり（--from, --to, --db）

ログとアーティファクト
---------------------
- デフォルトのログディレクトリ: logs/
  - setup_logging() により stdout 出力 + 日次ローテートファイル（logs/<app_name>.log）を生成
- レポートや起動サマリは artifacts/ 以下に保存されます（例: artifacts/pre_market/, artifacts/execution_startup/）

ディレクトリ構成（主要ファイル）
--------------------------------
リポジトリの src/kabusys 以下の主要モジュールを抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動読み込み / Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
  - run_pre_market_report.py  — Pre-Market Report エントリポイント
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py        — ログ設定ユーティリティ
    - process_priority.py     — プロセス優先度 / CPU affinity
  - execution/                 — 発注エンジン周り（Engine, OrderManager 等）
  - monitoring/                — 監視用 DB 初期化や SystemMonitor 実装
  - operations/                — レポート生成ロジック、pre_market_collector 等
  - portfolio/                 — ポートフォリオ構築／ポジションサイズ計算
  - research/                  — ファクター計算、特徴量探索
  - ai/                        — news_nlp（OpenAI 連携）
  - data/                      — （実行時生成される）data/*.db やフラグファイルを想定
  - artifacts/                 — （実行時の出力）レポート保存先

補足・運用上の注意
------------------
- KABUSYS_ENV は development / paper_trading / live のいずれかに設定してください。live 設定時は特に注意（LINE 通知設定やキルスイッチ設定などのチェックがあります）。
- .env は絶対にリポジトリにコミットしないでください（config_setup.py にもその旨の注意が含まれます）。
- run_execution は本番環境では実際に発注を行います。テストや検証は paper_trading モードを使用してください（完全に別の SQLite DB に記録されます）。
- run_monitoring は監視 DB（SQLITE_PATH）へ書き込みますが、monitoring 自体は常に sqlite_path（本番パス）を使用する設計になっています。運用時は監視用 DB パスの設定を確認してください。
- OpenAI を使う ai/news_nlp.py を実行するには OPENAI_API_KEY が必要です。また API 呼び出し回数に注意し、適切なレート制限とエラーハンドリング（実装済み）を確認してください。

よくあるコマンド一覧（まとめ）
--------------------------------
- .env 作成: python -m kabusys.config_setup
- 設定検証: python -m kabusys.validate_config [--strict]
- 実行エンジン起動: python -m kabusys.run_execution
- 監視起動: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Pre-Market レポート: python -m kabusys.run_pre_market_report [--save] [--json]
- Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

ライセンス・貢献
----------------
この README はコードベースを読み取りまとめたものです。実装の変更や拡張を行う場合は、既存のテストと設定検証（validate_config）を必ず実行してください。

---

不足している情報（開発者向けメモ）:
- requirements.txt / pyproject.toml の依存リストを参照してインストールしてください（本 README では主要依存のみ記載）。
- 実際のブローカー接続やデータ更新ジョブの設定（Task Scheduler、外部 API キーの取得方法等）は別途ドキュメントを参照してください。

必要に応じて README にサンプル .env の雛形やデプロイ手順（Windows Task Scheduler 連携、systemd サービス例など）を追加します。希望があれば追記します。