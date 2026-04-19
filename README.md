# KabuSys

日本株向け自動売買システムのサンプル実装ドキュメント（日本語）。  
このリポジトリは、監視（Monitoring）、発注エンジン（Execution）、ポートフォリオ構築、リサーチ、AI ベースのニュース評価など、実運用を想定したコンポーネント群を含みます。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- 株価データ / 財務データを用いたファクター計算・リサーチ
- ポートフォリオ構築・ポジションサイズ決定ロジック
- 発注エンジン（ExecutionEngine）による注文管理とブローカーインターフェース
- システム稼働監視（SystemMonitor）・取引監視（TradeMonitor）・リスク監視（RiskMonitor）
- ニュースを LLM（OpenAI）でスコアリングして市場レジーム判定に利用する AI モジュール
- ペーパートレード用の分離 DB と検証レポート生成ツール
- 簡易的な CLI（環境設定ウィザード、設定検証、レポート生成 等）

設計方針としては「外部副作用を最小化」「ルックアヘッドバイアスを防止」「冪等性（起動を繰り返しても安全）」などに配慮しています。

---

## 主な機能一覧

- 環境設定管理（.env の自動読み込み / config 設定）
- interactive な .env 作成ウィザード（kabusys.config_setup）
- 起動前設定検証（kabusys.validate_config）
- System / Trade / Risk の監視とログ永続化（SQLite）
- ExecutionEngine（本番 / ペーパートレード切り替え）
- ブローカークライアント抽象化（BrokerClientFactory）
- ポートフォリオ構築（候補選定、等重量・スコア重み、リスクベース割当）
- セクター集中制限、レジームに応じた資金乗数
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI ベースのニュース NLP（OpenAI を用いた銘柄別センチメント）
- 市場レジーム判定（ETF MA + マクロセンチメント合成）
- 各種ユーティリティ（ロギング設定、プロセス優先度 / CPU affinity 設定）
- Paper Trading 検証レポート生成ツール

---

## 動作要件（依存パッケージ）

最低限必要な Python パッケージ（一例）:

- python >= 3.9（型注釈に対応するバージョンを推奨）
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（config YAML の検証を有効化したい場合）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## 環境変数 / .env

設定は環境変数またはリポジトリルートの `.env` / `.env.local` から読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

主要な環境変数（必須 / 任意）:

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意・よく使う項目:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
- DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
- SQLITE_PATH — 監視 DB。デフォルト `data/monitoring.db`
- PAPER_TRADING_SQLITE_PATH — ペーパートレード時の専用 SQLite（デフォルト `data/paper_trading.db`）
- LOG_LEVEL — (DEBUG/INFO/WARNING/ERROR/CRITICAL)
- LOG_DIR — ログ保存ディレクトリ（デフォルト `logs/`）
- OPENAI_API_KEY — AI 機能を利用する場合に必要
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill flag を自動クリアするか（0/1）

簡易 `.env` 例（config_setup で生成可）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## セットアップ手順

1. リポジトリを clone して作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 依存パッケージをインストール（duckdb, psutil, openai, PyYAML 等）
4. `python -m kabusys.config_setup` を実行して `.env` を作成（対話式）
5. `python -m kabusys.validate_config` で設定を検証
6. 必要に応じて DB 初期化（monitoring 用は起動スクリプトが自動で init します）

注意:
- Paper Trading（KABUSYS_ENV=paper_trading）時は mock broker を使用し、ペーパートレード用 SQLite（PAPER_TRADING_SQLITE_PATH）へ記録します。本番 DB と分離されます。
- OpenAI を用いる機能は `OPENAI_API_KEY` が必要です。

---

## 使い方（起動と主要 CLI）

作業ディレクトリはプロジェクトルート（.git や pyproject.toml がある場所）を想定しています。

