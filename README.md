# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリです。J-Quants / kabuステーション / RSS / OpenAI 等と連携し、データのETL、品質チェック、ニュースのAIセンチメント集約、市場レジーム判定、ファクター算出、監査ログ等を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からニュースを収集し raw_news テーブルに保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- 研究用ファクター計算・将来リターン・IC 計算などのリサーチユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローを追跡する監査ログスキーマ（audit）と監査DB初期化ユーティリティ

設計上、バックテスト等でのルックアヘッドバイアスを避けるために日時参照やクエリ条件に配慮した実装がなされています。

---

## 主な機能一覧

- ETL
  - 日次 ETL（run_daily_etl）：カレンダー、株価、財務データの差分取得・保存
  - 個別 ETL ジョブ：run_prices_etl / run_financials_etl / run_calendar_etl
- データ取得・保存
  - J-Quants クライアント（jquants_client）：レート制限・リトライ・トークン自動更新対応
  - raw_prices / raw_financials / market_calendar / stocks などへの冪等保存
- ニュース
  - RSS 収集（news_collector）：URL正規化・SSRF対策・サイズ制限・重複排除
  - ニュース NLP（news_nlp.score_news）：銘柄毎にニュースを集約し OpenAI でセンチメントを算出して ai_scores に書き込み
- AI（OpenAI）
  - 市場レジーム判定（regime_detector.score_regime）：ETF 1321 の MA とマクロニュースセンチメントを合成
- 研究（research パッケージ）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC、統計サマリー、Zスコア正規化等
- 品質管理（data.quality）
  - 欠損・重複・スパイク・日付整合性チェック（run_all_checks）
- 監査・トレーサビリティ（data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- ユーティリティ
  - 汎用統計関数（data.stats.zscore_normalize）
  - 環境設定管理（config.Settings）

---

## 必要条件

- Python 3.10+
- 推奨ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリを取得して仮想環境を作成

```bash
git clone <repo-url>
cd <repo>
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

2. 必要パッケージをインストール（例）

```bash
pip install duckdb openai defusedxml
```

3. 環境変数を設定

プロジェクトルートに `.env` ファイルを置くと、自動で読み込まれます（デフォルト）。テストや CI 等で自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 `.env`:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション
KABU_API_PASSWORD=あなたの_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

環境変数の主要項目は下記「環境変数一覧」を参照してください。

4. DuckDB 初期化（必要に応じて監査DBも作成）

Python REPL やスクリプトで監査スキーマを初期化できます。

例:

```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_schema

conn = duckdb.connect(str(settings.duckdb_path))
# 監査スキーマを作成（トランザクション有）
init_audit_schema(conn, transactional=True)
```

別ファイルに監査DBを切り出す場合:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表例）

- 日次 ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコア付け（OpenAI が必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY は環境変数か api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究用ファクター計算

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026,3,20))
# momentum は dict のリスト
```

- RSS フィード取得（ニュースコレクタの一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src, source="yahoo_finance")
```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合、必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（通知機能）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development, paper_trading, live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動ロードを無効化

注意: config.Settings のプロパティは未設定時に ValueError を投げることがあります（必須項目）。

---

## ディレクトリ構成（抜粋）

（実際のツリーはリポジトリに依存します。以下は src/kabusys 配下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュースセンチメント集計（ai_scores へ）
    - regime_detector.py              # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               # J-Quants API クライアント（fetch/save）
    - pipeline.py                     # ETL パイプラインと run_daily_etl
    - etl.py                          # ETL 型再エクスポート
    - news_collector.py               # RSS 収集・前処理・保存ロジック
    - calendar_management.py          # 市場カレンダー管理／営業日判定
    - stats.py                        # 汎用統計ユーティリティ（z-score）
    - quality.py                      # データ品質チェック
    - audit.py                        # 監査ログ（スキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py              # Momentum/Volatility/Value 計算
    - feature_exploration.py          # 将来リターン / IC / rank / summary
  - research/（補助モジュール）
  - その他：strategy / execution / monitoring 等が __all__ に含まれる想定

---

## 開発メモ・注意点

- Python の union 型（A | B）を使っているため Python 3.10 以上を想定しています。
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用しており、レスポンス検証・リトライを備えています。API エラー時はフェイルセーフ（ゼロスコア等）にフォールバックする設計です。
- J-Quants クライアントはレート制限や 401 自動リフレッシュ、ページネーション対応を備えています。
- DuckDB に対する executemany の挙動（空リスト不可等）に配慮した実装がいくつかあります。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を検出して行われます。CI 等で無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 貢献 / 問い合わせ

- バグや改善要望は issue を作成してください。
- 大きな変更（API 互換性を壊す変更）は事前にディスカッションをお願いします。

---

README は上記を基点に必要に応じてプロジェクト固有のインストール手順やバージョン情報、requirements.txt を追加してください。