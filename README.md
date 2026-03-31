# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は日本株の自動売買基盤および研究基盤向けに設計されたモジュール群です。主な役割は次の通りです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB によるデータ保存（冪等保存 / ON CONFLICT）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント解析（銘柄別）およびマクロセンチメントを用いた市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索（IC 等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログスキーマ（signal → order_request → execution の追跡）
- 環境変数 / .env の取り扱いユーティリティ（自動ロード機能）

設計方針として「ルックアヘッドバイアスを防ぐ」「ETL/品質チェックで部分失敗を許容して情報を返す」「外部 API はレートリミット遵守・リトライ実装」などが徹底されています。

---

## 機能一覧

主な機能（モジュール・主要 API）

- kabusys.config
  - .env 自動読み込み（OS > .env.local > .env、プロジェクトルート自動検出）
  - Settings: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等のアクセス
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - id_token 管理、レートリミット、リトライ、JSON デコード検査
- kabusys.data.pipeline
  - run_daily_etl: カレンダー / 株価 / 財務 の差分 ETL + 品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult（処理結果の dataclass）
- kabusys.data.news_collector
  - fetch_rss: RSS 取得（SSRF 対策、gzip 上限検査、URL 正規化、記事 ID 生成）
  - preprocess_text 等の前処理ユーティリティ
- kabusys.ai.news_nlp
  - score_news: 銘柄ごとにニュースを集約し OpenAI でセンチメントを算出して ai_scores テーブルへ書込
- kabusys.ai.regime_detector
  - score_regime: ETF 1321 の MA200 乖離とマクロセンチメントを合成して market_regime に保存
- kabusys.research
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量解析・統計）
- kabusys.data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査ログテーブル・インデックスの初期化）

その他、統計ユーティリティ（zscore_normalize）やマーケットカレンダー管理、ニュースウィンドウ計算などの補助関数を多数提供します。

---

## セットアップ手順

想定: Python 3.10+（PEP 604 の型記法を利用しているため）を使用します。

1. リポジトリをクローン / 取得
   - プロジェクトルートに `pyproject.toml` または `.git` があることを前提に自動 .env ロードが動作します。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   必要な主要パッケージ例（プロジェクトの配布設定があればそちらを利用してください）:
   - duckdb
   - openai
   - defusedxml

   例:
   - pip install duckdb openai defusedxml

4. 開発インストール（プロジェクトに setup/pyproject があれば）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに `.env` および `.env.local`（ローカル上書き用）を置けます。
   - 自動ロードは OS 環境変数が優先され、`.env.local` が `.env` より優先されます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（または推奨）環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API（kabu-station）パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須、Slack 通知を使う場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須、Slack 通知を使う場合）
- OPENAI_API_KEY — OpenAI API キー（score_news/score_regime を使う場合）
- KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...; デフォルト: INFO)
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用など、デフォルト: data/monitoring.db）

例 .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（基本例）

※ 下記はライブラリ API を直接呼ぶ簡単な例です。実運用ではログやエラー処理、認証トークンの適切な管理を行ってください。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュースセンチメントのスコアリング（OpenAI 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を None にすると環境変数 OPENAI_API_KEY を使用します
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn が初期化済みの接続
```

5) ファクター計算・リサーチ例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# zscore_normalize を使って正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点
- OpenAI 呼び出しはリトライを実装していますが、API キーが設定されていないと ValueError を投げます。
- J-Quants クライアントはレート制限（120 req/min）を守るためスロットリングを入れています。
- ETL やスコアリングはルックアヘッドバイアスを避ける設計（target_date より前のデータのみ参照）になっています。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数 / .env ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメント（銘柄別）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL のエントリポイントと helper（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS ニュース収集 / 前処理
  - calendar_management.py — マーケットカレンダー管理 / is_trading_day 等
  - stats.py — zscore_normalize 等
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py — 監査ログスキーマと初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ計算
  - feature_exploration.py — forward returns / IC / rank / summary

（上記は主要ファイルの抜粋です。詳細は各モジュールの docstring を参照してください。）

---

## 動作モードとログ

- KABUSYS_ENV: "development" / "paper_trading" / "live"
  - settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL: "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"
- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml を起点）から `.env` / `.env.local` を読み込み
  - 優先順位: OS 環境 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化

---

## トラブルシューティング

- OpenAI レスポンスのパースに失敗した場合、モジュールはフェイルセーフとしてスコアを 0.0 にフォールバックし、警告ログを出力します（score_news / score_regime）。
- J-Quants API 呼び出しはリトライ・トークンリフレッシュを行います。頻繁に 401 / 429 / 5xx が発生する場合は環境変数のトークンやレート制限設定を確認してください。
- DuckDB の executemany が空のリストを受け付けないバージョン制約を考慮した実装がされていますが、古い/新しい DuckDB 互換性で問題が出る場合はバージョンを揃えてください。
- RSS フェッチで「プライベートホスト」判定によりブロックされる場合は URL が内部アドレスにリダイレクトされていないか確認してください。

---

## 参考 / 開発時の注意

- 多くの機能が外部 API（J-Quants / OpenAI / RSS）に依存します。テスト時は各モジュールの外部呼び出し関数をモックする設計になっています（例: news_nlp._call_openai_api の差し替え）。
- DB スキーマ（raw_prices, raw_financials, ai_scores, market_regime, market_calendar, news_symbols 等）は ETL / save_* 関数や audit.init_audit_schema の DDL と合わせて事前に準備してください。
- セキュリティ: RSS の取得は SSRF 対策・Content-Length 上限・gzip 解凍上限を備えていますが、運用環境でのネットワークポリシーも検討してください。

---

必要であれば、README に含める具体的な .env.example、SQL スキーマ定義、CI ワークフローや運用ガイド（運用スケジュール / cron / Airflow 例）などを追加で作成します。どの情報を優先して追加しますか？