- 環境ウィザード（.env の作成/更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告もエラー扱いにする場合:
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor が定期的に状態を記録）
  ```
  # 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  特記事項:
  - run_monitoring は常に Settings.sqlite_path（本番の monitoring DB）を使用します。
  - プロセス優先度を `high` に設定します。
  - `data/stop_requested.flag` が作られるとループが終了します。

- ExecutionEngine 起動（発注エンジン）
  ```
  python -m kabusys.run_execution
  ```
  特記事項:
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、`data/paper_trading.db` に記録します。
  - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします。
  - `data/execution.pid` に PID を書きます。
  - 実行中に `data/stop_requested.flag` を作成すると安全に停止します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI / リサーチ機能（ライブラリとしてインポートして使用）
  - ニューススコアリング: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - レジーム判定: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - ファクター計算: `kabusys.research.calc_momentum(conn, target_date)` 等

例（Python REPL から）:
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, date(2026,4,10), api_key="sk-...")
```

---

## ログと停止フラグ

- ログ:
  - デフォルトは stdout とファイル出力（logs/<app_name>.log）を併用。ファイルは日次ローテーション（30日保管）。
  - ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` で統一設定されます。
  - LOG_DIR 環境変数でログ保存先を上書き可能。

- 停止・Kill スイッチ:
  - `data/stop_requested.flag` — run_monitoring / run_execution の外部停止トリガ（存在でループ停止）。
  - `data/kill.flag` — KillSwitch により ExecutionEngine 停止を要求するために監視側が書き込む（Scheduling や管理者操作で作成可能）。
  - ExecutionEngine 起動時の `KILL_FLAG_CLEAR_ON_START=1` 設定は本番では危険なので注意。

---

## ディレクトリ構成

主要ファイル / ディレクトリ（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード（CLI）
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py       — ログ設定ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py      — システム・データ鮮度監視
    - risk_monitor.py        — ドローダウン・ポジション制限監視
    - trade_monitor.py       — (取引監視; 実装参照)
    - monitoring_engine.py   — 各 Monitor を束ねる実行ロジック
    - kill_switch.py         — kill.flag 管理
    - alert_manager.py       — (通知管理: LINE 等、実装参照)
  - execution/
    - execution_engine.py    — ExecutionEngine / EngineConfig
    - broker_factory.py      — BrokerClient の生成
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み計算
    - position_sizing.py     — 株数決定・スケーリング
    - risk_adjustment.py     — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py     — Momentum / Volatility / Value 等
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マクロ+ETF MA を組み合わせたレジーム判定
  - data/                    — デフォルトの DB / フラグファイル格納想定パス（README 参照）
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成

（実際のファイル一覧はリポジトリを参照してください）

---

## 開発時の注意点・設計のポイント

- DB:
  - monitoring（監視）DB は sqlite3。初期化は init_monitoring_db() により冪等的に行われます。
  - duckdb は分析用（prices_daily, raw_financials 等）を想定。

- Paper Trading:
  - `KABUSYS_ENV=paper_trading` の場合、Execution は MockBrokerClient を使いペーパートレード専用 DB に記録することで本番 DB と完全に分離します。

- AI 呼び出し:
  - OpenAI の API 呼び出しはリトライとエラーハンドリングを実装していますが、API キーは必ず設定してください。
  - レスポンスのバリデーションとスコアのクリップを行い、部分失敗時にも既存データを壊さない設計です。

- ログ・優先度:
  - 起動スクリプトは process priority を高優先度に上げます（失敗した場合は警告でスキップ）。
  - ログは stdout とファイルへ一貫したフォーマットで出力されます。

---

## よくある操作例

- 監視をデフォルト間隔（60秒）で起動:
  ```
  python -m kabusys.run_monitoring
  ```

- 監視を 10 秒間隔で起動（テスト用）:
  ```
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  ```

- Execution をペーパートレードモードで起動:
  ```
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```

- Paper Trading レポート（2026-04-01〜2026-04-11）:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## ライセンス・貢献

このドキュメントはコードベースの README 目的で生成しています。実際のライセンスや貢献ガイドラインはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

---

README に不足している個別 API や内部構造（ExecutionEngine の設定詳細、OrderRepository の DB スキーマ、TradeMonitor の仕様など）について、より詳しいドキュメントが必要であれば、関心のある箇所を指定してください。具体的な使い方サンプルや API ドキュメントを追加で作成します。