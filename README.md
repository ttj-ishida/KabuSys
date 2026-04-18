# KabuSys

日本株向け自動売買システムの軽量実装（リサーチ・ポートフォリオ構築・発注・監視・AI 補助機能を含む）。  
このリポジトリはモジュール化されており、ローカル開発・ペーパートレード・本番（live）を切り替えて動作します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の主要コンポーネントで構成されています。

- ExecutionEngine（発注エンジン） — ブローカークライアントを通じて発注を行う。paper_trading モードではモックブローカーを使用して本番 DB とは分離された paper_trading DB に記録。
- Monitoring（監視） — システム稼働状況、注文ログ、リスク監視、Kill Switch（停止フラグ）などをポーリングして監視・永続化。
- Portfolio（ポートフォリオ構築） — 候補選択、重み算出、ポジションサイジング、セクター制限などの純粋関数群。
- Research（ファクター／特徴量） — DuckDB 上の価格・財務データからファクター（モメンタム、ボラティリティ、バリュー等）を計算。
- AI（ニュース NLP / レジーム判定） — OpenAI を使ったニュースセンチメント評価や市場レジーム判定（OpenAI API キーが必要）。
- Tools — ペーパートレード検証レポート生成などのユーティリティスクリプト。
- Utils — ロギング設定、プロセス優先度設定、環境設定読込など共通ユーティリティ。

設計上のポイント：
- DB（監視用 SQLite / 分析用 DuckDB）はデフォルトで `data/` に格納。
- .env 自動読み込みを行う（プロジェクトルートが検出できる場合）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 本番実行時は `KABUSYS_ENV=live` を指定。ペーパートレードは `paper_trading`。

---

## 主な機能一覧

- 発注エンジン（ExecutionEngine）
  - リスク制御（RiskManager）
  - 注文の管理（OrderManager / OrderRepository）
  - 発注・再照合（Reconciler）
  - PID / Stop フラグ管理（data/*.pid, stop_requested.flag）

- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス稼働確認
  - データ鮮度チェック（prices_daily 等）
  - 注文ログ / リスクログの永続化（SQLite）
  - Kill Switch を介した安全停止（data/kill.flag）

- ポートフォリオ構築
  - 候補選出（スコア / ランク）
  - 等金額・スコア重み・リスクベースのポジション決定
  - セクター上限適用、レジーム乗数

- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター算出
  - 将来リターン、IC 計算、統計サマリ

- AI 機能
  - ニュースのセンチメント評価（OpenAI）
  - 市場レジーム判定（ETF MA + マクロニュース）
  - 失敗時のフォールバック・リトライ/バックオフ処理

- ツール
  - ペーパートレード検証レポート生成（期間指定可）
  - 環境設定ウィザード（.env 作成補助）
  - 設定検証 CLI（.env と config/*.yaml の検査）

---

## セットアップ手順（ローカル開発向け）

前提
- Python 3.10+ を推奨（型ヒントに `|` 形式を多用）
- SQLite は標準ライブラリ、別途インストール不要

1. ソースを取得
   - リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - 必要な主要パッケージ例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証 / 任意）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （requirements.txt がある場合は `pip install -r requirements.txt`）

4. 環境変数の設定
   - 対話式ウィザードを使って `.env` を作成:
     - python -m kabusys.config_setup
   - または .env を手動で作成（.env.example を参照して設定）
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_LEVEL, LOG_DIR など
   - .env 自動読み込み:
     - プロジェクトルートに `.env` / `.env.local` があれば自動で読み込まれます（OS 環境より低優先）。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いする厳密チェック: python -m kabusys.validate_config --strict

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動
  - python -m kabusys.run_execution
  - 挙動:
    - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient を使用し `data/paper_trading.db` に記録（本番 DB と分離）
    - 起動時に stop フラグ（data/stop_requested.flag）が立っていると起動を辞めます
    - PID ファイル: data/execution.pid（デフォルト）。設定は Settings.pid_file_path

- Monitoring を起動（ポーリング）
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒にて上書き可能（デフォルト 60）
    - 監視は monitoring DB（Settings.sqlite_path）を使用（環境に依らず本番 sqlite_path を参照）
    - 停止は data/stop_requested.flag を置くことで検知

- 環境設定ウィザード
  - python -m kabusys.config_setup
  - .env の初期作成 / 更新を対話式に行う

- 設定検証
  - python -m kabusys.validate_config
  - `--strict` を付けると警告もエラー（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI 機能（プログラム API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは引数か `OPENAI_API_KEY` 環境変数で指定
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

注意:
- Kill Switch（監視側）: 条件を満たすと `data/kill.flag` を書き込み、ExecutionEngine に停止シグナルを送ります。ExecutionEngine は起動時にこのフラグを検査・起動中にも監視して停止します。
- stop フラグ: `data/stop_requested.flag` を置くと run_monitoring / run_execution のループを終了させる設計です。

---

## 環境変数（主要・デフォルト）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境 / ログ / DB
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ出力ディレクトリ（デフォルト: logs/）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - KILL_FLAG_CLEAR_ON_START: 0|1（本番で 1 は危険）
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）

- OpenAI
  - OPENAI_API_KEY（`kabusys.ai` の機能を使う場合必須）

詳細はコード内 `kabusys.config.Settings` と `validate_config.py` を参照してください。

---

## ログ

- 標準出力に加えてファイル出力を行います（デフォルト `logs/<app_name>.log`、日次ローテート、30日保持）。  
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name="...")` で統一的に行われます。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

subpackages:
- ai/
  - news_nlp.py
  - regime_detector.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py (参照)
- execution/
  - execution_engine.py
  - broker_factory.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py
- utils/
  - logging_setup.py
  - process_priority.py
- tools/
  - paper_verification_report.py

その他:
- data/（デフォルトで DB・フラグ・PID 等を置く想定）
- logs/（ログデフォルト出力先）
- config/*.yaml（各種設定テンプレート。generate スクリプトで生成想定）

（実際のファイル一覧はリポジトリ内の `src/kabusys` を参照してください）

---

## 開発上の注意 / 運用上の注意

- 本番（KABUSYS_ENV=live）では `.env` に秘密情報を含めたまま Git 等へコミットしないこと。
- `KILL_FLAG_CLEAR_ON_START=1` は本番で設定すると Kill Switch を自動でクリアしてしまうため危険です（デフォルト 0 推奨）。
- paper_trading モードは本番 DB と分離して動作する設計ですが、DB パスの確認は必ず行ってください（`PAPER_TRADING_SQLITE_PATH`）。
- OpenAI を利用する機能は API 利用料が発生します。API キーの管理とコストに注意してください。
- psutil でプロセス優先度や CPU affinity を設定しますが、権限や OS により失敗する可能性があります（ロギングで警告されるのみ）。

---

README はここまでです。必要であれば次の追加を作成します：
- systemd / supervisor 用のサービスユニット例
- Dockerfile / docker-compose 例
- 主要ワークフローの図示（起動シーケンス・Kill Switch 動作フロー）