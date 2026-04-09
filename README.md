# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）等の機能を提供します。

> パッケージ名: kabusys  
> バージョン: 0.1.0

---

## 主な概要

KabuSys は以下の目的で設計されています。

- J-Quants API を用いた株価・財務・カレンダーの差分取得（レート制限・リトライ・ページネーション対応）
- DuckDB を利用した ETL パイプライン（差分取得、冪等保存、品質チェック）
- ニュース収集（RSS）と LLM（OpenAI）を用いたセンチメント / レジーム判定
- 研究向けファクター計算（モメンタム・ボラティリティ・バリュー等）と統計ユーティリティ
- 発注・約定の監査テーブル初期化（監査ログ、IDトレーサビリティ）
- 自動環境変数ロード（プロジェクトルートの .env / .env.local）

設計上の重要点:
- ルックアヘッドバイアスを避ける（内部で datetime.today() を直接参照しない設計）
- API 呼び出しにはリトライ・バックオフ・フェイルセーフが組み込まれている
- DuckDB を使い、SQL + Python の組合せで高性能に処理

---

## 機能一覧（抜粋）

- data/
  - jquants_client: J-Quants API クライアント（取得 / 保存関数、認証・トークン管理、レートリミット）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management: JPX カレンダーヘルパー（is_trading_day, next_trading_day など）
  - news_collector: RSS 取得・前処理・冪等保存ロジック
  - audit: 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - stats: zscore_normalize などの統計ユーティリティ
- ai/
  - news_nlp.score_news: ニュースをまとめて LLM に投げ、銘柄別 ai_score を ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースセンチメントを合成して market_regime を書き込む
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config:
  - 環境変数読み込み・設定（.env 自動ロード、必須キー取得ユーティリティ settings）

---

## 必要条件（推奨）

- Python 3.10+（型ヒントで union 型の `X | Y` を使用しているため）
- 必要ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging 等）

インストール例（仮）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発時にパッケージとしてインストールできる場合
# pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml があればそれを使用してください）

---

## セットアップ手順

1. 仮想環境作成・有効化
2. 依存パッケージをインストール（上記参照）
3. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に `.env` および（任意で）`.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須/主要な環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）
- KABU_API_PASSWORD : kabu ステーション API のパスワード（必須）
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime に必要）
- （任意）LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DB パス等（デフォルトがあるため省略可）
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)

.env の例:
```env
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-xxxxxxxxxxxx
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

以下は主要なユースケースの呼び出し例です。実行前に必要な環境変数と DuckDB のスキーマ（テーブル）が準備されていることを想定しています。

- DuckDB に接続して日次 ETL を実行する:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの LLM スコアリングを実行（OpenAI API キーが必要）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
print(f"wrote {n_written} scores")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
```

- 監査ログ用 DB を初期化して接続を得る:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等のテーブルが作成されます
```

- RSS を取得して記事データを組み立てる（保存ロジックは news_collector の他関数を利用）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- score_news / score_regime は OpenAI API 呼び出しを行うため、API キー（環境変数 OPENAI_API_KEY または引数）を必ず設定してください。
- ETL は J-Quants API 呼び出しを行うため JQUANTS_REFRESH_TOKEN が必須です。
- DuckDB テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime など）は ETL / 初期化処理で作成される想定ですが、スキーマ初期化用ユーティリティをプロジェクトに用意しておく必要があります（リポジトリに schema 初期化コードがある場合はそちらを参照してください）。

---

## ディレクトリ構成（主要ファイル）

プロジェクト（src/kabusys） の主なファイルと役割:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み、自動 .env ロード、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py        : ニュースの LLM スコアリング（score_news）
    - regime_detector.py : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  : J-Quants API クライアント（fetch_* / save_*）
    - pipeline.py        : ETL パイプライン（run_daily_etl 等）
    - quality.py         : データ品質チェック
    - stats.py           : zscore_normalize 等
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - news_collector.py  : RSS 収集・前処理
    - audit.py           : 監査ログスキーマの作成・初期化
    - etl.py             : ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py : calc_momentum, calc_value, calc_volatility
    - feature_exploration.py : calc_forward_returns, calc_ic, factor_summary, rank
  - research と data モジュールが研究用途とデータ処理を分離

---

## 実運用に関する注意事項

- API レート制限と課金:
  - J-Quants: レート制限に注意（jquants_client は固定間隔スロットリングを実装）
  - OpenAI: 呼び出しコストが発生するため、バッチサイズや頻度を設計で管理してください
- セキュリティ:
  - .env に API キーを保存する場合はファイルのアクセス権を管理してください
  - news_collector には SSRF 対策や XML パースの安全対策（defusedxml）を組み込んでいますが、追加の監査を推奨します
- データの整合性:
  - ETL の品質チェック（quality.run_all_checks）は重要です。ETL 後に検査結果をレビューしてください
- バックテストとの分離:
  - ルックアヘッドバイアスを避けるため、関数群は target_date を引数で受け取り、内部で現在時刻を参照しない設計になっています。バックテスト実行時は注意してください。

---

## 貢献 / 開発

- コーディング規約に従い、ユニットテストと型チェック（mypy 等）を追加することを推奨します。
- 外部 API 呼び出しを行う関数はモック可能（モジュール内で分離された _call_openai_api 等）になっているため、テストの作成が容易です。
- バグや機能追加の提案がある場合は issue を立ててください（リポジトリ運用ルールに従ってください）。

---

必要であれば、この README をベースに
- .env.example の完全テンプレート
- 具体的なスキーマ初期化手順（DuckDB SQL）
- 実運用のデプロイ / cron ジョブ例
などを追記します。どれを追加しますか？