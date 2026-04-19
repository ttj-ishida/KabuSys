# KabuSys

日本株向け自動売買システムのコアライブラリ群（ポートフォリオ構築・発注実行・監視・リサーチ・AI連携など）。

このリポジトリは、発注エンジン（ExecutionEngine）、監視機構（MonitoringEngine）、リサーチ/ファクタ計算、AI（ニュースセンチメント／レジーム判定）などを含むモジュール化された実装です。各コンポーネントはテストしやすい純粋関数／小さなクラスに分かれており、環境変数ベースの設定管理・対話式 .env ウィザード・起動前検証ツールが用意されています。

---

## 主な特徴（機能一覧）

- 環境設定
  - `.env` 自動ロード（プロジェクトルート検出）
  - 対話式ウィザードで `.env` 作成・更新（kabusys.config_setup）
  - 起動前設定検証 CLI（kabusys.validate_config）

- 実行 / 発注
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Paper Trading と Live を分離（paper_trading 用 DB を使用）
  - BrokerClientFactory によるブローカークライアントの切り替え
  - リスクマネージャ、OrderManager、Reconciler 等の組み立て済み

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログ永続化（SQLite）と DuckDB を利用した分析用データベース
  - Kill Switch（データファイルにフラグを書き込んで Execution を停止）
  - run_monitoring.py によるポーリングループ（MONITOR_POLL_INTERVAL 環境変数で間隔変更）

- ポートフォリオ構築
  - 候補選定、重み計算（等配分・スコア加重）、位置サイズ決定（ロット丸め・集計キャップ）
  - セクター集中制限、レジーム乗数（リスク調整）

- リサーチ
  - DuckDB を使ったファクタ計算（Momentum / Volatility / Value 等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリー

- AI（OpenAI）
  - ニュースを LLM でスコアリングして ai_scores テーブルへ保存（news_nlp）
  - マクロニュースと ETF MA を組み合わせた市場レジーム判定（regime_detector）
  - OpenAI 呼び出しはリトライ／バリデーション実装済み

- ユーティリティ
  - 統一的なログ設定（TimedRotatingFileHandler + stdout）
  - プロセス優先度・CPU affinity 設定ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（コードは新しい型ヒント構文などを使用）
- SQLite（標準ライブラリ）、DuckDB、psutil、openai 等が必要

推奨インストール例:

1. 仮想環境作成・有効化
   ```sh
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージをインストール
   （プロジェクトに requirements.txt がない場合の例）
   ```sh
   pip install duckdb psutil openai
   # 任意: PyYAML（validate_config が YAML 解析を行う場合）
   pip install PyYAML
   ```

3. ディレクトリ作成
   ログ / データ保存先がデフォルト設定のままの場合:
   ```sh
   mkdir -p data logs
   ```

4. 環境変数設定
   - 推奨: 対話式ウィザードで .env を作成
     ```sh
     python -m kabusys.config_setup
     ```
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - （OpenAI を使う場合）OPENAI_API_KEY
   - 主要な環境変数
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH, SQLITE_PATH
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - PAPER_FILL_MODE（instant|partial|never|reject）
     - LOG_LEVEL, LOG_DIR
     - KILL_FLAG_CLEAR_ON_START（起動時の kill.flag 自動クリア）
     - MONITOR_POLL_INTERVAL（監視ループ間隔 秒、デフォルト 60）

5. 設定検証（任意）
   ```sh
   python -m kabusys.validate_config         # ワーニングは表示
   python -m kabusys.validate_config --strict  # ワーニングを FAIL 扱い
   ```

---

## 使い方（主要な起動コマンド）

- 監視ループを起動
  ```sh
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（例: 30）。
  - 監視は常に本番用の sqlite_path を使用（環境にかかわらず monitoring DB は本番パス）。

- 発注エンジン（ExecutionEngine）を起動
  ```sh
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使い `data/paper_trading.db` に記録（本番 DB と完全分離）。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中に stop フラグが作成されるとエンジンを停止します。

- .env の対話式セットアップ
  ```sh
  python -m kabusys.config_setup
  ```

- 設定検証
  ```sh
  python -m kabusys.validate_config
  ```

- Paper Trading の検証レポート生成
  ```sh
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

