# KabuSys

日本株向け自動売買基盤ライブラリ「KabuSys」のリポジトリ README（日本語）

概要
----
KabuSys は日本株のデータ取得・ETL、特徴量生成、シグナル生成、ニュース収集、監査ログなどを含む自動売買プラットフォームのライブラリ群です。  
主に DuckDB をデータ層に用い、J-Quants API から市場データ・財務データ・カレンダーを取得し、研究（research）→特徴量（feature）→戦略（strategy）→発注（execution）の流れを支援するモジュール群を提供します。

主要な目的
- J-Quants など外部データソースからの差分 ETL（差分取得と冪等保存）
- DuckDB によるスキーマ定義・永続化
- ファクター計算（モメンタム／ボラティリティ／バリュー等）
- クロスセクション正規化（Z スコア）
- 戦略シグナル生成（BUY / SELL の判定、Bear レジーム抑制など）
- RSS ベースのニュース収集と銘柄紐付け
- 発注・監査用スキーマの用意

機能一覧
--------
- 環境設定読み込み（.env/.env.local 自動読込、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント（認証トークンリフレッシュ、ページネーション、レート制御、リトライ）
- DuckDB スキーマ初期化（init_schema）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- 研究用ファクター計算（calc_momentum / calc_volatility / calc_value）
- 特徴量作成（build_features：Z スコア正規化・ユニバースフィルタ適用・features テーブル UPSERT）
- シグナル生成（generate_signals：ファクター＋AI スコア統合、BUY/SELL 出力、signals テーブル更新）
- ニュース収集（RSS 取得、前処理、raw_news 保存、銘柄抽出 / news_symbols）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
- 監査ログ用スキーマ（signal_events, order_requests, executions など）
- 汎用統計ユーティリティ（zscore_normalize、IC 計算等）

セットアップ手順
----------------

前提
- Python 3.9+（コードは型注釈に Python 3.10 以降の構文を使っている箇所があるため、3.10 以上を推奨）
- DuckDB（Python パッケージ）
- defusedxml（RSS パースに使用）
- ネットワーク経由の API キー（J-Quants 等）

例: 仮想環境作成と最低限の依存をインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
```

環境変数
- 必須（Settings._require により未設定で ValueError）
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD : kabu ステーション API パスワード（execution 層使用時）
  - SLACK_BOT_TOKEN : Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID : Slack 通知先チャネル ID
- 任意（デフォルト有り）
  - KABUSYS_ENV : 実行環境 ("development" / "paper_trading" / "live")（デフォルト "development"）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" にすると .env 自動ロードを無効化
  - KABUSYSログ関連: LOG_LEVEL（"DEBUG"/"INFO"/...、デフォルト "INFO"）
  - DUCKDB_PATH（デフォルト "data/kabusys.duckdb"）
  - SQLITE_PATH（デフォルト "data/monitoring.db"）
  - KABU_API_BASE_URL（デフォルト "http://localhost:18080/kabusapi"）

.env の自動読込挙動
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env を読み込みます。
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

データベース初期化
- DuckDB スキーマを作成するには init_schema を使います。例えば：
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

使い方（例）
------------

1) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) 特徴量構築（build_features）
```python
from datetime import date
import duckdb
from kabusys.strategy import build_features
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
count = build_features(conn, target_date=date.today())
print(f"features upserted: {count}")
```

3) シグナル生成（generate_signals）
```python
from datetime import date
import duckdb
from kabusys.strategy import generate_signals
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
total = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals written: {total}")
```

4) ニュース収集ジョブ（RSS 取得 + DB 保存 + 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
known_codes = {"7203", "6758", "9984"}  # 既知銘柄セットを渡すと紐付けを行う
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

5) カレンダー更新（夜間ジョブ）
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

API / 主要関数一覧（サマリ）
- kabusys.config.settings：環境変数を読む設定オブジェクト
- kabusys.data.schema.init_schema(db_path)：DuckDB スキーマ作成
- kabusys.data.pipeline.run_daily_etl(...)：日次 ETL
- kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar：J-Quants からのフェッチ
- kabusys.data.jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar：DuckDB への保存
- kabusys.research.calc_momentum / calc_volatility / calc_value：ファクター計算
- kabusys.strategy.build_features：features テーブル作成（正規化・フィルタ）
- kabusys.strategy.generate_signals：signals テーブル生成（BUY/SELL）
- kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection：RSS ニュース処理
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days：営業日ロジック

ディレクトリ構成（src/kabusys 配下の主要ファイル）
-------------------------------------
- kabusys/
  - __init__.py                   : パッケージ定義（バージョン等）
  - config.py                     : 環境変数 / 設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py           : J-Quants API クライアント（認証/フェッチ/保存）
    - schema.py                   : DuckDB スキーマ定義と init_schema / get_connection
    - pipeline.py                 : ETL パイプライン（差分取得・run_daily_etl 等）
    - stats.py                    : zscore_normalize 等統計ユーティリティ
    - news_collector.py           : RSS 取得・記事前処理・DB 保存・銘柄抽出
    - calendar_management.py      : market_calendar 管理（営業日判定等）
    - features.py                 : features 再エクスポート（zscore）
    - audit.py                    : 監査ログ用スキーマ DDL
    - (その他)                    : quality / audit 等（品質チェック類は pipeline から参照）
  - research/
    - __init__.py
    - factor_research.py          : calc_momentum / calc_volatility / calc_value
    - feature_exploration.py      : IC / forward returns / summary
  - strategy/
    - __init__.py
    - feature_engineering.py      : build_features（ファクター正規化・ユニバースフィルタ）
    - signal_generator.py         : generate_signals（final_score 計算・BUY/SELL）
  - execution/                     : 発注/約定/ポジション処理（空ディレクトリ・実装拡張箇所）
  - monitoring/                    : 監視・メトリクス（将来的な実装領域）

運用上の注意点
-------------
- 自動売買を行う場合は必ず paper_trading / live の切り替えや SLACK 通知等のリスク管理を組み込んでください。
- J-Quants の API レート制限（120 req/min）を尊重するため、jquants_client は内部でレート制御とリトライを行いますが、運用側でも同様の配慮をしてください。
- DuckDB スキーマは冪等に作成されますが、既存データ構造を変更する DDL は考慮が必要です。バックアップを取りながら運用してください。
- RSS 取得は外部ネットワークを使用するため、SSRF 対策・受信サイズ制限・XML インジェクション対策（defusedxml を使用）を実装していますが、運用ポリシー（ホワイトリストやタイムアウト）を適切に設定してください。

ライセンス / 貢献
-----------------
本ドキュメントにはライセンス・貢献ルールは含まれていません。実際のリポジトリの LICENSE、CONTRIBUTING.md を確認してください。

サポート / 追加実装
------------------
- execution 層（実際の注文送信・ブローカー統合）は本コードベースでは限定的です。実運用でのブローカー API 連携、リスク管理、二重発注防止などは別途実装が必要です。
- 品質チェックモジュール（quality）は pipeline から呼ばれます。詳細なチェックやアラート閾値はプロジェクト要件に合わせて調整してください。

以上。必要であれば README に含めるコマンド例の追加、環境変数テンプレート（.env.example）や requirements.txt のサンプル作成も支援します。