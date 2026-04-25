# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。本リポジトリは取引実行エンジン、監視（Monitoring）、リサーチ/ポートフォリオ構築、AI を用いたニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次のような責務を持つコンポーネント群で構成されています。

- ExecutionEngine：発注処理／注文管理／リスク管理を行う実行エンジン（paper_trading モードでは MockBroker を使用し本番 DB と分離）
- Monitoring：システム状態・注文状況・リスク指標をポーリングしてログやアラート、Kill Switch を評価
- Research：DuckDB 上の市場データからファクターや将来リターン、IC 等を計算
- Portfolio：銘柄選定、重み計算、ポジションサイズ算出、セクター制限、レジーム乗数
- AI：ニュースを LLM（OpenAI）で解析して銘柄ごとのスコア、マーケットレジーム判定など
- Utils / Tools：ログ設定、プロセス優先度、設定ウィザード、設定検証、検証レポート生成 等

設計上、DuckDB（分析用）と SQLite（監視／発注ログ）を併用します。環境変数・`.env` による設定管理を想定しています。

---

## 主な機能一覧

- 実行（Execution）
  - Broker クライアント抽象化（本番と Mock 切り替え）
  - OrderManager / Reconciler / RiskManager を組み合わせた Engine
  - 発注・約定ログを SQLite に記録

- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス生存チェック
  - 注文滞留・約定異常の検出
  - ドローダウン / 保有上限の監視と Kill Switch（flag ファイル書き込み）
  - ポーリングループ（環境変数で間隔指定可能）

- リサーチ
  - Momentum / Volatility / Value 等のファクター計算 (DuckDB)
  - 将来リターン計算、IC（Spearman）計算、ファクター統計

- ポートフォリオ構築
  - 候補選定、等重・スコア重み、リスクベースのポジションサイズ
  - セクターキャップ、レジーム乗数

- AI（LLM）連携
  - ニュースを LLM でスコアリングして ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 乖離を合成して日次レジーム判定

- 開発/運用支援
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 用検証レポート生成ツール

---

## 前提 / 必要ライブラリ

（例）Python 3.10+ を想定。主要依存パッケージ：

- duckdb
- psutil
- openai
- PyYAML（config の検証を行う場合に必要、任意）
- その他（標準ライブラリ: sqlite3, logging 等）

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. レポジトリをクローンして作業ディレクトリに移動

2. 仮想環境を作成して依存をインストール（上記参照）

3. 初期環境ファイルの作成（推奨）
   - 対話式ウィザードで `.env` を作成できます。

```
python -m kabusys.config_setup
```

ウィザード完了後、`.env` が生成されます。生成後に以下検証を推奨します。

4. 設定検証

```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

5. データディレクトリ等の確認
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
   - ログディレクトリ: logs/（環境変数 LOG_DIR で変更可）

6. OpenAI を使う機能を利用する場合は `OPENAI_API_KEY` を `.env` に設定

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（paper_trading の注文成行挙動、"instant","partial","never","reject"）
- LOG_LEVEL（"DEBUG"/"INFO"/...、デフォルト: INFO）
- MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか、0/1）
- PID_FILE_PATH / KILL_FLAG_PATH（デフォルト: data/execution.pid / data/kill.flag）

注意:
- Monitoring の初期化 (run_monitoring.py) は KABUSYS_ENV にかかわらず monitoring 用に settings.sqlite_path（デフォルト：data/monitoring.db）を使用します。
- run_execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path（デフォルト：data/paper_trading.db）を利用して本番 DB と分離します。

---

## 使い方（コマンド例）

- 実行エンジン（ExecutionEngine）を起動

```
python -m kabusys.run_execution
```

- 監視ループを起動

```
# MONITOR_POLL_INTERVAL でポーリング間隔を秒で指定（省略時 60秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 設定ウィザード（.env の生成 / 更新）

```
python -m kabusys.config_setup
```

- 設定検証

```
python -m kabusys.validate_config
```

- Paper Trading 検証レポート生成（tools）

