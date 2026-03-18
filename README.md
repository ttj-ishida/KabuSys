# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API や RSS を用いたデータ収集、DuckDB を利用したスキーマ管理・ETL、品質チェック、監査ログ初期化などをサポートします。

※このリポジトリはライブラリ/モジュール群を提供することを目的としており、実際の発注連携（ブローカー連携）や運用ジョブは利用者側で組み合わせて使います。

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）と指数バックオフによるリトライ
  - 401 受信時にリフレッシュトークンで自動再取得
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィード取得 → 前処理 → raw_news への冪等保存（ON CONFLICT DO NOTHING）
  - URL 正規化とトラッキングパラメータ除去、SSRF や XML-Bomb 対策（defusedxml、受信サイズ制限）
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）で冪等性確保
  - 記事と銘柄コードの紐付け機能（news_symbols）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル DDL を定義
  - init_schema() による初期化と接続取得
  - 監査ログ用スキーマ（signal_events / order_requests / executions）初期化機能

- ETL パイプライン
  - run_daily_etl(): カレンダー取得 → 株価差分取得（backfill）→ 財務差分取得 → 品質チェック
  - 差分更新（DB 最終取得日ベース）とバックフィル設定
  - 品質チェック（欠損、重複、スパイク、日付不整合）

- マーケットカレンダー管理
  - 営業日判定、前後営業日取得、期間内営業日リスト取得等
  - カレンダー更新バッチ（calendar_update_job）

- 監査ログ初期化
  - 監査用 DB の初期化関数（init_audit_db / init_audit_schema）
  - UTC タイムゾーン固定、監査トレーサビリティ構造を提供

## 必要な環境変数

このプロジェクトは設定を環境変数（または .env / .env.local）から読み込みます。必須項目は以下。

- J-Quants / API 関連
  - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（必須）

- kabu ステーション（発注等）関連
  - KABU_API_PASSWORD : kabu API パスワード（必須）
  - KABU_API_BASE_URL : kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）

- Slack 通知（必要に応じて）
  - SLACK_BOT_TOKEN : Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID : 通知先チャンネル ID（必須）

- DB パス等（省略時はデフォルト）
  - DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH : SQLite（monitoring）DB パス（デフォルト: data/monitoring.db）

- 実行環境モード / ログ
  - KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動で .env / .env.local をプロジェクトルートから読み込みます（OS 環境変数が優先）。自動ロードを無効にする場合は環境変数を設定してください：

- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env の例（最低限）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

## セットアップ手順

前提: Python 3.9+（タイプヒントに Union | 等を使用しています。実際は 3.10+ を想定）および pip。

1. リポジトリをクローン
   - git clone ...

2. 必要なパッケージをインストール（例）
   - duckdb
   - defusedxml
   - 追加で requests 等（本コードは urllib を基本使用）

例:
```
python -m pip install duckdb defusedxml
```
※実プロジェクトでは requirements.txt / pyproject.toml を用意し、pip install -e . 等でインストールする想定です。

3. 環境変数 (.env) を準備
   - ルートに .env を作成するか、環境変数をエクスポートしてください。
   - .env.local は .env の上書きに使えます。

4. DuckDB スキーマ初期化
   - Python から schema.init_schema() を呼ぶことで DB と全テーブルを作成できます（デフォルトで親ディレクトリを作成）。

例:
```python
from kabusys.data import schema

conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ用 DB を別途用意する場合:
```python
from kabusys.data import audit

audit_conn = audit.init_audit_db("data/kabusys_audit.duckdb")
```

## 使い方（主要な利用例）

- 日次 ETL 実行（市場カレンダー/株価/財務/品質チェック）:
```python
from kabusys.data import schema, pipeline
from datetime import date

conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- 株価・財務データのみ差分 ETL を個別に実行:
```python
from kabusys.data import schema, pipeline
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
fetched, saved = pipeline.run_prices_etl(conn, target_date=date.today())
```

- RSS ニュース収集（raw_news 保存 + 銘柄紐付け）:
```python
from kabusys.data import schema
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出に使用する有効銘柄コードのセット（例: 上場銘柄一覧）
known_codes = {"7203", "6758", "9984"}
results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)
```

- J-Quants から直接データを取得（テスト用に id_token を注入可能）:
```python
from kabusys.data import jquants_client as jq
from kabusys.config import settings

id_token = jq.get_id_token()  # settings.jquants_refresh_token を利用
records = jq.fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

- 監査ログスキーマ初期化（既存接続に追加）:
```python
from kabusys.data import schema, audit

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn, transactional=True)
```

## 注意点・設計上のポイント

- J-Quants API のレート制限を厳守（既に実装で 120 req/min に制御）。
- API エラー時は指数バックオフ・最大リトライを行い、401 はリフレッシュトークンで自動更新します。
- データ保存はできる限り冪等（ON CONFLICT）を利用しているため、再実行でデータの重複を抑制します。
- ニュース収集では SSRF / XML 攻撃 / Gzip bomb 等への対策（受信サイズ制限、defusedxml、ホストプライベート判定）を実装しています。
- run_daily_etl は Fail-Fast ではなく、各ステップでエラーを集約して処理を継続する設計です（結果オブジェクト ETLResult にエラー・品質問題を収集します）。

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / Settings 管理（.env 読み込みロジック含む）
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（取得・保存ロジック）
  - news_collector.py              -- RSS ニュース収集 / 前処理 / 保存ロジック
  - pipeline.py                    -- ETL パイプライン（差分更新・品質チェック等）
  - schema.py                      -- DuckDB スキーマ定義・初期化
  - calendar_management.py         -- カレンダー管理・営業日判定
  - audit.py                       -- 監査ログスキーマ初期化（signal/order/execution）
  - quality.py                     -- データ品質チェック（欠損・重複・スパイク・日付不整合）
- strategy/
  - __init__.py                    -- 戦略モジュール（拡張ポイント）
- execution/
  - __init__.py                    -- 発注 / 約定管理（拡張ポイント）
- monitoring/
  - __init__.py                    -- 監視・メトリクス（拡張ポイント）

README に含まれているコードは、上記のようにモジュール単位で分かれています。strategy / execution / monitoring は拡張ポイントとして設計されています。

## 追加情報 / トラブルシュート

- 自動で .env を読み込まないようにしたい場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに有用）。

- ログ出力や詳細デバッグ:
  - LOG_LEVEL を DEBUG に設定してください。

- DuckDB がない場合:
  - pip で duckdb をインストールしてください： pip install duckdb

- セキュリティ:
  - news_collector は SSRF・XML 脆弱性や受信バッファのDoSに対処する設計ですが、外部 URL の取り扱いには十分ご注意ください。

---

必要であれば、インストール用の pyproject.toml / requirements.txt のテンプレート、サンプル .env.example、もしくは実運用向けの cron / systemd 用のジョブ例（ETL の定期実行）を追加で作成します。どれを希望しますか？