# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（プロトタイプ）。  
ポートフォリオ構築、ポジションサイジング、リスク制御、監視、ペーパートレード検証、ニュース NLP（OpenAI）連携などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的としたモジュール群で構成されています。

- 株価データや財務データを使ったファクター計算・特徴量探索（research）
- ポートフォリオ構築・配分・ポジションサイズ計算（portfolio）
- 発注処理・リスク管理を担う Execution エンジン（execution）
- システム・注文・リスク監視と Kill Switch（monitoring）
- ニュースを LLM に投げて銘柄別センチメントを算出する AI モジュール（ai）
- ペーパートレードの検証レポート生成ツール（tools）
- 環境設定ウィザード / 設定検証ツール（config_setup / validate_config）

設計方針として、DB（SQLite / DuckDB）を用いた永続化、外部APIやOpenAIは明示的な設定が必要、監視・停止はファイルフラグで制御することで安全性を高めています。

---

## 主な機能一覧

- 環境設定ウィザード（.env 作成 / 更新）: `kabusys.config_setup`
- 設定検証 CLI（環境変数・config/*.yaml のチェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト（本番 / ペーパートレード切替）: `kabusys.run_execution`
  - KABUSYS_ENV が `paper_trading` の場合は MockBroker を利用し、`data/paper_trading.db` に記録
- Monitoring 起動スクリプト（SystemMonitor のポーリング）: `kabusys.run_monitoring`
  - 環境に関わらず監視は本番 sqlite_path を使用
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視エンジン（システム、トレード、リスク監視）: alerts / kill switch 評価
- Paper Trading 検証レポート生成ツール: `kabusys.tools.paper_verification_report`
- AI: ニュースセンチメントのスコア化（OpenAI）、市場レジーム判定（OpenAI）
- ポートフォリオ関連純粋関数群（候補選定、重み計算、ポジションサイジング、セクター制限）

---

## セットアップ手順（開発 / 実行環境）

注: ここではローカルで動かす場合の一般的な手順を示します。CI/CD や本番デプロイは別途環境に合わせて調整してください。

1. リポジトリをクローンし、ソースルートへ移動
   ```
   git clone <repo_url>
   cd <repo_root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存ライブラリをインストール  
   必須（最低限）:
   - duckdb
   - psutil
   - openai (AI 機能を使う場合)
   - PyYAML（config の YAML 検証を行う場合に任意）

   例:
   ```
   pip install duckdb psutil openai pyyaml
   ```

   （requirements.txt がある場合は `pip install -r requirements.txt` を使用）

4. 環境変数を準備する（.env）
   - 手動で `.env` を作るか、ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - AI 機能を使う場合:
     - OPENAI_API_KEY を環境変数として設定（または score 関数に明示渡し）
   - 代表的な設定（デフォルトはプロジェクトルートの `data/` 以下）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, デフォルト: data/paper_trading.db)
     - KABUSYS_ENV: development | paper_trading | live
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR

5. 設定の検証（起動前推奨）
   ```
   python -m kabusys.validate_config
   # 警告を FAIL としたい場合:
   python -m kabusys.validate_config --strict
   ```

6. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト / コマンド）

- ExecutionEngine を起動する（バックグラウンドで実行する際はプロセスマネージャを併用）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合、MockBroker を利用して `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。
  - エンジンは `data/execution.pid`（デフォルト）に PID を書きます。
  - 停止リクエストは `data/stop_requested.flag` を作成することで検知します（ファイル存在チェック）。

- Monitoring を起動する
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を変更するには環境変数 `MONITOR_POLL_INTERVAL` を秒数で設定:
    ```
    export MONITOR_POLL_INTERVAL=30
    ```
  - 監視は SQLite（`SQLITE_PATH`）へ永続化します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使います。

- 環境設定ウィザード（.env 作成 / 更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite の paper trading DB を分析）
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI（ニュース NLP / レジーム判定）  
  - ニューススコアリング（プログラム上から呼ぶ API）:
    - kabusys.ai.score_news(conn, target_date, api_key=...) など
  - これらを CLI から直接起動する小スクリプトはありませんが、モジュール関数をスクリプト化して実行可能です。
  - OpenAI API キーは必須（引数または環境変数 OPENAI_API_KEY）。

- 停止・Kill Switch
  - Execution の即時停止（Kill Switch 発動）は監視側で `data/kill.flag` を書き込むことで実行されます（KillSwitch による判定で書かれます）。
  - 手動で停止フラグを書く場合:
    ```
    echo "manual stop" > data/stop_requested.flag
    ```
    または
    ```
    echo "reason" > data/kill.flag
    ```

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live (デフォルト: development)
- OPENAI_API_KEY: OpenAI を使用する場合に必須
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- MONITOR_POLL_INTERVAL (監視ポーリング間隔秒、デフォルト: 60)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（monitoring / execution 周り）

PAPER_FILL_MODE（ペーパートレードの約定モード）:
- instant | partial | never | reject（デフォルト: instant）

---

## ロギング

- ログ設定は `kabusys.utils.logging_setup.setup_logging` によって統一的に行われます。  
  - コンソール出力（stdout）と日次ローテーションのファイル出力（logs/<app_name>.log）を持ちます。
  - ログディレクトリは環境変数 `LOG_DIR` またはデフォルト `logs/`。
  - ログレベルは `LOG_LEVEL`（または引数）で指定します。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要なディレクトリ / ファイル構成（抜粋）です:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py (参照ファイル群)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (アラート管理)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py

ドキュメントや設計ノート（例: PortfolioConstruction.md, StrategyModel.md）が同梱されている想定の部分もあります（コード内コメントで参照）。

---

## 運用上の注意

- KABUSYS_ENV を `live` にすると実際の発注が行われる可能性があるため、設定・アクセスキー・通知先（LINE）などを慎重に管理してください。
- `.env` ファイルは機密情報を含むため、絶対にリポジトリへコミットしないでください。`config_setup.py` はその旨を明示しています。
- ExecutionEngine / Monitoring の停止はファイルフラグ（data/stop_requested.flag / data/kill.flag）を用いて行います。自動クリア設定 `KILL_FLAG_CLEAR_ON_START` は本番での誤設定に注意が必要です。
- AI 関連は OpenAI API を利用するため、API 利用量・料金・レート制限に留意してください。失敗時はフェイルセーフ（スコアを 0 にする等）実装がありますが、運用ポリシーを整えてください。

---

## 開発に関する補足

- 多くのモジュールは純粋関数または DB 接続を受け取る構造で、ユニットテストが書きやすくなっています（外部API呼び出し部分は差し替え可能）。
- DuckDB 接続を受け取り SQL でファクター計算する設計により、分析処理は DB 側で高速に計算できます。
- 監視・リスクログは SQLite に永続化され、簡単な集計・レポートや外部連携に利用できます。

---

何か追加で README に書きたい情報（例: デプロイ手順、監視ダッシュボード、CI 設定、サンプル .env の例など）があれば教えてください。必要に応じて追記・整形します。