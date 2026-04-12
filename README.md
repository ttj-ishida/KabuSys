# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注実行・監視・解析用ユーティリティを含むモジュール群です。DuckDB を用いたリサーチ/ファクター計算、SQLite を用いた監視ログ／発注履歴保存、OpenAI を利用したニュース NLP / レジーム検出などを備えています。

---

## 目次

- プロジェクト概要
- 機能一覧
- 前提・要件
- セットアップ手順
- 環境変数（主なもの）
- 実行例 / 使い方
- 監視関連
- ツール（レポート等）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買パイプラインを構成するライブラリ群です。主な目的は次のとおりです。

- DuckDB を使ったファクター計算（momentum / volatility / value 等）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- 発注エンジン（ExecutionEngine）とブローカークライアント（本番／Paper Trading 切替）
- 発注状態の再同期（Reconciler）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）とアラート送信（LINE）
- AI ツール（ニュース NLP による銘柄センチメント、レジーム検出）
- Paper Trading 検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

---

## 機能一覧

- research
  - calc_momentum / calc_volatility / calc_value：DuckDB 上でのファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析ユーティリティ
- portfolio
  - 候補選定、等金額/スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - position sizing（リスクベース / weight ベースの株数算出、単元切り捨て・スケール調整）
- execution
  - OrderManager: 注文ライフサイクル管理（作成・送信・同期）
  - Reconciler: 再起動時の自動復旧（OrderSent の突合、ポジション差分検出）
  - ブローカーファクトリによる paper_trading 用 MockBrokerClient の切替
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor、MonitoringDB（SQLite）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - KillSwitch：条件により ExecutionEngine を停止させるためのフラグファイル書き込み
  - streamlit_dashboard：監視情報の可視化
- ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でスコアリングして ai_scores に保存
  - regime_detector.score_regime：ETF MA とマクロ記事の LLM 評価を合成し market_regime を書き込み
- tools
  - paper_verification_report：Paper Trading DB から検証レポートを生成

---

## 前提・要件

推奨環境（一例）

- Python 3.10+
- 必要ライブラリ
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit (ダッシュボードを使う場合)
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（LINE API / OpenAI を使う場合）

セットアップ例（venv 作成・パッケージインストール）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

（実際の requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン、作業ディレクトリへ移動。

2. 仮想環境を作成して依存パッケージをインストール（上記参照）。

3. データディレクトリを作成（デフォルトの DB パスを使う場合）:

```bash
mkdir -p data
```

4. 環境変数を用意（.env ファイル推奨）。自動読み込みが有効（Settings モジュール）なのでプロジェクトルートに `.env` を置くと読み込まれます。

簡易的な .env 例:

```
# 必須（例）
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_api_password

# 動作モード
KABUSYS_ENV=development  # or paper_trading / live

# DB パス（オプション、デフォルトは data/*.db / data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

# OpenAI（AI モジュール使用時）
OPENAI_API_KEY=sk-...

# LINE 通知（任意）
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...

# Paper Trading の挙動
PAPER_FILL_MODE=instant  # instant|partial|never|reject

# モニターのポーリング間隔（秒）
MONITOR_POLL_INTERVAL=60
```

5. 必要に応じて data データベースを初期化（monitoring 起動時に自動でマイグレーションを行います）。

---

## 主な環境変数（抜粋）

- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）で使用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading 時の約定動作（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: PID / kill.flag のパス（デフォルト data/*.pid / data/kill.flag）

---

## 実行方法（主要スクリプト）

※ src 配下がパッケージとして動くように PYTHONPATH を設定するか、プロジェクトルートで `python -m kabusys.<module>` を実行してください。

- ExecutionEngine を起動（実際の発注処理）
  - 本番／paper_trading は KABUSYS_ENV に依存（paper_trading の場合は MockBrokerClient を使用）
  - 実行:

```bash
# 開発・デフォルトモード
python -m kabusys.run_execution

# 明示的に環境変数を指定して paper_trading で実行
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Monitoring の単独起動（SystemMonitor のポーリングループ）
  - MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒）:

```bash
python -m kabusys.run_monitoring
# 例: 30秒間隔
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- Streamlit ダッシュボード起動（監視 DB を読み取り専用で表示）:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート（ツール）:

```bash
# デフォルト DB を使用
python -m kabusys.tools.paper_verification_report

# 期間指定 / DB 指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```

- AI モジュール（プログラム内 API 呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（環境変数または引数）が必要

---

## 監視（Monitoring）について

- Monitoring は SQLite（monitoring.db）へ以下のテーブルを作成・使用します（init_monitoring_db が自動で作成／マイグレーションを行う）:
  - system_status: CPU / memory / disk / process_ok 等の定期ログ
  - trade_logs: 発注イベントログ（latency_ms カラムあり）
  - positions: 保有ポジション
  - risk_logs: リスクイベント（DRAWDOWN_ALERT / STALE_ORDER 等）
  - dashboard: ダッシュボード集計（id=1 の単一行）
- KillSwitch は RiskMonitor の出力に基づいて data/kill.flag を作成し、ExecutionEngine 側の停止トリガーとして機能します（ExecutionEngine 側は定期的に kill.flag を監視します）。
- AlertManager は LINE Push API を用いた一方向通知を行います（channel token / user id が未設定の場合はログのみ）。

---

## Paper Trading の分離

- KABUSYS_ENV=paper_trading の場合、発注は MockBrokerClient を使い、SQLite は `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）を使用します。本番用 DB と完全に分離されます（安全設計）。

---

## 注意点 / 実運用メモ

- process priority を起動時に High に設定する処理が含まれます（psutil による設定）。権限不足や非対応 OS の場合は警告を出してスキップされます。
- MONITOR_POLL_INTERVAL に 0 や負の値を設定すると無効（デフォルトにフォールバック）になります。
- OpenAI 呼び出しはネットワークエラーや 429 等に対して指数バックオフでリトライする実装ですが、API キーの設定や利用量に注意してください。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings 管理、.env 読み込みロジック
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト

src/kabusys/data/ ...
（prices_daily / raw_financials 等を想定するモジュール群 — 本ツリーでは省略）

src/kabusys/research/
- factor_research.py — momentum / volatility / value 等のファクター計算
- feature_exploration.py — forward returns / IC / 統計サマリ

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定 / 重み計算
- position_sizing.py — 発注株数計算
- risk_adjustment.py — セクターキャップ / レジーム乗数

src/kabusys/execution/
- order_manager.py
- reconciler.py
- （broker_factory / execution_engine / order_repository 等）

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマと永続化操作
- system_monitor.py / trade_monitor.py / risk_monitor.py
- monitoring_engine.py — 各 Monitor の統合実行ループ
- alert_manager.py — LINE 通知
- kill_switch.py — flag ファイルによる停止トリガー
- streamlit_dashboard.py — 可視化ツール

src/kabusys/ai/
- news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書き込む
- regime_detector.py — MA とマクロセンチメントを合成して market_regime に書き込む

src/kabusys/tools/
- paper_verification_report.py — Paper Trading 検証レポート生成

---

## 最後に

この README はコードベースからの概要説明・操作手順をまとめたものです。各モジュールの詳細な挙動（パラメータの意味、例外ハンドリング、内部の SQL スキーマなど）はソースコード内の docstring / コメントを参照してください。

不明点や README に追加してほしい情報があれば教えてください。