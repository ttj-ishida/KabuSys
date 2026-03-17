# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリです。  
J-Quants API からマーケットデータや財務データを取得し、DuckDB に保存・品質チェックを行い、ニュース収集や監査ログの管理までをサポートします。

バージョン: 0.1.0

---

## 概要

KabuSys は次の目的で設計された内部ライブラリです。

- J-Quants API を用いた株価（日足）・財務情報・マーケットカレンダー取得
- DuckDB を用いたデータ層（Raw / Processed / Feature / Execution）のスキーマ定義・初期化
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- RSS ベースのニュース収集（トラッキングパラメータ除去・SSRF対策・大容量防御）
- 監査ログ（シグナル→注文→約定のトレーサビリティ）用スキーマ
- 設定管理（.env の自動読み込み、環境変数経由の設定）

設計上のポイント：
- API レート制限（J-Quants: 120 req/min）に従う RateLimiter を実装
- HTTP リトライ（指数バックオフ）・401 時のトークン自動リフレッシュ対応
- DuckDB へは冪等に保存（ON CONFLICT）することで重複や再実行に強い
- ニュース収集はセキュリティ（SSRF、XML注入、メモリDoS）を配慮

---

## 主な機能一覧

- 設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）
  - 必須環境変数の取得ラッパー（`kabusys.config.settings`）

- J-Quants クライアント（kabusys.data.jquants_client）
  - ID トークン取得（refresh token）
  - 株価（日足）取得（ページネーション対応）
  - 財務データ（四半期）取得（ページネーション対応）
  - マーケットカレンダー取得
  - DuckDB への保存（raw_prices, raw_financials, market_calendar 等）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（最終取得日からの差分算出、バックフィル）
  - 日次 ETL 集約（カレンダー→株価→財務→品質チェック）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、前処理（URL 削除・空白正規化）
  - トラッキングパラメータ除去・URL 正規化・SHA-256 ベースの記事ID生成
  - SSRF 対策（スキーム確認・リダイレクト先のプライベートIP排除）
  - DuckDB への冪等保存（raw_news, news_symbols）

- スキーマ管理（kabusys.data.schema / audit）
  - DuckDB のテーブル定義（Raw / Processed / Feature / Execution）
  - 監査ログテーブル（signal_events, order_requests, executions）初期化

- データ品質チェック（kabusys.data.quality）
  - 欠損・重複・スパイク（前日比）・日付不整合検出
  - QualityIssue オブジェクトの返却（エラー／警告の分類）

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈で union 演算子 `T | None` を使用しているため）

推奨手順（プロジェクトルートで実行）:

1. リポジトリをクローン / 取得
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （必要に応じて）pip install -e . で開発インストール

備考:
- requirements.txt は本コードツリーに含まれていません。主要依存は上記の通りです（標準ライブラリの urllib, json 等を使用）。
- SQLite を利用するモジュール（監視等）に備えて sqlite3 は標準で使用可能です。

環境変数（.env）
- プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化）。
- 自動読み込みは、.git または pyproject.toml の存在する親ディレクトリをプロジェクトルートと判定して行われます。

必須（主な）環境変数例
- JQUANTS_REFRESH_TOKEN=<あなたの J-Quants リフレッシュトークン>
- KABU_API_PASSWORD=<kabu API 接続パスワード>
- SLACK_BOT_TOKEN=<Slack Bot Token>
- SLACK_CHANNEL_ID=<Slack チャネルID>
任意 / デフォルト
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live; 既定: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL; 既定: INFO)

.env の例:
```
# .env (例)
JQUANTS_REFRESH_TOKEN="xxxxxxxxxxxxxxxx"
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

.env パーサの特徴:
- `export KEY=val` 形式を許容
- シングル / ダブルクォート内のバックスラッシュエスケープをサポート
- コメントや行末コメントの取り扱いに配慮

---

## 使い方（すぐに試せる例）

以下のスニペットはプロジェクト内の Python インタープリタ等で実行します。

- DuckDB スキーマ初期化（推奨: 1 回目のみ）
```python
from kabusys.data.schema import init_schema
# デフォルトファイルパス（settings から取得しても良い）
conn = init_schema("data/kabusys.duckdb")
```

- 監査ログスキーマの初期化（既存接続に追加）
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema が返した接続を再利用できます
init_audit_schema(conn)
```

- 日次 ETL を実行（株価・財務・カレンダーを取得し品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

- ニュース収集ジョブを実行（既知銘柄コードを渡して紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes はサービス側で管理される銘柄コードセット（例: {'7203','6758'}）
known_codes = {"7203", "6758"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants の id_token を明示的に取得する例
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使用
print(token)
```

- 生データ保存関数を直接使う（fetch → save の流れ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
records = fetch_daily_quotes(code="7203", date_from=None, date_to=None)
saved = save_daily_quotes(conn, records)
print(f"saved {saved} rows")
```

エラーハンドリング:
- ETL / news collection は各ソース／ステップで例外を捕捉し、続行する設計です。戻り値や ETLResult の errors / quality_issues を参照して運用判断してください。

---

## 重要な設計・運用メモ

- レート制限
  - J-Quants への呼び出しは内部で固定間隔スロットリング（120 req/min）を行います。複数プロセスで同時に API を叩く場合は注意してください（外部での制御が必要な場合あり）。

- トークン管理
  - id_token はモジュールレベルでキャッシュされ、401 を受けた場合は自動リフレッシュして 1 回だけリトライします。

- ニュース収集の安全対策
  - URL のスキーム検証（http/https のみ）
  - リダイレクト先のプライベートアドレス拒否（SSRF 防止）
  - レスポンスサイズ上限（デフォルト 10MB）
  - defusedxml を用いて XML 関連の脆弱性を緩和

- 品質チェック
  - 欠損（OHLC）、重複、スパイク（前日比 50% 以上デフォルト）、日付不整合 を検出
  - 重大度（error/warning）を返却するので運用で対応方針を決定してください

- .env 自動読み込み制御
  - 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主なファイル）

プロジェクトは Python パッケージ `kabusys` として配置されています。主要モジュールは以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得 + 保存）
    - news_collector.py            -- RSS ベースのニュース収集
    - schema.py                    -- DuckDB スキーマ定義 / 初期化
    - pipeline.py                  -- ETL パイプライン（差分更新・日次 ETL）
    - calendar_management.py       -- カレンダー管理（営業日判定・更新バッチ）
    - audit.py                     -- 監査ログ（signal/order/execution）
    - quality.py                   -- データ品質チェック
  - strategy/
    - __init__.py                  -- 戦略関連（将来的な拡張）
  - execution/
    - __init__.py                  -- 発注・ブローカー連携（将来的な拡張）
  - monitoring/
    - __init__.py                  -- 監視用（将来的な拡張）

---

## 開発 / 貢献

- 型・ログ・例外の扱いを重視した設計になっています。新規機能追加や改善は既存の設計原則（冪等性・トレーサビリティ・セキュリティ）に従ってください。
- ユニットテストや統合テストでは、環境変数自動読み込みを無効にするため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定するとテストが安定します。
- network IO を伴う部分（news_collector._urlopen 等）はテスト時にモック可能な設計です。

---

ご不明点や README に追加したい具体的な使用例（CI/CD、Docker、運用手順など）があれば教えてください。必要に応じて追記・翻訳を行います。