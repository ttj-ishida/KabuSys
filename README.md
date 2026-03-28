KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリ（部分実装）。  
ETL、ニュースNLP（LLMによるセンチメント）、市場レジーム判定、リサーチ用ファクター計算、データ品質チェック、監査ログ（発注トレーサビリティ）等の機能を提供します。

特徴（要約）
-----------
- J-Quants API を用いた株価・財務・カレンダーの差分ETL（ページネーション・レート制御・リトライ対応）
- DuckDB をデータストアに利用する ETL / 分析パイプライン
- ニュース記事の収集（RSS）と前処理、LLM（OpenAI）を用いた銘柄別センチメントスコア生成
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメント）
- ファクター計算（モメンタム / ボラティリティ / バリュー等）および統計ユーティリティ（Zスコア等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）スキーマ初期化ユーティリティ
- 設定は環境変数 / .env から読み込み（自動ロード機構あり）

機能一覧
--------
- data/
  - jquants_client: J-Quants API クライアント（取得・保存ロジック、レートリミット、リトライ、トークン管理）
  - pipeline: 日次 ETL 実行 run_daily_etl、個別 ETL run_prices_etl 等
  - calendar_management: JPX カレンダー管理 / 営業日判定、calendar_update_job
  - news_collector: RSS 取得・前処理・DB 保存ユーティリティ
  - quality: データ品質チェック群（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - audit: 監査ログスキーマ作成 / init_audit_db
  - stats: zscore_normalize 等の統計ユーティリティ
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（OpenAI）
  - regime_detector.score_regime: 市場レジーム判定（MA200 + マクロニュース）
- research/
  - factor_research: calc_momentum, calc_volatility, calc_value
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config: .env 自動ロード／設定ラッパ（Settings インスタンス経由で取得）

セットアップ
------------

前提
- Python 3.10+ を想定（typing の Union 記法等を利用）
- DuckDB、OpenAI SDK、defusedxml 等のライブラリが必要

仮想環境作成（例）
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（プロジェクトに requirements.txt があればそれを使ってください）
   例（最低限）:
   - pip install duckdb openai defusedxml

推奨追加パッケージ（運用・開発によって必要）
- pytest（テスト）
- requests（任意・HTTP 利用）

環境変数 / .env
----------------
config.Settings で参照される主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN    -> J-Quants の refresh token（jquants_client.get_id_token で使用）
- SLACK_BOT_TOKEN          -> Slack 通知に使う場合
- SLACK_CHANNEL_ID         -> Slack の channel id
- KABU_API_PASSWORD        -> kabuステーション API を使う場合

任意（デフォルトあり）:
- KABU_API_BASE_URL        -> kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH              -> DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH              -> SQLite（監視等）パス（デフォルト data/monitoring.db）
- KABUSYS_ENV              -> development / paper_trading / live（デフォルト development）
- LOG_LEVEL                -> INFO 等（デフォルト INFO）
- OPENAI_API_KEY           -> OpenAI API キー（ai モジュールで使用）
- KABUSYS_DISABLE_AUTO_ENV_LOAD -> 1 を設定すると自動 .env ロードを無効化

自動ロード:
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml の存在）を探し、OS 環境変数 > .env.local > .env の順で読み込みます。
- .env のパースは export KEY=val / quoted values / inline comments 等に対応します。
- テスト等で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（短い例）
----------------

共通準備: DuckDB 接続を作成
```py
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")  # または ":memory:"
```

1) 日次 ETL の実行
```py
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコアリング（ai.news_nlp.score_news）
```py
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY は環境変数か api_key 引数で渡す
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

3) 市場レジーム判定（ai.regime_detector.score_regime）
```py
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

4) ファクター計算（research）
```py
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

m = calc_momentum(conn, date(2026, 3, 20))
v = calc_volatility(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
```

5) 品質チェック
```py
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

6) 監査ログ DB 初期化
```py
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査用の DuckDB 接続
```

設計上の注意点 / ポリシー
-------------------------
- Look-ahead bias を防ぐため、各処理は target_date を明示して date.today() を参照しない実装方針を採っています（バックテストや再現性の確保に有利）。
- API 呼び出しはリトライ（指数バックオフ）・タイムアウト・レート制御を行います。LLM（OpenAI）呼び出し失敗時はフォールバック値で継続する設計があります（例: macro_sentiment=0.0）。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT / DELETE→INSERT）で行い、部分失敗が既存データを消さないように配慮しています。
- RSS の取得では SSRF 対策、gzip サイズチェック、defusedxml の利用などセキュリティ考慮を行っています。

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下）
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
  - etl.py (ETLResult 再公開)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py

- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

主要モジュールの役割（短く）
- config.py: 環境変数/.env の読み込みと Settings 抽象化
- jquants_client.py: J-Quants からの取得と DuckDB 保存ロジック
- pipeline.py: 日次 ETL のオーケストレーション（run_daily_etl など）
- news_nlp.py: ニュースの銘柄別センチメント取得（OpenAI 呼び出し）
- regime_detector.py: MA200 とニュースを合成した市場レジーム判定
- audit.py: 監査ログスキーマの初期化ユーティリティ

よくある質問（短め）
-------------------
Q: .env の自動読み込みを無効化するには？
A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

Q: OpenAI の API キーはどこで指定する？
A: 環境変数 OPENAI_API_KEY、または score_news / score_regime の api_key 引数で渡せます。

Q: J-Quants の認証はどうする？
A: settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）を設定すると、jquants_client.get_id_token が refresh token を使って id_token を取得します。

ライセンス・貢献
----------------
（このリポジトリのライセンスや貢献ルールをここに追加してください。）

補足
----
- 本 README はコードベースの公開関数・設定・設計方針に基づいて作成しています。詳細な API 仕様や運用手順（cron ジョブ、監視、Slack 通知の使用例など）は別途ドキュメント化を推奨します。