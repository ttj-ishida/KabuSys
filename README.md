# KabuSys

バージョン: 0.1.0

KabuSys は日本株の自動売買システム（研究・ポートフォリオ構築・発注・監視・AI支援）を目的とした Python コードベースです。本リポジトリはローカル環境やペーパートレード環境での検証を想定しつつ、本番（live）運用にも対応する設計になっています。

以下はこのコードベースの README.md（日本語）です。

---

## 概要

- 日本株アルゴリズムトレーディングのためのモジュール群を提供します。
  - データ処理（DuckDB ベース）
  - ファクター計算・特徴量解析（research）
  - ポートフォリオ構築（選定・配分・リスク調整・ポジションサイズ）
  - Execution エンジン（broker クライアントを抽象化、paper/live 切替）
  - 監視（System / Trade / Risk の定期チェック、Kill Switch）
  - AI 支援（ニュースセンチメント、レジーム判定） — OpenAI API を利用
  - 運用支援ツール（.env ウィザード、設定検証、Paper Trading レポート）

- 設計方針のポイント
  - 環境変数による設定（.env/.env.local 自動読み込み）
  - Paper Trading は本番 DB と分離（デフォルト: `data/paper_trading.db`）
  - 監視用 DB（SQLite）は monitoring 用に固定的に使用される（monitoring は KABUSYS_ENV に依らず本番 sqlite_path を使用）
  - ログはコンソールと日次ローテートログファイルに出力（`logs/<app>.log`）

---

## 主な機能一覧

- 環境設定ウィザード
  - `python -m kabusys.config_setup` で .env の作成 / 更新を対話式に支援
- 設定検証 CLI
  - `python -m kabusys.validate_config` で環境変数・設定ファイルの不足・不整合をチェック
- 実行エンジン起動スクリプト
  - `python -m kabusys.run_execution`（環境に応じて MockBroker / 実ブローカーを切替）
- 監視ループ起動スクリプト
  - `python -m kabusys.run_monitoring`（SystemMonitor のポーリング）
- Paper Trading 検証レポート
  - `python -m kabusys.tools.paper_verification_report`（期間指定でペーパートレード DB を解析）
- 研究用モジュール
  - ファクター計算（momentum / value / volatility 等）、IC 計算、特徴量要約
- AI モジュール
  - ニュース NLP による銘柄センチメント（OpenAI）、市場レジーム判定（OpenAI）
- ポートフォリオ構築
  - 候補選定、重み付け、セクター制約、レジーム乗数、ポジションサイズ計算
- ユーティリティ
  - ログ設定、プロセス優先度 / CPU affinity 設定、監視 DB ラッパー等

---

## 要件（推奨）

- Python 3.9+
- 必要ライブラリ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を利用する場合)
  - PyYAML（設定 YAML 検証を行う場合）
- OS: Linux / macOS / Windows（process priority は OS に依存して最適化）

requirements.txt が付属している場合はそれを使用してください。ない場合は最低限以下をインストールします:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install -r requirements.txt   # requirements.txt がある場合
   # または最低限:
   pip install duckdb psutil openai pyyaml
   ```

4. 環境変数（.env）の作成
   - 対話式ウィザードを推奨:
     ```
     python -m kabusys.config_setup
     ```
   - ウィザードは .env（デフォルト）を生成します。生成後は `python -m kabusys.validate_config` でチェックしてください。

5. データディレクトリ作成（必要に応じて）
   - デフォルトの DB / PID / フラグファイル は `data/` 配下に保存されます。多くのスクリプトが起動時に自動作成しますが、権限に注意してください。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: `development` | `paper_trading` | `live`（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite（デフォルト: `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（例: INFO, DEBUG）
- LOG_DIR: ログ保存ディレクトリ（デフォルト: `logs/`）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、既定 60） — run_monitoring で使用
- PAPER_FILL_MODE: paper_trading の MockBroker の fill モード（`instant|partial|never|reject`）
- KILL_FLAG_CLEAR_ON_START: `1` にすると起動時に kill.flag を自動クリア（本番は `0` 推奨）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルトは `data/` 配下（設定上書き可）

注意: `.env` は機密情報を含むため絶対に Git にコミットしないでください。

---

## 使い方

