# KabuSys — README

本リポジトリは日本株自動売買システム KabuSys の実装コードの一部です。本 README ではプロジェクト概要、主な機能、セットアップ手順、実行方法、ディレクトリ構成を日本語で説明します。

目次
- プロジェクト概要
- 機能一覧
- 必要条件 / 依存ライブラリ
- セットアップ手順
- 環境変数（主な設定）
- 使い方（実行コマンド例）
- 開発・運用時の注意点
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント群（シグナル生成・ポートフォリオ構築・ポジションサイジング・発注管理・監視・リスク管理・ツール）を集めたシステムです。DuckDB を用いた時系列データ処理、SQLite による監視ログ／注文ログの永続化、OpenAI を使ったニュース NLP / レジーム検出などを含みます。

設計方針の要点:
- データ処理は可能な限りローカル DB（DuckDB / SQLite）で実施し外部 API 呼び出しを限定。
- Paper Trading（検証）と Live（本番）を設定で切り替え可能。paper_trading 時は注文はモックブローカに送られ、専用 SQLite に記録して本番 DB と完全分離。
- 監視コンポーネントは別プロセスでポーリングし、問題発生時にフラグファイルを書き出して ExecutionEngine を停止させる仕組みを持つ。
- LLM（OpenAI）呼び出しはリトライ・バリデーション・スコアクリッピング等の安全策を適用。

---

## 機能一覧

主要機能（抜粋）:

- portfolio
  - 候補銘柄選定（スコア順、上位 N）
  - 重み算出（等分配、スコア加重）
  - ポジションサイズ計算（リスクベース、等配分、スコアベース）
  - セクター集中上限適用、レジーム乗数

- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリー

- ai
  - news_nlp: ニュース記事を集約して OpenAI により銘柄別センチメントスコアを算出し ai_scores テーブルへ書込み
  - regime_detector: ETF（1321）MA200 乖離とマクロニュースで日次の市場レジーム（bull/neutral/bear）を判定

- execution
  - OrderManager / OrderRepository による注文状態管理
  - Reconciler による再起動時の注文照合・ポジション差分検出
  - RiskManager（レート制限、ドローダウン等）や ExecutionEngine（セッション実行）は実装ファイル参照

- monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセス生存・データ鮮度のチェック
  - TradeMonitor: 滞留注文 / 約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視
  - KillSwitch: フラグファイルを書き出して ExecutionEngine を停止
  - AlertManager: LINE Push による通知（クールダウン管理）
  - MonitoringEngine: 各モニタのポーリング統括、Streamlit ダッシュボード用スクリプトあり

- tools
  - paper_verification_report: Paper Trading の検証レポートを生成（稼働率、成功率、レイテンシなど）
  - streamlit_dashboard: 監視用ダッシュボード（Streamlit）

---

## 必要条件 / 依存ライブラリ

最低限必要なソフトウェア・ライブラリ（抜粋）:

- Python 3.10+
- duckdb (Python パッケージ)
- psutil
- requests
- openai (OpenAI の Python SDK)
- streamlit（ダッシュボードを使う場合）
- sqlite3（標準ライブラリに含まれる）
- その他、requirements.txt を用意する場合はそちらに従ってください。

インストール例（venv を使う場合）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動します。

2. 仮想環境を作成・有効化して依存パッケージをインストールします（上記参照）。

3. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

4. 必須の環境変数を設定してください（主なものは下記参照）。

5. データディレクトリ（デフォルト: data/）を作成しておくと便利です。
```bash
mkdir -p data
```

6. DuckDB/SQLite の初期化は多くのスクリプトが自動で実行します（monitoring 用のテーブルは init_monitoring_db により冪等に作成されます）。必要に応じて DuckDB のスキーマや prices_daily/raw_financials テーブルを準備してください。

---

## 環境変数（主な設定）

Settings クラスで読み込む主要な環境変数（抜粋）:

