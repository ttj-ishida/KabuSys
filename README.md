# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ＋実行スクリプト）。  
このリポジトリはトレーディングロジック、ポートフォリオ構築、監視、AI を用いたニュース解析やレジーム判定、Paper Trading 用の検証ツール等を含みます。

---

## プロジェクト概要

KabuSys は、以下の目的を持つコンポーネント群を提供します。

- 注文発行・状態管理・再同期（Execution）
- ポートフォリオ構築（候補選定・重み付け・株数決定・リスク調整）
- 監視（システム状態、注文の滞留・約定異常、ドローダウン監視、kill switch、LINE 通知）
- 研究・ファクター計算（DuckDB を用いたファクター計算・特徴量解析）
- AI を使ったニュースセンチメント（OpenAI）とレジーム判定
- Paper Trading 用検証レポートと Streamlit ダッシュボード

設計方針の例:
- DuckDB / SQLite をデータソースとして使い、外部 API への依存は必要箇所のみ最小化
- ルックアヘッドバイアスを避ける（日時参照の扱いに注意）
- フェイルセーフ：外部 API エラーが発生しても重大障害とならない設計

---

## 主な機能一覧

- Execution
  - 起動時のリコンシリエーション（Reconciler）
  - OrderManager による注文生成 / 送信 / 同期
  - paper_trading 環境では MockBroker を利用して本番 DB と分離

- Portfolio
  - 候補選定（スコア降順）
  - 等金額 / スコア加重 / リスクベースのポジションサイズ計算
  - セクターキャップ適用、レジーム乗数

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / プロセス稼働 / データ鮮度チェック
  - TradeMonitor: 滞留注文チェック・約定価格異常検出
  - RiskMonitor: ドローダウン・保有数上限の検出とログ記録
  - KillSwitch: 条件成立時にフラグファイルを書いて ExecutionEngine を停止
  - AlertManager: LINE push による通知（クールダウン制御）
  - Streamlit ダッシュボード（監視データ可視化）

- Research / AI
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - ニュース NLP（OpenAI）で銘柄別センチメントを生成して ai_scores に書込
  - レジーム判定（ETF MA とマクロセンチメントの合成）

- Tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
  - Streamlit ダッシュボード（監視）

---

## 必要要件 (主な依存パッケージ)

