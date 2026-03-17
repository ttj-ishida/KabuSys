# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ集です。  
J-Quants / RSS 等からマーケットデータとニュースを収集し、DuckDB に格納して ETL → 品質チェック → 特徴量生成 → 発注フロー（監査ログ）へつなげるための基盤機能を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で安全に保存
- API レート制限・リトライ・トークン自動更新を内包
- Look-ahead bias 回避のため取得時刻(fetched_at) を記録
- RSS 収集は SSRF / XML Bomb / メモリ DoS 等の攻撃対策を実装
- DuckDB を中心に、軽量でローカル運用可能なデータレイヤを提供

---

## 機能一覧
- 環境設定管理（.env 自動読み込み、必須項目検査）
  - 自動ロード: プロジェクトルート（.git / pyproject.toml を探索）にある `.env` / `.env.local` を読み込み
  - 無効化: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダー取得
  - レートリミッタ（120 req/min）、リトライ（指数バックオフ）、401 のトークン自動リフレッシュ対応
  - DuckDB への保存ユーティリティ（冪等保存）
- ETL パイプライン（data.pipeline）
  - 差分取得（最終取得日を参照）、バックフィルオプション、自動営業日調整
  - 日次 ETL エントリポイント `run_daily_etl`
  - 品質チェック（欠損・スパイク・重複・日付不整合）と結果集約
- ニュース収集（data.news_collector）
  - RSS 取得・前処理・記事ID生成（正規化URL→SHA256）・DuckDB への冪等保存
  - SSRF / private host / gzip サイズ制限 / defusedxml による安全な処理
  - 銘柄コード抽出（テキスト中の4桁数字 → known_codes によるフィルタ）
- マーケットカレンダー管理（data.calendar_management）
  - JPX カレンダーの差分更新ジョブ、営業日判定、前後営業日取得、期間内営業日列挙
- スキーマ定義・初期化（data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル DDL を定義
  - インデックス作成、`init_schema()` による初期化
- 監査ログ（data.audit）
  - シグナル→発注要求→約定のトレースを担保する監査テーブル群と初期化関数
- データ品質チェック（data.quality）
  - 各種チェックを実行する API と QualityIssue 型

---

## 必要要件
- Python 3.10+（型注釈に Union 演算子や typing 機能を想定）
- pip パッケージ（例）:
  - duckdb
  - defusedxml

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# またはパッケージ化されていれば: pip install -e .
```

---

## 環境変数（主なキー）
設定は環境変数またはプロジェクトルートの `.env` / `.env.local` で行います。自動読み込みはデフォルトで有効です。

必須（アプリケーションで参照されるキー）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID

任意（デフォルト付き）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 `.env` 読み込みを無効化します（テスト等で利用）。

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（duckdb, defusedxml 等）
4. プロジェクトルートに `.env` を作成し、必要な環境変数を設定
   - 例: `.env` に `JQUANTS_REFRESH_TOKEN=xxxxx` を記載
5. DuckDB スキーマ初期化を実行

例:
```python
from kabusys.config import settings
from kabusys.data import schema
conn = schema.init_schema(settings.duckdb_path)
```

監査ログ用 DB を別途作る場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
```

---

## 使い方（代表的な API/ワークフロー例）

1) J-Quants ID トークン取得（内部で refresh token を使用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
```

2) スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

3) 日次 ETL 実行（カレンダー／株価／財務データ取得＋品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date 省略で今日
print(result.to_dict())
```

4) ニュース収集ジョブ実行（RSS → raw_news、news_symbols）
```python
from kabusys.data.news_collector import run_news_collection
# known_codes は抽出対象の銘柄コードセット（例: 東証銘柄一覧）
known_codes = {"7203", "6758", "9432"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # ソース毎の新規保存数を返す
```

5) カレンダー更新ジョブ（夜間バッチ等で実行）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved: {saved}")
```

6) 監査スキーマ適用（既存 conn に追加）
```python
from kabusys.data.audit import init_audit_schema
# conn は schema.init_schema() で作成した DuckDB 接続
init_audit_schema(conn)
```

7) individual fetch/save（テストやバックフィル用）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
saved_count = save_daily_quotes(conn, records)
```

---

## ロギング・環境
settings.log_level によりログレベルが制御されます（環境変数 LOG_LEVEL）。  
settings.env により環境 (development / paper_trading / live) を切替可能で、ライブ運用時の安全制御やモード分岐に利用してください。

---

## 実装上の注意点（重要）
- J-Quants API はレート上限 120 req/min に合わせて固定間隔スロットリングを実装しています。大量リクエストを行う場合はパフォーマンス制約に注意してください。
- jquants_client の _request は 401 を受け取ると自動で id_token をリフレッシュして一度だけリトライします（無限再帰は防止）。
- RSS 収集は外部入力を扱うため、URL スキーム/ホストの検証、レスポンスサイズ制限、gzip 解凍後のサイズチェック、defusedxml による安全なパース等が組み込まれています。別途 http クライアントを差し替える際はこれらの安全機構を維持してください。
- DuckDB に対する INSERT は多くが ON CONFLICT DO UPDATE / DO NOTHING により冪等性を保っています。ETL の再実行が安全に行える前提です。

---

## ディレクトリ構成
（主要ファイル・モジュールの抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理（自動 .env 読み込み）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存）
    - news_collector.py      — RSS → raw_news / news_symbols
    - schema.py              — DuckDB スキーマ定義と init_schema()
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログ（signal/order/execution）
    - quality.py             — データ品質チェック
    - pipeline.py
  - strategy/
    - __init__.py
    - (戦略実装モジュールを配置)
  - execution/
    - __init__.py
    - (ブローカー連携 / 発注ロジックを配置)
  - monitoring/
    - __init__.py
    - (監視用コードを配置)
- pyproject.toml / setup.cfg / README.md (本ファイル)

---

## 開発・貢献
- 仕様（DataPlatform.md 等）に基づいて機能が分割されています。新しいデータソースや戦略は各レイヤに沿って追加してください。
- テストを書く際は、config の自動 .env ロードを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用すると環境依存を避けられます。
- DuckDB の接続は軽量なので、テストでは `:memory:` を使うことができます（例: schema.init_schema(":memory:")）。

---

README は以上です。必要であれば以下を追加できます：
- .env.example の雛形
- もっと具体的な CLI / systemd / cron による日次ジョブ実行例
- 戦略・発注層の利用ガイド（strategy / execution 用のサンプル）