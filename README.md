# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
J-Quants API による市場データ取得、ニュース収集・NLP によるセンチメント評価、ファクター計算、ETL パイプライン、監査ログ（オーダー追跡）など、自動売買システム構築に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能（概要）

- 環境変数・設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（J-Quants / OpenAI / Slack 等）

- データ取得・ETL
  - J-Quants クライアント（株価日足 / 財務 / マーケットカレンダー / 上場銘柄情報）
  - 差分取得・ページネーション・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL パイプライン（run_daily_etl）

- データ品質管理
  - 欠損・スパイク・重複・日付不整合チェック（quality モジュール）
  - 品質チェックの集約（run_all_checks）

- カレンダー管理
  - JPX カレンダーの管理（market_calendar）
  - 営業日判定・前後営業日検索・期間内営業日取得
  - 夜間バッチ更新ジョブ（calendar_update_job）

- ニュース収集・NLP
  - RSS フィード収集（SSRF・サイズ制限・トラッキング除去など堅牢化）
  - raw_news / news_symbols を使った銘柄紐付け
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（news_nlp.score_news）
  - マクロニュース + ETF 1321 の MA200 を統合した市場レジーム判定（ai.regime_detector.score_regime）

- 研究（Research）
  - ファクター計算（モメンタム / バリュー / ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - クロスセクション正規化ユーティリティ（zscore_normalize）

- 監査（Audit / トレーサビリティ）
  - signal_events, order_requests, executions テーブル定義・初期化
  - 監査DB 初期化ユーティリティ（init_audit_db / init_audit_schema）

- 各種ユーティリティ
  - レートリミッタ、レスポンスパース・検証、堅牢なリトライロジック等

---

## 必要要件（依存パッケージ・環境）

最低限の依存パッケージ（実行環境に合わせてバージョン管理してください）:
- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

例（pip）:
```bash
pip install duckdb openai defusedxml
```

注意:
- J-Quants API と OpenAI を使用するため、それぞれの API キー/トークンが必要です。
- ニュース収集ではネットワーク接続が必要です。

---

## セットアップ手順

1. リポジトリをクローン／配置（パッケージは src/ 配置を想定）:
   - 例: git clone <repo>

2. Python 仮想環境を作成・有効化（推奨）:
```bash
python -m venv .venv
source .venv/bin/activate  # macOS / Linux
.venv\Scripts\activate     # Windows
```

3. 依存パッケージをインストール:
```bash
pip install -U pip
pip install duckdb openai defusedxml
```
（プロジェクトに requirements.txt があればそれを使用してください）

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。
   - 必須例（.env）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Kabutステーション API
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 必要なら上書き

# Slack (通知用)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C...

# DB パス（省略可）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development / paper_trading / live
LOG_LEVEL=INFO
```

5. （任意）自動ロードを無効にしたいテスト等:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

---

## 使い方（主な例）

以下は典型的な利用例です。DuckDB 接続は duckdb.connect(...) を使用して渡します。

- 日次 ETL を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアを作成する:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み件数: {n_written}")
```

- 市場レジーム判定を行う:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベースを初期化する:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続になり、監査用テーブルが作成されます
```

- ニュース RSS を取得する（単一ソース）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

注意:
- OpenAI 呼び出しを行う機能（news_nlp, regime_detector）は OPENAI_API_KEY の設定が必要です（関数呼び出し時に api_key 引数で明示的に渡すことも可能）。
- J-Quants 呼び出しは JQUANTS_REFRESH_TOKEN 必須（settings.jquants_refresh_token から取得）。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.env / settings.is_live / settings.is_paper / settings.is_dev
  - settings.duckdb_path / settings.sqlite_path

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, id_token=None, ...)

- kabusys.data.jquants_client
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
  - get_id_token(...)

- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)

- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)

- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)

- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)

- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_value(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_forward_returns(conn, target_date, horizons)
  - calc_ic(...)
  - factor_summary(...)
  - zscore_normalize(...)

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

各モジュールの責務はソース内ドキュメント（docstring）に詳細が記載されています。必要な機能はそれぞれのモジュール API を参照してください。

---

## 運用上の注意点 / 設計方針のまとめ

- Look-ahead bias 回避
  - バックテストやスコア算出において現在時刻参照を避ける設計（関数は target_date を明示的に受け取る）。
- 冪等性
  - DB 保存は基本的に ON CONFLICT DO UPDATE 等で冪等に設計。
- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時は、影響を最小化するためフォールバックやスキップ・警告ログで継続する設計が多く採用されています。
- セキュリティ
  - RSS 取得で SSRF 対策、defusedxml による XML パース保護、レスポンスサイズ制限等を導入。
- レート制限・リトライ
  - J-Quants クライアントは内部でレート制御とリトライ（指数バックオフ）を実装。OpenAI 呼び出しにもリトライロジックがある（AI モジュール内）。

---

## よくある質問（FAQ）

Q: .env は自動で読み込まれますか？  
A: はい。プロジェクトルート（.git または pyproject.toml を基準）を自動検出し `.env` → `.env.local` の順に読み込みます。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI のレスポンスが不安定な場合は？  
A: news_nlp / regime_detector ともに 429・タイムアウト・一部 5xx エラーに対してはリトライ処理を行い、最終的に失敗した場合は警告ログを出して処理をスキップ（ゼロスコア等を使用）します。

Q: ETL が部分的に失敗した場合の挙動は？  
A: run_daily_etl は各ステップを独立して実行し、個別失敗時はエラーメッセージを ETLResult.errors に追加して処理を続行します。部分的な失敗があっても他のデータは可能な限り処理されます。

---

README に記載している使い方や設定は本コードベースの現状設計に基づく簡易ガイドです。個別の運用環境や本番運用要件に合わせて監視・ログ・権限管理・シークレット管理・テストを適切に行ってください。必要であれば、各モジュールの docstring を参照し、追加の利用例やユニットテストを作成することを推奨します。