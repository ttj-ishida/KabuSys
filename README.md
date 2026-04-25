# KabuSys — 日本株自動売買システム (README)

このリポジトリは日本株向けの自動売買／リサーチ／モニタリング基盤の一部実装を含みます。  
以下はコードベース（src/kabusys 以下）を利用するための README です。

---

## プロジェクト概要

KabuSys は、シグナル生成・ポートフォリオ構築・注文実行・モニタリング・研究向けユーティリティを含む日本株自動売買システムです。  
主な設計方針は以下の通りです。

- 明確に分離されたモジュール群（execution / monitoring / research / portfolio / ai / utils）
- 本番 DB とペーパートレード DB の分離（KABUSYS_ENV に依存）
- DuckDB を用いたリサーチ・特徴量計算、SQLite を用いたモニタリング／発注ログ
- LLM を利用したニュースセンチメント（OpenAI）連携（オプション）
- 起動スクリプト群を通じた単純な運用フロー（daemon/loop）

---

## 主な機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートを探索）
  - 対話式設定ウィザード（`config_setup.py`）
  - 起動前設定検証 CLI（`validate_config.py`）
- 実行（Execution）
  - ExecutionEngine（発注・risk管理・注文管理）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - ブローカークライアントファクトリ（Mock の使用など）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - kill.flag による外部停止シグナル（KillSwitch）
  - 監視ログ永続化（SQLite テーブル群）
- ポートフォリオ構築
  - 候補選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- リサーチ
  - ファクター算出（モメンタム／ボラティリティ／バリュー）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
- AI（任意）
  - ニュースの NLP センチメントスコア化（OpenAI）
  - 市場レジーム判定（ma200 + マクロニュース）
- ツール
  - Paper Trading 検証レポート生成スクリプト（`tools/paper_verification_report.py`）

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリに移動します。
   - 例: `git clone <repo> && cd <repo>`

2. Python 仮想環境を作成・有効化します（推奨）。
   - 例: `python -m venv .venv && source .venv/bin/activate`（Windows: `.venv\Scripts\activate`）

3. 依存パッケージをインストールします。
   - 依存ファイル（requirements.txt）はプロジェクトに依存します。最低限必要となるパッケージは以下です:
     - duckdb
     - psutil
     - openai（AI 機能を使う場合）
     - PyYAML（`validate_config` の YAML 検証に任意で使用）
   - 例: `pip install duckdb psutil openai PyYAML`

4. 環境変数を用意します（.env を作成）。
   - 対話式ウィザードを使う:
     - `python -m kabusys.config_setup`
   - あるいは `.env.example` があればコピーして編集:
     - `cp .env.example .env`（存在する場合）
   - 必須環境変数:
     - `JQUANTS_REFRESH_TOKEN`
     - `KABU_API_PASSWORD`
   - AI 機能を使う場合:
     - `OPENAI_API_KEY` を設定

5. デフォルトで必要なディレクトリ（`data/`, `logs/`）は起動時に生成されますが、事前に作成しておくこともできます:
   - `mkdir -p data logs`

注意:
- 自動 .env 読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用途）。
- 本番環境では `KABUSYS_ENV=live` を設定します。ペーパートレードは `paper_trading`、開発は `development`。

---

## 使い方（主要 CLI / スクリプト）

以下のスクリプトはモジュールとして実行できます。プロジェクトの仮想環境を有効にして実行してください。

- 環境設定ウィザード（.env を作成）
  - `python -m kabusys.config_setup`

- 設定検証（起動前チェック）
  - `python -m kabusys.validate_config`
  - `--strict` を付けると警告も失敗扱い（exit code 1）

- 監視ループ起動（SystemMonitor ベースのポーリング）
  - `python -m kabusys.run_monitoring`
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に「本番用の sqlite_path」を使用して監視 DB を初期化します

- 実行エンジン起動（ExecutionEngine）
  - `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: `data/paper_trading.db`）に記録します
  - 起動時に `data/execution.pid` を使い PID 管理を行い、停止は `data/stop_requested.flag`（`run_execution` / `run_monitoring` が検知）または `KILL FLAG` による停止フローがあります

- Paper Trading 検証レポート生成
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
  - デフォルト DB: 環境変数 `PAPER_TRADING_SQLITE_PATH` または `data/paper_trading.db`

- AI 関連
  - ニュース NLP スコア付け:
    - プログラムから `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)` を呼ぶ
    - `api_key` が None の場合は `OPENAI_API_KEY` 環境変数を参照
  - レジーム判定:
    - `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

