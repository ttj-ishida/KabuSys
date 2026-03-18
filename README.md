# KabuSys

日本株向けの自動売買基盤（ライブラリ）です。データ取得・ETL・品質チェック・マーケットカレンダー管理・ニュース収集・監査ログなど、アルゴリズム取引システムの基盤機能群を提供します。

主に以下を目的としたモジュール群を含みます。
- J-Quants API からの市場データ取得（株価・財務・カレンダー）
- RSS ベースのニュース収集と銘柄紐付け
- DuckDB を用いたスキーマ定義と冪等な保存処理
- 日次 ETL パイプラインとデータ品質チェック
- マーケットカレンダーの判定ユーティリティ
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

バージョン: 0.1.0

---

## 機能一覧

- 環境変数/設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得およびバリデーション
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、四半期財務、マーケットカレンダーの取得
  - レートリミット制御・リトライ・トークン自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・XML パース（defusedxml 使用）
  - URL 正規化（トラッキングパラメータ除去）、SSRF 対策、受信サイズ制限
  - raw_news テーブルへの冪等保存・記事IDは正規化 URL の SHA-256 ハッシュ
  - テキストからの銘柄コード抽出と news_symbols への紐付け
- スキーマ管理（kabusys.data.schema）
  - DuckDB のスキーマ定義（Raw / Processed / Feature / Execution 層）
  - init_schema / get_connection を提供
- ETL パイプライン（kabusys.data.pipeline）
  - 差分取得・バックフィル・品質チェックを含む日次 ETL（run_daily_etl）
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - 品質チェック呼び出し（kabusys.data.quality）
- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、next/prev trading day、期間内営業日取得
  - 夜間カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義
  - init_audit_schema / init_audit_db を提供
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue 出力）

（strategy, execution, monitoring パッケージは骨組みとして存在します）

---

## 動作要件

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 必須 Python パッケージ（最低限）
  - duckdb
  - defusedxml

必要に応じて別途 HTTP クライアント等を追加で使用できます（本コードは標準ライブラリの urllib を使用）。

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

プロジェクト配布方法に応じて、pip install -e . などを行ってください。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境の作成と依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```
3. 環境変数を設定
   - プロジェクトルートに `.env`（およびテスト用に `.env.local`）を配置すると、自動で読み込まれます（読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) — default: development
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — default: INFO
     - DUCKDB_PATH — default: data/kabusys.duckdb
     - SQLITE_PATH — default: data/monitoring.db
4. DuckDB スキーマ初期化
   Python REPL またはスクリプトで schema.init_schema を実行します:
   ```python
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```
5. 監査ログ用スキーマ（必要に応じて）
   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection("data/kabusys.duckdb")  # 既に init_schema している想定
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的な例）

- 日次 ETL 実行（例）
  ```python
  from datetime import date
  import logging
  from kabusys.data import schema, pipeline

  logging.basicConfig(level=logging.INFO)
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブ（RSS から収集して保存）
  ```python
  from kabusys.data import schema, news_collector

  conn = schema.get_connection("data/kabusys.duckdb")
  # known_codes は銘柄抽出に用いる有効なコードセット（任意）
  known_codes = {"7203", "6758", "9984"}
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- J-Quants API のトークン取得 / データ取得（低レベル）
  ```python
  from kabusys.data import jquants_client as jq

  idtok = jq.get_id_token()  # settings.jquants_refresh_token を使用
  quotes = jq.fetch_daily_quotes(id_token=idtok, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェック単独実行
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

注意点:
- J-Quants API のレート制限（120 req/min）に準拠する実装が組み込まれています。
- save_* 系関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）を意識して実装されています。
- news_collector は SSRF・XML Bomb・Gzip Bomb 等の安全対策を備えています。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意／デフォルト:
- KABUSYS_ENV — development | paper_trading | live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化するには 1 を設定

.env のパースは柔軟に実装されており、export プレフィックスやクォート、インラインコメント等に対応します。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトルートの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント + DuckDB 保存
    - news_collector.py     — RSS ニュース収集・前処理・保存
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - schema.py             — DuckDB スキーマ定義・init_schema
    - calendar_management.py— マーケットカレンダー管理・判定ユーティリティ
    - audit.py              — 監査ログ（signal / order / execution）
    - quality.py            — データ品質チェック
  - strategy/
    - __init__.py           — 戦略モジュールの骨組み
  - execution/
    - __init__.py           — 実行（ブローカ連携）骨組み
  - monitoring/
    - __init__.py           — 監視関連（骨組み）

---

## 開発・貢献

- 型注釈とログ出力を重視した設計になっています。ユニットテストやモックを用いたテストの追加を推奨します。
- news_collector._urlopen 等はテストで差し替えやすいように設計されています（HTTP 周りのモックが容易）。
- DB スキーマ変更を行う際は既存データの互換性とインデックスの影響を考慮してください。

---

Appendix / 参考
- DuckDB をデータ層に採用しているため、ローカルの分析や軽量な永続化に向いています。
- 設計文書（DataPlatform.md 等）を参照すると、各モジュールの想定ワークフローや制約が理解しやすくなります（本リポジトリに含まれている想定）。

何か追加で README に記載したい項目（例: CI、リリース手順、より詳しい環境変数一覧、サンプル .env 内容など）があれば教えてください。