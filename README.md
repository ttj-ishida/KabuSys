# KabuSys

日本株向けデータプラットフォーム＆自動売買支援ライブラリ

KabuSys は日本株のデータ取得（J-Quants）、ニュース収集・NLP によるセンチメント算出、
ファクター計算、ETL パイプライン、監査ログ（発注トレーサビリティ）等を提供する
Python パッケージ群です。バックテストや自動売買システムの基盤機能を想定しています。

バージョン: 0.1.0

---

## 概要（Project Overview）

このコードベースは以下の主要領域で構成されています。

- data: J-Quants 連携クライアント、ETL パイプライン、マーケットカレンダー、データ品質チェック、ニュース収集、監査ログ（audit）などデータ基盤。
- ai: ニュースの NLP スコアリング（OpenAI）および市場レジーム判定（MA200 + マクロニュースの LLM 評価）。
- research: ファクター計算（モメンタム / バリュー / ボラティリティ等）と特徴量探索（将来リターン、IC、統計サマリ）。
- config: 環境変数の管理（.env 自動読込、必須値チェックなど）。

設計の共通方針として「ルックアヘッドバイアスを避ける」「DuckDB を用いた効率的な SQL 処理」
「外部 API 呼び出しはリトライ/フェイルセーフを実装」「冪等性を重視」などが採用されています。

---

## 機能一覧（Features）

- J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
- DuckDB への冪等的保存（ON CONFLICT DO UPDATE）
- ETL パイプライン（daily ETL: calendar / prices / financials + 品質チェック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- マーケットカレンダー管理（営業日判定、next/prev/get_trading_days）
- ニュース収集（RSS、SSRF 対策、前処理、冪等保存）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント算出、JSON Mode 利用）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成）
- 研究用ユーティリティ（ファクター計算・正規化・将来リターン・IC 等）
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ

---

## 必要条件（Requirements）

- Python 3.10+
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他: 標準ライブラリの urllib などを利用

インストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発としてローカル install
pip install -e .
```

---

## 環境変数（主要なもの）

このプロジェクトは .env ファイルまたは環境変数を参照します。自動ロードは package 起点（.git または pyproject.toml を親階層で探索）で行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行に必要）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション連携用パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

OpenAI 用（AI 機能利用時に必要）:
- OPENAI_API_KEY — OpenAI API キー（関数呼び出しで api_key を渡すことも可能）

データベース等（省略時はデフォルト値を使用）:
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

注意: Settings は必須項目が未設定だと ValueError を投げます。README と併せて `.env.example` を参照して設定してください（リポジトリに同梱されている想定）。

---

## セットアップ手順（Setup）

1. リポジトリをクローン、仮想環境を作成して依存をインストール

```bash
git clone <repo-url>
cd <repo-dir>
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# または開発モードでインストール
pip install -e .
```

2. .env を作成する

リポジトリルートに `.env`（および任意の `.env.local`）を作成し、必要な環境変数を設定します。例:

```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxxx
KABU_API_PASSWORD=your_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
```

自動読み込みが動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。

3. データディレクトリの作成

デフォルトパス（例: data/）を作成しておきます。

```bash
mkdir -p data
```

4. 監査 DB 初期化（任意）

監査ログ用 DB を初期化する例:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection
```

---

## 使い方（Usage）

以下は主要ユースケースの簡単なサンプル。

- DuckDB 接続を作る（デフォルトファイルを使用）

```python
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
```

- 日次 ETL 実行（データ取得・保存・品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（AI による銘柄別スコアを ai_scores に書き込む）

```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を直接渡すか、環境変数 OPENAI_API_KEY を設定
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
print("scored:", n_written)
```

- 市場レジーム判定（MA200 + マクロセンチメント）

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 研究用ファクター計算

```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
```

- 監査スキーマ初期化（既存 DB にテーブルを追加）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- RSS フィード取得（ニュース収集）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

url = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(url, source="yahoo_finance")
```

注意点:
- AI によるスコアリング機能は OpenAI API を呼ぶため、API キーの設定とコスト管理に注意してください。
- ETL / API 呼び出しは外部サービス（J-Quants 等）へのリクエストが発生します。API レートや認証設定を事前に確認してください。

---

## ディレクトリ構成（Directory Structure）

主要なファイル・モジュール構成（抜粋）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ ai/
   │  ├─ __init__.py
   │  ├─ news_nlp.py
   │  └─ regime_detector.py
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py
   │  ├─ pipeline.py
   │  ├─ etl.py
   │  ├─ stats.py
   │  ├─ quality.py
   │  ├─ calendar_management.py
   │  ├─ news_collector.py
   │  └─ audit.py
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ (その他: strategy, execution, monitoring 等の名前空間が想定)
```

各モジュールの役割は前節の「機能一覧」を参照してください。

---

## 実運用上の注意（Operational Notes）

- 環境変数管理: `.env` 自動ロードはプロジェクトルート検出に依存します。CI やコンテナで明示的に環境変数を設定することを推奨します。
- OpenAI 呼び出し: レスポンスのパース失敗や API 障害はフェイルセーフ（スコア = 0 等）で扱う設計です。ただし運用では失敗ログを監視してください。
- J-Quants API: レート制限（120 req/min）を守る実装が組み込まれていますが、アカウントごとのルールや利用制限は事前確認してください。
- DuckDB: 一部実装は DuckDB のバージョン差異に依存する記述（executemany の空リストなど）があります。使用する DuckDB の推奨バージョンで動作確認してください。
- 監査ログ: 監査テーブルは削除せず追記前提です。バックアップや retention ポリシーを運用で決めてください。

---

## 開発・テスト（Development）

- 単体テストを追加する場合、OpenAI の呼び出しやネットワーク I/O はモックして実行してください（コード内でも unittest.mock で差し替え可能な箇所を想定しています）。
- .env 自動読込を抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するか、Settings を直接操作してテストを行ってください。

---

この README はコードベースの主要点をまとめたものです。細かい API 使用方法や設定例は各モジュールの docstring（モジュール先頭の説明）を参照してください。必要であればサンプルスクリプトや運用手順のテンプレートを別途用意します。