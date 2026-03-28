# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
DuckDB をバックエンドに、J-Quants からの ETL、ニュース収集・NLP（OpenAI でのセンチメント評価）、研究用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

---

## 主な特徴

- ETLパイプライン（株価 / 財務 / 市場カレンダー）の差分取得・保存（J-Quants API 経由）
- ニュース収集（RSS）と前処理、銘柄紐付け
- ニュースの LLM ベースセンチメント評価（gpt-4o-mini を利用、JSON Mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
- 研究用ユーティリティ（モメンタム・ボラティリティ・バリュー等のファクター計算、IC 計算、Z-score 正規化）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用 DDL 初期化ユーティリティ
- 環境変数 / .env の自動読み込み（プロジェクトルート検出）

---

## 必要条件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて追加で urllib / ssl 等の標準ライブラリと、J-Quants の利用に必要なネットワークが必要です）

推奨インストール（プロジェクトに setup/pyproject がある想定）：
pip install -r requirements.txt
（requirements.txt がない場合は上記パッケージを個別にインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / パッケージを配置
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトの extras があれば pip install -e . 等）
4. 環境変数を設定（.env をプロジェクトルートに置くことで自動読み込みされます）
   - 必要な環境変数例（後述の .env 例参照）
5. DuckDB 用ディレクトリを作成（デフォルトでは data/ 配下）
   - mkdir -p data

自動 .env 読み込みについて:
- プロジェクトルートはこのパッケージのファイルパス（__file__）から親ディレクトリを上がり `.git` または `pyproject.toml` を探して決定します。
- 読み込み順序: OS 環境 > .env.local > .env
- テスト等で自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（.env 例）

以下は本プロジェクトで参照される主な環境変数例です。用途に応じて .env/.env.local に設定してください。

- JQUANTS_REFRESH_TOKEN=...(必須)  
  J-Quants のリフレッシュトークン（ETL で使用）。
- KABU_API_PASSWORD=...(必須)  
  kabuステーション API のパスワード（発注系で利用する想定）。
- KABU_API_BASE_URL=http://localhost:18080/kabusapi  (任意)  
  kabu API のベース URL（デフォルト値あり）。
- SLACK_BOT_TOKEN=...(必須)  
  Slack 通知用トークン（必要に応じて）。
- SLACK_CHANNEL_ID=...(必須)  
  Slack 通知先チャンネル ID。
- OPENAI_API_KEY=...(AI 機能に必要)  
  OpenAI API キー（news_nlp / regime_detector で利用）。
- DUCKDB_PATH=data/kabusys.duckdb (任意)  
  DuckDB ファイルパスのデフォルト。
- SQLITE_PATH=data/monitoring.db (任意)
- KABUSYS_ENV=development | paper_trading | live (任意、デフォルト development)
- LOG_LEVEL=INFO (任意、デフォルト INFO)

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABU_API_PASSWORD=yourpass
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（クイックスタート）

以下は Python スクリプト／REPL での基本的な呼び出し例です。DuckDB 接続には duckdb.connect を使います。

1) 日次 ETL の実行（prices / financials / calendar の差分収集と品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースのスコアリング（OpenAI を使用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {count} codes")
```

3) 市場レジーム判定（MA200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログテーブルを初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# conn は初期化済みの duckdb 接続
```

5) ニュース RSS 取得（低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点:
- AI 関連関数は OpenAI API キー（OPENAI_API_KEY）を要求します。api_key 引数で直接渡すこともできます。
- ETL / API 呼び出しはネットワークアクセスを伴います。API レート制限や認証に注意してください。

---

## 主要モジュール（簡易説明）

- kabusys.config
  - 環境変数読み込み・設定アクセス（settings オブジェクト）
  - 自動的に .env / .env.local をプロジェクトルートから読み込む（無効化可能）

- kabusys.data
  - jquants_client: J-Quants API の取得・保存ユーティリティ（rate limit / retry / save_*）
  - pipeline: run_daily_etl, 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集・前処理（SSRF 対策・トラッキング削除）
  - calendar_management: 市場カレンダーと営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: zscore_normalize 等の統計ユーティリティ
  - audit: 監査ログ（DDL 定義・初期化・インデックス）

- kabusys.ai
  - news_nlp: ニュースを銘柄単位に集約して OpenAI でスコアリング
  - regime_detector: ETF(1321) MA200 とマクロニュースで市場レジームを判定

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - データ分析・研究用ユーティリティ群（DuckDB 上の SQL と Python の組合せ）

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル構成（src 側）:

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
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit_db 初期化ユーティリティ等
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research や data のユーティリティモジュール群

（上記は本 README に含まれるファイルの主要な抜粋です）

---

## 設計上の注意・ポリシー

- Look-ahead bias（ルックアヘッドバイアス）に配慮して日付処理を行う実装方針を採用しています。内部実装の多くは date/datetime の明示的引数を用い、date.today()/datetime.today() に依存しない設計です。
- J-Quants / OpenAI 呼び出しにはリトライ・バックオフを組み込んでいます。また、失敗時はフェイルセーフ的に中立スコア（0）を使う等の設計をしています。
- DuckDB に対する書き込みは基本的に冪等性（ON CONFLICT 等）を考慮して実装されています。

---

## 開発・テスト時のヒント

- 自動 .env 読み込みを無効にしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで OS 環境を明示的に制御したい場合に便利）。
- OpenAI の呼び出しは内部で _call_openai_api を経由しており、ユニットテストでは該当関数をモックすることで API コールをシミュレートできます。
- news_collector のネットワークリクエストは内部で _urlopen を使っており、テスト時にモックしてレスポンスを差し替え可能です。

---

## 貢献・ライセンス

リポジトリに CONTRIBUTING.md や LICENSE があればそれに従ってください。  
（この README はコードベースの解説を目的としており、実運用に際しては各自のセキュリティポリシー・API 利用規約に従ってください。）

---

必要であれば README に「より詳細な API リファレンス」「運用手順（cron / Cloud Run など）」や「デプロイ手順」「サンプル .env.example ファイル」等を追加します。どの情報を追記しましょうか？