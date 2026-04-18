# KabuSys

日本株自動売買システムのサブモジュール群（リサーチ、ポートフォリオ構築、実行エンジン、監視、AI / NLP ユーティリティなど）をまとめたコードベースです。本 README はリポジトリをローカルで起動・検証するための手順と各コンポーネントの概要を日本語でまとめたものです。

> 注: 本リポジトリは複数の実行スクリプト（監視ループ、ExecutionEngine、設定ウィザード、設定検証、レポート生成など）を含みます。実行前に環境変数（.env）を適切に設定してください。

## 目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（代表的なコマンド）
- 環境変数（主要なもの）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項 / 運用メモ

---

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ基盤を支えるモジュール群です。本コードベースは以下の責務を持つモジュールで構成されています（抜粋）:

- データアクセス / 解析（DuckDB を使ったファクター計算・将来リターン計算）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制約）
- 実行（ExecutionEngine: ブローカークライアント経由で発注。`paper_trading` 環境はモック）
- 監視（System/Trade/Risk モニタ、Kill Switch、ログ永続化）
- AI（ニュースの NLP スコアリング、レジーム判定） — OpenAI API と連携
- 運用ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

---

## 機能一覧
主要な提供機能:

- SystemMonitor / TradeMonitor / RiskMonitor による定期監視とログ記録（SQLite）
- MonitoringEngine によるアラート判定・Kill Switch 発動機能
- ExecutionEngine（実行環境）:
  - KABUSYS_ENV=paper_trading でモックブローカーを使い本番 DB とは分離
  - リスク管理・オーダー管理・リコンシリエーション機能
- Portfolio モジュール:
  - 候補選定（スコア順等）
  - 重み付け（等配分 / スコア加重）
  - ポジションサイズ計算（リスクベース、単元丸め、aggregate cap）
  - セクター集中制限、レジーム乗数
- Research モジュール:
  - モメンタム・ボラティリティ・バリュー算出（DuckDB クエリ）
  - 将来リターン・IC（Information Coefficient）計算、統計サマリ
- AI モジュール:
  - ニュース NLP による銘柄センチメントスコアの算出（OpenAI 使用）
  - マクロニュースと ETF MA200 を合成した市場レジーム判定
