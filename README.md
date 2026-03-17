KabuSys
=======

概要
----
KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
J-Quants API からのマーケットデータ取得、RSS ベースのニュース収集、DuckDB によるスキーマ管理・ETL、品質チェック、監査ログ（発注→約定トレース）など、取引システムに必要なデータパイプラインとユーティリティを提供します。

主な設計方針
- API レート制限・リトライ・トークン自動リフレッシュを考慮した安全な API クライアント
- データの冪等保存（DuckDB の ON CONFLICT を利用）
- Look-ahead bias を避けるための fetched_at / UTC 管理
- RSS 収集での SSRF / XML 攻撃対策、受信サイズ制限
- 品質チェックを集めて返す（Fail-Fast ではなく呼び出し元が判断）

機能一覧
--------
- J-Quants クライアント（株価日足・財務データ・マーケットカレンダーの取得）
  - レート制御、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
- DuckDB のスキーマ定義と初期化
  - Raw / Processed / Feature / Execution 層を含むテーブル群とインデックス
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl でカレンダー・株価・財務データの差分更新と品質チェックを一括実行
- ニュース収集（RSS → raw_news、銘柄紐付け）
  - URL 正規化、記事ID（SHA-256 先頭 32 文字）で冪等性確保、SSRF/サイズ対策
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）

セットアップ手順
----------------

前提
- Python 3.10 以上（typing の新構文や型ヒントに依存）
- pip

依存パッケージ（主要）
- duckdb
- defusedxml

インストール（開発中にローカルで使う例）
1. リポジトリルートで仮想環境を作成・有効化
   - Unix/macOS:
     python -m venv .venv
     source .venv/bin/activate
   - Windows:
     python -m venv .venv
     .venv\Scripts\activate

2. 必要パッケージをインストール
   pip install duckdb defusedxml

   （プロジェクトに requirements.txt があれば）
   pip install -r requirements.txt

3. パッケージを開発モードでインストール（任意）
   pip install -e .

環境変数
- 自動で .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数が優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN  （J-Quants のリフレッシュトークン）
- KABU_API_PASSWORD      （kabu API のパスワード）
- SLACK_BOT_TOKEN        （Slack 通知用ボットトークン）
- SLACK_CHANNEL_ID       （Slack チャンネル ID）

任意 / デフォルトあり
- KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH       （デフォルト: data/kabusys.duckdb）
- SQLITE_PATH       （デフォルト: data/monitoring.db）
- KABUSYS_ENV       （development / paper_trading / live、デフォルト development）
- LOG_LEVEL         （DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

サンプル .env（プロジェクトルート）
- .env.example として管理するとよいです（実際の値は秘匿してください）。

  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  KABU_API_PASSWORD=your_kabu_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO

使い方（簡単な例）
-----------------

Python から操作する例をいくつか示します。conn は duckdb の接続オブジェクトです。

1) スキーマ初期化（DuckDB ファイル作成）
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)  # デフォルトなら data/kabusys.duckdb を作成して接続を返す

2) 日次 ETL を実行（市場カレンダー・株価・財務・品質チェック）
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を渡さなければ今日を対象に実行
# result は ETLResult オブジェクト。to_dict() で辞書化可。
print(result.to_dict())

3) ニュース収集ジョブ（RSS を取得して raw_news に保存）
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
new_counts = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
# 戻り値はソースごとの新規保存件数の辞書

4) カレンダー夜間更新ジョブ（calendar_update_job）
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)  # lookahead_days の引数を変更可能

5) 監査スキーマの初期化
from kabusys.data.audit import init_audit_schema
# init_schema で作った conn を渡す
init_audit_schema(conn, transactional=True)

6) 設定へのアクセス
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)

主な戻り値 / 例外
- jquants_client の _request は再試行後に失敗すると RuntimeError を投げします。
- ETL の各種 run_* 関数は (fetched, saved) のタプルを返します。run_daily_etl は ETLResult を返して、quality チェック結果や発生したエラー概要を含みます。

ディレクトリ構成
----------------

リポジトリ / パッケージ内の主なファイルとモジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得 + 保存ユーティリティ）
    - news_collector.py      # RSS 収集・正規化・DB保存・銘柄紐付け
    - pipeline.py            # ETL パイプライン（差分取得・バックフィル・品質チェック）
    - calendar_management.py # マーケットカレンダー管理（営業日判定・更新ジョブ）
    - schema.py              # DuckDB スキーマ定義・初期化
    - audit.py               # 監査ログ（発注→約定トレース）DDL + 初期化
    - quality.py             # データ品質チェックモジュール
  - strategy/
    - __init__.py            # 戦略層（拡張ポイント）
  - execution/
    - __init__.py            # 発注実行層（拡張ポイント）
  - monitoring/
    - __init__.py            # 監視用モジュール（将来的な拡張）

運用上の注意
------------
- J-Quants API のレート制限（120 req/min）に従う実装になっていますが、大量のページネーションや並列処理を行う場合はシステム側でも注意が必要です。
- DuckDB のファイル保存先（DUCKDB_PATH）のバックアップやアクセス権管理を適切に行ってください。
- .env に秘匿情報（トークン・パスワード）を保存する場合は、リポジトリにコミットしないでください。`.gitignore` に .env を追加することを推奨します。
- ニュースの RSS 取得は外部 URL にアクセスするため、ネットワークポリシーや SSRF リスクを踏まえた運用をしてください（news_collector は多重対策を組み込んでいますが、環境によっては追加制限が必要です）。

開発 / 貢献
------------
- 新機能や修正は issue を立て、PR を作成してください。
- テストを追加する際は、外部 API の呼び出しはモックしてテスト可能にしてください（設定ファイルで KABUSYS_DISABLE_AUTO_ENV_LOAD を使う等のユーティリティあり）。

ライセンス
---------
- 本 README ではライセンス情報を含めていません。プロジェクトに LICENSE ファイルがあればそちらを参照してください。

問い合わせ
----------
- 実装や使い方に関する質問は、リポジトリの issue を利用してください。

以上が簡単な README になります。必要に応じて、実行コマンド（systemd / cron / Airflow でのスケジュール例）やより詳細な .env.example、CI/CD の設定例などを追加できます。どの情報を追加したいか教えてください。