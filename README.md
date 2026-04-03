KabuSys
=======

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データETL、ニュースのAIセンチメント評価、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、および外部APIクライアント（J-Quants / OpenAI / kabuステーション想定）を提供します。

バージョン
---------
0.1.0（パッケージ定義: kabusys.__version__）

主な特徴
--------
- データ収集（J-Quants）から DuckDB へ冪等保存する ETL パイプライン
- ニュース収集（RSS）と前処理、銘柄紐付け機能（news_collector）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（ai.news_nlp）
- マクロニュース + ETF（1321）のMA乖離から市場レジーム判定（ai.regime_detector）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析（research）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- マーケットカレンダー管理（JPX カレンダー）と営業日ユーティリティ
- 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ
- 設定管理（環境変数 / .env 自動読み込み）

セットアップ
-----------

1. リポジトリをクローンし、仮想環境を作成・有効化します（例: venv, pyenv）。
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストールします（pip の requirements.txt があればそちらを利用してください）。主要な依存は以下の通りです：
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ：urllib 等を使用）
   例：
   ```
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定します。開発ではプロジェクトルートに .env / .env.local を置くと自動で読み込まれます（設定は kabusys.config で管理）。
   自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

推奨 .env（例）
---------------
以下は最低限の設定例（実運用では機密情報は安全に管理してください）。
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション API（必要なら）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# DB パス（デフォルト）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行モード (development | paper_trading | live)
KABUSYS_ENV=development

# ログレベル
LOG_LEVEL=INFO
```

使い方（主要な関数・例）
----------------------

※ 各 API は DuckDB の接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

1) 日次ETL の実行（株価 / 財務 / カレンダー取得 + 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {written}")
```

3) 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを統合）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 必要なテーブル・インデックスが作成されます
```

5) RSS フィード取得（news_collector.fetch_rss）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
for a in articles:
    print(a["id"], a["title"], a["datetime"])
```

設定（kabusys.config）
--------------------
- settings オブジェクト経由で各種設定へアクセスできます（例: settings.jquants_refresh_token）。
- 自動的にプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を読み込む仕組みがあります。
- 環境: KABUSYS_ENV は development / paper_trading / live のいずれかで検証されます。
- データベースの既定パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db

注意点 / 設計上の方針
-------------------
- Look-ahead bias 防止: 多くの処理（ニュースウィンドウ、レジーム判定、ETL 等）は date 引数ベースで動作し、内部で datetime.today() を盲目的に参照しない設計です。バックテスト時は target_date を明示的に渡してください。
- 冪等性: ETL や save_* 関数は ON CONFLICT DO UPDATE を使って冪等保存を行います。
- API リトライ / レート制御:
  - J-Quants クライアントには簡易的なレートリミッタとリトライロジックが組み込まれています（120 req/min）。
  - OpenAI 呼び出しは各モジュールでリトライ/フォールバックを実装しています（失敗時は安全側の既定値で継続）。
- セキュリティ:
  - news_collector は SSRF 対策（リダイレクト検査 / プライベートアドレスブロック）、XML パースの安全化（defusedxml）などを行います。

ディレクトリ構成（主なファイル）
------------------------------
src/kabusys/
- __init__.py
- config.py                        -- 環境変数 / .env 読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py                     -- ニュースセンチメント評価（OpenAI）
  - regime_detector.py              -- 市場レジーム判定（ETF + マクロ）
- data/
  - __init__.py
  - calendar_management.py          -- マーケットカレンダー管理・営業日ロジック
  - etl.py / pipeline.py            -- ETL パイプラインと公開型（ETLResult）
  - jquants_client.py               -- J-Quants API クライアント + DuckDB 保存
  - news_collector.py               -- RSS 収集・前処理
  - quality.py                      -- データ品質チェック
  - stats.py                        -- 汎用統計ユーティリティ（zscore 等）
  - audit.py                        -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py              -- モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py          -- 将来リターン / IC / 統計サマリー 等

その他
- 設定やトークン類は .env / 環境変数で管理してください。
- テストや CI 向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を 1 にして自動 .env 読み込みを無効化できます。

ライセンス・貢献
----------------
（リポジトリの LICENSE を参照してください）

フィードバック・バグ報告
-----------------------
Issue を立てる際は再現手順、使用した設定（機密情報は除く）、ログ出力を添えてください。

以上。必要であれば、README にサンプル .env.example や具体的な SQL スキーマ（テーブル定義）を追加します。どの情報を追記しますか？