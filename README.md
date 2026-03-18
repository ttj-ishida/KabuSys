# KabuSys

日本株向け自動売買基盤ライブラリ（パッケージ名: `kabusys`）

このリポジトリは、J-Quants API や RSS を用いたデータ収集、DuckDB を用いたデータ永続化、ETL パイプライン、データ品質チェック、監査ログスキーマなどを備えた日本株自動売買システムの基盤モジュール群を提供します。

主な設計方針：
- データ取得はレート制限・リトライ・トークンリフレッシュに対応
- データ保存は冪等（ON CONFLICT 句）を意識
- ニュース収集では SSRF / XML Bomb 等の安全対策を実装
- 品質チェックは Fail-Fast ではなく全問題を収集して呼び出し元で判断

---

## 機能一覧

- 環境設定管理
  - `.env` / `.env.local` の自動ロード（プロジェクトルート判定）
  - 必須環境変数チェック
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 日足（OHLCV）/ 財務データ / マーケットカレンダーの取得
  - レートリミッタ、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存ユーティリティ
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得・パース・前処理
  - 記事ID のハッシュ化（冪等）、SSRF や XML 攻撃対策、受信サイズ制限
  - DuckDB へのバルク保存（INSERT ... RETURNING）
  - 銘柄コード抽出・紐付け
- データスキーマ管理（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ定義・初期化
  - インデックス作成
- ETL パイプライン（`kabusys.data.pipeline`）
  - 日次 ETL（カレンダー → 日足 → 財務 → 品質チェック）
  - 差分更新・バックフィル・品質チェック統合
- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - 営業日判定、next/prev_trading_day、期間の営業日取得
  - カレンダー差分更新ジョブ
- 監査ログ（`kabusys.data.audit`）
  - シグナル → 発注要求 → 約定まで追跡する監査スキーマ
  - 監査用 DB 初期化ユーティリティ
- 品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク、重複、日付不整合の検出と QualityIssue レポート

---

## システム要件 / 依存関係

- Python 3.10 以上（型ヒントの union 型 `X | Y` を使用）
- 必須パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   ```

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（少なくとも実行する機能に応じて設定してください）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
   - 任意の環境変数:
     - KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト: development）
     - LOG_LEVEL — one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト: INFO）
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # ファイルがなければ作成されテーブルが作成される
   ```

6. 監査ログ DB の初期化（専用 DB を使う場合）
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（代表的な操作例）

- 日次 ETL 実行（株価・財務・カレンダー収集 + 品質チェック）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 省略時は今日が対象日
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS から記事を取得して保存、銘柄紐付けを行う）
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema(settings.duckdb_path)
  # known_codes: 有効な銘柄コード集合（抽出候補をフィルタリングするため）
  known_codes = {"7203", "6758", "9984"}
  stats = run_news_collection(conn, known_codes=known_codes)
  print(stats)  # {source_name: new_count, ...}
  ```

- 単体の J-Quants データ取得
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  # id_token を自前で取得して注入可能
  token = get_id_token()
  records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- マーケットカレンダー更新ジョブ
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print("saved:", saved)
  ```

- 品質チェックを単独で実行
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意点:
- `run_daily_etl` などは内部で try/except によりステップ単位でエラーを捕捉します。戻り値の ETLResult に errors / quality_issues が蓄積されるのでログだけでなく戻り値で判定してください。
- 自動環境変数ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト等で無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定するか、環境変数をプログラム側で直接注入してください。

---

## ディレクトリ構成

パッケージの主要ファイル／ディレクトリ構成（src 配下）:

- src/kabusys/
  - __init__.py
  - config.py
  - execution/
    - __init__.py
  - strategy/
    - __init__.py
  - monitoring/
    - __init__.py
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント（取得・保存ユーティリティ）
    - news_collector.py         -- RSS ニュース収集・保存・銘柄抽出
    - schema.py                 -- DuckDB スキーマ定義・初期化
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    -- 市場カレンダー管理・営業日判定
    - audit.py                  -- 監査ログ（signal/order/execution）のスキーマと初期化
    - quality.py                -- データ品質チェック
  - その他： strategy、execution、monitoring は骨格（拡張箇所）

---

## 実運用上の注意 / 設計上のポイント

- J-Quants API のレート制限（120 req/min）を考慮した RateLimiter を組み込んでいます。大量取得時は時間がかかることを想定してください。
- ニュース収集では外部からの悪意あるコンテンツ（XML Bomb、SSRF）対策を実装していますが、追加の防御が必要なケースは運用に応じて拡張してください。
- DuckDB はローカルファイルに書き込みます。バックアップ・排他制御（複数プロセスの同時書き込み）等の運用設計は環境に合わせて行ってください。
- 監査ログは削除しない前提で設計されています。スキーマの FK 制約やインデックスはトレーサビリティを強化しますが、運用のパフォーマンス面も考慮してください。
- 環境ごと（development / paper_trading / live）で挙動が切り替わるため、`KABUSYS_ENV` を適切に設定してください。

---

## 参考 / 開発者向けメモ

- 自動ロードされる `.env` のパースは厳密に実装されています（export 形式、クォート・エスケープ、コメント取り扱いなど）。
- DuckDB の初期化は `init_schema(db_path)` を使って行ってください。監査ログだけ別 DB にしたい場合は `init_audit_db(db_path)` を使用します。
- テスト時には `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化するとテスト環境構築が容易です。

---

必要であれば README にサンプル .env.example、CI 実行例、より詳細な運用手順（バックアップ・ロールアウト・監視）も追加できます。どの情報を追加したいか教えてください。