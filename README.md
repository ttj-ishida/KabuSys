# KabuSys

日本株のデータ取得・前処理・研究・AIスコアリング・監査ログを備えた自動売買／データプラットフォームのライブラリ群です。DuckDB を中心にローカルDBでデータを管理し、J-Quants / RSS / OpenAI 等と連携して ETL、ニュースセンチメント、レジーム判定、ファクター計算などを提供します。

---

## 主な特徴

- J-Quants API を用いた差分取得（株価・財務・上場銘柄・取引カレンダー）と DuckDB への冪等保存
- ETL パイプライン（差分取得、バックフィル、品質チェック一括実行）
- ニュース収集（RSS）と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）およびマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ユーティリティ（モメンタム、バリュー、ボラティリティ／流動性ファクター、将来リターン、IC、Zスコア正規化 等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ

---

## 要求環境

- Python 3.10+
- 依存主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージをプロジェクトとしてインストール（開発中）
   ```
   pip install -e .
   ```
   （プロジェクトルートに pyproject.toml / setup.py がある想定）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 主な環境変数

必須・よく使う設定例：

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token に使用）
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime で使用。関数呼出し時に引数で渡すことも可能）
- kabuステーション API（発注等）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE 通知
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- データベースパス（デフォルト値）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- 監視関連
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
- 実行環境
  - KABUSYS_ENV: development | paper_trading | live (デフォルト development)
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定は kabusys.config.settings で取得できます（例: settings.jquants_refresh_token）。

---

## 使い方（例）

以下はライブラリの代表的な使い方サンプルです。実行には DuckDB のスキーマ準備や必要なテーブル作成が前提になる場合があります（ETL は保存先テーブルを想定）。

基本的な DuckDB 接続例：
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（AI）でスコアリング
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か、api_key 引数で指定
num_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", num_written)
```

3) 市場レジーム判定（ETF 1321 の ma200 とマクロニュースを合成）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

res = score_regime(conn, target_date=date(2026, 3, 20))
print("score_regime result:", res)
```

4) 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

5) 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# init_audit_db は UTC タイムゾーン設定等を行い、監査テーブルを作成します
```

6) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["title"], a["datetime"])
```

---

## 主要モジュール一覧（API 要約）

- kabusys.config
  - settings: 環境変数経由の設定取得（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）

- kabusys.data
  - jquants_client: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar、save_* 系（DuckDB への保存）
  - pipeline: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl、ETLResult
  - news_collector: fetch_rss, preprocess_text 等
  - quality: データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - stats: zscore_normalize
  - calendar_management: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - audit: init_audit_schema / init_audit_db

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - utils: zscore_normalize (data.stats)

---

## ディレクトリ構成

（リポジトリの主要ファイルを抜粋）

- src/
  - kabusys/
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
      - etl.py
      - (その他: audit/schema 初期化など)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他)
    - research/
    - monitoring/ (パッケージ表記あり — モニタリング関連が入る想定)
    - execution/ (発注・実行関連が入る想定)
    - strategy/ (戦略ロジックが入る想定)
    - data/ (上記)

（上記はコード抜粋に基づく主要モジュール配置です）

---

## 注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策: バックテストやスコアリング関数は内部で datetime.today() を直接参照しない設計を心がけています。関数呼び出し側で target_date を明示してください。
- 冪等性: ETL と保存処理は可能な限り ON CONFLICT / INSERT ... DO UPDATE 等で冪等に実装されています。
- フェイルセーフ: 外部 API（OpenAI / J-Quants）で発生する一時エラーはリトライやフォールバック（ゼロスコア等）で影響を小さくする設計です。
- セキュリティ: RSS 収集は SSRF 対策、XML の安全パース（defusedxml）等を実施しています。

---

## 貢献・ライセンス

本リポジトリに対する修正・改善提案は Issue / Pull Request を通じて受け付けます。ライセンス情報はプロジェクトルートの LICENSE を参照してください（ここでは明示されていません）。

---

README は上記のサンプル利用法・設計方針をカバーしています。より詳細な使用法やテーブルスキーマ、外部 API キーの取得手順（J-Quants / OpenAI 等）はプロジェクトのドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README に含めるサンプルや手順を追加します。