```
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パス明示
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI スコアリング / レジーム判定（ライブラリ API）
  - duckdb 接続を作成して、以下の関数を呼ぶことで実行できます（コード内 API）。

例（スニペット）:

```py
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,4,20), api_key="sk-...")
r = score_regime(conn, target_date=date(2026,4,20), api_key="sk-...")
```

---

## 停止・Kill Switch の操作

- 実行ループ（run_execution/run_monitoring）はプロジェクトルート下の `data/stop_requested.flag` を検出すると安全に終了します。
- ExecutionEngine 側の強制停止判定は `data/kill.flag` を用いる Kill Switch により行われ、Kill Switch が書かれると execution を停止する（flag を用いた制御）。
- 起動時に `KILL_FLAG_CLEAR_ON_START=1` が設定されていると自動クリアされますが、本番環境では推奨されません。

PID ファイル:
- run_execution は `data/execution.pid`（デフォルト）に PID を書き込みます。

---

## ロギング

- 共通のロギング設定関数 setup_logging を用いて、コンソール（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。
- ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/` を使用。
- ファイル出力ができない場合はコンソールのみで継続します。

---

## DB 周り（DuckDB / SQLite）

- DuckDB: 分析用の大規模データを保持する（prices_daily, raw_financials, raw_news, ai_scores, market_regime など）
  - デフォルト: data/kabusys.duckdb

- SQLite: 監視・発注ログ、ダッシュボード等を保持
  - Monitoring 用デフォルト: data/monitoring.db
  - Paper trading 用: data/paper_trading.db（KABUSYS_ENV=paper_trading 時に使用）

- monitoring_db モジュールには初期化・マイグレーションロジック（テーブル作成、カラム追加）があります。

---

## ディレクトリ構成（主要ファイル）

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数・Settings
   ├─ config_setup.py           # .env ウィザード
   ├─ validate_config.py        # 設定検証 CLI
   ├─ run_execution.py         # ExecutionEngine 起動スクリプト
   ├─ run_monitoring.py        # SystemMonitor ポーリング起動スクリプト
   ├─ utils/
   │   ├─ __init__.py
   │   ├─ logging_setup.py     # ログ設定
   │   └─ process_priority.py  # 優先度 / CPU affinity
   ├─ monitoring/
   │   ├─ monitoring_db.py
   │   ├─ system_monitor.py
   │   ├─ trade_monitor.py     # （注文監視ロジック）
   │   ├─ risk_monitor.py
   │   ├─ kill_switch.py
   │   ├─ monitoring_engine.py
   │   └─ alert_manager.py     # （通知/アラート管理）
   ├─ execution/
   │   ├─ execution_engine.py
   │   ├─ order_manager.py
   │   ├─ order_repository.py
   │   ├─ broker_factory.py
   │   ├─ reconciler.py
   │   └─ risk_manager.py
   ├─ portfolio/
   │   ├─ portfolio_builder.py
   │   ├─ position_sizing.py
   │   └─ risk_adjustment.py
   ├─ research/
   │   ├─ factor_research.py
   │   └─ feature_exploration.py
   ├─ ai/
   │   ├─ news_nlp.py
   │   └─ regime_detector.py
   ├─ data/                      # 実行時に生成される想定のディレクトリ（DB / flag / pid）
   └─ tools/
       └─ paper_verification_report.py
```

（注）実際のファイル群は上記に加えて細分化されています。monitoring/trade_monitor.py や alert_manager.py、execution の詳細実装は本 README では省略しています。

---

## 開発者向けメモ / 注意事項

- 設定の自動読み込み: config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Monitoring の注意点: run_monitoring は MONITOR_POLL_INTERVAL（秒）でループします。0 や負の値は無効としてデフォルト 60 秒にフォールバックします。
- Paper Trading: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて発注を模擬し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）にログを記録します。実際の発注は行いません。
- OpenAI 呼び出し: API エラーやタイムアウトに対して指数バックオフでリトライしますが、最終的に失敗した場合はフェイルセーフ（スコア 0.0 を採用する等）で継続します。API キー管理に注意してください。
- DB 書き込みは冪等性や部分更新（該当コードのみ DELETE → INSERT）を考慮する実装になっていますが、運用前にバックアップ・テストを行ってください。
- ローカルでの動作確認やユニットテスト時は環境変数を適切に設定し、本番 DB へのアクセスが発生しないよう注意してください（特に API トークンや本番 DB パス）。

---

不明点や README に追加したい情報（例: 実際の requirements.txt、デプロイ手順、systemd/cron 用の起動例、より詳細なアーキテクチャ図 等）があれば教えてください。必要に応じて追記します。