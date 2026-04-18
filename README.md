# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム KabuSys の一部実装です。バックグラウンドでの監視・実行・リサーチ・AI（ニュース NLP）・ポートフォリオ構築などのコンポーネントを含みます。

---

## プロジェクト概要

KabuSys は次を目的としたモジュール群を提供します。

- ExecutionEngine：発注・注文管理・リスク管理の実行
- Monitoring：システム稼働監視、リスク監視、Kill Switch（停止フラグ）管理、アラート
- Research：DuckDB を用いたファクター計算・特徴量解析
- AI：OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価・市場レジーム判定
- Portfolio：候補選定、重み計算、数量算出（単元株で丸め）
- CLI ツール群：設定ウィザード、設定検証、ペーパートレード検証レポート等

設計方針の例：
- 設定は .env または環境変数で管理（自動ロードあり）
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB と分離（専用 SQLite）
- DuckDB は分析・リサーチ用途に使用
- OpenAI を用いる機能は API キーが必要。失敗時はフェイルセーフで継続する設計

---

## 主な機能一覧

- 環境設定ウィザード（.env 生成）: `kabusys.config_setup`
- 設定検証 CLI（.env と config/*.yaml の静的チェック）: `kabusys.validate_config`
- ExecutionEngine 起動スクリプト: `kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` のとき MockBrokerClient を利用し、`data/paper_trading.db` に記録
  - 停止は `data/stop_requested.flag` / `data/kill.flag` を使用
- Monitoring（System / Trade / Risk）ポーリング: `kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（デフォルト: `data/monitoring.db`）に永続化
- ペーパートレード検証レポート生成ツール: `kabusys.tools.paper_verification_report`
- AI モジュール:
  - ニュース NLP による銘柄別センチメントスコア書き込み（DuckDB 上の `raw_news` → `ai_scores`）
  - 市場レジーム（bull/neutral/bear）判定と `market_regime` テーブルへの書き込み
- Research モジュール:
  - momentum / volatility / value ファクター計算
  - 将来リターン、IC、統計サマリー等
- Portfolio モジュール:
  - 候補選定（スコア順）、等金額／スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、等配分）、単元株丸め、アグリゲートキャップ調整

---

## 前提（依存関係）

主な Python パッケージ（例）:
- Python 3.9+
- duckdb
- psutil
- openai
- （オプション）PyYAML（`validate_config` の YAML 検証用）

インストール例（仮）:
pip install duckdb psutil openai pyyaml

※ 実運用では requirements.txt / pyproject.toml に合わせて環境を構築してください。

---

## 環境変数（主なもの）

デフォルト値や必須のものを抜粋します。フルリストは `kabusys.config.Settings` を参照してください。

必須:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

任意・デフォルト付き:
- KABUSYS_ENV: 実行環境。`development`（デフォルト） | `paper_trading` | `live`
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視 DB（デフォルト `data/monitoring.db`）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL: ログレベル（デフォルト `INFO`）
- LOG_DIR: ログ保存ディレクトリ（デフォルト `logs/`）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
- PAPER_FILL_MODE: paper_trading の埋め方（`instant` / `partial` / `never` / `reject`、デフォルト `instant`）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など

.env の自動ロード:
- プロジェクトルート（.git または pyproject.toml を基点）から `.env` と `.env.local` を自動ロードします（ただし `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして Python 仮想環境を作成・有効化
2. 依存関係をインストール
   - 例: pip install -r requirements.txt もしくは手動で duckdb, psutil, openai, pyyaml をインストール
3. 設定ファイル `.env` を作成
   - 対話式ウィザード:
     python -m kabusys.config_setup
   - もしくは `.env.example` を参考に `.env` を作成
4. 設定検証
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: --strict

5. データディレクトリの準備（自動作成されるが確認を推奨）
   - data/（SQLite / PID / flag 等）
   - logs/（ログ）

---

## 実行方法（例）

- 設定ウィザード（.env 作成）
  python -m kabusys.config_setup

- 設定検証
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict

- ExecutionEngine 起動
  python -m kabusys.run_execution
  - Paper trading 用 DB を使う場合は KABUSYS_ENV=paper_trading を指定してください:
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 停止は `data/stop_requested.flag` を作成するか、`data/kill.flag` を用いる（KillSwitch 経由）

- Monitoring 起動
  python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する場合:
    python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI 関連（プログラム内 API 呼び出し）
  - OpenAI API キー必須（環境変数 OPENAI_API_KEY）
  - ニュース採点（プログラムから呼び出す例）
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=None)

  - レジーム判定
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=None)

---

## ログとファイル

- ログ:
  - デフォルトは `logs/<app_name>.log`（日次ローテート、30 日保持）
  - `LOG_DIR` 環境変数で変更可能
  - ログの設定は `kabusys.utils.logging_setup.setup_logging` で統一

- DB:
  - DuckDB: `DUCKDB_PATH`（デフォルト `data/kabusys.duckdb`） — リサーチ / AI 用
  - SQLite (monitoring): `SQLITE_PATH`（デフォルト `data/monitoring.db`）
  - SQLite (paper trading): `PAPER_TRADING_SQLITE_PATH`（Paper Trading 専用）

- PID / フラグ:
  - 実行 PID: `data/execution.pid`（`Settings.pid_file_path`）
  - 停止フラグ: `data/stop_requested.flag`（run_* スクリプトはこれを監視）
  - Kill Switch: `data/kill.flag`（KillSwitch により書き込まれる）

---

## 使い方の注意点と運用上のポイント

- 本番環境では `KABUSYS_ENV=live` を設定すると強い警告が出ます。LINE 通知等を正しく設定してください。
- Paper Trading は本番 DB と分離されています。Paper モードでは MockBroker を使用し、DB は `data/paper_trading.db` に記録されます。
- OpenAI を利用する機能は API 失敗時にフォールバックし、例外を上位に投げない設計ですが、API キーの漏洩やコスト管理には注意してください。
- `KILL_FLAG_CLEAR_ON_START=1` を本番で使うと危険です（起動時に kill flag が自動クリアされるため）。本番は `0` を推奨します。
- `MONITOR_POLL_INTERVAL` は 1 未満の値は許容されず、無効値はデフォルト 60 秒にフォールバックします。

---

## ディレクトリ構成

以下は主要なソースツリーの概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI を用いたスコア算出）
    - regime_detector.py     — 市場レジーム判定（ma200 + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（system_status, trade_logs, risk_logs, positions, dashboard）
    - system_monitor.py      — システム状態・データ鮮度監視
    - trade_monitor.py       — （存在）トレード監視（滞留注文等）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — kill.flag 管理
    - monitoring_engine.py   — 各 Monitor を束ねるエンジン
    - alert_manager.py       — （存在）アラート送信管理（LINE 等）
  - execution/
    - execution_engine.py    — 実行エンジン本体
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
    - __init__.py

（上記に加え、config/*.yaml, data/, logs/ 等の外部リソースが想定されます）

---

## よくある操作例

- .env を作成して検証する:
  python -m kabusys.config_setup
  python -m kabusys.validate_config --strict

- 監視をバックグラウンドで実行（systemd / supervisor 等のサービス化を推奨）
  MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

- ExecutionEngine を起動（本番/ペーパー切替は KABUSYS_ENV）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Paper Trading の検証:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に / 貢献

- README はコードの抜粋に基づく概要です。詳細な仕様（StrategyModel.md, PortfolioConstruction.md 等）は別ドキュメントを参照してください。
- バグ報告・改善案は Issue を立ててください。Pull Request も歓迎します。

--- 

必要であれば、README にサンプル .env テンプレートや systemd ユニットファイル例、Docker 化手順、開発用テストコマンド等を追加で作成できます。どれを追加しますか？