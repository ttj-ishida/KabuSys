# KabuSys

軽量な日本株自動売買（バックテスト / ペーパートレード / 実運用）補助ライブラリ群および起動スクリプト群です。  
このリポジトリは、データ処理（DuckDB）、監視（SQLite）、発注エンジンラッパー、ポートフォリオ構築、ファクター計算、LLM を使ったニュースセンチメントなどの機能を持ちます。

バージョン: 0.1.0（src/kabusys/__init__.py）

---

目次
- プロジェクト概要
- 機能一覧
- 必要な依存パッケージ
- セットアップ手順
- 使い方（主要スクリプト）
- 環境変数（主要）
- ディレクトリ構成（抜粋）
- 運用メモ / 注意点

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。主に次を提供します。

- データ処理・リサーチ（DuckDB を用いたファクター計算・特徴量探索）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング、セクター制約）
- 発注エンジン起動スクリプト（本番 / ペーパートレード切替）
- 監視機能（システム稼働・注文ログ・リスク監視、Kill Switch）
- AI モジュール（OpenAI を用いたニュースセンチメント、レジーム判定）
- 運用ツール（.env ウィザード、設定検証、ペーパートレード検証レポート）

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス防止（日時の参照に注意）」などが組み込まれています。

---

## 機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor ポーリングループ起動（監視ログを SQLite に永続化）
- 設定関連
  - config_setup.py: .env 対話式ウィザード（.env の初期作成・更新）
  - validate_config.py: 環境変数 / config/*.yaml のプリ起動検証
- 監視
  - monitoring_engine.py: 各 Monitor の束ね
  - system_monitor.py / trade_monitor.py / risk_monitor.py: 各種監視ロジック
  - monitoring_db.py: SQLite テーブル作成・読み書きユーティリティ
  - kill_switch.py: data/kill.flag による ExecutionEngine 停止機能
- ポートフォリオ構築
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- 研究・リサーチ
  - research.factor_research: momentum / volatility / value 等ファクター算出
  - research.feature_exploration: forward returns / IC / summary
- AI（OpenAI）
  - ai.news_nlp: ニュース -> センチメント（ai_scores への書き込み）
  - ai.regime_detector: マクロ + ETF MA200 で市場レジーム判定
- ツール
  - tools.paper_verification_report: ペーパートレード DB の検証レポート出力

---

## 必要な依存パッケージ（代表例）

本リポジトリの主要機能を使うために少なくとも以下が必要です。プロジェクト毎に requirements.txt を用意していない場合は手動でインストールしてください。

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config の YAML 検証を行う場合に任意）

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをチェックアウト / コピーして作業ディレクトリに移動します（プロジェクトルートには pyproject.toml または .git があると自動で検出されます）。

2. 依存パッケージをインストールします（上記参照）。

3. .env の作成（推奨）
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
     プロンプトに従って必要な環境変数を入力してください。
   - 手動で作る場合は .env.example を参考にしてください（リポジトリに example がない場合は README の「環境変数」節を参照）。

4. 設定の検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   # 警告も厳密に扱いたい場合:
   python -m kabusys.validate_config --strict
   ```

5. （AI 機能を使用する場合）OpenAI API キーを環境変数に設定:
   ```
   export OPENAI_API_KEY="sk-..."
   ```

6. DB やログディレクトリはデフォルトで自動生成を試みます。必要なら .env でパスを変更してください。

---

## 使い方（主要スクリプト）

起動はモジュール実行で行います（プロジェクトルートで実行することを想定）。

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、データは data/paper_trading.db に記録されます（本番 DB と分離）。

- Monitoring を起動（監視ループ）
  ```
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き（秒、デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 設定ウィザード（.env 生成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成
  ```
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # 別 DB を指定する場合
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

運用中の停止制御:
- run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag により外部から終了指示を受け取ります（存在を検知するとループを抜けます）。
- KillSwitch（risk 監視により）を発動させると data/kill.flag が書き込まれ、これは ExecutionEngine の停止トリガーとして扱われます。起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると自動でクリアされますが、本番では 0 を推奨します。

ログ:
- デフォルトログディレクトリは `logs/`。環境変数 LOG_DIR で変更可。
- ログ設定は kabusys.utils.logging_setup.setup_logging が統一的に行います。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要な任意/設定:
- KABUSYS_ENV: 実行環境（development, paper_trading, live）デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログの閾値（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1、本番は 0 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: カスタムパスを指定可能

自動 .env ロード:
- プロジェクトルートに `.env` / `.env.local` がある場合、起動時に自動読み込みします（OS 環境変数を上書きしないルールあり）。
- 自動ロードを無効化したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

簡単な .env 例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）
  - regime_detector.py     — レジーム判定（LLM + MA200）
- monitoring/
  - monitoring_db.py       — SQLite スキーマ・永続化
  - monitoring_engine.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py (参照用)
- execution/               — 発注エンジン周り（broker_factory 等）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- utils/
  - logging_setup.py       — ログ設定ユーティリティ
  - process_priority.py    — プロセス優先度設定
- tools/
  - paper_verification_report.py

data/ （実データ・フラグ類、通常 .gitignore に含める）
- monitoring.db (デフォルト)
- paper_trading.db (paper_trading 用)
- kill.flag, stop_requested.flag
- execution.pid

logs/
- execution.log
- monitoring.log
- など（TimedRotatingFileHandler により日次ローテーション）

---

## 運用メモ / 注意点

- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を調整できます（デフォルト 60 秒）。0 以下や不正値は無視されデフォルトにフォールバックします。
- Monitoring は Settings に関わらず監視用の本番 sqlite_path を使用します（監視ログは本番監視 DB に記録される設計）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB に記録します。本番 DB と完全に分離されます。
- OpenAI を利用した処理は API キーが必須。API の失敗時はフェイルセーフ（多くのケースで 0.0 にフォールバックして継続）実装がされていますが、キー未設定だと例外を投げる関数もあります（明示的にチェックしているため）。
- ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになります（警告が出ます）。
- kill.flag / stop_requested.flag などのフラグファイルは運用者が管理する必要があります。自動クリア設定は危険なので本番では無効（0）を推奨します。
- DB マイグレーション（monitoring_db.init_monitoring_db）は既存 DB に対してカラム追加等を行えるような簡易処理を含みますが、本格的なマイグレーションは別途管理を推奨します。

---

もし README をさらに詳しく（起動時のログの読み方、ExecutionEngine の内部 API、Broker の実装・差し替え方法、ユニットテスト実行方法など）に拡張したい場合は、どの項目を優先して追加するか教えてください。