ログ:
- `kabusys.utils.logging_setup.setup_logging(app_name="execution")` により、コンソール出力（stdout）と日次ローテーションファイル（`logs/<app_name>.log`）が設定されます。ログディレクトリは `LOG_DIR` 環境変数で上書き可。

停止 / Kill Switch:
- KillSwitch は `Settings.kill_flag_path`（デフォルト `data/kill.flag`）に書き込むことで ExecutionEngine に停止シグナルを送ります。
- `run_execution` / `run_monitoring` は `data/stop_requested.flag` を監視し、存在すれば安全終了します。

---

## 設定項目（主な環境変数）

- 動作環境
  - KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- API キー / トークン
  - JQUANTS_REFRESH_TOKEN (必須)
  - KABU_API_PASSWORD (必須)
  - OPENAI_API_KEY (AI 機能で必要)
- DB パス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — KABUSYS_ENV=paper_trading の時に使用
- ログ関連
  - LOG_LEVEL (DEBUG/INFO/...、デフォルト INFO)
  - LOG_DIR (ログファイル保存先)
- 監視 / Kill
  - PID_FILE_PATH (デフォルト: data/execution.pid)
  - KILL_FLAG_PATH (デフォルト: data/kill.flag)
  - KILL_FLAG_CLEAR_ON_START (0/1、デフォルト 0)
- 監視間隔
  - MONITOR_POLL_INTERVAL (run_monitoring 向け、秒)

設定は `.env` に記述しておくか、環境変数として設定してください。自動ロード順は OS 環境 > .env.local > .env（プロジェクトルートが検出できない場合は自動ロードをスキップ）。

---

## ディレクトリ構成

（src/kabusys 配下を中心に抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                  — 環境変数 / Settings 管理
    - config_setup.py            — 対話式 .env ウィザード
    - validate_config.py         — 起動前チェック CLI
    - run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py           — ExecutionEngine 起動スクリプト
    - utils/
      - logging_setup.py         — ログ設定ユーティリティ
      - process_priority.py      — プロセス優先度 / CPU affinity
    - monitoring/
      - monitoring_db.py         — SQLite 永続化層
      - system_monitor.py        — システム状態・データ鮮度監視
      - monitoring_engine.py     — 各 Monitor を束ねる
      - risk_monitor.py
      - trade_monitor.py
      - alert_manager.py
      - kill_switch.py
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
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py

- data/  — 実行時に使用する SQLite / pid / flag 等（デフォルトパス）
- logs/  — ログファイル出力先

---

## 実運用・運用上の注意点

- KABUSYS_ENV を `live` にする場合、全設定を十分に確認してください（`validate_config.py` は `--strict` モードで警告を失敗扱いにできます）。
- 本番では Kill Switch（`KILL_FLAG_CLEAR_ON_START=0`）を自動クリアしないことを推奨します。
- AI 機能は外部 API（OpenAI）に依存します。API 呼び出しの失敗はフェイルセーフ（0.0 でフォールバック等）で設計されていますが、コストやレート制限に注意してください。
- ログディレクトリ作成に失敗するとファイル出力は無効化されますが、コンソール出力は継続します。
- `psutil` を使うプロセス優先度設定は権限依存（AccessDenied）です。設定に失敗した場合は警告ログのみ出ます。

---

## よくある操作例

- ウィザードで .env を作る:
  - `python -m kabusys.config_setup`
- 設定検証:
  - `python -m kabusys.validate_config`  
  - (警告も失敗扱い) `python -m kabusys.validate_config --strict`
- 監視を起動:
  - `python -m kabusys.run_monitoring`
- 実行エンジンを起動:
  - `python -m kabusys.run_execution`
- ペーパートレードレポート:
  - `python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11`

---

## 補足（開発者向け）

- 自動 .env ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定（テスト用）。
- `kabusys.research` の関数群は DuckDB 接続を受け取り SQL ベースで処理します。リサーチ系は本番注文 API へアクセスしません。
- LLM 呼び出し部分（news_nlp / regime_detector）は内部でリトライやレスポンス検証を行います。ユニットテスト時は `_call_openai_api` をモックすることを想定しています。

---

この README はコード内のドキュメント文字列および設定ファイルの記載を元に作成しています。詳細な実装・追加の CLI オプションや内部 API はソースコード（src/kabusys 以下）を参照してください。必要があれば、特定モジュールの利用方法や API 仕様の追記を行います。