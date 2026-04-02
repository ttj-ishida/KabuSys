# KabuSys

日本株向けの自動データプラットフォーム兼リサーチ / 自動売買補助ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）による銘柄スコアリング、研究用ファクター計算、監査ログ（発注トレース）などの機能を提供します。

Version: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得（レート制限・リトライ・トークン自動更新対応）
- DuckDB を用いたデータ保存と ETL パイプライン（冪等保存、品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価（銘柄別 ai_score、マクロセンチメント）
- 研究用途のファクター計算／特徴量探索ユーティリティ
- 監査ログ（signal → order_request → executions）スキーマ初期化ユーティリティ

設計上、バックテスト時のルックアヘッドバイアスを避ける実装（明示的な target_date を使う等）を重視しています。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants クライアント（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar 等）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - データ保存（DuckDB への冪等保存）
- データ品質チェック
  - 欠損データ、スパイク、重複、日付不整合の検出（quality.run_all_checks）
- ニュース収集・NLP
  - RSS 収集（news_collector.fetch_rss、前処理、SSRF対策）
  - 銘柄別ニュースセンチメント（ai.news_nlp.score_news）
  - マクロセンチメント + MA200 比較による市場レジーム判定（ai.regime_detector.score_regime）
- 研究 / リサーチ
  - ファクター計算（research.factor_research: momentum, value, volatility）
  - 将来リターン・IC 計算・統計サマリー（research.feature_exploration）
  - Zスコア正規化（data.stats.zscore_normalize）
- 監査ログ（トレーサビリティ）
  - 監査スキーマ初期化（data.audit.init_audit_schema / init_audit_db）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `X | Y` や from __future__ annotations を利用）
- DuckDB、OpenAI SDK、defusedxml などが必要です。

推奨インストール（例）
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 開発用にパッケージとしてインストールする場合 (プロジェクトに setup/pyproject がある前提)
# pip install -e .
```

環境変数・設定
- 本パッケージは環境変数またはルートの `.env` / `.env.local` を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
- 必須となる主な環境変数:
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token で ID トークン取得に使用）
  - KABU_API_PASSWORD : kabuステーション等の API パスワード（発注関連で使用）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用（モニタリング等で使用）
  - OPENAI_API_KEY : OpenAI を使う機能（news_nlp / regime_detector）で使用（関数引数で渡すことも可能）
- オプション:
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV （development / paper_trading / live）
  - LOG_LEVEL （DEBUG/INFO/WARNING/ERROR/CRITICAL）

サンプル `.env`（README 用）
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡易クイックスタート）

基本的な操作は Python API から行います。以下は代表的な例です。

1) DuckDB 接続を作り ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定して日次 ETL を実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを算出して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数で設定済みか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n_written} codes")
```

3) 市場レジーム判定（ma200 と マクロニュースの合成）
```python
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events/order_requests/executions テーブル等が作成されます
```

5) J-Quants の ID トークン取得（必要な場面で直接使える）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
```

注意点
- AI モジュール（news_nlp, regime_detector）は OpenAI API を呼びます。API キーや料金に注意してください。
- 各処理はルックアヘッドバイアスを避けるため、明示的な target_date を受け取る実装になっています。内部で date.today() を参照しない設計です（一部ユーティリティは date.today() を使用する箇所あり）。
- DuckDB の executemany に空リストを渡せない制約（バージョン依存）をコード内で考慮しています。

---

## ディレクトリ構成

主要モジュールとファイル構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理（.env 自動読込）
  - ai/
    - __init__.py
    - news_nlp.py          — 銘柄ニュースの AI スコアリング
    - regime_detector.py   — マクロ + MA200 ベースの市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + DuckDB 保存
    - pipeline.py          — ETL パイプライン（run_daily_etl 等）
    - etl.py               — ETL インターフェース再エクスポート
    - news_collector.py    — RSS 収集、前処理、DB 保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計ユーティリティ（z-score）
    - audit.py             — 監査ログ（DDL / 初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py   — モメンタム/バリュー/ボラティリティ算出
    - feature_exploration.py — 将来リターン、IC、統計サマリー
  - research/ ... (その他ユーティリティ)
- pyproject.toml / setup.py 等（存在する場合、パッケージ化情報）

各ファイルには詳細な docstring と設計方針が記載されています。コード内コメントを参照してください。

---

## テスト・開発時のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml ベース）を検出して行います。テストで自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はモック可能に実装されています（ユニットテストでは該当関数を patch して差し替える想定）。
- DuckDB はファイルベースのため、テストには `:memory:` を渡すことでインメモリ DB を利用できます（例: init_audit_db(":memory:")）。

---

## 参照

- 各モジュールの詳細はソースコード内の docstring を参照してください（設計方針やトレードオフ、エラーハンドリング方針などの説明を多数含みます）。
- 環境変数の一覧は `src/kabusys/config.py` を参照してください。

---

もし README に追加したい詳しい使い方（CI、デプロイ手順、発注フロー、Slack 通知設定の詳細など）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。