# KabuSys

日本株向け自動売買データ基盤およびETLライブラリ

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたデータ収集・加工・品質管理のためのライブラリ群です。J-Quants API や RSS フィードからのデータ収集、DuckDB への冪等的保存、品質チェック、マーケットカレンダー管理、監査ログ（発注→約定のトレース）などの機能を提供します。

主な設計方針：
- API レート制限とリトライを組み込んだ堅牢なデータ取得
- DuckDB を用いたローカルDB に対する冪等保存（ON CONFLICT）
- Look-ahead bias を避けるための fetched_at / UTC タイムスタンプの記録
- RSS の安全なパース（defusedxml）や SSRF 対策等のセキュリティ配慮
- 品質チェック (欠損・重複・スパイク・日付整合性) を組み込み

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local 自動読み込み（プロジェクトルート基準）
  - 環境変数の必須チェック・型整備（settings）

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務四半期データ、JPX マーケットカレンダー取得
  - レートリミット（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等保存用の save_* 関数

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（backfill 対応）
  - 日次 ETL 実行（カレンダー → 株価 → 財務 → 品質チェック）
  - ETL 実行結果を ETLResult として集約

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日の判定、前後の営業日の取得
  - 夜間カレンダー更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、記事正規化、tracking パラメータ除去、ID（SHA-256 先頭32文字）生成
  - SSRF 対策、レスポンスサイズ上限、防御的XML処理
  - DuckDB への冪等保存（raw_news, news_symbols）

- スキーマ初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス作成

- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで結果を返す

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution までのトレーサビリティ用テーブル群の初期化

---

## 前提条件（Prerequisites）

- Python 3.10+
- pip
- 必要パッケージ（最低限）:
  - duckdb
  - defusedxml

必要に応じて追加パッケージ（HTTP クライアント等）をプロジェクトに追加してください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されていれば）pip install -e .

4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要な環境変数を配置することで自動読み込みされます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数（settings から）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

任意／デフォルト値あり:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1で自動ロードを無効化)
- KABUSYS_* その他は code 中で参照されるものを確認してください

データベースパス（デフォルト）:
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db

---

## 使い方（簡易ガイド）

以下は代表的な利用例です。Python スクリプトや REPL から呼び出して利用できます。

- DuckDB スキーマ初期化

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

- 監査ログ用スキーマ初期化（既存接続に追加）

```python
from kabusys.data import audit
# conn は schema.init_schema などで得た接続
audit.init_audit_schema(conn, transactional=True)
```

- 日次 ETL を実行（J-Quants トークンは settings を使用）

```python
from kabusys.data import pipeline, schema
conn = schema.init_schema("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集ジョブを実行（既知の銘柄コード集合を渡すことで銘柄紐付けを行う）

```python
from kabusys.data import news_collector, schema
conn = schema.init_schema("data/kabusys.duckdb")
known_codes = {"7203", "6758", "9984"}  # 例: 有効な銘柄コードセット
results = news_collector.run_news_collection(conn, known_codes=known_codes)
print(results)
```

- カレンダー更新ジョブ（夜間バッチ想定）

```python
from kabusys.data import calendar_management, schema
conn = schema.init_schema("data/kabusys.duckdb")
saved = calendar_management.calendar_update_job(conn)
print(f"saved: {saved}")
```

- 直接 J-Quants API からデータを取得する（トークンは settings から自動取得）

```python
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意事項:
- run_daily_etl などは内部で品質チェックや例外ハンドリングを行いますが、呼び出し側で結果（ETLResult）をログや監視に送るようにしてください。
- 実行環境が production（live）の場合は KABUSYS_ENV を `live` に設定して安全チェックやログレベル等を切り替えてください（settings.is_live 等で確認可能）。

---

## 環境変数・設定（まとめ）

主要な環境変数（settings で参照）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env 読み込みを無効化）

.env ファイルのパースルール:
- export KEY=val 形式を許可
- シングル/ダブルクォート内のエスケープに対応
- 行末のコメントは、クォート外かつ直前が空白／タブの場合のみ扱う

---

## ディレクトリ構成

パッケージの主要ファイルとディレクトリ（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、.env 自動読み込み
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - news_collector.py      — RSS ニュース収集・保存
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - schema.py              — DuckDB スキーマ定義・初期化
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログ（トレーサビリティ）初期化
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略関連（将来的に拡張）
  - execution/
    - __init__.py            — 発注 / ブローカー連携（将来的に拡張）
  - monitoring/
    - __init__.py            — 監視・メトリクス（将来的に拡張）

注: 上記は現在のコードベースに含まれるモジュールの一覧です。strategy / execution / monitoring は初期化ファイルのみで、将来的な実装が想定されています。

---

## ロギング・監視

- 各モジュールは標準の Python ロギングを使用しています。LOG_LEVEL 環境変数でログ出力レベルを制御してください。
- ETL やニュース収集では警告／エラー時に logger.warning / logger.error / logger.exception を出力します。運用時はファイル出力や外部監視（例: Slack 通知）と連携してください（Slack トークン等は設定済み）。

---

## セキュリティ・運用注意点

- RSS の XML パースは defusedxml を使用し XML Bomb 等に対処しています。
- fetch_rss は SSRF 対策（スキーム検証、プライベートIPフィルタ、リダイレクト検査、レスポンスサイズ上限）を実施しています。
- J-Quants API クライアントは 401 時に自動でトークンをリフレッシュしますが、無限再帰を避けるための保護ロジックがあります。
- DuckDB はローカルファイルにデータを保存します。バックアップやファイル権限の管理を行ってください。

---

## 貢献・拡張

- strategy / execution / monitoring の各モジュールは今後の拡張ポイントです。戦略の実装、発注ライブラリ（kabu API 連携）、モニタリングダッシュボード等を統合することができます。
- テストは各モジュールの外部依存（HTTP, J-Quants, RSS など）をモックして行うのが容易な設計です（id_token 注入や _urlopen のモック等を用意）。

---

必要であれば README に具体的な .env.example のサンプル、CI/CD や運用スケジュール（cron / Airflow ジョブの例）を追加します。どのような追加情報が欲しいか教えてください。