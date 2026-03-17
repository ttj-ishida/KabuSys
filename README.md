# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。J-Quants API や RSS を用いて市場データ・財務データ・ニュースを収集し、DuckDB に蓄積・品質チェックを行い、売買シグナルや監査ログを管理するためのモジュール群を提供します。

主な目的は「データ取得 → 整形 → 品質管理 → 戦略 / 発注 連携」がトレース可能かつ冪等（idempotent）に実行できる基盤を提供することです。

バージョン: 0.1.0

---

## 主な機能（概要）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - レート制限（120 req/min）の尊重、指数バックオフ・リトライ、401 時の自動トークンリフレッシュ
  - データ取得時の fetched_at（UTC）付与によるトレーサビリティ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS から記事を取得して前処理（URL 除去・空白正規化）
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）で冪等性保証
  - SSRF 対策（スキーム検証、ホストのプライベート判定、リダイレクト検査）
  - レスポンスサイズ上限・gzip 解凍検査・defusedxml による XML 攻撃対策
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING）

- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル（後出し修正吸収）
  - 市場カレンダー先読み（lookahead）、株価/財務データ取得と保存
  - 品質チェック（欠損・重複・スパイク・日付不整合検出）

- マーケットカレンダー管理
  - 営業日判定、前後営業日の取得、期間内営業日リスト取得
  - calendar_update_job による夜間差分更新・バックフィル

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 に至る UUID ベースのトレーサビリティテーブル群
  - 発注要求の冪等キー（order_request_id）・ステータス管理

- データスキーマ（DuckDB）
  - Raw / Processed / Feature / Execution / Audit 層に分けたテーブル定義
  - 各種インデックスの作成

---

## システム要件 / 依存関係

- Python 3.10 以上（PEP604 のユニオン型表記（A | B）を使用）
- 必要な Python パッケージ（主要なもの）
  - duckdb
  - defusedxml

（その他、プロジェクトによって Slack 連携や kabu API クライアント等の追加依存が必要になる場合があります）

例（仮の requirements.txt）:
```
duckdb>=0.7
defusedxml>=0.7
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
   - （例）git clone ...

2. Python 仮想環境の作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb defusedxml

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（デフォルト）。
   - 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN （J-Quants リフレッシュトークン）
     - KABU_API_PASSWORD （kabuステーション API パスワード）
     - SLACK_BOT_TOKEN （Slack ボットトークン）
     - SLACK_CHANNEL_ID （Slack チャンネルID）
   - 任意:
     - KABUSYS_ENV (development|paper_trading|live) - デフォルトは development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト INFO
     - DUCKDB_PATH （例: data/kabusys.duckdb）
     - SQLITE_PATH （監視用 DB、例: data/monitoring.db）

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース（DuckDB）スキーマの初期化
   - 下記の Usage を参照して Python から初期化します。

---

## 使い方（簡易ガイド）

以下は主要な操作のコード例です。

- DuckDB スキーマの初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は環境変数から読み込まれます
conn = schema.init_schema(settings.duckdb_path)
# またはメモリDB:
# conn = schema.init_schema(":memory:")
```

- 監査ログ（Audit）テーブルの追加初期化
```python
from kabusys.data import audit, schema
conn = schema.init_schema("data/kabusys.duckdb")
audit.init_audit_schema(conn)  # 既存接続に監査テーブルを追加
```

- 日次 ETL 実行（市場カレンダー、株価、財務、品質チェック）
```python
from kabusys.data import pipeline, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
result = pipeline.run_daily_etl(conn)
print(result.to_dict())  # ETL 結果のサマリ
```

- ニュース収集ジョブの実行（RSS）
```python
from kabusys.data import news_collector, schema
from kabusys.config import settings

conn = schema.init_schema(settings.duckdb_path)
# デフォルトの RSS ソースを使用
stats = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(stats)  # {source_name: 新規挿入件数, ...}
```

- J-Quants の生データを直接取得・保存
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings
import duckdb

id_token = jq.get_id_token()  # settings.jquants_refresh_token を用いて取得
records = jq.fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
conn = duckdb.connect(str(settings.duckdb_path))
jq.save_daily_quotes(conn, records)
```

- 品質チェックを個別で実行
```python
from kabusys.data import quality, schema
conn = schema.init_schema("data/kabusys.duckdb")
issues = quality.run_all_checks(conn)
for i in issues:
    print(i.check_name, i.severity, i.detail)
```

注意点:
- ETL は各ステップで独立したエラーハンドリングを行うため、部分的な失敗でも処理が続行されます。戻り値（ETLResult）で詳細を確認してください。
- J-Quants API はレート制限とリトライを組み込んでいますが、運用時は API 使用量に注意してください。
- news_collector は外部 URL を扱うため SSRF 等の攻撃対策が組み込まれています。テスト時に _urlopen をモックすると便利です。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意 / デフォルト:
- KABUSYS_ENV = development | paper_trading | live （デフォルト: development）
- LOG_LEVEL = INFO（デフォルト: INFO）
- DUCKDB_PATH = data/kabusys.duckdb（デフォルト）
- SQLITE_PATH = data/monitoring.db（デフォルト）
- KABUSYS_DISABLE_AUTO_ENV_LOAD = 1（自動 .env ロード無効化）

設定はプロジェクトルートの `.env` / `.env.local` から自動読み込みされます。.git または pyproject.toml をプロジェクトルート判定に使用します。

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py                -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      -- RSS ニュース収集・保存
    - schema.py              -- DuckDB スキーマ定義・初期化
    - pipeline.py            -- ETL パイプライン（差分取得・品質チェック）
    - calendar_management.py -- マーケットカレンダー管理・夜間更新ジョブ
    - audit.py               -- 監査ログテーブル定義・初期化
    - quality.py             -- データ品質チェック（欠損・重複・スパイク等）
  - strategy/
    - __init__.py            -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py            -- 発注/実行関連（拡張ポイント）
  - monitoring/
    - __init__.py            -- 監視用モジュール（拡張ポイント）

その他:
- .env.example (想定)        -- 必須環境変数のサンプル（存在すれば参照）

---

## 開発 / 運用上の注意

- 型注釈や設計文書（コメント）に基づいて実装されているため、拡張・ユニットテストは比較的容易です。
- DuckDB を用いるためローカルで軽量に動作します。運用時はバックアップや定期的な Vacuum（必要なら）を検討してください。
- セキュリティ: 外部 URL を扱う箇所（news_collector）は SSRF や XML 攻撃対策を実装していますが、運用環境のネットワークポリシーや追加の検査（プロキシ、WAF 等）も検討してください。
- J-Quants トークンや kabu API の資格情報は厳重に管理し、公開リポジトリに含めないでください。

---

以上が本リポジトリの概要とセットアップ・利用方法の基本です。詳細は各モジュールの docstring を参照してください（src/kabusys/data/*.py）。必要であれば README を拡張して CLI 例や運用手順（スケジューラ / systemd / Airflow 連携例）を追記できます。