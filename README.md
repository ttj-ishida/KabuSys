# KabuSys

日本株自動売買システムのパッケージ（ライブラリ + 起動スクリプト群）。

このリポジトリはシステム監視、発注エンジン、ポートフォリオ構築、ファクター計算、AI ベースのニュースセンチメントなどを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するコンポーネント群です。主な目的は以下：

- 発注用 ExecutionEngine（本番 / ペーパートレード切替）
- 実行・監視（System / Trade / Risk）と Kill Switch（安全停止）
- ポートフォリオ構築・ポジションサイズ計算（純粋関数）
- DuckDB を利用したファクター計算・リサーチ機能
- OpenAI を用いたニュース NLP（センチメント評価）とレジーム判定
- 運用を助ける CLI（.env 設定ウィザード、設定検証、検証レポート等）

注意:
- 設定は .env ファイルまたは環境変数から読み込みます（自動ロード機能あり）。
- KABUSYS_ENV によって `development` / `paper_trading` / `live` が選べます。`paper_trading` は発注をモック化して専用 SQLite に記録します。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により本番/ペーパー切替）
  - run_monitoring.py: SystemMonitor のポーリングループを起動（監視ログを SQLite に記録）
- 環境設定・検証
  - config_setup.py: 対話的に .env を作成 / 更新するウィザード
  - validate_config.py: .env と config/*.yaml の基本チェックを行う CLI
- 監視（monitoring）
  - system_monitor, trade_monitor, risk_monitor, monitoring_engine, kill_switch, monitoring_db 等
- ポートフォリオ（portfolio）
  - 候補選定、重み計算、リスク調整、ポジションサイズ計算（pure functions）
- リサーチ（research）
  - ファクター計算（momentum / volatility / value）、特徴量探索、IC 計算
- AI（ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集計・ai_scores 書き込み
  - regime_detector: 市場レジーム判定（MA + マクロセンチメント合成）
- ツール
  - tools.paper_verification_report: Paper Trading の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   - requirements ファイルがある場合:
     ```bash
     pip install -r requirements.txt
     ```
   - 主な必須パッケージ（一部）:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（validate_config の YAML 検証を利用する場合）
   - SQLite は標準ライブラリで使用可能です。

4. .env の初期作成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   このウィザードにより .env を対話式で生成できます。

5. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

---

## 必須 / 主要な環境変数

自動読み込み:
- プロジェクトルートに `.env` / `.env.local` が存在すると自動で読み込まれます（OS 環境変数が優先）。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（例）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`（Monitoring 用）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- PAPER_FILL_MODE: ペーパー約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

サンプル（.env に書く内容の例）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_pass
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動コマンド例）

- 環境設定ウィザード（.env の作成／更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- ExecutionEngine を起動（本番 / ペーパーは KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  ポイント:
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 発注は `paper_trading` 時に MockBroker を使い `data/paper_trading.db` に記録されます。
  - 実行中は `data/execution.pid` が作成されます。停止は stop flag や kill flag の書き込みで行います。

- Monitoring を起動（ポーリング）
  ```bash
  # ポーリング間隔を変更する例（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  ポイント:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず `sqlite_path`（監視 DB）を使用します。
  - 停止はプロジェクトの `data/stop_requested.flag` を作ることで検知して終了します。

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB を使う場合
  python -m kabusys.tools.paper_verification_report

  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB パス指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連
  - ニューススコアリング（プログラム呼び出し）:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - api_key を渡すか環境変数 OPENAI_API_KEY を設定してください。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
      - OpenAI API を使用します。失敗時はフォールバック挙動あり。

---

## 停止 / Kill Switch

- 実行の強制停止（ExecutionEngine 側）
  - `kabusys.monitoring.kill_switch.KillSwitch` により条件（ドローダウン超過やポジション過多）が満たされると `data/kill.flag` を書き込みます。ExecutionEngine はこれを検知して停止する設計です。
- 手動停止フラグ
  - `data/stop_requested.flag` を作成すると `run_execution` / `run_monitoring` が起動中に検知して安全に終了します。

注意: `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険です（起動時に kill flag を自動でクリアしてしまうため）。本番では 0 を推奨します。

---

## ログ

- ログ設定ユーティリティ: kabusys.utils.logging_setup.setup_logging
  - デフォルトで stdout と日毎ローテートのファイルハンドラ（logs/<app_name>.log）を設定します。
  - ログディレクトリは `LOG_DIR` 環境変数または `logs/`（デフォルト）。

---

## ディレクトリ構成（主要ファイル）

以下は package 内の主要ファイル・モジュール構成（src/kabusys）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings クラス）
  - config_setup.py          — .env 作成ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成ツール
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出し・スコア化）
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続化（監視ログ）
    - system_monitor.py
    - trade_monitor.py       — (存在するファイルに基づく)
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py       — (アラート送信ロジック)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上のリストは主要ファイルを抜粋したものです。詳細は src/kabusys 以下を参照してください。）

---

## 開発者向けメモ / 注意点

- DB マイグレーション: monitoring_db.init_monitoring_db は実行時に必要テーブルの作成と簡単なカラム追加（マイグレーション）を行います。
- DuckDB は分析用途、SQLite は監視・取引ログ用途で使い分けています。
- ペーパートレード時は本番 DB と完全分離するよう paper_sqlite_path を使用します。
- OpenAI 呼び出し周りはネットワークエラーやレート制限を考慮してリトライ・フォールバック実装が行われています。API キー漏洩に注意してください（.env は Git にコミットしないでください）。

---

## よくある操作例

- 全コンポーネント起動（開発・ローカルテスト）
  1. .env を作成
     ```bash
     python -m kabusys.config_setup
     ```
  2. 設定検証
     ```bash
     python -m kabusys.validate_config
     ```
  3. 実行エンジン起動（別ターミナル）
     ```bash
     python -m kabusys.run_execution
     ```
  4. 監視プロセス起動（別ターミナル）
     ```bash
     python -m kabusys.run_monitoring
     ```

- 手動停止
  ```bash
  # プロジェクトルートに stop フラグを作成
  touch data/stop_requested.flag
  # Kill Switch をトリガーしたい（危険: 本番では注意）
  echo "reason" > data/kill.flag
  ```

---

README に書かれている動作やファイルの詳細はコードベースのドキュメントやソースコメント（各モジュールの docstring）を参照してください。ご要望があれば、特定モジュールの使い方（例: ExecutionEngine API、AI モジュールの呼び出し方など）を追記します。