### 1) 設定と検証

- 対話式 .env 作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  # 警告も失敗扱いにする場合:
  python -m kabusys.validate_config --strict
  ```

### 2) 監視ループの起動

- 監視モジュール（SystemMonitor のポーリング）を起動:
  ```
  python -m kabusys.run_monitoring
  ```

- ポーリング間隔を環境変数で上書き:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- 監視は monitoring DB（SQLite）へ状態やリスクイベントを記録します。監視は KABUSYS_ENV に関係なく production の sqlite_path を使用します。

- 監視を止める
  - プロセスを KeyboardInterrupt（Ctrl+C）で止めるか、プロジェクトルートの `data/stop_requested.flag` を作成するとループが検知して安全に終了します。

### 3) 実行エンジン起動

- 実行エンジンを起動:
  ```
  python -m kabusys.run_execution
  ```

- KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH、デフォルト `data/paper_trading.db`）に記録します。production（live）では本番設定に従います。

- ExecutionEngine は `data/execution.pid`（デフォルト）を利用し、停止フラグ `data/stop_requested.flag` を検出すると安全停止します。

### 4) Paper Trading 検証レポート

- レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- DB パスを指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

レポートは稼働率、注文成功率、送信率、レイテンシなどを表示し PASS/FAIL を判定します。

### 5) AI 機能（ニュース NLP・レジーム判定）

- OpenAI API キーが必要（環境変数 `OPENAI_API_KEY` または関数引数で指定）。
- ニュース NLP（銘柄センチメント）:
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意: API 呼び出しはレート制限や一時的失敗に対してリトライ戦略を実装していますが、API キーやクォータに注意してください。

---

## 運用上のフラグ / ファイル

- data/stop_requested.flag
  - run_monitoring / run_execution のループ停止用フラグ（存在を検知して安全に終了）
- data/kill.flag
  - KillSwitch が書き込むフラグ。ExecutionEngine に対する停止（Kill Switch）を表す
- data/execution.pid
  - ExecutionEngine の PID 保持
- logs/<app>.log
  - 日次ローテーションでログを保存（例: logs/execution.log, logs/monitoring.log）

---

## 主要なディレクトリ構成

（この README に含まれるファイル群を元に抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env のロード・Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - utils/
    - logging_setup.py        — ロギングの統一設定
    - process_priority.py     — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py        — SQLite 監視テーブル初期化／永続化クラス
    - system_monitor.py       — システム状態・データ鮮度のチェック
    - trade_monitor.py        — （取引監視）※この README の抜粋コード以外に実装あり
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — KillSwitch 実装
    - monitoring_engine.py    — 各モニタを束ねるエンジン
    - alert_manager.py        — アラート送信ロジック（LINE など、実装に依存）
  - execution/
    - execution_engine.py     — ExecutionEngine（セッション管理、発注処理など）
    - order_manager.py
    - order_repository.py
    - broker_factory.py       — ブローカー（実・Mock）を提供
    - reconciler.py
    - risk_manager.py
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
  - tools/
    - paper_verification_report.py

（上記は主要モジュールの抜粋です。実際のソースツリーを参照してください。）

---

## 開発メモ / 設計上の注意点

- .env の自動読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動読み込みします。ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動ロードを無効化できます（テスト用）。
- DB のマイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル作成および軽微なカラム追加マイグレーションを行います。
- Paper vs Live:
  - 実行時の DB 分離や MockBroker の挙動は `KABUSYS_ENV` により切替えられます。`paper_trading` では paper DB に記録され、本番 DB と完全に分離されます。
- ロギング:
  - ルートロガーを統一設定します。ログファイル保存に失敗した場合はコンソール出力のみで継続します。
- プロセス優先度:
  - run_* スクリプトは起動直後にプロセス優先度を「high」に設定しようとしますが、権限不足や OS により失敗する場合は警告ログを出しスキップします。

---

## よく使うコマンドまとめ

- .env 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- 実行エンジン起動:
  ```
  python -m kabusys.run_execution
  ```

- 監視起動:
  ```
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要に応じて README を拡張して、CI / デプロイ手順、詳細な設定例、API ドキュメント（関数引数や戻り値の例）を追加できます。追加したいトピックがあれば指定してください。