- KABUSYS_ENV: 起動環境（development | paper_trading | live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（monitoring）DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch が書き込むフラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を削除するか（"1" で有効）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）

監視関連しきい値:
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

監視ポーリング間隔:
- MONITOR_POLL_INTERVAL: SystemMonitor のポーリング間隔（秒、デフォルト 60）。0 以下や不正値はデフォルトにフォールバック。

簡単な .env 例（プロジェクトルートに配置）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
OPENAI_API_KEY=sk-xxxx...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
LOG_LEVEL=INFO
```

---

## 使い方（実行コマンド例）

※ パッケージルート（src が PYTHONPATH に含まれるか、パッケージインストール後）で実行してください。推奨: リポジトリのルートから `python -m kabusys...` を実行。

- 監視ループ（SystemMonitor のシンプル起動）
```bash
# 既定: MONITOR_POLL_INTERVAL=60
python -m kabusys.run_monitoring
# または環境変数で間隔を変更
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 実行エンジン（ExecutionEngine）起動
```bash
python -m kabusys.run_execution
# Paper trading に切り替える例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
paper_trading の場合、モックブローカを使い PAPER_TRADING_SQLITE_PATH に記録します（本番 DB と分離）。

- Paper Trading 検証レポート生成（ツール）
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パス指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- Streamlit ダッシュボード（監視）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
注意: dashboard は監視 DB を読み取り専用で開きます。MonitoringEngine が監視ログを書き込んでいることを確認してください。

- AI スコア / レジーム処理（ライブラリ呼び出し）
Python から直接関数を呼ぶ例:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
# ニューススコア付与（日付指定）
score_news(conn, target_date=date(2026, 4, 11), api_key="sk-...")
# レジーム判定
score_regime(conn, target_date=date(2026, 4, 11), api_key="sk-...")
```

---

## 開発・運用時の注意点

- 環境自動ロード: `kabusys.config` はプロジェクトルートを .git または pyproject.toml で探索し、`.env` / `.env.local` を自動読み込みします。テスト等で自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- Paper Trading と Live の DB は分離する設計です。paper_trading では paper_sqlite_path を使用します。

- Process Priority: run_monitoring / run_execution の起動時に `set_process_priority("high")` を呼んでいます。権限がない場合は警告を出してスキップします。

- KillSwitch: 危険な状況（ドローダウン超過など）の場合 `data/kill.flag` に理由を書き込み、ExecutionEngine に停止を促します。ExecutionEngine 起動時にこのフラグを自動クリアする設定 (`KILL_FLAG_CLEAR_ON_START=1`) を利用できます。

- OpenAI API 呼び出し: API エラー時のリトライや応答バリデーションを実装していますが、API キーと課金に注意してください。テストではモック化して呼び出しを避けてください。

- DuckDB のテーブル（prices_daily, raw_financials など）は外部データ取り込み手順が必要です（本 README には含まれていません）。

- ログ: 各スクリプトは基本的に logging を利用しています。`LOG_LEVEL` 環境変数で制御可能です。

---

## ディレクトリ構成

主要なファイル・サブパッケージ（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (その他: broker, order_repository 等、実装ファイル群)
  - utils/
    - process_priority.py
  - research/ (既述)
  - data/ (想定: データファイルを配置するディレクトリ、リポジトリには含まれない)

- data/
  - (デフォルトの DB ファイルや PID / flag ファイルがここに置かれます)
  - data/kabusys.duckdb
  - data/monitoring.db
  - data/paper_trading.db
  - data/execution.pid
  - data/kill.flag

---

以上がこのコードベースの README です。必要であれば以下の追加を作成します:
- requirements.txt の提案
- .env.example のファイル
- より細かいデプロイ手順（systemd ユニット、Dockerfile 等）
- 各モジュール（ExecutionEngine / Broker 接続等）の API ドキュメント

どれを優先して作成しますか？