- Python 3.9+
- duckdb
- psutil
- requests
- streamlit (ダッシュボード利用時)
- openai (AI 機能利用時)

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil requests streamlit openai
# またはプロジェクトがパッケージ化されていれば:
# pip install -e .
```

（pyproject.toml / requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順（開発 / 実行のための最小手順）

1. リポジトリをクローンし、Python 仮想環境を作成して有効化する。

2. 依存パッケージをインストールする（上記参照）。

3. 環境変数の設定
   - ルートに `.env` を置くと自動で読み込まれます（プロジェクトルートが .git または pyproject.toml で特定できる場合）。
   - 自動ロードを無効にしたい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の主要環境変数（例）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY（AI 機能を使う場合）
   - その他重要な環境変数（デフォルト値あり）:
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
     - PID_FILE_PATH, KILL_FLAG_PATH
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の模擬約定挙動）
     - LOG_LEVEL（INFO 等）
     - MONITOR_POLL_INTERVAL（監視ポーリング間隔秒、デフォルト 60）

4. データディレクトリの作成（デフォルトの sqlite/duckdb パスが data/ 以下なので、存在することを確認）:
```bash
mkdir -p data
```

---

## 実行方法（代表的なコマンド例）

注意: パッケージをインストールしていない場合は、リポジトリルートから PYTHONPATH を通すか、`pip install -e .` してください。

- ExecutionEngine を起動（本番 / 開発 / paper_trading は KABUSYS_ENV に依存）:
```bash
# 例: Paper Trading モードで起動
export KABUSYS_ENV=paper_trading
python -m kabusys.run_execution
```
- Monitoring のポーリングループ起動:
```bash
# ポーリング間隔を 30 秒にする例
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- Streamlit ダッシュボード（監視 DB を参照）:
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- Paper Trading 検証レポート生成:
```bash
# デフォルト DB を使って全期間
python -m kabusys.tools.paper_verification_report

# 期間指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# DB パスを直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI 機能（ニューススコア付け / レジーム判定）のライブラリ呼び出し例（Python REPL 等）:
```python
import duckdb, datetime
from kabusys.ai.news_nlp import score_news
conn = duckdb.connect("data/kabusys.duckdb")
# target_date は date 型 (例: 2026-04-01)
score_news(conn, datetime.date(2026,4,1), api_key="あなたのOpenAIキー")
```

---

## 主要設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- KABUSYS_ENV — "development" | "paper_trading" | "live"
  - paper_trading の場合、Execution は MockBroker を使い、データは PAPER_TRADING_SQLITE_PATH に記録されます（本番 DB と完全分離）。
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB (monitoring)（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH — Execution のプロセス管理 / 停止フラグ
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- PAPER_FILL_MODE — paper_trading 時の模擬約定モード（instant/partial/never/reject）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視しきい値

---

## 使い方のポイント・実運用注意

- Paper Trading モードは本番 DB と完全に分離されます。検証時は必ず KABUSYS_ENV=paper_trading を指定してください。
- Monitoring は常に（KABUSYS_ENV に関係なく）本番の sqlite_path を使う設計になっている部分があります。運用時は注意して DB パスを設定してください。
- AI（OpenAI）への呼び出しはネットワーク/料金が発生します。API キーの管理とレート、コストに注意してください。
- kill.flag による停止は冪等で書き込みされ、既存ファイルがある場合は再作成されません。Execution 起動時に KILL_FLAG_CLEAR_ON_START 環境変数により自動クリアを制御できます。
- PID 管理: Execution は PID ファイルを書き、SystemMonitor は存在/生存確認を行います。PID ファイルの管理場所（PID_FILE_PATH）を適切に設定してください。
- Streamlit ダッシュボードは監視 DB を読み取り専用で開くことが推奨です（起動コマンド内で URI に ?mode=ro を付与しています）。

---

## ライブラリ API（簡易）

- kabusys.portfolio
  - select_candidates(buy_signals, max_positions=10)
  - calc_equal_weights(candidates)
  - calc_score_weights(candidates)
  - calc_position_sizes(weights, candidates, portfolio_value, available_cash, ...)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons=None)
  - calc_ic(factor_records, forward_records, factor_col, return_col)
  - factor_summary(records, columns)

- kabusys.ai
  - score_news(conn, target_date, api_key=None)
  - score_regime(conn, target_date, api_key=None)  (regime_detector モジュール)

- kabusys.monitoring
  - MonitoringDB / MonitoringEngine / SystemMonitor / TradeMonitor / RiskMonitor / AlertManager / KillSwitch

これらはドキュメント文字列と型注釈で使い方が示されています。具体的には各モジュールの docstring を参照してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定ローダ
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
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
    - news_nlp.py             — ニュース NLP (OpenAI) スコアリング
    - regime_detector.py      — レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
    - __init__.py
  - execution/
    - order_manager.py
    - reconciler.py
    - ... （ブローカ API / repository 等）
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (想定されるデータファイル置き場、例)
    - kabusys.duckdb
    - monitoring.db
    - paper_trading.db

---

## 開発・デバッグのヒント

- .env の構文パーサは多少の shell 形式（export KEY=val / コメント / クォート）に対応しています。
- config.Settings は自動でプロジェクトルートの .env / .env.local をロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- ログレベルは LOG_LEVEL 環境変数で制御可能です。
- process priority / CPU affinity は utils/process_priority.py から設定されます（set_process_priority が起動時に呼ばれます）。権限不足や非対応 OS では警告を出してスキップします。
- DuckDB の接続は通常ファイルパスを渡して使います。research / ai モジュールは DuckDB 接続を受け取る設計です。

---

## 最後に

本 README はコードベースのエントリポイント、主要機能、実行方法、設定項目をまとめたものです。各モジュールには詳細な docstring と実装コメントが付与されているため、具体的な振る舞いやパラメータは該当ファイルを参照してください。

ご不明点や README に追記してほしい事項があれば教えてください。