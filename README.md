# KabuSys — README

このリポジトリは日本株向けの自動売買 / 監視 / 研究フレームワークです。  
本ドキュメントはプロジェクトの概要、主要機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめた README.md です。

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成される自動売買システムです。

- ExecutionEngine：発注ロジック、リスク管理、オーダー管理を担うエンジン。
- Monitoring：システム状態・注文状況・リスクを監視し、必要であれば Kill Switch を作動させる。
- Portfolio：銘柄選定、配分計算、ポジションサイジング、セクター制約などの純粋関数群。
- Research：DuckDB を使ったファクター計算・特徴量探索・IC 計算等の研究用モジュール。
- AI モジュール：ニュースの NLP によるセンチメント評価や市場レジーム判定（OpenAI API を利用）。
- Tools：ペーパートレード検証レポートなどのユーティリティスクリプト。
- 設定ユーティリティ：対話式 .env ウィザード、設定検証 CLI。

設計上の特徴：
- DuckDB / SQLite をデータ層に使用（分析用 DB と監視 DB を分離可能）。
- Paper Trading モードでは実際のブローカーに発注せず、専用のペーパートレード DB に記録。
- OpenAI を用いたニュースセンチメントやレジーム判定をサポート（API キー必要）。
- フェイルセーフ（API 失敗時のフォールバック、Kill Switch、ログ重視）を重視。

---

## 機能一覧

- 起動スクリプト
  - `run_execution.py`：ExecutionEngine の起動（KABUSYS_ENV による挙動切替）
  - `run_monitoring.py`：監視ループの起動（MONITOR_POLL_INTERVAL で間隔変更可能）
