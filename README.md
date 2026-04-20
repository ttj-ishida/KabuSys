# KabuSys

日本株向け自動売買システムのコードベース（README 日本語版）

---

## プロジェクト概要

KabuSys は日本株の自動売買および関連分析を目的としたモジュール群です。  
主な機能は以下に示す実行エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算 / 特徴量解析）、および AI を用いたニューススコアリング等です。  
本リポジトリはコアロジックを純粋関数や DB 層に分離して実装しており、Paper Trading（テスト）と Live（本番）を分離して運用できます。

---

## 機能一覧

- ExecutionEngine 起動・注文管理（本番 / ペーパートレード分離）
- System / Trade / Risk の継続監視（MonitoringEngine）
- Kill Switch（閾値超過時に ExecutionEngine を停止するフラグ）
- 監視ログ永続化（SQLite ベースの monitoring DB）
- ポートフォリオ構築（候補選定・重み計算・リスク調整・株数算出）
- リサーチ（DuckDB を用いたファクター計算、forward returns、IC 等）
- AI モジュール（OpenAI を使ったニュースセンチメント / 市場レジーム判定）
- 設定ウィザード（.env 生成支援）および設定検証 CLI
- ツール: Paper Trading 検証レポート生成スクリプト

---

## 必要条件（主な依存パッケージ）

- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（config/*.yaml の内容検証に使用）

例（pip）:
```
pip install duckdb psutil openai
# 設定検証で YAML を使う場合
pip install pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成・アクティベート（任意）
3. 依存パッケージをインストール（上記参照）
4. 環境変数設定
   - プロジェクトルートに `.env` を作成するか環境変数をエクスポートしてください。
   - 自動ウィザードを使う場合:
     ```
     python -m kabusys.config_setup
     ```
5. 設定検証（推奨）:
   ```
   python -m kabusys.validate_config
   # 警告を厳格扱いにする:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリ作成（実行時に自動作成されますが、あらかじめ準備しておくと良いです）:
   - `data/`（SQLite / DUCKDB / pid / flag 等）
   - `logs/`（ログファイル保存）

---

## 主要な環境変数（代表）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/...）（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE — PaperTrading の Fill 動作（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

注意: `.env` 自動読み込みは以下の優先順位で行われます:
OS 環境 > .env.local（上書き） > .env（未設定時に補完）。
自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

重要: `.env` は絶対に Git にコミットしないでください。

---

## データベース・ファイル（デフォルト）

- DuckDB: data/kabusys.duckdb
- SQLite（監視）: data/monitoring.db
- SQLite（paper trading）: data/paper_trading.db
- ログディレクトリ: logs/
- PID / フラグ: data/execution.pid, data/stop_requested.flag, data/kill.flag

Execution は paper_trading 環境時に専用の paper_sqlite_path を使って本番 DB と分離します。

---

## 実行方法（主な CLI / モジュール）

- 実行エンジン（ExecutionEngine）起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使われ、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動しません。
  - プロセス優先度を High に設定します。

- 監視ループ起動（SystemMonitor を含む）
  ```
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
  ```
  - `MONITOR_POLL_INTERVAL` でポーリング間隔を秒単位で上書き可能（デフォルト 60）。
  - 監視は常に（KABUSYS_ENV に関係なく）本番 sqlite_path を参照します。
  - 停止は `data/stop_requested.flag` を作成することで通知できます。

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config [--strict]
  ```

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  ```
  - DB パスは `--db` > 環境変数 `PAPER_TRADING_SQLITE_PATH` > デフォルト `data/paper_trading.db` の順で解決されます。

- AI モジュール（プログラムとして呼び出す）
  - ニュース NLP スコアリング:
    - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
    - 引数: DuckDB 接続、対象日、API キー（未指定時は OPENAI_API_KEY 環境変数を使用）
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

- リサーチ / ファクター計算（プログラム呼び出し）
  - `kabusys.research.calc_momentum(conn, target_date)`
  - `kabusys.research.calc_volatility(conn, target_date)`
  - `kabusys.research.calc_value(conn, target_date)`
  - など。いずれも DuckDB 接続を受け取ります。

---

## 使い方の例（最小起動フロー）

1. `.env` を作る（または `python -m kabusys.config_setup`）
2. 設定を検証:
   ```
   python -m kabusys.validate_config
   ```
3. 監視を起動（別プロセスで）:
   ```
   python -m kabusys.run_monitoring
   ```
4. 実行エンジンを起動:
   ```
   python -m kabusys.run_execution
   ```
5. 必要に応じて Paper Trading レポートを生成:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-10
   ```

停止シグナル:
- `data/stop_requested.flag` を作成すると run_execution / run_monitoring のループで検出して優雅に終了します。
- 監視側の KillSwitch が閾値超過で `data/kill.flag` を書き込むと Execution 側が起動時に検出・停止できます。

---

## 開発・デバッグのヒント

- `.env` の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行います。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして自動ロードを無効化できます。
- ログは `kabusys.utils.logging_setup.setup_logging` により統一的に stdout + 日次ローテートファイルに出力されます。ログディレクトリは `LOG_DIR` 環境変数で上書き可能です。
- PyYAML がインストールされていない場合、`validate_config` は config/*.yaml の検証をスキップします（警告が表示されます）。
- OpenAI の呼び出しはリトライやバックオフを含む実装になっていますが、実行には `OPENAI_API_KEY` が必要です。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - __version__ = "0.1.0"
    - config.py                — 環境変数 / settings 管理
    - config_setup.py          — .env ウィザード（CLI）
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリング起動スクリプト
    - utils/
      - logging_setup.py       — ロギングの統一設定
      - process_priority.py    — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite 永続化層（テーブル初期化 / CRUD）
      - system_monitor.py      — システム状態・データ鮮度監視
      - trade_monitor.py       — （注文監視）※実装ファイルあり
      - risk_monitor.py        — ドローダウン / 保有数監視
      - kill_switch.py         — kill.flag 書き込み・評価
      - monitoring_engine.py   — 各 Monitor を束ねる
      - alert_manager.py       — 通知管理（LINE 等）※実装ファイルあり
    - execution/
      - execution_engine.py    — ExecutionEngine 本体（セッション管理）
      - order_manager.py
      - order_repository.py
      - broker_factory.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - factor_research.py     — momentum / volatility / value
      - feature_exploration.py — forward returns / IC / summary
    - ai/
      - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
      - regime_detector.py     — 市場レジーム判定（OpenAI + MA）
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート

---

## 注意事項 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では `.env` の管理に特に注意してください（LINE 通知設定・KILL FLAG 設定など）。
- `.env` は機密情報を含むため、必ず Git 管理下にコミットしないでください。
- Paper Trading は本番 DB とは分離されますが、スクリプトや設定ミスで本番に接続しないよう十分に確認してください。
- OpenAI API を利用する機能はコスト・レート制限が発生するため、運用時には API キーの管理と呼び出し頻度に注意してください。

---

必要であれば、README にサンプルの .env テンプレートや、より詳細な実行フロー図（監視→kill switch→execution の相互作用）を追加できます。どの情報を深掘りしますか？