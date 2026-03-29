KabuSys
=======

日本株向けのデータプラットフォーム＆自動売買補助ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）など、
バックテスト／研究／本番運用を想定したユーティリティ群を提供します。

概要
----
KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）  
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去）  
- OpenAI を使ったニュースのセンチメント評価（銘柄別 ai_score / マクロセンチメント）  
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）  
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ  
- データ品質チェック（欠損、重複、スパイク、将来日など）  
- 監査ログ（signal / order_request / execution）テーブルや初期化機能（冪等）  
- DuckDB を主データストアとして利用（データ保存・集計を SQL で実行）

主な機能一覧
-------------
- data.pipeline
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl：日次差分 ETL
  - ETLResult：ETL 実行結果の集約
- data.jquants_client
  - J-Quants API ラッパー（ページネーション・トークン管理・リトライ・レート制御）
  - fetch_*/save_* 関数（raw_prices / raw_financials / market_calendar への保存）
- data.news_collector
  - fetch_rss：RSS 取得（SSRF 対策、gzip/サイズ制限）
  - preprocess_text / URL 正規化 / 記事 ID 生成
- ai.news_nlp
  - score_news：銘柄別ニュースセンチメントを OpenAI で評価し ai_scores に保存
- ai.regime_detector
  - score_regime：1321（日経225 ETF）の 200 日 MA 乖離＋マクロニュースで日次レジーム判定
- research
  - calc_momentum / calc_volatility / calc_value：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank：特徴量探索・評価
- data.quality
  - run_all_checks：欠損・重複・スパイク・日付整合性チェック
- data.audit
  - init_audit_schema / init_audit_db：監査ログテーブル初期化（冪等・UTC タイムゾーン固定）
- config
  - Settings：環境変数管理（.env 自動ロード、必須キー検証、プロファイル判定）

要件
----
- Python 3.10 以上（型記法、Union 演算子等を使用）  
- 主要 dependency（例）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外は requirements.txt 等で管理してください）

インストール
------------
開発環境であればソースルートにて通常の Python パッケージインストール手順を使います。

例:
- 仮想環境を作成してアクティベート
- 必要パッケージをインストール（pip install duckdb openai defusedxml など）
- パッケージを開発モードでインストール:
  pip install -e .

環境変数 / .env
----------------
パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env / .env.local を自動で読み込みます。自動ロードを無効にする場合は環境変数を設定してください:

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な設定項目（.env に設定）:
- JQUANTS_REFRESH_TOKEN  (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD      (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL      — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       (必須) — Slack チャンネル ID
- OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime に使用）
- DUCKDB_PATH            — データベースファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV            — 環境 (development | paper_trading | live)
- LOG_LEVEL              — ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

セットアップ手順（最小）
---------------------
1. リポジトリをクローンして依存パッケージをインストール  
2. .env を作成し、必須環境変数を設定（JQUANTS_REFRESH_TOKEN など）  
3. データディレクトリを作成（例: mkdir -p data）  
4. DuckDB 接続を開き、必要なら監査 DB を初期化

監査 DB 初期化例:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 初期化後 conn をアプリで使える
```

使い方（簡易コード例）
--------------------

ETL（日次パイプライン）の実行:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

単体 ETL（株価）:
```python
from kabusys.data.pipeline import run_prices_etl
fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
```

ニュース収集（RSS の取得）:
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

ニュース NLP スコア（銘柄別スコア算出）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
# conn: duckdb connection
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"wrote {n_written} ai_scores")
```

市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

ファクター計算（研究）:
```python
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は date/code を持つ dict のリスト
```

品質チェック:
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

設定と実行上の注意
-----------------
- OpenAI 呼び出しはネットワークエラーやレート制限を想定してリトライ/フェイルセーフ（失敗時はスコア 0.0）を行いますが、API キーは必須です。ENV または関数引数で渡してください。  
- J-Quants API はレート制限を厳守するためモジュール内で固定間隔スロットリングを行います。get_id_token は自動リフレッシュと 401 ハンドリングを含みます。  
- ETL・NLP・レジーム判定モジュールは「ルックアヘッドバイアス」を避ける設計：内部で datetime.today() を直接参照せず、target_date を明示的に渡すことを前提としています。  
- DuckDB の executemany に空リストを渡すとエラーになる古いバージョン対策が各所にあります。運用する環境の duckdb バージョンに注意してください。  
- KABUSYS_ENV は development / paper_trading / live のいずれか。live フラグで発注等の挙動を切り替える設計を想定しています（外部実装側でチェック）。

ディレクトリ構成
----------------
以下は主要ファイル／モジュールの概観（src/kabusys 以下）:

- __init__.py
- config.py               — 環境変数 / .env 自動ロード / Settings
- ai/
  - __init__.py
  - news_nlp.py           — ニュースセンチメント評価（銘柄別）
  - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py — マーケットカレンダー管理（営業日判定等）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py     — J-Quants API クライアント（fetch/save）
  - news_collector.py     — RSS 収集と前処理
  - quality.py            — データ品質チェック
  - stats.py              — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py              — 監査ログスキーマ / 初期化
  - etl.py                — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py    — Momentum / Volatility / Value の計算
  - feature_exploration.py— 将来リターン・IC・統計サマリー等

ライセンス・貢献
----------------
（ここにライセンス情報やコントリビューションルールを追記してください）

最後に
------
この README はコード内の docstring / 設計コメントを元にまとめています。実運用には .env の管理、OpenAI/J-Quants の API キーの安全保管、ログ設定、監視体制の整備を推奨します。必要であれば、個別機能の利用例や運用ガイド（デプロイ / cron / Airflow 等）を別途追記できます。