ログ設定
- setup_logging(app_name="execution" | "monitoring") を呼ぶことで
  - stdout にログを出力
  - logs/<app_name>.log に日次ローテーションで出力（最大30日保持）
  - LOG_DIR 環境変数や引数でログディレクトリを変更可能

停止 / Kill Switch
- 監視側が条件を満たすと KillSwitch が `data/kill.flag` に理由を書き込み、ExecutionEngine がこれを検出して安全に停止します。
- 手動でプロセスを停止したい場合は `data/stop_requested.flag` を作成すると run_monitoring/run_execution のループが検出して終了します。

---

## 主要コンポーネントとファイル（ディレクトリ構成）

リポジトリの主要部分（src/kabusys）を抜粋して説明します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動ロード、Settings クラス（すべての設定プロパティ）
  - config_setup.py
    - .env を対話式に生成・更新するウィザード
  - validate_config.py
    - 起動前の環境・設定ファイル検証ツール
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 用 DB 分離）
  - utils/
    - logging_setup.py : 統一的なログ設定
    - process_priority.py : プロセス優先度 / CPU affinity のユーティリティ
  - monitoring/
    - monitoring_db.py : SQLite ベースの監視ログ永続化（テーブル作成・CRUD）
    - system_monitor.py : システム CPU/メモリ/DISK / データ鮮度 / プロセス生存チェック
    - risk_monitor.py : ドローダウン・ポジション上限監視（ダッシュボード更新・リスクログ）
    - trade_monitor.py, alert_manager.py, kill_switch.py, monitoring_engine.py など（監視周りの結合）
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py など（発注関連）
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py（銘柄選定・配分・サイズ決定）
  - research/
    - factor_research.py, feature_exploration.py（DuckDB を用いたファクタ計算・解析）
  - ai/
    - news_nlp.py : ニュースを LLM でスコアリングして ai_scores に書き込む
    - regime_detector.py : マクロ＋ETF MA を用いた日次レジーム判定
  - tools/
    - paper_verification_report.py : Paper Trading の検証レポートを生成するスクリプト

補助ディレクトリ（プロジェクトルート想定）
- data/ : SQLite DB、pid/flag ファイルなどを格納（デフォルトパス）
  - data/monitoring.db (SQLITE_PATH)
  - data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - data/kabusys.duckdb (DUCKDB_PATH)
  - data/execution.pid（PID）、data/kill.flag、data/stop_requested.flag
- logs/ : ログ出力先（LOG_DIR）

---

## 環境変数（主なもの）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行/データ
  - KABUSYS_ENV (development | paper_trading | live)
  - DUCKDB_PATH (default: data/kabusys.duckdb)
  - SQLITE_PATH (default: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
  - PAPER_FILL_MODE (instant | partial | never | reject)

- ログ / 動作制御
  - LOG_LEVEL (DEBUG|INFO|...)
  - LOG_DIR
  - MONITOR_POLL_INTERVAL (監視ループの秒間隔、デフォルト 60)
  - KILL_FLAG_PATH (default: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1。本番で自動クリアする設定は危険)

- OpenAI（AI 機能を使う場合）
  - OPENAI_API_KEY

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。デフォルトは 0 を推奨します。
- run_monitoring は環境に関わらず本番 sqlite_path を参照して監視データを記録します。paper_trading と監視 DB が分離されていない点に注意してください（設計上の仕様）。
- OpenAI を利用する機能は API 呼び出しのコストとレイテンシ・失敗リスクがあるため、API キー管理とリトライ挙動を理解した上で使用してください。API 失敗時はフェイルセーフ（スコア 0 など）で継続する実装になっていますが、ログで確認することを推奨します。
- DuckDB / SQLite のファイルパスやログディレクトリは起動前に親ディレクトリが存在するか確認してください。validate_config はこれらのチェックを支援します。

---

もし README に追加したい事項（例: CI・テスト実行方法、より詳しい設定例、CI 用の環境変数テンプレートなど）があれば教えてください。必要に応じてサンプル .env.example の作成や運用手順ドキュメントを追記します。