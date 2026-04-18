# KabuSys

日本株自動売買システムのコードベース（README）。このドキュメントはプロジェクトの概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

目次
- プロジェクト概要
- 機能一覧
- 前提・依存関係
- セットアップ手順
- 環境設定（.env）と検証
- 起動・停止方法（主要スクリプト）
- 使い方（よく使うコマンド例）
- 主要設定・環境変数
- ディレクトリ構成（ファイル一覧と説明）
- 運用上の注意点

---

## プロジェクト概要

KabuSys は日本株の自動売買（Execution）と監視（Monitoring）およびリサーチ（Research）機能を備えたシステムです。  
設計方針として、発注ロジック／リスク制御／ポートフォリオ構築／監視は分離されており、ペーパートレード（モックブローカー）と本番を環境変数で切り替え可能です。DuckDB/SQLite をデータ格納に利用し、OpenAI を用いたニュース NLP やレジーム検出の仕組みも含みます。

---

## 機能一覧

- Execution（発注エンジン）
  - 本番／ペーパートレード切替（環境変数 KABUSYS_ENV）
  - OrderManager / RiskManager / Reconciler を用いた発注管理・リスク管理
  - 発注ログの永続化（SQLite）
- Monitoring（監視）
  - システムリソース（CPU/メモリ/ディスク）と Execution プロセス監視
  - データ鮮度チェック（株価データの最終日）
  - トレードログ監視（滞留注文や約定異常の検出）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch による安全停止（data/kill.flag）
- Research（研究用モジュール）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計要約
  - DuckDB を用いた高速集計
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア重み、ポジションサイズ計算
  - セクターキャップ、レジーム乗数
- AI（ニュース NLP / レジーム検出）
  - OpenAI（gpt-4o-mini など）でニュースをセンチメント化し ai_scores に保存
  - レジーム（bull/neutral/bear）判定
- ユーティリティ
  - ロギング設定（stdout + 日次ローテーションファイル）
  - プロセス優先度・CPU affinity 設定
  - .env 対話式設定ウィザード・設定検証 CLI
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

---

## 前提・依存関係

最低限の推奨環境:
- Python 3.9+
- pip
- DuckDB（Pythonパッケージ: duckdb）
- psutil
- openai（AI機能を使う場合）
- PyYAML（config YAML ファイル検証を行う場合、必須ではないが推奨）

推奨インストール例（仮の requirements）:
pip install duckdb psutil openai PyYAML

