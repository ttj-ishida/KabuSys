# KabuSys — 日本株自動売買システム (README)

以下はこのリポジトリ（KabuSys）の概要、機能、セットアップ手順、基本的な使い方、ディレクトリ構成の説明です。

## プロジェクト概要
KabuSys は日本株の自動売買システムを想定したコードベースです。主な機能は以下の通りです：
- 発注/約定管理を行う ExecutionEngine（本番 / Paper Trading モード）
- システム監視（CPU/メモリ/ディスク、プロセス監視、データ鮮度チェック）
- リスク監視（ドローダウン、ポジション上限など）と KillSwitch（停止フラグ）
- LINE によるアラート送信（AlertManager）
- 監視結果の永続化（SQLite）および市場データ解析（DuckDB）
- 研究用モジュール（ファクター計算・IC 等）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント評価）とレジーム判定
- Paper Trading の検証レポート出力ツール、Streamlit ダッシュボード

設計方針としては、データ永続化は SQLite（監視ログ等）および DuckDB（市場データ解析）を使い、AI 機能は OpenAI API を必要に応じて呼び出す形になっています。設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込みます。

---

## 主な機能一覧
- Execution
  - 本番 / paper_trading を切り替え（KABUSYS_ENV）
  - Broker クライアントの抽象化（MockBrokerClient を paper_trading で使用）
  - 起動時のリコンシリエーション（Reconciler）で注文・ポジションの同期
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク、プロセス PID、データ鮮度
  - TradeMonitor: 滞留注文、約定価格の異常検知
  - RiskMonitor: ドローダウン / ポジション上限監視
  - KillSwitch: フラグファイル（data/kill.flag）による ExecutionEngine 停止指令
  - AlertManager: LINE push による通知（クールダウン機能付き）
  - Streamlit ダッシュボード（read-only で monitoring DB を可視化）
- Portfolio / Strategy 補助
  - 候補選定、重み算出、ポジションサイズ計算、セクター制限、レジーム乗数など
- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC、統計サマリ等の探索的分析
- AI
  - ニュースを LLM（gpt-4o-mini）でスコアリングして ai_scores に書き込み
  - マクロニュース + ETF MA を用いた市場レジーム判定

---

## 前提 / 必要要件
- Python 3.10+
- 必要ライブラリ（一例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- DuckDB に市場データ（prices_daily / raw_financials など）がロードされていること（研究・AI モジュールを使う場合）
- ネットワーク接続（OpenAI API を使う場合）

依存パッケージはプロジェクトが配布する requirements ファイルがあればそれを使う、無ければ手動でインストールしてください。例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests streamlit
# または pip install -r requirements.txt（存在する場合）
```

---

## 設定（環境変数 / .env）
自動的に `.env` と `.env.local` をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

代表的な環境変数（必要に応じて設定）:
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須な箇所がある場合）
- KABU_API_PASSWORD — kabuステーション API パスワード
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector を使う場合）
- KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
- PAPER_FILL_MODE — paper_trading の補完モード: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill flag ファイルパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアするか（"1" でクリア）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知の設定
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

簡易 `.env` 例:
```
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=
LINE_USER_ID=
```

---

## セットアップ手順（要点）
1. Python 環境を準備（3.10+）
2. 依存パッケージをインストール（上記参照）
3. DuckDB ファイル（data/kabusys.duckdb）に prices_daily / raw_financials / raw_news 等のテーブルを用意（研究・AI を使う場合）
4. 必要な環境変数を `.env` / `.env.local` または OS 環境に設定
5. データディレクトリの作成（例: data/）
6. 実行スクリプトを起動（後述）

注: 監視用の SQLite DB（monitoring DB）は起動スクリプトが自動でスキーマを初期化します（init_monitoring_db）。

---

## 使い方（主要コマンド）
プロジェクトをパッケージとしてインストールしているか、ソースツリーのルートで実行してください。

- ExecutionEngine を起動（本番/ペーパートレード切替は KABUSYS_ENV）:
```
# 本番風に起動（例）
KABUSYS_ENV=live python -m kabusys.run_execution

