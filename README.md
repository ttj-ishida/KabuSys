# KabuSys

日本株向けの自動売買プラットフォーム向けライブラリ群です。  
市場データの取得・ETL、特徴量計算、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログスキーマなど、戦略開発〜実行に必要な主要コンポーネントを含みます。

主な設計方針：
- ルックアヘッドバイアスを防ぐ（計算は target_date 時点のデータのみ使用）
- DuckDB を中心としたローカル DB にデータを冪等に保存
- API のレート制御・リトライ・トークン自動リフレッシュを組み込み
- 外部依存を最小化し、研究用モジュールと実行用モジュールを分離

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（fetch/save：日足・財務・マーケットカレンダー）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
- ETL（差分更新）
  - 日次 ETL（市場カレンダー → 日足 → 財務 → 品質チェック）
  - 差分取得・バックフィル対応
- スキーマ定義
  - DuckDB 用の Raw / Processed / Feature / Execution レイヤーの DDL とインデックス
  - 監査ログ（signal_events / order_requests / executions 等）
- 研究用ファクター計算
  - Momentum（1/3/6 ヶ月等）、MA200 乖離
  - Volatility（ATR20、出来高比率等）
  - Value（PER / ROE 等）
  - 将来リターン・IC（Spearman）等の解析ユーティリティ
- 特徴量エンジニアリング
  - 生ファクターのマージ、ユニバースフィルタ、Zスコア正規化、クリッピング、features テーブルへの UPSERT
- シグナル生成
  - 各コンポーネントスコアの計算（momentum/value/volatility/liquidity/news）
  - 最終スコアの重み付け、Bear レジーム抑制、BUY/SELL シグナル生成、signals テーブルへの置換保存
- ニュース収集
  - RSS フィード取得（SSRF・XML インジェクション対策、gzip 制限、トラッキング除去）
  - raw_news, news_symbols への冪等保存
  - テキスト前処理・銘柄コード抽出
- マーケットカレンダー管理
  - DB を優先した営業日判定、前後営業日の取得、日次バッチ更新ジョブ
- 統計ユーティリティ
  - Z スコア正規化、ランク計算、IC / 要約統計量

---

## 必要条件

- Python 3.10 以上（型ヒントに `X | Y` を利用）
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- （任意）J-Quants API トークン等の環境変数

インストール例：
pip install duckdb defusedxml

プロジェクトをパッケージとして使う場合は、リポジトリルートで:
pip install -e .

（requirements.txt を用意している場合はそちらを使用してください）

---

## 環境変数 / 設定

設定は .env ファイルまたは環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われ、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（実行層で利用）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID: Slack 通知のチャンネル ID

任意 / デフォルト設定:
- KABUSYS_ENV: 開発モード（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）デフォルト `INFO`
- DUCKDB_PATH: DuckDB ファイルパス デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視 DB などの SQLite パス デフォルト `data/monitoring.db`

設定は `from kabusys.config import settings` でアクセスできます（例: settings.jquants_refresh_token）。

.env のパースはシェルライクなクォートやコメントに対応します。

---

## セットアップ手順（開発者向け）

1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または: pip install duckdb defusedxml
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=your_refresh_token
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=your_password
5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで次を実行:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - これにより必要なテーブルとインデックスが作成されます。

---

## 使い方（よく使う API・ワークフロー）

以下は主要な一連の操作例です。詳細は各モジュールのドキュメント文字列を参照してください。

1) DB 初期化
- 初回のみ:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 既存 DB へ接続:
  from kabusys.data.schema import get_connection
  conn = get_connection("data/kabusys.duckdb")

2) 日次 ETL 実行（市場カレンダー / 日足 / 財務）
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

3) 特徴量生成（features テーブルへの書き込み）
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date.today())
  print(f"features upserted: {n}")

4) シグナル生成（signals テーブルへの書き込み）
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals written: {total}")

5) ニュース収集（RSS）
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203", "6758"})
  print(res)

6) カレンダーの夜間更新ジョブ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

7) J-Quants からのデータ直接取得（テストやバックフィル）
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
  saved = save_daily_quotes(conn, records)

注意:
- すべての「日付単位の置換」処理はトランザクションで実行され、冪等性が保たれます。
- ETL の一部や API 呼び出しは外部サービスやネットワークに依存するため、実行時に例外が発生する可能性があります。ログを参照してください。

---

## ディレクトリ構成（主要ファイル）

以下はこのコードベース内の主要モジュール構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - news_collector.py             -- RSS ニュース収集・保存
    - schema.py                     -- DuckDB スキーマ定義・初期化
    - stats.py                      -- 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- マーケットカレンダー操作・更新
    - features.py                   -- features 用の公開インターフェース
    - audit.py                      -- 監査ログ関連 DDL
    - (その他: execution 層関連ファイル)
  - research/
    - __init__.py
    - factor_research.py            -- Momentum / Volatility / Value の算出
    - feature_exploration.py        -- forward returns / IC / summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py        -- features を作成して DB に保存
    - signal_generator.py           -- final_score 計算と signals 生成
  - execution/                      -- 発注・約定管理（実行層）
  - monitoring/                     -- 監視・アラート（存在する場合）

（上記はコードベースの主要モジュールを示した抜粋です。詳細はソースを参照してください。）

---

## 開発上の注意点 / 既知の挙動

- DuckDB に格納する日付/タイムスタンプは基本的にタイムゾーンを含まない設計になっています（UTC を前提に取得時に正規化してください）。
- J-Quants API はページネーションとレート制限（120 req/min）に対応しています。モジュール内部で RateLimiter とリトライを実装済みです。
- news_collector は SSRF や XML 攻撃対策（defusedxml、ホスト/IP のチェック、レスポンスサイズ制限、gzip 解凍後サイズチェック）を行っています。
- 設定読み込みは .env / .env.local をプロジェクトルートから自動読み込みします。自動ロードを無効化する際は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかである必要があります。

---

## 貢献・ライセンス

ライセンス情報や貢献ガイドラインはリポジトリに含めてください（本 README では省略）。

---

必要であれば、各モジュール（jquants_client、pipeline、feature_engineering、signal_generator、news_collector、calendar_management）の具体的なサンプルコードやユニットテストの例も追加します。どの部分を詳しく書いて欲しいか教えてください。