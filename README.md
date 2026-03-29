# KabuSys

日本株自動売買システムのライブラリ（パッケージ）。データ取得（J‑Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ等のユーティリティを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチプラットフォーム向けの共通モジュール群です。主に以下を提供します。

- J‑Quants API 連携（株価・財務・カレンダー取得、保存）
- DuckDB を用いたローカルデータ保存／ETL パイプライン
- ニュース収集（RSS）とニュースの前処理
- OpenAI によるニュースセンチメント（銘柄別）スコアリング
- 市場レジーム判定（ETF の MA 乖離 + マクロ記事の LLM センチメント合成）
- データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ等）
- 監査ログスキーマ（signal → order_request → execution のトレース）
- 環境変数管理（.env 自動読み込み、保護機能）

設計上の特徴：
- ルックアヘッドバイアスを避けるため datetime.today()/date.today() を不用意に参照しない実装。
- API 呼び出しはリトライ・バックオフ・レート制御あり。
- DuckDB へは冪等保存パターン（ON CONFLICT）でデータ整合性を担保。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）・必須設定取得ヘルパ
- kabusys.data
  - jquants_client: J‑Quants API 呼び出し／保存（rate limit・リトライ・トークン自動更新）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・raw_news への保存支援
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログテーブル定義・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で算出して ai_scores に書き込み
  - regime_detector.score_regime: ETF 200日MA 乖離とマクロニュースの LLM スコアを合成して market_regime に保存
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `X | None` を使用）
- ネットワークアクセス（J‑Quants / OpenAI / RSS ソース）

1. リポジトリをクローン / パッケージを配置
   - 例: git clone ...（実際のリポジトリ URL に合わせてください）

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  または  .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 必要に応じて他のライブラリを追加してください（標準ライブラリ中心に実装されていますが、OpenAI SDK と DuckDB は必須）

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を配置すると、自動的に読み込まれます（起動時）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

推奨の .env（必須項目）
- JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token_
- KABU_API_PASSWORD=kabuステーションAPI パスワード
- SLACK_BOT_TOKEN=Slack ボットトークン
- SLACK_CHANNEL_ID=通知先チャンネルID
- OPENAI_API_KEY=OpenAI API キー（AI 関連機能を使う場合）
オプション
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- KABUSYS_ENV（development / paper_trading / live、デフォルト development）
- LOG_LEVEL（DEBUG/INFO/...）

注意: Settings クラスは必須環境変数が未設定だと ValueError を投げます。

---

## 使い方（サンプル）

以下は主要なユースケースの簡単な利用例（Python スクリプトからの呼び出し例）。

- DuckDB に接続して日次 ETL 実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI によるニューススコア算出（ai.news_nlp.score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
print(f"scored {count} symbols")
```

- 市場レジーム判定（ai.regime_detector.score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# SQL 実行やアプリ側で監査ログを書き込む
```

- ニュース RSS を取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

- リサーチ用ファクター計算
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

※ 実運用では OpenAI / J‑Quants の API キーやトークンを環境変数で管理することを推奨します。

---

## 設定（環境変数の一覧・意味）

主要な環境変数（settings により参照されるもの）
- JQUANTS_REFRESH_TOKEN (必須) : J‑Quants のリフレッシュトークン（get_id_token で id_token を取得）
- KABU_API_PASSWORD (必須) : kabu ステーション API のパスワード
- KABU_API_BASE_URL (任意) : kabu ステーションのベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) : Slack チャンネル ID
- DUCKDB_PATH (任意) : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH (任意) : 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV (任意) : 実行環境（development, paper_trading, live）
- LOG_LEVEL (任意) : ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY (必要に応じて) : OpenAI 呼び出しで使用（ai モジュール）

自動 .env 読み込みの挙動:
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に `.env` と `.env.local` を順に読み込みます。
- OS 環境変数が優先されます。.env.local は .env の上書きに使われます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（ユニットテスト等で有用）。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys）

- __init__.py
- config.py
  - 環境変数ロード・Settings クラス
- ai/
  - __init__.py
  - news_nlp.py         — 銘柄別ニュースセンチメント (score_news)
  - regime_detector.py  — 市場レジーム判定 (score_regime)
- data/
  - __init__.py
  - jquants_client.py   — J‑Quants API クライアント（取得＋保存）
  - pipeline.py         — ETL パイプライン（run_daily_etl 他）
  - etl.py              — ETLResult の再エクスポート
  - news_collector.py   — RSS 取得・前処理
  - quality.py          — データ品質チェック
  - calendar_management.py — 市場カレンダーの管理・営業日判定
  - audit.py            — 監査ログスキーマ初期化
  - stats.py            — zscore_normalize 等
- research/
  - __init__.py
  - factor_research.py  — モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py — 将来リターン／IC／統計サマリー
- その他ユーティリティ・テスト用モックは modules 内に分散

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取り、SQL と Python を組み合わせて効率的に処理を行う設計です。

---

## 実行上の注意点 / ベストプラクティス

- OpenAI / J‑Quants API 呼び出しには課金・レート制限が伴います。開発時はテスト用キーやモックを使ってください。
- ETL や AI の処理は外部 API に依存するためネットワーク障害に対するロバストネスを考慮してください（本ライブラリはリトライ・フォールバックを備えていますが、運用側でも監視を推奨します）。
- DuckDB への書き込みは基本的に冪等化されていますが、バックアップ・監査を運用で確保してください。
- ニュース収集は RSS の仕様差分やソース側の変更によりパース失敗が起きることがあります。fetch_rss は XML パースエラー等をログ出力して空リストを返す実装です。
- ユニットテストでは OpenAI/J‑Quants 呼び出しポイントをモックする設計になっています（各モジュールの _call_openai_api 等を patch）。

---

## 開発 / 貢献

- 型注釈・ロギングに配慮した実装です。新機能追加時は既存の設計原則（ルックアヘッド防止、冪等性、トークン管理、リトライ）を踏襲してください。
- テストは外部 API 呼び出しをモックして実行することを推奨します。ai モジュールや jquants_client の HTTP 層は差し替えやすく作られています。

---

必要に応じて README の補足（API の詳細、.env.example、スキーマ定義、使用例スクリプト）を追加できます。どの部分を詳しくしたいか教えてください。