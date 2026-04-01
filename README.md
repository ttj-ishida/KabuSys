# KabuSys

日本株向けのデータプラットフォーム兼自動売買（バックテスト／研究／本番運用）基盤の一部実装です。ETL、ニュース収集・NLP、ファクター計算、マーケットカレンダー管理、監査ログなど、取引システムに必要な基盤機能をモジュール化して提供します。

---

## 概要

KabuSys は以下のような目的で設計されたライブラリ群です。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS によるニュース収集と OpenAI を使った銘柄センチメント（ai_scores）生成
- 市場レジーム判定（ETF MA とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）テーブル定義・初期化
- J-Quants クライアント（レート制限・リトライ・トークン自動リフレッシュ対応）

設計上の特徴:
- ルックアヘッドバイアスを避ける（date 引数ベースで処理）
- DuckDB を中心に SQL と純 Python を組み合わせた実装
- OpenAI 呼び出しは安全策（リトライ・タイムアウト・JSON バリデーション）を組み込み
- 各 ETL / チェックはフェイルセーフで部分失敗でも残り処理を継続

---

## 機能一覧

主な公開 API / 機能（抜粋）

- 設定管理
  - kabusys.config.settings（.env 自動読み込み、必須環境変数チェック）

- データ ETL / クライアント
  - kabusys.data.jquants_client
    - fetch_daily_quotes / save_daily_quotes
    - fetch_financial_statements / save_financial_statements
    - fetch_market_calendar / save_market_calendar
    - get_id_token（リフレッシュトークン→id_token）
  - kabusys.data.pipeline
    - run_daily_etl（カレンダー→株価→財務→品質チェック の一括実行）
    - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL）
    - ETLResult（実行結果のデータクラス）

- ニュース収集・NLP
  - kabusys.data.news_collector.fetch_rss（RSS 取得・前処理）
  - kabusys.ai.news_nlp.score_news（銘柄ごとのニュースセンチメントを ai_scores に書き込み）
  - kabusys.ai.regime_detector.score_regime（市場レジーム判定を market_regime に書き込み）

- データ品質
  - kabusys.data.quality.run_all_checks（欠損・重複・スパイク・日付整合性チェック）
  - 個別チェック: check_missing_data, check_duplicates, check_spike, check_date_consistency

- カレンダー管理
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（J-Quants から差分取得して保存）

- 監査ログ
  - kabusys.data.audit.init_audit_db / init_audit_schema（監査用テーブルの作成・初期化）

- 研究ユーティリティ
  - kabusys.research.factor_research: calc_momentum, calc_value, calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.data.stats.zscore_normalize

---

## セットアップ手順

※ 以下はリポジトリルートに package がある前提の一般的な導入手順です。

1. Python 環境
   - 推奨 Python: 3.10+（typing の記法等に合わせてください）

2. 依存パッケージのインストール（例）
   - 必須: duckdb, openai, defusedxml
   - pip 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用: pytest 等を追加でインストールしてください

   > 補足: プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください。

3. パッケージのインストール（開発モード）
   ```
   pip install -e .
   ```

4. 環境変数の準備
   - リポジトリルートに .env を配置（kabusys.config は自動でルートの .env / .env.local をロードします）
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN=（必須：J-Quants リフレッシュトークン）
     - OPENAI_API_KEY=（必須：OpenAI API キー。score_news/score_regime に使用）
     - KABU_API_PASSWORD=（kabu ステーション API 用パスワード）
     - KABU_API_BASE_URL=（任意。デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN=（Slack 通知用）
     - SLACK_CHANNEL_ID=（Slack 通知用）
     - DUCKDB_PATH=data/kabusys.duckdb（DuckDB ファイルパス）
     - SQLITE_PATH=data/monitoring.db（監視 DB）
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 使い方（例）

以下は基本的な利用例です。実行環境で settings が .env から読み込まれていることを前提とします。

1. DuckDB 接続を開く
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 監査ログ用 DB を初期化
```python
from kabusys.data.audit import init_audit_db

# settings.duckdb_path を監査用 DB として使うか、別ファイルを指定
audit_conn = init_audit_db(settings.duckdb_path)  # returns duckdb connection
```

3. 日次 ETL を実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

4. ニュースをスコアリング（OpenAI）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

5. 市場レジームスコアを算出
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, date(2026, 3, 20), api_key=None)
```

6. データ品質チェックを実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

7. RSS を取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意事項:
- OpenAI 呼び出しはコストが発生するため、テスト時は api_key を与えない・モックするか、内部の _call_openai_api を unittest.mock で差し替えてください（score_news / regime_detector の実装でテスト用フックを想定）。
- J-Quants API は rate limit と認証トークンの取り扱いに注意してください。kabusys.data.jquants_client は自動リフレッシュとレート制御を持ちます。

---

## よく使う環境変数（.env 例）

.env の雛形（必要に応じて .env.local を作成して上書き）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション
KABU_API_PASSWORD=your_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（概要）

以下は主要モジュールの構成です（src/kabusys 以下）。

- kabusys/
  - __init__.py
  - config.py                      - 環境変数・設定管理（.env 自動読み込み等）
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP（gpt-4o-mini を用いた銘柄センチメント）
    - regime_detector.py            - 市場レジーム判定（ETF MA + マクロニュース LLM）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント＆ DuckDB 保存関数
    - pipeline.py                   - ETL パイプライン (run_daily_etl 等)
    - etl.py                        - ETL インターフェース再エクスポート（ETLResult）
    - news_collector.py             - RSS 取得・前処理
    - calendar_management.py        - 市場カレンダー管理・営業日ユーティリティ
    - quality.py                    - データ品質チェック
    - stats.py                      - 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                      - 監査ログ（DDL・初期化）
  - research/
    - __init__.py
    - factor_research.py            - ファクター計算（momentum/value/volatility）
    - feature_exploration.py        - 将来リターン・IC・統計サマリー等
  - (strategy/, execution/, monitoring/ ...)
    - パッケージの __all__ に含めているが、実装や利用はプロジェクト固有。  

（ファイル・関数の詳細はソース内の docstring を参照してください）

---

## テスト・開発上の注意

- データベース（DuckDB）の実体を汚したくないテストでは ":memory:" を使うことができます（init_audit_db(":memory:") 等）。
- OpenAI 呼び出し回りは外部ネットワークとコストが発生するため、ユニットテストでは _call_openai_api をモックする設計になっています。
- kabusys.config は実行時にリポジトリルートの .env を自動読み込みします。CI 等で意図せず読み込ませたくない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB のバージョンや SQL の互換性に注意して下さい（プロジェクト内で DuckDB の特性に依存した実装が含まれます）。

---

## ライセンス / 貢献

- この README はコードベースの説明を目的としています。実際のリポジトリの LICENSE を確認してください。
- バグ報告や改善提案は issue / Pull Request で歓迎します。変更の際は既存の設計方針（ルックアヘッドバイアス回避、フェイルセーフ）を尊重してください。

---

必要に応じて README に追記できます。例: 実行スクリプト/CLI の使い方、cron / Airflow での運用例、Slack 通知の設定手順など。どの部分を詳しく追記したいか教えてください。