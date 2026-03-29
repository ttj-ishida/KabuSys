# KabuSys

KabuSys は日本株のデータプラットフォームと研究・自動売買の基盤となるライブラリです。  
DuckDB をデータレイクとして用い、J-Quants API や RSS などからデータを取得して ETL → 品質チェック → 解析 → AI（OpenAI）を用いたニュースセンチメントや市場レジーム判定までをサポートします。

バージョン: 0.1.0

---

## 主要な用途（概要）

- J-Quants API から株価・財務・カレンダー情報を取得して DuckDB に保存（差分取得・冪等保存）
- RSS からニュース収集（SSRF 対策・トラッキング除去）し raw_news に格納、銘柄紐付け
- ニュースを OpenAI（gpt-4o-mini）でスコアリングして銘柄別 ai_scores を生成
- マクロニュース＋ETF（1321）の MA200 乖離を合成して市場レジーム判定（bull/neutral/bear）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ）および特徴量探索（将来リターン、IC、統計サマリー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution）のスキーマ作成と初期化ユーティリティ

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須設定の取得と検証（Settings クラス）

- データ取得・ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
  - J-Quants クライアント（トークン自動リフレッシュ、レートリミット、リトライ）

- ニュース収集
  - RSS 取得（SSRF 対策、gzip 対応、トラッキング除去）
  - raw_news / news_symbols への冪等保存

- AI スコアリング
  - score_news: 銘柄別ニュースセンチメントを ai_scores に保存
  - score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込み
  - OpenAI 呼び出しは JSON mode で結果を受け取り、堅牢なバリデーションとリトライを備える

- 研究用モジュール
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（共通統計ヘルパ）

- データ品質管理
  - 欠損チェック / 重複チェック / スパイク検出 / 日付整合性チェック
  - run_all_checks でまとめて実行し QualityIssue のリストを取得

- 監査ログ（audit）
  - 監査テーブル定義と初期化関数（init_audit_schema / init_audit_db）
  - signal_events, order_requests, executions の作成と索引追加

---

## 動作要件（推奨）

- Python 3.10+（型ヒントで `X | Y` 構文を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（プロジェクト内で urllib 等標準ライブラリを多用しているため requests は必須ではありませんが、必要に応じて追加してください）

例: requirements.txt（参考）
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存関係のインストール
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml を用意している場合はそれに従ってください）

3. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml のあるディレクトリ）に `.env`（または `.env.local`）を配置すると自動で読み込まれます。
   - 例: .env に以下を設定

     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO

   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データベース用ディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（サンプル）

以下は Python REPL／スクリプトから呼ぶ典型的なユースケース例です。各例は既に環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が設定済みであることを前提とします。

- DuckDB 接続を作成して ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect('data/kabusys.duckdb')
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（score_news）を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect('data/kabusys.duckdb')
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）を実行する

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect('data/kabusys.duckdb')
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAIキーは環境変数で参照
```

- 研究用ファクター計算（calc_momentum 等）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect('data/kabusys.duckdb')
m = calc_momentum(conn, date(2026, 3, 20))
v = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- 監査 DB の初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_kabusys.duckdb")
# conn は DuckDB 接続（UTC タイムゾーン設定済み）
```

- テスト時の注意点
  - OpenAI 呼び出しはモジュール内で `_call_openai_api` を定義しており、ユニットテスト時は該当関数を patch して外部呼び出しをモックできます（コメントでもその旨が記載されています）。
  - .env の自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 設計上の注意点 / ポリシー

- Look-ahead bias を避ける設計
  - 日付処理は内部で date.today() を参照する箇所を限定し、関数呼び出し時に明示的な target_date を渡すことを推奨
  - prices_daily 等の取得は target_date 未満のデータのみを参照する等、バックテストでのリークを防止する設計になっています

- 冪等性
  - ETL の保存処理（raw_prices / raw_financials / market_calendar 等）は ON CONFLICT を用いた冪等保存を採用しています

- フェイルセーフ
  - AI API 呼び出しや外部 API の失敗は適切にログに出力してフォールバック（例: macro_sentiment=0.0）する実装がなされています

- セキュリティ配慮
  - RSS の収集で SSRF 対策（リダイレクト先の検査、プライベート IP の検出）
  - defusedxml を使った XML パース（XML Bomb 対策）
  - URL 正規化・トラッキングパラメータ除去による記事冪等化

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧と説明です（抜粋）。

- kabusys/
  - __init__.py (パッケージ初期化、__version__ = "0.1.0")
  - config.py (環境変数読み込み・Settings クラス、自動 .env ロード)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースを OpenAI でスコアリング → ai_scores へ書き込み)
    - regime_detector.py (MA200 とマクロニュースの LLM スコアを合成して market_regime に書込)
  - data/
    - __init__.py
    - calendar_management.py (JPX カレンダー管理・営業日判定・更新ジョブ)
    - etl.py (ETLResult の公開)
    - pipeline.py (run_daily_etl 等、ETL パイプライン本体)
    - stats.py (zscore_normalize 等ユーティリティ)
    - quality.py (品質チェック群と QualityIssue)
    - audit.py (監査ログの DDL / 初期化ユーティリティ)
    - jquants_client.py (J-Quants API クライアント、取得・保存関数)
    - news_collector.py (RSS 収集・前処理・raw_news 保存)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (calc_forward_returns / calc_ic / factor_summary / rank)

---

## 追加情報 / 開発ノート

- OpenAI を利用する機能（news_nlp, regime_detector）は gpt-4o-mini を利用する想定で実装されています。テスト時は API 呼び出しをモックしてください。
- J-Quants クライアントはレート制限（120 req/min）に対応するスロットリングを内蔵しています。ID トークンの自動リフレッシュや 5xx / 429 のリトライロジックを備えています。
- DuckDB のバージョン依存で executemany の挙動や配列バインドが異なる点に配慮した実装がなされています（空リストバインドを回避するガード等）。
- README に掲載している例は最小限の呼び出し例です。実運用ではログ設定、エラーハンドリング、スケジューリング（Cron / Airflow 等）を組み合わせて運用してください。

---

必要であれば、README に含める具体的な .env.example、requirements.txt、よくあるエラーと対処方法、よく使う CLI スクリプト例（ETL を実行する wrapper スクリプト等）を別途作成します。どの情報を優先して追加しますか？