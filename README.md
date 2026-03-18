# KabuSys

KabuSys は日本株の自動売買プラットフォーム向けに設計された Python モジュール群です。J-Quants から市場データ・財務データ・カレンダーを取得し、DuckDB に蓄積、品質チェック、ニュース収集、監査ログなどを提供します。戦略層・実行層のための基盤機能（データレイヤ / ETL / カレンダー管理 / ニュース収集 / 監査）を実装しています。

主な設計方針：
- Idempotent（重複更新を避ける）な DB 書き込み（ON CONFLICT を活用）
- API レート制限やリトライ、トークン自動リフレッシュに対応
- Look-ahead bias を避けるため取得時刻（UTC）を記録
- RSS ニュース収集時の SSRF・XML 攻撃対策やサイズ制限
- DuckDB を中心とした軽量かつ高速なローカルデータストア

---

## 機能一覧

- 環境設定管理（自動 .env ロード、必須設定チェック）
  - 環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, KABUSYS_ENV, LOG_LEVEL
  - 自動ロード順序: OS 環境 > .env.local > .env（プロジェクトルート検出: .git または pyproject.toml）
  - テスト等で自動ロードを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- J-Quants API クライアント（data/jquants_client.py）
  - 株価日足（OHLCV）、財務データ、JPX カレンダーの取得
  - レート制限（120 req/min）・指数バックオフ・リトライ・401時のトークン自動リフレッシュ
  - DuckDB への安全な保存関数（冪等保存：ON CONFLICT）

- ETL パイプライン（data/pipeline.py）
  - 差分更新（DB の最終取得日に基づく取得範囲計算）
  - 市場カレンダー先読み、バックフィルによる後出し修正の吸収
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- マーケットカレンダー管理（data/calendar_management.py）
  - 営業日判定（is_trading_day、next_trading_day、prev_trading_day、get_trading_days、is_sq_day）
  - 夜間バッチ更新ジョブ（calendar_update_job）

- ニュース収集（data/news_collector.py）
  - RSS 取得・XML の安全パース（defusedxml）・URL 正規化・トラッキング削除・記事 ID（SHA-256 切り出し）生成
  - SSRF 対策（スキーム検査、プライベートIP拒否、リダイレクト検査）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO NOTHING / RETURNING で新規挿入を把握）
  - 銘柄コード抽出（正規表現により 4 桁コードを抽出、known_codes でフィルタ）

- データ品質チェック（data/quality.py）
  - 欠損データ・スパイク・重複・日付不整合の検出
  - QualityIssue オブジェクトで詳細レポートを返す

- スキーマ定義・初期化（data/schema.py）
  - Raw / Processed / Feature / Execution 層のテーブル DDL 定義
  - インデックス定義、init_schema() による初期化

- 監査ログ（data/audit.py）
  - シグナル → 発注要求 → 約定まで追跡可能な監査テーブル群
  - init_audit_db / init_audit_schema による初期化（UTC タイムゾーン固定）

---

## 前提・依存関係

- Python 3.10 以上（typing の | 演算子等を使用）
- 必要な Python パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発時はパッケージを編集可能モードでインストールする場合:
# pip install -e .
```

※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存を書いて管理してください。

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成・依存インストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```

3. 環境変数（.env）を作成
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（OS 環境変数を優先）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - SLACK_BOT_TOKEN: Slack ボットトークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意 / 既定値:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで初期化します。
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")  # メモリなら ":memory:"
   ```

5. 監査ログ DB 初期化（監査を別 DB にしたい場合）
   ```python
   from kabusys.data import audit
   audit_conn = audit.init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（例）

以下は主要機能の簡単な使用例です。スクリプトやジョブから呼び出して利用します。

- J-Quants から株価を取得して保存する
```python
from datetime import date
import duckdb
from kabusys.data import jquants_client as jq, schema

conn = schema.get_connection("data/kabusys.duckdb")
# 認証トークンは settings から自動利用する / 必要に応じ id_token を渡せる
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date.today())
saved = jq.save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data import pipeline, schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブ
```python
from kabusys.data import news_collector, schema

conn = schema.get_connection("data/kabusys.duckdb")
known_codes = {"7203","6758","9984"}  # 収集後に紐付けする銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

- カレンダー夜間バッチ更新
```python
from kabusys.data import calendar_management, schema

conn = schema.get_connection("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

- 品質チェックを手動実行
```python
from kabusys.data import quality, schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
issues = quality.run_all_checks(conn, target_date=date.today())
for i in issues:
    print(i)
```

---

## 主要モジュールとディレクトリ構成

簡略化したツリー（主要ファイルのみ）:

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定管理
    - data/
      - __init__.py
      - jquants_client.py        # J-Quants API クライアント（取得 + 保存）
      - news_collector.py        # RSS ニュース収集・保存・銘柄抽出
      - schema.py                # DuckDB スキーマ定義・初期化
      - pipeline.py              # ETL パイプライン（run_daily_etl 等）
      - calendar_management.py   # 市場カレンダー管理 / 営業日ロジック
      - audit.py                 # 監査ログ（signal/order/execution の監査）
      - quality.py               # データ品質チェック
    - strategy/
      - __init__.py              # 戦略関連（拡張ポイント）
    - execution/
      - __init__.py              # 実行・ブローカー連携（拡張ポイント）
    - monitoring/
      - __init__.py              # 監視関連（拡張ポイント）

各ファイルの役割（要約）
- config.py: .env 自動読み込み、必須設定の取得、環境フラグ（is_live / is_paper / is_dev）やログレベル検証
- jquants_client.py: API 呼び出しの共通処理（レートリミット・リトライ）、データ取得と DuckDB への保存関数
- news_collector.py: RSS 取得→前処理→記事保存→銘柄紐付けを行う一連処理
- schema.py: すべてのテーブル DDL とインデックスの定義、init_schema() で初期化
- pipeline.py: 日次 ETL のオーケストレーションと差分更新ロジック
- calendar_management.py: calendar_update_job と営業日ユーティリティ
- audit.py: 監査用テーブルと初期化ロジック
- quality.py: データ品質チェック群（欠損・スパイク等）

---

## 環境変数一覧（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知に必要（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル（必須）

オプション / 既定値あり:
- KABUSYS_ENV — "development" / "paper_trading" / "live"（既定: development）
- LOG_LEVEL — ログレベル（既定: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" にすると自動 .env ロードを無効化
- KABU_API_BASE_URL — kabu API ベース URL（既定: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（既定: data/monitoring.db）

---

## 注意事項 / 運用上のヒント

- J-Quants のレート制限（120 req/min）を守るため、jquants_client は内部でスロットリングを行います。複数プロセスで同時に呼ぶ場合、アプリ側で調整が必要です。
- DuckDB は単一プロセスでの読み書きに適した軽量ストレージです。複数プロセスから同時書き込みする設計の場合は注意してください。
- ニュース収集では外部 URL にアクセスするため SSRF や巨大レスポンス対策を入れていますが、運用環境に応じた追加制限（プロキシやアウトバウンド制限）も検討してください。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をテストで使うと .env 自動読み込みを無効化できます。CI/CD では環境変数注入の方法を検討してください。
- audit.init_audit_db() は UTC タイムゾーンを強制します（監査ログは UTC で統一）。

---

この README はプロジェクト内のコード（src/kabusys/*.py）からの情報に基づいて作成しています。実際の運用・配布時は pyproject.toml / requirements.txt / LICENSE・CONTRIBUTING ドキュメント等を整備してください。必要であればサンプルの docker-compose や systemd ユニット、cron ジョブ例も作成できます。