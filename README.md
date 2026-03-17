# KabuSys

日本株向け自動売買データ基盤およびETLライブラリ。  
J-Quants API や RSS を用いたデータ取得、DuckDB によるスキーマ定義・永続化、品質チェック、監査ログ用スキーマなどを備えた基盤モジュール群です。

主な用途
- J-Quants からの株価・財務・市場カレンダー取得と DuckDB への保存（冪等）
- RSS からのニュース収集と銘柄紐付け
- 日次 ETL パイプライン（差分更新、バックフィル、品質チェック）
- JPX カレンダー管理（営業日判定・前後営業日検索）
- 監査ログ（シグナル→発注→約定までのトレーサビリティ）用スキーマ初期化
- データ品質チェック（欠損・重複・スパイク・日付不整合）

バージョン: 0.1.0

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定取得ヘルパ（settings オブジェクト）
  - 環境: development / paper_trading / live、ログレベル検証
- kabusys.data.jquants_client
  - J-Quants API クライアント（ID トークン取得、ページネーション、リトライ、レート制御）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB へ保存する save_* 関数（冪等、ON CONFLICT 処理）
- kabusys.data.news_collector
  - RSS フィード取得（SSRF/リダイレクト対策、gzip・サイズ上限、defusedxml）
  - 記事正規化（URL トラッキング除去）、SHA-256 による記事ID生成（先頭32文字）
  - raw_news / news_symbols へのバルク保存（トランザクション、INSERT ... RETURNING）
  - 銘柄コード抽出（4桁数字＋ known_codes フィルタ）
- kabusys.data.schema
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - init_schema(db_path) で全テーブル・インデックスを冪等に作成
  - get_connection(db_path) で既存 DB への接続を取得
- kabusys.data.pipeline
  - ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl / run_daily_etl）
  - 差分更新ロジック、バックフィル、品質チェック連携
- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job による夜間カレンダー差分更新
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events, order_requests, executions）と初期化関数
  - init_audit_schema / init_audit_db
- kabusys.data.quality
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - run_all_checks でまとめて実行し QualityIssue リストを返す

---

## セットアップ手順

前提
- Python 3.9+（ソースで typing | None などを使っているため 3.9 以降を想定）
- DuckDB（Python パッケージ経由で利用）
- ネットワークアクセス（J-Quants/API、RSS）

推奨インストール手順（ローカル開発）:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト化している場合）pip install -e .

   ※ requirements.txt がない場合は必要なパッケージを上記のように個別インストールしてください。

3. 環境変数（.env）を用意
   リポジトリルートに .env（または .env.local）を置くと自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。自動ロードは .git または pyproject.toml を基準にプロジェクトルートを検出します。

   最低限設定が必要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

   任意 / デフォルトあり:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
   - SQLITE_PATH: data/monitoring.db（デフォルト）

4. DuckDB の初期化
   - Python REPL またはスクリプト内で schema.init_schema() を呼び出して DB を初期化します（ファイルパスの親ディレクトリは自動作成されます）。

   例:
   ```py
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

5. 監査ログ用 DB（任意）
   - 監査ログを別 DB にしたい場合:
   ```py
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

環境変数と DB を準備したあと、ETL を実行する典型的なコード例:

- 日次 ETL を実行（市場カレンダー取得→株価/財務差分取得→品質チェック）
```py
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from datetime import date

# DB 初期化（初回のみ）
conn = init_schema(settings.duckdb_path)

# ETL 実行（省略時は target_date = today）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブの実行
```py
from kabusys.data.schema import init_schema
from kabusys.data.news_collector import run_news_collection

conn = init_schema("data/kabusys.duckdb")

# known_codes は有効な銘柄コードのセット（抽出に使用）
known_codes = {"7203", "6758", "6954", ...}

results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: saved_count, ...}
```

- カレンダー夜間更新ジョブ
```py
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

- J-Quants の ID トークン取得（テストや低レベル利用）
```py
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を用いて POST 取得
```

- audit スキーマの初期化（既存接続に追加）
```py
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```

注意点 / 運用ヒント
- run_daily_etl は各ステップで例外を捕捉し続行する設計です。戻り値の ETLResult.errors / quality_issues を監視して運用判断を行ってください。
- J-Quants クライアントは内部で固定間隔スロットリング（120 req/min）とリトライ（指数バックオフ）を行います。
- fetch_rss は SSRF 対策、サイズ上限、gzip 解凍の安全対策を実装しています。
- DuckDB ファイルパスに ":memory:" を渡すとインメモリ DB になります（テスト向け）。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション（デフォルトを示す）:
- DUCKDB_PATH (data/kabusys.duckdb)
- SQLITE_PATH (data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — default: development
- LOG_LEVEL (INFO 等) — default: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると .env 自動読み込みを無効化)

.env のパース仕様:
- export KEY=val 形式の行を許容
- シングル/ダブルクォート内のエスケープシーケンスに対応
- クォートなしの場合、インラインコメントは直前が空白/タブのときのみ '#' をコメントとみなす

---

## ディレクトリ構成（主要ファイル）

プロジェクト内の主要なファイル構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - execution/ (__init__.py)  # 発注・実行関連の拡張ポイント
    - strategy/  (__init__.py)  # 戦略実装用の名前空間
    - monitoring/ (__init__.py)  # 監視用モジュール（空のプレースホルダ）
    - data/
      - __init__.py
      - jquants_client.py         # J-Quants API クライアント（取得・保存）
      - news_collector.py        # RSS ニュース収集
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py   # 市場カレンダー管理ユーティリティ
      - audit.py                 # 監査ログスキーマ（signal/order/execution）
      - quality.py               # データ品質チェック

---

## 実装上の重要なポイント（運用者向け）

- 冪等性
  - 保存系関数（save_daily_quotes 等）は ON CONFLICT で重複を処理することで再実行耐性を持ちます。
  - news_collector は記事IDを URL 正規化→SHA256 の先頭32文字で生成し、重複挿入を防ぎます。

- レート制御 & リトライ
  - J-Quants クライアントは 120 req/min を守るため固定間隔（min_interval）でスロットリングします。
  - リトライは指数バックオフで最大 3 回。HTTP 401 はトークン自動リフレッシュを試みます（1 回のみ）。

- セキュリティ / 安全対策
  - RSS 取得では defusedxml を使用し XML Bomb を防止。
  - リダイレクト先のスキーム・プライベートアドレスチェックで SSRF を低減。
  - RSS レスポンスサイズ上限（デフォルト 10 MB）を設けてメモリDoS を防止。

- 品質チェック
  - run_all_checks はエラー/警告をすべて収集し、呼び出し側が重症度に応じて処理を決められる設計です。

---

## トラブルシューティング

- .env がロードされない
  - 自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）から行われます。テストなどで自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の権限エラー / ディレクトリがない
  - init_schema は親ディレクトリを自動作成しますが、OS 権限で作成できない場合は適切なディレクトリ権限を確認してください。
- API 呼び出しが 401 を返す
  - jquants_client は 401 受信時にリフレッシュトークンから id_token を再取得して1回リトライします。リフレッシュトークンが無効な場合は設定値（JQUANTS_REFRESH_TOKEN）を確認してください。
- 大量の RSS を投入した際のメモリ問題
  - news_collector はレスポンス読み込みサイズを制限していますが、独自の大量ソースを追加する際は chunk サイズや timeout を調整してください。

---

必要であれば、README に実行例スクリプト（systemd/cron 用の起動シェルや Dockerfile、CI 用のテスト例など）を追加します。どの実行環境向けのガイドが欲しいか教えてください。