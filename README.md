# KabuSys

日本株向けの自動売買／データプラットフォーム基盤ライブラリ (KabuSys)

このリポジトリは、J-Quants API 等から日本株データを取得して DuckDB に保存し、ETL / 品質チェック / ニュース収集 / カレンダー管理 / 監査ログ（発注〜約定のトレーサビリティ）までを提供するモジュール群です。自動売買システムのデータ基盤と実行基盤の基礎を構築することを目的としています。

バージョン: 0.1.0

---

## 主な機能

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務（BS/PL）、JPX マーケットカレンダー取得
  - レート制限（120 req/min）対応 / 再試行（指数バックオフ） / 401 時のトークン自動リフレッシュ
  - 取得時に fetched_at を UTC で記録（Look-ahead バイアス対策）
  - DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）

- ETL パイプライン
  - 差分更新（最終取得日を基準に未取得範囲のみ取得）
  - backfill による後出し修正吸収
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリーポイント

- ニュース収集（RSS）
  - RSS 取得、前処理（URL 除去・空白正規化）
  - 記事ID は正規化 URL の SHA-256（先頭32文字）で冪等性保証
  - SSRF 対策（スキーム検証、プライベートアドレス拒否、リダイレクト検査）
  - defusedxml による XML 攻撃対策
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING）

- マーケットカレンダー管理
  - 営業日判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - DB に基づく優先判定、未取得日の曜日フォールバック
  - 夜間カレンダー更新ジョブ

- 品質チェック（quality モジュール）
  - 欠損データ、異常スパイク、主キー重複、日付不整合の検出
  - QualityIssue 型で問題を返却（error / warning）

- 監査ログ（audit）
  - signal → order_request → execution のトレースを保存する監査テーブル群
  - 発注の冪等性（order_request_id）と UTC タイムスタンプ

---

## セットアップ

前提: Python 3.9+（型ヒントに | 型注釈があるため 3.10+ を推奨します）。依存ライブラリの最小セット:

- duckdb
- defusedxml

例: 仮想環境を作成して必要パッケージをインストールする手順

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb defusedxml
# 開発インストール (プロジェクトに pyproject.toml/setup.py があれば)
# pip install -e .
```

環境変数の設定:
- プロジェクトルートの .env または .env.local、または OS 環境変数で設定します。
- 自動ロードの優先順位: OS 環境変数 > .env.local > .env
- 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト向け）。
- プロジェクトルートの検出基準は .git または pyproject.toml があるディレクトリです。

必要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（オプション、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)

簡易な .env.example:

```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（主な操作例）

以下は Python REPL やスクリプトから呼び出す例です。DBパスを指定してスキーマを初期化し、ETL / ニュース収集を実行できます。

1) DuckDB スキーマ初期化

```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# またはインメモリ:
# conn = init_schema(":memory:")
```

2) 監査ログ用スキーマ初期化（既存 conn に追加）

```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)  # conn は init_schema の返り値
```

3) 日次 ETL を実行する（市場カレンダー取得 → 株価 → 財務 → 品質チェック）

```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定可能。id_token を注入してテストも可能。
print(result.to_dict())
```

オプション例（backfill を変更、品質チェック無効化など）:

```python
result = run_daily_etl(conn, backfill_days=1, run_quality_checks=False)
```

4) ニュース収集ジョブ（RSS → raw_news に保存）

```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "8306"}  # 既知の銘柄コードセット
results = run_news_collection(conn, sources=None, known_codes=known_codes)
print(results)  # {source_name: saved_count}
```

5) J-Quants API を直接使ってデータ取得（テスト・デバッグ）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
# id_token を取得・注入可能
token = get_id_token()
recs = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

ログレベルは環境変数 LOG_LEVEL で調整してください。

---

## よくある操作のヒント

- 自動で .env を読み込まないようにするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- テスト時は id_token を外から注入してネットワーク依存を切ると簡単です。
- news_collector は外部 URL にアクセスするため、テストでは _urlopen をモックできます。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。必要に応じて DUCKDB_PATH を設定してください。

---

## ディレクトリ構成

主要モジュール・ファイル一覧（src/kabusys 以下）:

- __init__.py
  - パッケージのエクスポート: data, strategy, execution, monitoring
- config.py
  - 環境変数読み込みと Settings クラス（必須変数取得・バリデーション・自動 .env ロード）
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（取得 / レート制御 / リトライ / 保存関数）
  - news_collector.py
    - RSS ニュース取得・前処理・SSRF 対策・DuckDB 保存
  - pipeline.py
    - ETL パイプライン（差分更新・日次統合処理）
  - calendar_management.py
    - market_calendar の管理、営業日判定・検索
  - schema.py
    - DuckDB スキーマ定義と init_schema, get_connection
  - audit.py
    - 監査ログ用スキーマ（signal_events / order_requests / executions 等）
  - quality.py
    - データ品質チェック（missing / spike / duplicates / date_consistency）
- strategy/
  - __init__.py
  - （戦略実装を置くための名前空間）
- execution/
  - __init__.py
  - （発注・約定管理等の実装を置くための名前空間）
- monitoring/
  - __init__.py
  - （監視・アラート周りの実装を置くための名前空間）

---

## 開発・拡張ポイント

- strategy / execution / monitoring は現在プレースホルダですが、ETL・監査・データレイヤーは整備済みです。戦略や約定ロジックを実装して統合してください。
- J-Quants のレート制限や 401 の自動リフレッシュ処理が組み込まれているため、ページネーションを含む長時間ジョブでも安全に動作します。
- news_collector は SSRF・Gzip bomb 等に対する対策を取り入れています。外部 RSS ソースを追加する際は DEFAULT_RSS_SOURCES を編集してください。
- DuckDB スキーマは冪等に作成されます。新規カラム追加・DDL 変更時はマイグレーション戦略を検討してください。

---

## ライセンス / 注意

- このドキュメントはコードベースの解析から作成しています。実際の運用では J-Quants / kabuステーション / 各サービス利用規約を遵守してください。
- 実環境（特に live 環境）で運用する場合は、十分なテスト・リスク管理（注文二重送信防止、監査ログの保全、アクセス制御等）を実装してください。

---

質問や使い方の具体的なサンプルが必要であれば、どの機能（ETL、ニュース収集、監査スキーマ、J-Quants 呼び出し等）について詳しく示すか教えてください。必要に応じて実行スクリプト例や unittest のサンプルも作成します。