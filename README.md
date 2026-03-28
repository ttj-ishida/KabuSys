# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
ETL（データ取得・保存）、データ品質チェック、ニュースの NLP 分析、ファクター計算、監査ログ（オーディット）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- ニュース収集と LLM を用いた銘柄別センチメント算出（AI スコア）
- 市場レジーム（強気/中立/弱気）判定（ETF MA とマクロニュースの融合）
- ファクター計算・研究ユーティリティ（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 発注から約定に至る監査ログ（audit テーブル群）と初期化ユーティリティ
- RSS ベースのニュース収集（SSRF 対策・前処理あり）

設計方針として、ルックアヘッドバイアス防止（内部で date.today()/datetime.today() を直接参照しない）、DuckDB を中心とした SQL ベース処理、外部 API 呼び出し時の堅牢なリトライ設計および冪等性重視を採用しています。

---

## 主要機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得 + DuckDB への冪等保存）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・前処理・raw_news への保存補助）
  - データ品質チェック（missing_data, duplicates, spike, date_consistency, run_all_checks）
  - 監査ログ初期化（init_audit_schema, init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - ニュース NLP（score_news: gpt-4o-mini で銘柄ごとのセンチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースを合成）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - .env 自動ロード（.env / .env.local）と Settings クラス（環境変数の取得・検証）
- audit / execution / monitoring / strategy 等（パッケージ公開の想定）

---

## 必要条件

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで多くをカバーしていますが、ネットワーク/API 呼び出しには urllib 等を使用）

（プロジェクトに requirements.txt があればそれを使用してください。ない場合は上記ライブラリを個別にインストールしてください。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / コピー

2. 仮想環境を作成して依存をインストール:
   - Python >= 3.10 を使用
   - pip で必要パッケージをインストール（上記参照）

3. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings クラスで _require() が用いられているもの）:

例の .env テンプレート:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI (AI 関連関数を使う場合は env または引数で指定)
OPENAI_API_KEY=your_openai_api_key

# kabuステーション API（必要なら）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

4. DB ディレクトリ作成（必要に応じて）
```
mkdir -p data
```

---

## 基本的な使い方（コード例）

下記はいくつかの主要なユーティリティの呼び出し例です。すべて DuckDB 接続を受け取るので、duckdb.connect() を使って接続を作成してください。

- 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアを算出して ai_scores テーブルに書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")
print(f"wrote ai_scores for {n_written} codes")
```
※ api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定しておいてください。

- 市場レジーム判定を行う
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="your_openai_api_key")
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 返り値は DuckDB 接続。テーブルが作成されます。
```

- 市場カレンダー関連ユーティリティ
```python
import duckdb
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- RSS をフェッチして記事を取得（ニュース収集モジュールの低レベル関数）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```
注意: fetch_rss はネットワークリクエストを行います。SSRF 対策・受信制限・XML パースエラー処理を内包しています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API 用の refresh token
- OPENAI_API_KEY — OpenAI API を使う場合に必要（score_news, score_regime 等）
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

設定は .env/.env.local に記載するか、OS 環境変数として設定してください。プロジェクトルートに .env を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py                # ニュースセンチメント（score_news, calc_news_window 等）
    - regime_detector.py        # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py         # J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py               # ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py                    # ETL 公開インターフェース（再エクスポート）
    - calendar_management.py    # 市場カレンダー管理（is_trading_day, next_trading_day 等）
    - news_collector.py         # RSS 取得・前処理・保存補助
    - quality.py                # データ品質チェック
    - stats.py                  # zscore_normalize 等
    - audit.py                  # 監査ログテーブルのDDL / init_audit_db
  - research/
    - __init__.py
    - factor_research.py        # calc_momentum, calc_value, calc_volatility
    - feature_exploration.py    # calc_forward_returns, calc_ic, factor_summary, rank
  - ai, research, data 以下に更に細かな実装が含まれます。

---

## 運用上の注意

- AI モジュール（score_news, score_regime）は OpenAI API を使用します。API 呼び出しにはコストとレート制限があります。api_key を環境変数または関数引数で渡して下さい。
- J-Quants クライアントはレート制限とトークンの自動リフレッシュを実装していますが、ID トークンや refresh token の管理は慎重に行ってください。
- DuckDB のバージョンによっては executemany の空リストの扱い等で注意が必要な箇所があります（コード中に互換性対応の注釈あり）。
- 本ライブラリはバックテストや本番運用での「ルックアヘッドバイアス」を避ける設計になっていますが、呼び出し側でも target_date を明示して使用することを推奨します。
- 監査ログ（audit）テーブルは削除しない前提の設計です。データ保持ポリシーに従って管理してください。

---

## 貢献・拡張

- 新しいデータソースや RSS を追加する場合、news_collector の方針（URL 正規化、SSRF 対策、前処理）に従って実装してください。
- AI モデルやプロンプト改善は ai/news_nlp.py, ai/regime_detector.py を参照し、バリデーション・フォールバックを厳密に保ってください。
- テストでは環境変数の自動ロードを無効にする KABUSYS_DISABLE_AUTO_ENV_LOAD=1 の利用や、OpenAI 呼び出しのパッチ（unittest.mock.patch）で外部 API をモックすることが想定されています。

---

README に記載のサンプルは最小限の利用例です。さらに詳しい使用方法や運用手順（CI/CD、監視、バックテスト統合等）はプロジェクト内の設計ドキュメント（StrategyModel.md, DataPlatform.md 等）を参照してください。必要であれば README に追記しますので、強調してほしい項目（例: CLI コマンド、デプロイ手順）を教えてください。