# Paper Trading（Mock Broker + data/paper_trading.db を使用）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- Monitoring（SystemMonitor のポーリングループ）を起動:
```
# デフォルト 60 秒間隔
python -m kabusys.run_monitoring

# ポーリング間隔を上書き（環境変数）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Paper Trading 検証レポート生成:
```
# 基本実行（デフォルト DB: data/paper_trading.db）
python -m kabusys.tools.paper_verification_report

# 期間指定・DB 指定
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db
```
- Streamlit ダッシュボード（監視 DB を参照）:
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- AI 機能（プログラム内呼び出し例）:
  - ニューススコア付け（score_news）は DuckDB 接続と target_date を渡して呼び出します。事前に OPENAI_API_KEY を設定してください。
  - 例（最小イメージ）:
```
import duckdb
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026,4,10), api_key=None)  # api_key None なら env の OPENAI_API_KEY を使う
```

---

## KillSwitch / 停止フラグ
- KillSwitch は条件（主にドローダウンやポジション上限）を満たすと `KILL_FLAG_PATH`（デフォルト: data/kill.flag）に理由を書き込みます。
- ExecutionEngine は起動時や定期的にフラグ/PID を参照し、停止または復旧処理を行います。`KILL_FLAG_CLEAR_ON_START` を "1" にすると起動時に既存の kill.flag を自動で削除します。

---

## 重要な設計・挙動のポイント
- Settings（kabusys.config）は `.env` / `.env.local` を自動で読み込みます（OS 環境変数は保護）。自動ロードは無効化可能。
- Paper Trading は本番 DB と完全に分離して `PAPER_TRADING_SQLITE_PATH` を使います（モード切替により MockBroker を使用）。
- Monitoring の DB 初期化（init_monitoring_db）は冪等で、既存カラムのマイグレーション処理も内包しています。
- OpenAI 呼び出し部分はリトライ・バックオフ・レスポンス検証を行い、失敗時はフェイルセーフ（0 相当の代替値やスキップ）で継続します。

---

## 主要ファイル / ディレクトリ構成
（抜粋、主なモジュールのみ）

- src/kabusys/
  - __init__.py — パッケージ初期化
  - config.py — 環境変数 / 設定読み込みロジック
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity ユーティリティ
  - execution/
    - order_manager.py — 発注フロー（OrderManager）
    - reconciler.py — 起動時リコンシリエーション
    - (その他 broker / order_repository 等)
  - monitoring/
    - monitoring_db.py — SQLite スキーマ + DB 操作用ユーティリティ
    - system_monitor.py, trade_monitor.py, risk_monitor.py — 各種監視ロジック
    - kill_switch.py — 停止フラグ書き込み
    - monitoring_engine.py — 監視コンポーネントを束ねるエンジン
    - alert_manager.py — LINE 通知
    - streamlit_dashboard.py — ダッシュボード
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py — ポートフォリオ構築ロジック
  - research/
    - factor_research.py, feature_exploration.py — ファクター計算・探索
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）
    - regime_detector.py — レジーム判定（OpenAI + ETF MA）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - data/ (想定)
    - monitoring.db (SQLite)
    - paper_trading.db (paper mode)
    - kabusys.duckdb (DuckDB 市場データ)

---

## 開発者向けメモ / 注意点
- Python の型ヒントに |（union）を使用しているため Python 3.10 以上を使用してください。
- DuckDB のスキーマ（prices_daily / raw_financials / raw_news 等）は、研究/AI 機能を使う前提で用意する必要があります。
- OpenAI 絡みの処理は API 呼び出しを含むため、テストではモック化（関数単位の patch）が想定されています（コード内にその旨の記述あり）。
- ログ／アラートの閾値や各種パラメータは Settings（環境変数）や各モジュールの引数で調整できます。

---

もし README に追加してほしい内容（例: 動作確認手順、詳細な開発フロー、例となる .env.example、CI 設定、単体テストの実行方法など）があれば教えてください。必要に応じて追記・整形します。