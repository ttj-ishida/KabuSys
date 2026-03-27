# KabuSys — 日本株自動売買プラットフォーム（README）

## プロジェクト概要
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買基盤の一部を提供する Python パッケージです。本リポジトリには以下の主要機能群が含まれます。
- J-Quants API を用いた株価・財務・カレンダーの差分取得（ETL）
- ニュース収集・NLP による銘柄センチメント評価（OpenAI を利用）
- 市場レジーム判定（ETF MA + マクロニュースの LLM 評価を合成）
- ファクター計算・特徴量探索（モメンタム／バリュー／ボラティリティ等）
- データ品質チェック・マーケットカレンダー管理
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ初期化

設計上の方針として、バックテスト時のルックアヘッドバイアスを避ける実装や、API 呼び出しでの堅牢なリトライ・レート制御、DuckDB を用いた冪等保存などが盛り込まれています。

---

## 機能一覧
- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・ページネーション・レート制御）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化 / 監査用 DB 作成
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に記録
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー等

---

## 必要条件（主な依存）
- Python 3.9+（typing 機能を多用）
- duckdb
- openai（OpenAI の公式 SDK、Chat Completions / JSON Mode を使用）
- defusedxml
- （標準ライブラリ以外は pip でインストール）

例:
pip install duckdb openai defusedxml

プロジェクトとしては requirements.txt / pyproject.toml を用意する想定です（本コードベースは関数実装中心のモジュール群を提供します）。

---

## セットアップ手順

1. リポジトリをクローン／取得
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows は .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他の依存もインストール）
4. .env を用意する（プロジェクトルートに配置）
   - config モジュールは自動的にプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - サンプル（.env.example を参考に作成してください）:

.env（例）
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_api_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

5. DuckDB 用のデータディレクトリを作る（必要に応じて）
   - mkdir -p data

---

## 環境変数（主要）
- OPENAI_API_KEY: OpenAI API キー（ai/news_nlp と ai/regime_detector で使用）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu ステーション API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知チャネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env ロードを無効化する（テスト用）

---

## 使い方（代表的な呼び出し例）

以下は簡単なコード例です。実行環境や接続の作り方は適宜調整してください。

- Settings の利用例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)  # 必須項目は未設定時に ValueError
```

- DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("/path/to/data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API 必須）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("/path/to/data/kabusys.duckdb"))
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"wrote {written} scores")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB の初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- RSS 取得（ニュース収集の低レベル関数）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- ai モジュールは OpenAI の Chat API（gpt-4o-mini 等）を利用します。API レスポンスの JSON パースや失敗時のフォールバック実装が組み込まれており、API キーが未設定だと ValueError を投げます。
- J-Quants API 呼び出しは認証トークンの自動リフレッシュとレート制御を行います。

---

## よくある操作コマンド例

- パッケージ開発としてローカルから使う際は、プロジェクトルートで仮想環境を作り依存を入れ、Python パスに src を追加して実行してください（pyproject.toml の配置次第で編集）:
  - export PYTHONPATH=./src
  - python examples/run_etl.py

---

## ディレクトリ構成（主要ファイルと説明）
src/kabusys/
- __init__.py
  - パッケージエントリ。公開サブパッケージを定義。
- config.py
  - 環境変数の読み取り・自動 .env ロード・設定オブジェクト（settings）。
- ai/
  - __init__.py
  - news_nlp.py: ニュースを銘柄別に集約して OpenAI でセンチメントを算出し ai_scores に保存するロジック。
  - regime_detector.py: ETF(1321) の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に記録する処理。
- data/
  - __init__.py
  - calendar_management.py: 市場カレンダー管理、営業日判定、next/prev/get_trading_days、calendar_update_job。
  - pipeline.py: ETL パイプライン（run_daily_etl 等）と ETLResult。
  - jquants_client.py: J-Quants API の取得／保存／認証／レート制御／リトライ実装。
  - news_collector.py: RSS 取得、前処理、SSRF 対策、raw_news 保存用ユーティリティ。
  - quality.py: データ品質チェック群（欠損・スパイク・重複・日付不整合）。
  - stats.py: zscore_normalize 等の統計ユーティリティ。
  - audit.py: 監査ログ用テーブル DDL、初期化関数（init_audit_schema / init_audit_db）。
  - etl.py: ETL インターフェース再エクスポート（ETLResult 等）。
- research/
  - __init__.py
  - factor_research.py: calc_momentum, calc_value, calc_volatility。
  - feature_exploration.py: calc_forward_returns, calc_ic, factor_summary, rank。

その他:
- examples/ （存在する場合）: 実行例スクリプト（ETL, scoring 等）を置くと便利です。
- data/: デフォルトの DB ファイル置き場（DUCKDB_PATH, SQLITE_PATH で変更可能）

---

## 備考・運用上の注意
- 環境変数・API キーの管理は厳重に行ってください（特に OpenAI / J-Quants / Slack トークン）。
- DuckDB のスキーマ設計上、executemany の空リストはバージョンにより扱いが異なるため内部でガードしてあります。
- LLM を利用する処理は外部 API に依存するため、Network エラーや JSON パース失敗に対するフォールバックが組み込まれています。運用時には API レートやコストを考慮してください。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から判定します。CI やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。

---

README はここまでです。必要であれば「導入手順の詳細」「スキーマ定義の一覧」「よくあるエラーと対処法」などの追加ドキュメントを作成します。どのトピックを優先しますか？