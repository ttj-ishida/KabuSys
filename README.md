# KabuSys

KabuSys は日本株向けの自動売買プラットフォームの基盤ライブラリです。J-Quants API からの市場データ取得、DuckDB への永続化、ニュース収集、データ品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）などデータプラットフォーム／ETL／監査に必要な機能群を提供します。

主な設計方針は「冪等性」「トレーサビリティ」「安全な外部通信（SSRF 対策等）」「API レート制御」「再現性の高いデータ品質チェック」です。

---

## 機能一覧

- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min 固定間隔）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - DuckDB へ冪等に保存する save_* 関数（ON CONFLICT DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日を参照し未取得分のみ取得）
  - backfill による再取得（API の後出し修正を吸収）
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）

- ニュース収集（RSS）
  - RSS フィード取得、前処理（URL 除去・空白正規化）、記事IDは正規化 URL の SHA-256（先頭32文字）で冪等保証
  - SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
  - gzip 解凍上限、defusedxml による XML 攻撃保護、DuckDB にバルク挿入（INSERT ... RETURNING）

- マーケットカレンダー管理
  - JPX カレンダーの差分取得と保存
  - 営業日判定、前後営業日の取得、期間内営業日リスト生成（DB 優先、未登録日は曜日フォールバック）

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、重複チェック、日付整合性（未来日・非営業日データ）
  - QualityIssue オブジェクトで検出結果を返す（severity: error|warning）

- 監査ログ（Audit）
  - signal → order_request → execution の階層構造で監査テーブル提供
  - 発注冪等キー、ステータス管理、UTC タイムゾーン固定

---

## 動作要件

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - defusedxml
- （プロジェクト配布に requirements.txt があればそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローンまたは取得する。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Unix/macOS）または .venv\Scripts\activate（Windows）

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - プロジェクトに requirements.txt がある場合: pip install -r requirements.txt
   - 開発用にローカルインストールする場合:
     - pip install -e .

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）が検出されると、`.env` と `.env.local` が自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必要な環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネルID（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略可, デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（省略可, デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（モニタリング）パス（省略可, デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development, paper_trading, live のいずれか。デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから呼び出す基本例です。

- DuckDB スキーマを初期化して接続を取得する
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL を実行する（市場カレンダー・株価・財務・品質チェックを順に実行）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定しなければ今日
print(result.to_dict())
```

- 市場カレンダーの夜間更新のみを実行する
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn)
print(f"saved={saved}")
```

- RSS ニュース収集ジョブを実行する（既知の銘柄コードリストを渡すことで銘柄紐付けを行う）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758"}  # 例: トヨタ、ソニー
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

注意:
- J-Quants API 呼び出しは内部でレート制御（120 req/min）およびリトライを行います。
- get_id_token() はリフレッシュトークンを使って ID トークンを取得し、401 時の自動リフレッシュに対応します。

---

## ディレクトリ構成

典型的なソースツリー（本リポジトリの src 配下）:

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数と自動 .env ロード、Settings
  - data/
    - __init__.py
    - schema.py                    -- DuckDB スキーマ定義 / 初期化
    - jquants_client.py            -- J-Quants API クライアント（取得 + 保存）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py            -- RSS ニュース取得・前処理・保存
    - calendar_management.py       -- カレンダー管理・営業日ロジック
    - quality.py                   -- データ品質チェック
    - audit.py                     -- 監査ログ（発注→約定トレーサビリティ）
    - pipeline.py
  - strategy/
    - __init__.py                  -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                  -- 発注・注文管理（拡張ポイント）
  - monitoring/
    - __init__.py                  -- モニタリング / メトリクス（拡張ポイント）

上記のファイル群は各レイヤ（Raw / Processed / Feature / Execution）に対応するテーブル設計・ユーティリティを提供します。

---

## 開発メモ / 実装上の注意点

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を起点に行われます。CI やテストで自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB への書き込みは冪等性を考慮しており、raw レイヤは ON CONFLICT DO UPDATE / DO NOTHING を使用します。
- news_collector は SSRF・XML 攻撃・Gzip Bomb 等を考慮した堅牢な実装になっています（defusedxml、最大読み取りバイト数、リダイレクト検査、プライベートアドレスブロック）。
- quality モジュールは Fail-Fast ではなく問題を収集して返す設計です。呼び出し側でどの重大度で処理を中止するかを決めてください。
- audit.init_audit_schema() は接続の TimeZone を UTC に固定します。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を追記してください）

---

必要であれば README に使い方のより詳細なコード例（ETL のスケジュール実行、Slack 通知統合、kabu ステーションとの発注フロー等）を追加します。どの項目を詳しく書くか教えてください。