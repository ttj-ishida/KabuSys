# KabuSys

日本株自動売買システムの一部コードベース（ライブラリ + 起動スクリプト群）です。本 README はこのリポジトリ内の主要な機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買／研究プラットフォームです。本リポジトリには次のような機能群が含まれます。

- 実行エンジン（ExecutionEngine）起動スクリプト
- システム監視（Monitoring）ポーリングループ
- ポートフォリオ構築・ポジションサイジングなどの純粋関数群
- リサーチ／ファクター計算（DuckDB を利用したファクター計算）
- AI を用いたニュースセンチメント評価（OpenAI）
- 監視データの永続化（SQLite）と監視ロジック
- 環境設定ウィザード・設定検証ツール
- Paper Trading 検証レポート生成ツール

設計上の注意点：
- 環境依存設定は .env ファイル（または環境変数）で管理。自動ロード機能あり（必要なら無効化可）。
- Paper Trading（`KABUSYS_ENV=paper_trading`）は本番 DB とは分離して専用の SQLite を使用します（データ分離）。
- OpenAI を使う機能は API キーが必須です（環境変数 `OPENAI_API_KEY` または引数で指定）。

---

## 機能一覧（主要）

- 起動スクリプト
  - run_execution.py — ExecutionEngine を起動する（本番／Paper 切替対応、pid/stop フラグ管理）
  - run_monitoring.py — SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔指定可）
- 設定管理
  - config.py — Settings クラス：環境変数および .env の読み込み・検証用ユーティリティ
  - config_setup.py — 対話式ウィザードで .env を作成／更新
  - validate_config.py — 起動前の設定検証 CLI（--strict オプションあり）
- 監視（monitoring）
  - monitoring_db.py — SQLite へのテーブル作成/CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度・プロセス生存チェック等
  - risk_monitor.py — ドローダウン／ポジション上限監視と Dashboard 更新
  - kill_switch.py — 条件に応じて data/kill.flag を書くことで ExecutionEngine 停止を指示
  - monitoring_engine.py — 各種モニタを束ねたポーリング実行ロジック
- Execution / Order
  - 実行に関するファクトリ・リポジトリ・リスク管理等（execution パッケージ）
- ポートフォリオ構築（portfolio）
  - portfolio_builder, position_sizing, risk_adjustment：候補選定、重み付け、株数決定、セクター制限等
- リサーチ（research）
  - factor_research.py：モメンタム／ボラティリティ／バリュー計算（DuckDB）
  - feature_exploration.py：将来リターン計算・IC 計算など
- AI（ai）
  - news_nlp.py：OpenAI を使ったニュースセンチメント → ai_scores への書き込み
  - regime_detector.py：マクロセンチメント + ETF MA 乖離から日次レジーム判定
- ユーティリティ
  - utils/logging_setup.py：統一ログ設定（stdout + 日次ローテートファイル）
  - utils/process_priority.py：プロセス優先度 / CPU affinity 設定（psutil ベース）
- ツール
  - tools/paper_verification_report.py：Paper Trading データから検証レポート生成 CLI

---

## 必須・推奨依存パッケージ

- Python 3.10+
- 必須ライブラリ（最低限）:
  - duckdb
  - psutil
  - openai