- 運用ツール:
  - 対話式 .env 作成ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - Paper Trading 検証レポート生成ツール

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動

   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール

   ここでは主要な依存を例示します（プロジェクトに requirements.txt があればそれを使用してください）:

   ```
   pip install duckdb psutil openai
   # 以下は optional:
   pip install pyyaml
   ```

   - duckdb: リサーチ / AI 向けの分析 DB
   - psutil: システム情報取得（CPU、メモリ、プロセス優先度など）
   - openai: ニュース NLP / レジーム判定（API 利用時）
   - pyyaml: config/*.yaml の検証に使用（任意）

4. ディレクトリ作成（data / logs 等）

   ```
   mkdir -p data logs
   ```

   - SQLite / DuckDB のデフォルトファイルは `data/` 配下になります。
   - ログは `logs/` 配下に出力されます（logging_setup が日次ローテーションする）。

5. .env を作成

   - 対話式ウィザードを使う：

     ```
     python -m kabusys.config_setup
     ```

   - または `.env` を手動作成（例）:

     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_kabu_password_here
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     LOG_LEVEL=INFO
     ```

6. 設定検証（推奨）

   ```
   python -m kabusys.validate_config
   ```

   --strict を付けると警告も FAIL 扱いになります。

---

## 使い方（代表的なコマンド）

- 監視ループを起動（SystemMonitor をポーリングして DB に記録）:

  ```
  python -m kabusys.run_monitoring
  ```

  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト: 60）。
  - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に依存しない）。
  - 停止はプロジェクトルート `data/stop_requested.flag` ファイルを作成すると検出して終了します。

- 実行エンジン（ExecutionEngine）を起動:

  ```
  python -m kabusys.run_execution
  ```

  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使用され `data/paper_trading.db` に記録され、本番 DB と分離されます。
  - 実行中に停止させたい場合はプロジェクトの `data/stop_requested.flag` を作成してください（スクリプトが検知してエンジンを停止します）。
  - 実行時の PID ファイルは `data/execution.pid`（設定で変更可）に書かれます。

- .env ウィザード（対話式）:

  ```
  python -m kabusys.config_setup
  ```

- 設定検証 CLI:

  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading の検証レポート生成:

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  - デフォルトの DB パスは `data/paper_trading.db`。`--db` または環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

- AI 機能（プログラムから呼び出す）:

  - ニュース NLP スコアリング:

    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - OpenAI API キーは `OPENAI_API_KEY` 環境変数、または引数で渡します。

  - レジーム判定:

    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## 環境変数（主要なもの）
（.env で設定。ここでは重要度の高い項目を抜粋）

- セキュリティ / API
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY（AI 機能使用時に必要）
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用、任意）

- 実行 / DB / ログ
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - `paper_trading` は実際の発注を行わず専用 DB を使います
  - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存ディレクトリ（デフォルト: logs）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: Kill Switch 用フラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト: 0）

- 監視 / 実行
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒数（デフォルト: 60）
  - PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject、デフォルト: instant）
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視しきい値）

※ `kabusys.config.Settings` クラスで必須チェックやデフォルト値の解決を行っています。`.env.example` を参照して .env を作成してください。

---

## ディレクトリ構成（主要ファイルの説明）
（`src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス（値の検証とデフォルト解決）
  - config_setup.py
    - .env を対話式で作成するウィザード
  - validate_config.py
    - .env と config/*.yaml の事前検証ツール
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプト（paper_trading 時はモックブローカー）
  - ai/
    - news_nlp.py: ニュースを OpenAI でセンチメントスコア化して ai_scores に書き込む
    - regime_detector.py: マクロニュース + ETF MA200 でレジーム判定
  - monitoring/
    - monitoring_db.py: SQLite による監視ログ永続化（テーブル作成 / マイグレーション含む）
    - system_monitor.py: システムリソース / データ鮮度監視
    - risk_monitor.py: ドローダウン・ポジション上限監視
    - trade_monitor.py: （取引状況監視）※本リストの他ファイル参照
    - kill_switch.py: Kill Switch の管理（flag ファイル）
    - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
    - alert_manager.py:（通知管理）※実装に依存
  - portfolio/
    - portfolio_builder.py: 候補選定 / 重み付け
    - position_sizing.py: 株数計算・スケーリング
    - risk_adjustment.py: セクターキャップ、レジーム乗数
  - research/
    - factor_research.py: モメンタム / ボラ / バリュー等の計算（DuckDB）
    - feature_exploration.py: 将来リターン・IC 計算等
  - utils/
    - logging_setup.py: ログ設定ユーティリティ（コンソール + 日次ローテートファイル）
    - process_priority.py: プロセス優先度 / CPU affinity 設定ユーティリティ
  - tools/
    - paper_verification_report.py: Paper Trading 検証レポート生成スクリプト

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください）

---

## 注意事項 / 運用メモ

- 本番（KABUSYS_ENV=live）で運用する場合、必須環境変数の設定や LINE 通知設定などを事前に十分確認してください。validate_config の警告・エラーを必ず解消することを推奨します。
- AI 機能（news_nlp / regime_detector）は OpenAI API を使用します。API 呼び出しによる課金・レート制限等に注意してください。OpenAI 呼び出しはリトライ・フェイルセーフロジックを備えていますが、API キーは安全に管理してください。
- データベース（SQLite / DuckDB）ファイルはデフォルトで `data/` 配下に作成されます。バックアップやファイルローテーション運用を検討してください。
- 監視ループやエンジンの停止は `data/stop_requested.flag` や `data/kill.flag` 等のフラグファイルに依存する箇所があります。運用時にはフラグファイルの取り扱いに注意してください（`KILL_FLAG_CLEAR_ON_START=1` は本番では危険な場合があります）。
- ログは `logs/<app_name>.log` に日次ローテーションで保存されます。ディスク容量に注意してください。

---

必要に応じて README に追記したい点（例: 実行例のログ抜粋、ユニットテストの実行方法、CI 設定、より詳細な環境変数表など）があれば教えてください。README を用途に合わせて拡張します。