- 設定管理
  - `config_setup.py`：対話式で .env を生成・更新するウィザード
  - `validate_config.py`：環境変数・config/*.yaml の事前検証 CLI
- 監視
  - システム（CPU/メモリ/ディスク）監視、データ鮮度チェック
  - 注文ログの監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン、ポジション上限）
  - Kill Switch（`data/kill.flag` を書き込んで ExecutionEngine を停止）
- ポートフォリオ構築
  - 候補選定、等重／スコア加重の配分、リスクベースのポジションサイズ計算
  - セクター制限、レジーム乗数の適用
- 研究
  - Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - 将来リターンや IC（Information Coefficient）計算、統計サマリ
- AI（OpenAI）
  - ニュース記事の銘柄別センチメント評価（ai_scores へ格納）
  - マクロニュース＋ETF MA による日次レジーム判定（market_regime へ格納）
- ツール
  - `paper_verification_report.py`：ペーパートレードの検証レポート生成（検証基準は稼働率 / 成功率 / レイテンシ等）

---

## 必要条件

- Python 3.10 以上（型ヒントで `X | Y` 記法を使用）
- 主な Python ライブラリ（要インストール）
  - duckdb
  - psutil
  - openai
  - pyyaml（config YAML 検証を行う場合）
- OS レベルではネットワークアクセス（kabu API / OpenAI など）やファイル書込み権限

（プロジェクトに requirements.txt がある場合はそちらを使用してください。ない場合は上記を pip でインストールしてください）

例：
```
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン／展開する

2. Python 仮想環境を作成・有効化（推奨）
```
python -m venv .venv
# Windows
.venv\Scripts\activate
# Unix/macOS
source .venv/bin/activate
```

3. 必要パッケージをインストール
```
pip install -r requirements.txt   # もし requirements.txt があれば
# または最低限:
pip install duckdb psutil openai pyyaml
```

4. .env の作成（対話式ウィザード推奨）
```
python -m kabusys.config_setup
```
ウィザードでは以下の主要項目を設定します（抜粋）：
- KABUSYS_ENV: development / paper_trading / live
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（DEBUG/INFO/…）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（任意、アラート用）
- KILL_FLAG_CLEAR_ON_START（0/1）

5. 設定検証（起動前に推奨）
```
python -m kabusys.validate_config
# --strict を付けると警告でも exit code 1
python -m kabusys.validate_config --strict
```

6. データディレクトリ確認／作成
- デフォルトでは `data/` や `logs/` 下にファイルを作成します。アクセス権を確認してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を使用し、ペーパートレード用 DB（PAPER_TRADING_SQLITE_PATH）に記録
- DUCKDB_PATH（default: data/kabusys.duckdb）
- SQLITE_PATH（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 時の DB）
- OPENAI_API_KEY（AI モジュール利用時に必要）
- LOG_LEVEL（default: INFO）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔（秒）、run_monitoring で利用）
- PAPER_FILL_MODE（paper_trading のフィルモード: instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか）

---

## 使い方（起動／CLI）

基本的なコマンド例（リポジトリのルートで実行）：

- ExecutionEngine を起動（本番／ペーパーは KABUSYS_ENV に依存）
```
python -m kabusys.run_execution
```

- Monitoring を起動（デフォルト 60 秒間隔、MONITOR_POLL_INTERVAL で変更可）
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- 対話式 .env ウィザード
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポート生成
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを明示する場合
python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
```

ログは既定で `logs/` 以下にアプリ名ごとの日次ローテートログが生成されます（例: logs/execution.log, logs/monitoring.log）。

停止の仕組み：
- `data/stop_requested.flag` が存在すると run_execution/run_monitoring はそれを検知して終了します。
- Kill Switch は `data/kill.flag` を書き込むことで ExecutionEngine に停止シグナルを送ります（監視側ロジックで評価される）。

Paper Trading の注意点：
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い、実取引 DB と分離して `PAPER_TRADING_SQLITE_PATH` に記録します。
- PAPER_FILL_MODE によって約定動作が変わります（instant, partial, never, reject）。

AI モジュール（news_nlp / regime_detector）を利用する場合：
- 必ず OPENAI_API_KEY を設定してください。API 呼び出しはリトライ・フォールバックが入っていますが、キー未設定だと例外になります。
- news_nlp は raw_news / news_symbols / ai_scores 等のテーブルを DuckDB に期待します。

---

## 開発・デバッグのヒント

- ロギング設定は `kabusys.utils.logging_setup.setup_logging` を通じて統一されています。ログ出力先は `LOG_DIR` 環境変数またはデフォルト `logs/`。
- プロセス優先度や CPU affinity は `kabusys.utils.process_priority` で抽象化されています。管理者権限がないと設定が失敗する場合があります（警告ログのみ）。
- DuckDB 接続は研究モジュールや AI モジュールに渡して SQL を直接利用する設計です。テーブルやスキーマ（prices_daily / raw_financials / raw_news 等）が想定されています。
- テスト時は OpenAI 呼び出し部分や時間依存部分をモック（patch）することを想定した実装になっています。

---

## ディレクトリ構成（主要ファイル）

以下は主要なディレクトリ・ファイル一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/
    - (ExecutionEngine / order_manager / broker_factory 等)*
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (runtime file 空間、デフォルト)
    - monitoring.db (SQLite)
    - paper_trading.db (paper_trading 用)
    - kill.flag
    - stop_requested.flag
    - execution.pid
  - logs/ (runtime logs)

(* 実装ファイルは execution/ ディレクトリ以下に分割されています。)

---

## 付録：重要ファイル／フラグ

- data/kill.flag
  - 監視から書き込まれる Kill Switch のフラグ。存在すると ExecutionEngine に停止シグナルを伝達する（監視側が検出して停止処理を呼ぶ）。
- data/stop_requested.flag
  - 起動スクリプト（run_*.py）が検知して自己終了するための停止要求ファイル。
- data/*.db
  - monitoring 用 SQLite、paper_trading 用 SQLite、DuckDB ファイルなど。

---

以上がこのコードベースの README です。  
必要があれば、README にサンプル .env のテンプレートやより詳細な起動例（systemd、cron、コンテナ化手順）を追記できます。どの追加情報が必要か教えてください。