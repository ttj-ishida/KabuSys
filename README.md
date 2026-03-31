# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
J-Quants・ニュース・OpenAI を組み合わせてデータ収集（ETL）、品質チェック、AI によるニュースセンチメント評価、研究用ファクター計算、監査ログ（発注→約定トレース）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータパイプラインとリサーチ、ならびに自動売買に必要な基盤コンポーネントを集めたライブラリです。主な責務は以下の通りです。

- J-Quants からの株価・財務・カレンダーの差分取得（ETL）および DuckDB への保存
- ニュース収集（RSS）と前処理、ニュース → 銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄別 / マクロ）評価（gpt-4o-mini）
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ用スキーマ（signal → order_request → execution の追跡）
- 環境設定管理（.env と環境変数の読み込み）

設計方針として、バックテスト等でのルックアヘッドバイアスを避けるために現在時刻を直接参照しない設計や、API 呼び出しの堅牢なリトライ・フェイルセーフ処理を重視しています。

---

## 機能一覧（抜粋）

- 環境設定: kabusys.config.Settings による環境変数取得（.env 自動読み込み対応）
- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）: fetch_* / save_* 関数
- データ品質: kabusys.data.quality（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
- ニュース:
  - RSS 取得と前処理（kabusys.data.news_collector.fetch_rss）
  - ニュース NLP（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime（ETF 1321 の MA とマクロニュースを合成）
- 研究（Research）: kabusys.research（calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank）
- 統計ユーティリティ: kabusys.data.stats.zscore_normalize
- 監査ログ初期化: kabusys.data.audit.init_audit_schema / init_audit_db

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントの union 型 | を使用しているため）
- Git（.env 自動検出のためプロジェクトルートに .git があると便利）

1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ... && cd ...

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトで requirements.txt / pyproject.toml があればそちらを使用してください）

4. 開発インストール（任意）
   - pip install -e .

5. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml を基準）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる主要環境変数（例）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- KABU_API_PASSWORD=your_kabu_api_password
- SLACK_BOT_TOKEN=your_slack_bot_token
- SLACK_CHANNEL_ID=your_slack_channel_id
- OPENAI_API_KEY=your_openai_api_key

オプション（デフォルト有り）
- KABUSYS_ENV (development | paper_trading | live)  デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト: INFO
- DUCKDB_PATH デフォルト: data/kabusys.duckdb
- SQLITE_PATH デフォルト: data/monitoring.db
- PID_FILE_PATH デフォルト: data/execution.pid

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxx
OPENAI_API_KEY=sk-xxx
KABU_API_PASSWORD=pass
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡易ガイド）

ここでは代表的な関数の使い方を示します。import はパッケージ名 `kabusys` を使います。

1) DuckDB 接続と ETL の実行（日次 ETL）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメント（銘柄別）スコア生成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（マクロ + ETF MA）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（別 DB ファイルで運用する場合）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は DuckDB 接続。init_audit_db がスキーマを作成します。
```

5) RSS フィードの取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- OpenAI API 呼び出しを行う関数は api_key 引数を受け取ります。指定しない場合は環境変数 `OPENAI_API_KEY` が使われます。
- DB 書き込みは多くが冪等（ON CONFLICT DO UPDATE / DO NOTHING）です。部分失敗で他レコードを失わない工夫が各所にあります。
- ETL / AI 呼び出しはネットワークエラーや API レート制限を考慮したリトライ処理が組み込まれています。

---

## ディレクトリ構成（主要ファイル）

以下は本リポジトリの主要モジュール（src/kabusys 以下）の抜粋ツリーです:

- src/kabusys/
  - __init__.py
  - config.py                    （環境設定・.env 読み込み）
  - ai/
    - __init__.py
    - news_nlp.py                （銘柄別ニューススコアリング）
    - regime_detector.py         （マクロ＋ETF MA による市場レジーム）
  - data/
    - __init__.py
    - jquants_client.py          （J-Quants API クライアント・保存処理）
    - pipeline.py                （ETL パイプライン）
    - etl.py                     （ETL インターフェース）
    - news_collector.py          （RSS ニュース収集）
    - calendar_management.py     （市場カレンダー管理）
    - quality.py                 （データ品質チェック）
    - stats.py                   （統計ユーティリティ）
    - audit.py                   （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py         （モメンタム/バリュー/ボラティリティ）
    - feature_exploration.py     （将来リターン / IC / サマリー）
  - (その他)                      （strategy / execution / monitoring 等の名前は __all__ に記載）

各モジュールは docstring と設計方針を伴って実装されており、用途別に分割されています。

---

## 開発メモ / 注意事項

- Python の型注釈や recent 構文（| 型合成）を利用しているため Python 3.10 以上を推奨します。
- .env 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に動作します。テストなどで自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）想定の実装です。API の挙動変化に対して堅牢にパースする工夫（余分なプレフィックス除去や例外フォールバック）を入れていますが、API 仕様変更時は注意が必要です。
- J-Quants API はレート制限（120 req/min）を考慮した RateLimiter と、401 時のトークン自動リフレッシュなどを備えています。J-Quants のクレデンシャルは必ず安全に管理してください。
- DuckDB に対する executemany 等はバージョン差による挙動差（空リスト不可 等）を考慮して実装されています。

---

必要であれば次の内容も作成できます:
- .env.example（推奨環境変数テンプレート）
- 実運用向けデプロイ手順（systemd / supervisor / コンテナ）
- 追加のサンプルスクリプト（ETL スケジューラ / 監視ジョブ）

ご希望の出力（例: .env.example、起動スクリプト、API 使用例のサンプル）を教えてください。