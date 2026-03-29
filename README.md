# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。本リポジトリは以下の機能を提供します：J-Quants からのデータ ETL、ニュース収集と LLM によるニュースセンチメント解析、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）等。

---

## 主な特徴

- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・マーケットカレンダーを差分取得・保存（DuckDB）
  - レートリミット、リトライ、トークン自動リフレッシュ対応
- ニュース収集 & NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント scoring（JSON Mode、バッチ・リトライ対応）
- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジーム判定
- 研究用分析ツール
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの自動検知
- 監査ログ（Audit）
  - シグナル→発注→約定のトレーサビリティを保持する監査スキーマを提供（DuckDB）

---

## 動作環境（目安）

- Python 3.10+
  - （注）ソースでの型ヒント（A | B 形式）を利用しているため 3.10 以降を想定しています
- 必要ライブラリ（最低限）
  - duckdb
  - openai
  - defusedxml
- その他
  - J-Quants API 利用にはリフレッシュトークン
  - OpenAI API キー（ニュース NLP / レジーム判定で使用）

インストール例:
```bash
python -m pip install duckdb openai defusedxml
# 開発用にパッケージ化されていれば:
# pip install -e .
```

---

## 環境変数（必須/推奨）

このパッケージは .env / .env.local（プロジェクトルート）または環境変数から設定を読み込みます。自動読み込みはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot Token（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector に必要）
- DUCKDB_PATH — DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（モニタリング用）パス（省略時: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（既定: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

.env の読み込み優先順:
- OS 環境変数 > .env.local > .env

---

## セットアップ手順（簡易）

1. リポジトリをクローンして作業ディレクトリへ
2. Python 仮想環境を作成して有効化
3. 依存パッケージをインストール
   - 例: pip install duckdb openai defusedxml
4. プロジェクトルートに `.env`（必要な環境変数）を作成
   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（使用パーツに依存）
5. DuckDB ファイルの親ディレクトリが無ければ作成（`data/` 等）
6. （オプション）監査 DB 初期化などを実行

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトでの利用例です。適宜 logging 設定等を行ってください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（settings.duckdb_path は Path を返す）
conn = duckdb.connect(str(settings.duckdb_path))

# 日次 ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成する（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/kabusys.duckdb"))
# OPENAI_API_KEY を環境変数に設定しておくか、api_key に直接渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" を指定してメモリ DB 可
```

- 監査スキーマを既存接続に初期化
```python
from kabusys.data.audit import init_audit_schema
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

- ニュース RSS 取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI 呼び出しでは API エラー時にフェイルセーフでスコア 0 を採る等の挙動があります。API キーは環境変数 OPENAI_API_KEY、もしくは各関数の api_key 引数で渡してください。
- DuckDB に対する書き込みは多くの関数で BEGIN/COMMIT を用いた冪等性を考慮した実装がされています。

---

## 主なモジュール・関数（抜粋）

- kabusys.config
  - settings: 環境設定アクセス（.jquants_refresh_token など）
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult
- kabusys.data.news_collector
  - fetch_rss, preprocess_text, _make_article_id
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.audit
  - init_audit_schema, init_audit_db
- kabusys.ai.news_nlp
  - score_news
- kabusys.ai.regime_detector
  - score_regime
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートに src/ 配下のパッケージ構成）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - quality.py
    - stats.py
    - calendar_management.py
    - audit.py
    - audit.py
    - etl.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/
  - その他（strategy, execution, monitoring を想定した公開 API）

（README で言及している以外にも細かなサブモジュールが含まれます。上は主要ファイルの抜粋です。）

---

## 開発・運用上の注意

- ルックアヘッドバイアス対策: 多くの処理は target_date を明示して過去データのみを参照する設計です。バックテスト等で date を指定せずに current date を用いると意図しないリークが発生する可能性がありますので注意してください。
- 環境変数自動ロード: パッケージ起動時にプロジェクトルート（.git または pyproject.toml を起点）から .env/.env.local を自動ロードします。テスト時に無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- API 使用量とコスト: OpenAI 呼び出しや J-Quants API 呼び出しは課金対象になるため、実行回数・バッチサイズに注意してください。
- テスト可能性: OpenAI / ネットワーク呼び出し部分は内部で差し替え可能に設計されており、unittest.mock 等でモックしてユニットテストが書きやすくなっています。

---

## 参考・補足

- .env.example を準備して、必要な値（トークンやキー）を記載すると運用が楽になります。
- DuckDB のスキーマ準備（raw_prices, raw_financials, market_calendar, raw_news, ai_scores, market_regime 等）は本 README では省略しています。ETL 実行前にスキーマ定義/マイグレーション手順を用意してください（schema 初期化用ユーティリティが別にある想定）。

---

必要であれば、README に記載する .env.example のテンプレート、DuckDB スキーマ初期化例、cron / Airflow でのジョブ化サンプル、もしくは主要ワークフローの図解を追加で作成します。どれを追加しますか？