※ 実際の requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install duckdb psutil openai PyYAML
   ```
   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. 環境変数設定
   - 対話式ウィザードで .env を作成:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って必要な値（J-Quants トークン、Kabu API パスワード等）を入力します。

   - 既存の .env を手動編集する場合は `.env.example` を参考にしてください（リポジトリに例がある場合）。

5. 設定の検証（起動前チェック）
   ```
   python -m kabusys.validate_config
   ```
   警告も失敗にしたい場合:
   ```
   python -m kabusys.validate_config --strict
   ```

6. 必要に応じてデータディレクトリを作成（ログ、DB 保存先）
   ```
   mkdir -p data logs
   ```

---

## 環境設定（.env）と自動ロード

- 自動ロード順序:
  1. OS 環境変数（優先）
  2. .env.local（存在すれば上書き）
  3. .env（デフォルト読み込み）
- 自動ロードを無効化する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 主要な環境変数（一部）
  - 必須:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
  - 推奨/任意:
    - KABUSYS_ENV (development | paper_trading | live)
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
    - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
    - PAPER_TRADING_SQLITE_PATH (paper_trading 専用 DB)
    - LOG_LEVEL (DEBUG/INFO/...)
    - OPENAI_API_KEY（AI を使う場合）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用、任意）
  - その他:
    - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
    - PAPER_FILL_MODE（ペーパートレードの約定挙動: instant|partial|never|reject）
    - KILL_FLAG_CLEAR_ON_START（本番での自動クリアは危険。0 推奨）

詳しいキーは src/kabusys/config.py と src/kabusys/validate_config.py を参照してください。

---

## 起動・停止方法（主要スクリプト）

プロジェクトはモジュールとして提供されています。主要な実行エントリ:

- 監視プロセス（Monitoring）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視プロセスは常に production（settings.sqlite_path） の監視 DB を使用します。
  - 停止: プロジェクトルート/data/stop_requested.flag ファイルを作成するとループが終了します。

- 発注エンジン（Execution）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、paper_trading 用の SQLite（data/paper_trading.db デフォルト）に記録します（本番 DB と分離）。
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します。
  - 実行中に停止したい場合は data/stop_requested.flag を作成（監視と同じフラグ）。または kill flag により Execution 停止を判定する仕組み（data/kill.flag）。

- .env ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは `--db` オプションまたは環境変数 `PAPER_TRADING_SQLITE_PATH` で指定可能。

---

## 使い方（よく使うコマンド例）

- 開発環境でまず設定を作成・検証する:
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- 監視を起動（デバッグログで起動したい場合）:
  ```
  export LOG_LEVEL=DEBUG
  python -m kabusys.run_monitoring
  ```

- Execution をペーパートレードで起動:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- モニタ停止フラグを作る（手動で停止指示）:
  ```
  touch data/stop_requested.flag
  ```

- Kill Switch の確認・クリア（スクリプト内 KillSwitch を参照）:
  - 作成: kill.flag は内部ロジックから書き込まれます。手動で書くと同様に停止の合図になります。
  - クリア: `data/kill.flag` を削除するか、起動オプションで `KILL_FLAG_CLEAR_ON_START=1` にすると起動時に自動クリアされます（本番では非推奨）。

---

## 主要設定の振る舞いと注意点

- KABUSYS_ENV:
  - development: ローカル開発（発注なし）
  - paper_trading: ペーパートレード（MockBroker 使用、専用 DB）
  - live: 本番（実際に発注）
- Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用して監視情報を残します（運用の一貫性確保）。
- PAPER_FILL_MODE: ペーパートレードの約定挙動を制御（"instant" 等）。不正値は ValueError。
- MONITOR_POLL_INTERVAL: 監視ループの秒数。環境変数で上書き可能。1 以上の整数で指定。
- ロギング: kabusys.utils.logging_setup.setup_logging を用いて stdout と日次ローテーションログ（logs/<app>.log）を出力します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- プロセス優先度: 起動スクリプトは最初に set_process_priority("high") を実行しますが、権限やプラットフォームにより警告が出る場合があります。

---

## ディレクトリ構成（主要ファイル・説明）

以下は src/kabusys 以下の主要モジュール一覧と簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス（設定の集中管理）
  - config_setup.py
    - .env 対話式ウィザード（作成・更新）
  - validate_config.py
    - 起動前の設定検証 CLI
  - run_monitoring.py
    - Monitoring のエントリポイント（ポーリングループ）
  - run_execution.py
    - ExecutionEngine のエントリポイント（発注エンジン）
  - monitoring/
    - monitoring_db.py
      - SQLite の監視テーブル定義・操作クラス（MonitoringDB）
    - system_monitor.py
      - システム監視（CPU/メモリ/ディスク/プロセス/データ鮮度）
    - trade_monitor.py
      - （該当ロジックファイルあり）トレードログ監視（滞留注文や異常検出）
    - risk_monitor.py
      - ドローダウン・ポジション上限監視
    - kill_switch.py
      - Kill Switch（kill.flag の作成／評価）
    - monitoring_engine.py
      - 各 Monitor を束ねるエンジン
    - alert_manager.py
      - （通知管理）LINE など外部通知送信ロジック
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
    - （発注に関する主要ロジック群）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - ポートフォリオ構築に関する純粋関数群
  - research/
    - factor_research.py
    - feature_exploration.py
    - 研究用のファクター算出・IC 計算など
  - data/
    - pipeline.py
    - stats.py
    - （データパイプライン／統計ユーティリティ）
  - ai/
    - news_nlp.py
      - ニュースを OpenAI でスコア化するロジック（ai_scores への書き込み）
    - regime_detector.py
      - ETF MA とマクロニュースを用いたレジーム判定
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証レポート生成ツール
  - utils/
    - logging_setup.py
      - ログ設定ユーティリティ
    - process_priority.py
      - プロセス優先度 / CPU affinity 設定
    - その他ユーティリティ

（実際のプロジェクトルートには `data/`, `logs/`, `config/` 等が存在することを想定）

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）は危険です。0 を推奨します。
- OpenAI API を利用する機能は API キー（OPENAI_API_KEY）が必要です。キーの漏洩防止に留意してください。
- Paper Trading は実運用データベースと分離されていますが、起動前に .env の設定を必ず validate してください。
- ログ・DB ファイルは定期的にバックアップ／ローテーション管理を行ってください（ログはデフォルト 30日保持）。
- run_monitoring/run_execution は stop flag（data/stop_requested.flag）により安全に終了できます。スクリプトがハングした場合などには PID ファイルを確認してください（data/execution.pid など）。

---

この README はコードベースの主要点をまとめたものです。各モジュールの詳細実装や追加の設定（LINE 通知、ブローカークライアントの設定等）は該当ファイルの docstring と実装コメントを参照してください。必要があれば、この README をベースにさらに「運用マニュアル」「障害対応手順」「デプロイ手順」などを追加できます。