- 任意（機能により必要）:
  - PyYAML（config/*.yaml のパース検証用）
- 標準ライブラリ:
  - sqlite3（組み込み）

インストール例（仮想環境推奨）:
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai PyYAML
```

（requirements.txt がある場合はそれを使用してください。）

---

## 環境変数（代表的なもの）

必須（起動検証でチェックされる）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要な設定（デフォルト値・用途）:
- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス。デフォルト: data/kabusys.duckdb
- SQLITE_PATH: 監視用 SQLite（monitoring.db）パス。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite。デフォルト: data/paper_trading.db
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）デフォルト: INFO
- LOG_DIR: ログの出力ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（ai 機能で必須）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject）

自動 .env ロード:
- リポジトリルートの `.env` と `.env.local` を自動でロードします（OS 環境変数が優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（手順の一例）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化する。
2. 依存パッケージをインストール（上記参照）。
3. 環境変数を .env で用意する（対話式ウィザード推奨）:
   ```
   python -m kabusys.config_setup
   ```
   ウィザード後に `.env` が作成されます。
4. 作成した .env を検証:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict   # 警告も失敗扱いにする
   ```
5. データディレクトリを用意（必要に応じて）:
   - data/（SQLite、pid、flag を置く）
   - logs/（ログ）
   多くのコードは起動時にディレクトリを作成しますが、パーミッションに注意してください。
6. （Paper Trading の検証）Paper DB がない場合は初期化等を行ってください。Paper 用 DB は `PAPER_TRADING_SQLITE_PATH` で指定できます。

---

## 起動・使い方（主なコマンド）

- ExecutionEngine 起動（通常）
  ```
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し paper DB（デフォルト: data/paper_trading.db）に記録します。
  - 実行中は `data/execution.pid` が使用され、停止は `data/stop_requested.flag` か監視側から書き込まれる `data/kill.flag` で行えます。

- Monitoring 起動（システム監視ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  - 監視は常に本番 sqlite_path（`SQLITE_PATH`）を使います（環境に関係なく）。

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db PATH` で DB を直接指定可能。指定がない場合は `PAPER_TRADING_SQLITE_PATH` 環境変数またはデフォルト `data/paper_trading.db` が使用されます。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup     # .env 作成
  python -m kabusys.validate_config # 設定検証
  ```

- AI 関連（プログラム内 API）
  - ニューススコアリング:
    - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
    - `api_key` または環境変数 `OPENAI_API_KEY` が必要
  - レジーム判定:
    - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

---

## Stop / Kill フラグの仕組み

- 停止要求（run_execution / run_monitoring の外部停止）
  - `data/stop_requested.flag` が存在すると、実行中のスクリプトはループを抜けて終了します（run_execution と run_monitoring の双方で検出）。
- Kill Switch（監視による強制停止）
  - `KillSwitch` は各種監視結果（ドローダウン、ポジション上限等）を評価して `data/kill.flag` を書きます。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START=1` の設定に注意します（本番では 0 推奨）。

---

## ロギング

- 共通ロギング設定は `kabusys.utils.logging_setup.setup_logging` により行われます。
- 出力先:
  - stdout（StreamHandler）
  - 日次ローテートファイル：`<LOG_DIR>/<app_name>.log`（デフォルト `logs/<app_name>.log`、30日保持）
- ログレベルは CLI 引数ではなく環境変数 `LOG_LEVEL` または `setup_logging` の引数で制御します。

---

## 主要ファイル・ディレクトリ構成

（抜粋・主要箇所）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (存在する場合)
  - execution/  (ExecutionEngine, OrderManager, BrokerFactory など)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py

プロジェクトルート（想定）:
- .env, .env.local
- data/ (monitoring.db, paper_trading.db, pid/flag ファイル等)
- logs/
- config/ (yaml ファイル群: system_config.yaml 等)

---

## よくあるトラブルと対処

- OpenAI API キー未設定:
  - AI 機能を呼ぶと ValueError が発生します。`OPENAI_API_KEY` を .env / 環境変数に設定してください。
- psutil の権限不足:
  - プロセス優先度変更や CPU affinity の設定はアクセス権限が必要な場合があります。警告が出る場合は無視しても処理は継続します。
- DuckDB / SQLite ファイルの親ディレクトリがない:
  - validate_config で警告が出ます。`data/` 等を作成するか起動時に自動作成される場合もありますが、パーミッションに注意してください。
- YAML の検証をスキップ:
  - PyYAML が未インストールだと config/*.yaml の検証がスキップされます（警告表示）。必要なら `pip install PyYAML`。

---

## 開発上の注記

- 多くのモジュールは「副作用の少ない純粋関数」を意識して設計されています（特に portfolio / research）。
- 時刻関連処理はルックアヘッド・バイアスを防ぐ実装方針（target_date を明示的に受け取るなど）を採用しています。
- DB マイグレーション（簡易）は monitoring_db.init_monitoring_db 内で実施されます（冪等）。

---

必要に応じてこの README をプロジェクトの実際の運用フロー（systemd サービス化、コンテナ化、CI/CD）に合わせて拡張してください。質問や追加で記載したい項目があれば教えてください。