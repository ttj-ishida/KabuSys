# KabuSys

日本株向けの自動売買 / データパイプライン基盤コンポーネント群です。  
ETL・データ品質チェック・ニュース収集・LLM（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定・リサーチ用ファクタ計算・監査ログ（発注／約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームと研究・運用に必要な機能群を提供します。主に以下をカバーします。

- J-Quants API を用いた株価・財務・カレンダーの差分 ETL（DuckDB 保存、冪等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（銘柄単位のセンチメント）およびマクロセンチメント評価
- ETF の移動平均とマクロセンチメントを合成した市場レジーム判定
- 研究用ファクター計算（Momentum / Value / Volatility 等）と特徴量解析ユーティリティ
- 監査ログスキーマ（signal → order_request → executions）と DB 初期化ユーティリティ
- 設定管理（.env 自動ロード、環境変数経由）

設計上、ルックアヘッドバイアス回避（内部での date.today()/datetime.today() 参照を最小化）や API リトライ／フェイルセーフ、冪等性を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS fetch_rss、記事正規化、SSRF 対策）
  - データ品質チェック（missing / duplicates / spike / date_consistency）
  - 監査ログ（init_audit_db / init_audit_schema）
  - 汎用統計（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュース LLM を合成して market_regime テーブルへ保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - 環境変数 / .env 読み込み、設定値ラッパ（settings）

---

## 必要条件（ざっくり）

- Python 3.10+（typing 表記に Path | None 等を使用）
- 主要ライブラリ（例）
  - duckdb
  - openai (または openai-client が提供する OpenAI クライアント)
  - defusedxml
  - その他標準ライブラリ（urllib, json, datetime, logging 等）

（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトルートへ移動

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - その他依存がある場合は適宜追加

4. 環境変数の設定
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を作成します。
   - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env  
     自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要な環境変数（最低限設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
   - OPENAI_API_KEY : OpenAI API キー（score_news / score_regime に必要）
   - KABU_API_PASSWORD : kabuステーション API 用パスワード（発注系が必要な場合）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : 通知用（オプション、ただし settings は必須扱い）
   - DUCKDB_PATH : DuckDB のファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH : 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV : development|paper_trading|live（デフォルト development）
   - LOG_LEVEL : DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（監査ログを使う場合）
   - 監査用 DB を作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存 DuckDB 接続へ監査スキーマを追加する場合は init_audit_schema(conn)

---

## 使い方（主な API / 実行例）

ここでは簡単なコード例を示します。各関数は DuckDB 接続（duckdb.connect(...) の戻り値）を受け取ります。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続を作る
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- ETL（日次パイプライン）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日（設計上は調整あり）
print(result.to_dict())
```

- 個別 ETL（株価のみ）
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
```

- ニュースセンチメントのスコア付け（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None なら OPENAI_API_KEY を参照
print(f"scored {count} codes")
```

- 市場レジーム判定（ETF 1321 を基準）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究系 (ファクター計算)
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

- ニュース収集（RSS の取得）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

- 監査ログ初期化（既存接続へ）
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 重要な設計注意点 / 動作上のポイント

- 環境変数の自動ロード
  - パッケージ初期化時（kabusys.config モジュール）にプロジェクトルート (.git または pyproject.toml を探索) を基に `.env` / `.env.local` を自動ロードします。
  - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で抑止できます（テスト等で利用）。

- Look-ahead バイアス対策
  - ai モジュールや ETL・研究系は、内部で日付を自動参照して将来データを使わないよう注意して実装されています（target_date 未満のデータを使用、または明示的な target_date 引数を必要とする等）。

- OpenAI 呼び出し
  - gpt-4o-mini を用い、JSON レスポンスモード（response_format）でパースしやすくしています。
  - リトライ (RateLimit / Connection / Timeout / 5xx) やフォールバック（失敗時は中立スコア 0.0）を実装しています。
  - テスト環境では内部の _call_openai_api をモックして API 呼び出しを差し替えられる設計です。

- J-Quants クライアント
  - レート制限（120 req/min）を固定間隔スロットリングで守ります。
  - 401 を受けた場合は refresh token で自動リフレッシュして 1 回だけ再試行します。
  - ページネーション対応・冪等保存（ON CONFLICT DO UPDATE）を行います。

---

## ディレクトリ構成 (主要ファイル)

以下は src/kabusys の主要モジュール一覧（今回のコードベースに基づく）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py (re-export)
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
  - research (exports zscore_normalize from data.stats)
  - (その他 strategy / execution / monitoring パッケージは __all__ に含まれるが、省略されているファイルがある場合もあります)

（実際のリポジトリルートには pyproject.toml / requirements.txt / .env.example 等がある想定です）

---

## トラブルシューティング / よくある質問

- OpenAI のレスポンスが期待通りの JSON にならない場合  
  - モジュール側で余分な前後テキストを除去して復元する処理がありますが、安定動作させるにはモデルの出力フォーマットが重要です。API キー / モデル設定を確認してください。

- J-Quants API が 401 を返す（認証失敗）  
  - `JQUANTS_REFRESH_TOKEN` が正しいか、期限切れでないか確認してください。get_id_token は自動で refresh を行いますが、refresh token 自体が無効な場合は再取得が必要です。

- DuckDB に保存できない / executemany に関するエラー  
  - DuckDB のバージョンによって executemany に空リストを渡せない制約を考慮して実装しています。空のリストで実行しないこと、DB ファイルの正当性、テーブルスキーマを確認してください。

---

## 貢献 / 開発

- テストを行う場合、OpenAI 呼び出し箇所（kabusys.ai.news_nlp._call_openai_api、kabusys.ai.regime_detector._call_openai_api や news_collector._urlopen）をモックして外部 API 依存を排除してください。
- .env.sample（または .env.example）を用意して、必要な環境変数をドキュメント化すると良いです。

---

必要であれば、README に以下を追加で含めます：
- pyproject.toml / requirements.txt の具体的な依存バージョン例
- .env.example のテンプレート
- 実運用（paper/live）時の運用手順（cron/airflow 例）
- Dockerfile / docker-compose のサンプル

追加要望があれば教えてください。