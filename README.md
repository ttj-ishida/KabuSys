# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（KabuSys）です。  
本リポジトリはデータ取得・ETL、データ品質チェック、ニュース収集、マーケットカレンダー管理、監査ログ（発注→約定のトレーサビリティ）など、システムの基盤機能を提供します。

主な設計方針:
- データの冪等性（ON CONFLICT を利用した安全な保存）
- 外部API呼び出しのレート制御・リトライ・トークン自動リフレッシュ
- Look-ahead bias 回避のため取得時刻（UTC）を記録
- ニュース収集時の SSRF 保護、XML インジェクション対策、受信サイズ制限
- DuckDB を用いたローカルデータレイク構成

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（OS 環境変数優先）
  - 必須環境変数の明示的取得
- J-Quants API クライアント（`kabusys.data.jquants_client`）
  - 株価日足（OHLCV）、四半期財務データ、JPX カレンダー取得
  - レートリミッタ（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存関数（save_*）
- ETL パイプライン（`kabusys.data.pipeline`）
  - 差分更新ロジック（最終取得日からの差分取得、backfill）
  - 日次 ETL エントリポイント（run_daily_etl）
  - 品質チェック（quality モジュールとの連携）
- データスキーマ（`kabusys.data.schema`）
  - Raw / Processed / Feature / Execution 層の DuckDB スキーマ定義
  - スキーマ初期化・接続ヘルパー（init_schema / get_connection）
- ニュース収集（`kabusys.data.news_collector`）
  - RSS 取得・前処理（URL除去・空白正規化）
  - 記事ID：正規化 URL の SHA-256（先頭32文字）
  - SSRF 対策、defusedxml による XML 安全化、受信サイズ制限
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（`kabusys.data.calendar_management`）
  - 営業日の判定、前後営業日取得、カレンダーの夜間差分更新ジョブ
- 監査ログ（`kabusys.data.audit`）
  - signal / order_request / execution を含む監査用テーブル群・初期化
  - UTC タイムゾーン固定、トランザクションオプション
- データ品質チェック（`kabusys.data.quality`）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
  - 問題は QualityIssue オブジェクトで集約（error / warning）

---

## 前提（Prerequisites）

- Python 3.10 以上（typing の新構文を使用）
- 必須ライブラリ（代表例）
  - duckdb
  - defusedxml
- 標準ライブラリ（urllib, json, logging 等）

インストール例（開発時）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# パッケージを開発モードでインストールする場合（プロジェクトルートに setup/pyproject がある想定）
pip install -e .
```

（プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して依存パッケージをインストール
3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト等で使用）。
4. DuckDB スキーマ初期化（例: data/kabusys.duckdb を作成）
   - Python REPL やスクリプトから init_schema を呼ぶ（例は次節の使い方参照）。

必須（または推奨）環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuステーション API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（省略時: data/monitoring.db）
- KABUSYS_ENV: 開発環境フラグ（development / paper_trading / live、省略時: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、省略時: INFO）

例 .env:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## 使い方（主要ユースケース）

以下は基本的な Python からの操作例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

# settings.duckdb_path はデフォルト "data/kabusys.duckdb"
conn = init_schema(settings.duckdb_path)
# conn は duckdb.DuckDBPyConnection
```

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を渡せば任意日を処理できます
print(result.to_dict())
```

3) ニュース収集ジョブの実行（RSS -> raw_news, news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")

# known_codes: 銘柄抽出に使う有効な銘柄コード集合（例: DBから取得）
known_codes = {"7203", "6758", "9984"}

results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

4) カレンダー夜間バッチ更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved: {saved}")
```

5) 監査ログ用スキーマ初期化（既存 conn に追加）
```python
from kabusys.data.schema import init_schema
from kabusys.data.audit import init_audit_schema

conn = init_schema("data/kabusys.duckdb")
init_audit_schema(conn, transactional=True)
```
あるいは監査専用DBを作る:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 実装上の注目点（設計・安全性）

- J-Quants クライアント
  - レートリミット: 120 req/min 固定スロットリング（_RateLimiter）
  - リトライ: 指数バックオフ（最大 3 回）、408/429/5xx を対象
  - 401: トークン自動リフレッシュを 1 回行って再試行
  - ページネーション対応（pagination_key）

- ニュース収集
  - defusedxml による XML パース（XMLBomb 等防止）
  - リンク正規化（トラッキングパラメータ除去）→ SHA-256（先頭32文字）で記事ID生成
  - SSRF 対策: リダイレクト先のスキーム・ホスト検証、プライベートIP拒否
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査

- データ品質チェック
  - 欠損（OHLC の NULL）、重複、スパイク（前日比 ±閾値）、将来日付 / 非営業日データ検出
  - 問題は QualityIssue オブジェクトで集約して返却

- スキーマ
  - Raw / Processed / Feature / Execution / Audit の多層構造
  - 多くのテーブルは PRIMARY KEY / CHECK 制約を持ち、データ整合性を高める
  - インデックスを作成しクエリパフォーマンスに配慮

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）
```
src/
  kabusys/
    __init__.py
    config.py                    # 環境変数・設定管理
    data/
      __init__.py
      jquants_client.py          # J-Quants API クライアント（取得 + 保存）
      news_collector.py          # RSS ニュース収集 / 保存
      schema.py                  # DuckDB スキーマ定義・初期化
      pipeline.py                # ETL パイプライン（run_daily_etl 等）
      calendar_management.py     # マーケットカレンダー管理
      audit.py                   # 監査ログスキーマ・初期化
      quality.py                 # データ品質チェック
    strategy/
      __init__.py                # 戦略層（将来的に実装）
    execution/
      __init__.py                # 発注/実行層（将来的に実装）
    monitoring/
      __init__.py                # 監視・アラート（将来的に実装）
```

---

## 開発・運用上の注意事項

- .env 自動読み込み
  - プロジェクトルート（.git または pyproject.toml を起点）から `.env` と `.env.local` を読み込みます。
  - 読み込み優先度: OS 環境 > .env.local > .env
  - テスト等で自動ロードを抑止するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- 時刻・タイムゾーン
  - 取得時刻や監査ログのタイムスタンプは UTC を利用する設計です（保存前に UTC に変換）。

- テスト可能性
  - jquants_client や news_collector の HTTP 呼び出しは内部関数（例: _urlopen）をモックしやすい構造になっています。

- 安全性
  - ニュース収集・RSS パースは defusedxml を使用。
  - 外部 URL へのアクセスはスキーム/ホスト検証を行い、プライベートネットワークへのアクセスを避けます。

---

## 追加情報 / 今後の拡張

- strategy / execution / monitoring モジュールは骨組みとして存在します。戦略実装、ブローカ（kabuステーション）連携、監視ルールは今後実装されます。
- 本 README は現在のコードベースに基づく概要であり、詳細は各モジュールの docstring を参照してください。

---

ご不明点や README に追加したい項目（例: CI、デプロイ手順、具体的な戦略テンプレートなど）があれば教えてください。README を追記・改良します。