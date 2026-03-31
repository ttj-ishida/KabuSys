# KabuSys

日本株向けのデータプラットフォーム / 研究・自動売買基盤のコアライブラリです。  
DuckDB をデータレイヤに用い、J-Quants / RSS / OpenAI（LLM）等と連携してデータ収集・ETL・データ品質チェック・AI ニュース分析・ファクター計算・監査ログを提供します。

現在のバージョン: 0.1.0

---

## 特徴（概要）

- データ収集（J-Quants API）：株価（日足）、財務データ、JPX カレンダー取得（差分・ページネ―ション・レート制御・自動リフレッシュ）
- ETL パイプライン：差分更新、バックフィル、品質チェックを組み合わせた日次 ETL（冪等保存）
- ニュース収集：安全対策（SSRF/サイズ制限/トラッキング除去）付き RSS 収集と冪等保存
- AI ニュース分析：OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント算出（バッチ・リトライ・レスポンス検証）
- 市場レジーム判定：ETF 1321 の MA とマクロニュースの LLM センチメントを合成して日次レジーム判定
- 研究用ユーティリティ：モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン・IC・統計サマリー
- データ品質チェック：欠損、重複、スパイク、日付不整合の検出
- 監査ログ：シグナル→発注→約定までのトレーサビリティ用テーブル定義と初期化ユーティリティ
- Look-ahead バイアス対策やログ、トランザクション保護など運用上の堅牢性に配慮

---

## 主要機能一覧

- kabusys.config.Settings: 環境変数管理（.env 自動読み込み機構を内蔵）
- kabusys.data.jquants_client:
  - fetch_daily_quotes / save_daily_quotes
  - fetch_financial_statements / save_financial_statements
  - fetch_market_calendar / save_market_calendar
  - fetch_listed_info、get_id_token 等
- kabusys.data.pipeline:
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult（実行結果）
- kabusys.data.news_collector:
  - fetch_rss, preprocess_text など（RSS 収集・整形・保存用ユーティリティ）
- kabusys.data.quality:
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.data.calendar_management:
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
- kabusys.data.audit:
  - init_audit_schema, init_audit_db（監査ログ用テーブルの初期化）
- kabusys.ai.news_nlp:
  - score_news（銘柄別ニュースセンチメントを ai_scores に書き込む）
- kabusys.ai.regime_detector:
  - score_regime（市場レジームを market_regime に書き込む）
- kabusys.research:
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats:
  - zscore_normalize（クロスセクション Z スコア正規化）

---

## セットアップ手順

前提
- Python 3.10+（type | None 注釈があるため少なくとも 3.10 以上推奨）
- DuckDB を用いるためネイティブ拡張をビルドせず pip でインストール可能

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使ってください）

4. 環境変数 / .env の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` / `.env.local` を置くと自動的に読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（利用する機能に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN （J-Quants 認証リフレッシュトークン）
   - KABU_API_PASSWORD （kabuステーション API パスワード）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID （Slack 通知を使う場合）
   - OPENAI_API_KEY （AI 関連機能を使う場合、score_news / score_regime は引数で渡すことも可能）
   - DUCKDB_PATH（省略可、デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視系 SQLite: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL（DEBUG / INFO / ...、デフォルト INFO）

   例 .env（一部）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

---

## 使い方（基本例）

以下は最も基本的な例を示します。DuckDB 接続を作成し、ETL や AI スコア関数を呼び出す流れです。

- DuckDB 接続と ETL の実行例
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング（api_key を明示的に渡す例）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n_written} symbols")
```

- 市場レジーム評価
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- ファクター計算（研究用）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
```

- RSS 収集例
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
# 取得した記事は raw_news テーブルへ保存するロジックと組み合わせてください
```

注意点:
- AI 呼び出し（OpenAI）は外部 API 呼び出しのため、API キーは env または関数引数で必ず指定してください。関数内部で失敗時は安全措置（ゼロフォールバックやスキップ）を取る設計です。
- 多くの保存系関数は冪等で、ON CONFLICT DO UPDATE を使用しているため再実行可能です。
- 自動 .env 読み込みはプロジェクトルート検出に .git または pyproject.toml を使います。テストで無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

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
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

各モジュールの役割（抜粋）
- config.py: 環境変数の読み込み・設定値アクセスラッパー
- data/jquants_client.py: J-Quants API クライアント + DuckDB 保存ロジック
- data/pipeline.py: 日次 ETL のオーケストレーション
- data/news_collector.py: RSS の安全な取得と前処理
- data/quality.py: データ品質チェック群
- data/calendar_management.py: 市場カレンダーの判定・更新ロジック
- data/audit.py: 監査ログスキーマの初期化ユーティリティ
- ai/news_nlp.py: 銘柄ごとのニュースセンチメント算出
- ai/regime_detector.py: マクロ＋テクニカルで市場レジーム判定
- research/*: ファクター計算・特徴量探索ユーティリティ

---

## 運用上の注意 / 設計上のコメント

- Look-ahead バイアス対策: 多くの関数は内部で date.today() を直接参照せず、外部から target_date を受け取る設計です。
- 冪等性: ETL / 保存処理は ON CONFLICT DO UPDATE や個別 DELETE→INSERT の方針で冪等性を確保しています。
- API リトライ & レート制御: J-Quants は固定間隔レートリミッタ、OpenAI はリトライ／バックオフ処理を備えています。
- セキュリティ: news_collector で SSRF / XML 攻撃対策（リダイレクト検証・defusedxml・サイズ上限など）を実装しています。
- テスト: 外部 API 呼び出しは差し替え可能（モック）に設計されている箇所が多く、ユニットテストでの差し替えが容易です。

---

README に書かれている以外の細かな使い方や API の引数仕様は、各モジュールの docstring を参照してください。質問や補足の要望があれば具体的なユースケース（例: ETL スケジュール設定、OpenAI のレスポンス検証、DuckDB のスキーマ初期化手順 等）を教えてください。必要に応じてサンプルコードや運用ガイドを追加します。