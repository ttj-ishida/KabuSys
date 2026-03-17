# KabuSys

日本株向け自動売買プラットフォーム用ライブラリ（KabuSys）。  
データ収集（J-Quants / RSS）、ETLパイプライン、データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なデータ基盤と周辺ユーティリティをまとめた Python パッケージです。主な役割は以下です。

- J-Quants API からの株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新対応）
- RSS を用いたニュース収集（SSRF対策・トラッキングパラメータ除去・冪等保存）
- DuckDB を用いたデータスキーマ定義・初期化
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー（営業日判定 / next/prev / 期間取得 等）
- 監査ログ（signal → order → execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上のポイント:
- API レート制限やリトライ（指数バックオフ）を内蔵
- データ保存は冪等（ON CONFLICT を使用）
- ニュース取得時のセキュリティ対策（XMLパースの安全化、SSRF対策、レスポンスサイズ制限）
- DuckDB を中心としたシンプルなローカルデータ管理

---

## 主な機能一覧

- data/jquants_client.py
  - J-Quants から日次株価、財務データ、マーケットカレンダーを取得
  - レートリミット（120 req/min）、最大3回のリトライ、401時の自動トークンリフレッシュ
  - DuckDB へ冪等保存する save_* 関数を提供

- data/news_collector.py
  - RSS からニュース取得、テキスト前処理、記事ID生成（正規化URLの SHA-256 の先頭 32 文字）
  - SSRF / XML Bomb / 大容量レスポンス対策
  - raw_news / news_symbols への保存機能（チャンク挿入、INSERT RETURNING で実挿入数取得）

- data/schema.py
  - DuckDB 用のスキーマ定義（Raw / Processed / Feature / Execution レイヤー）
  - init_schema() でテーブル／インデックスを作成

- data/pipeline.py
  - 差分取得・バックフィルを考慮した ETL（run_daily_etl を提供）
  - 品質チェック（quality モジュール）と統合

- data/calendar_management.py
  - market_calendar を基にした営業日判定、next/prev_trading_day、期間内営業日取得
  - calendar_update_job による夜間差分更新

- data/audit.py
  - 監査ログテーブル（signal_events, order_requests, executions）を初期化する機能
  - 発注トレーサビリティのための設計

- data/quality.py
  - 欠損、スパイク、重複、日付不整合検出（QualityIssue を返す）

- config.py
  - .env または OS 環境変数から設定を読み込み（自動ロード機構あり）
  - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL 等の検証ヘルパー

---

## セットアップ手順

前提:
- Python 3.10 以上（typing のパイプ演算子 `|` を使用）
- pip と仮想環境の利用を推奨

1. リポジトリをクローン / 取得して作業ディレクトリに移動

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb defusedxml
   ```
   ※ 実行環境に応じて追加パッケージが必要になる場合があります。

4. パッケージをインストール（開発モード）
   リポジトリ上に pyproject.toml / setup.py がある想定であれば:
   ```
   pip install -e .
   ```
   無ければ、プロジェクトの Python パスに src を含めるか、スクリプトから相対 import を使ってください。

5. 環境変数の設定
   プロジェクトルートに `.env` を作成すると自動読み込みされます（config.py による自動ロード）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-xxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は代表的な利用例です。実際にはアプリケーション側から呼び出してスケジューラで定期実行する想定です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリが自動作成されます）
conn = schema.init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行
```python
from kabusys.data import pipeline
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

- run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェック の順に処理します。
- id_token を外部から注入してテストすることも可能です（id_token 引数）。

3) ニュース収集ジョブ実行
```python
from kabusys.data import news_collector
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
# sources を渡さない場合はデフォルトの RSS ソースを使用
results = news_collector.run_news_collection(conn, known_codes={"7203", "6758"})
print(results)  # {source_name: saved_count, ...}
```

4) J-Quants の直接呼び出し例
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(code="7203", date_from=None, date_to=None)
jq.save_daily_quotes(conn, records)
```

5) 監査スキーマの初期化
```python
from kabusys.data import audit
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
audit.init_audit_schema(conn)
```

ログ出力や運用レベルでは、KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL 環境変数で挙動を制御してください。

---

## 環境変数一覧（主要）

必須（少なくとも開発・運用で設定が必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABUSYS_ENV: development / paper_trading / live （デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動ロード制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると config.py の .env 自動読み込みを無効化（テスト用途等）

---

## 運用上の注意点

- J-Quants API のレート制限（120 req/min）を守るため、クライアントは内部で固定間隔レートリミッタを使用しています。独自に並列で大量リクエストを行う際は注意してください。
- 401 エラー時は自動でトークンリフレッシュを試みますが、リフレッシュに失敗すると例外になります。
- news_collector は外部の RSS を解析するため、XML パーサや HTTP の安全対策（defusedxml、SSRF ガード、サイズ制限）を実装しています。それでも未知の脆弱性には注意してください。
- DuckDB ファイルはローカルファイルです。バックアップや排他制御（複数プロセスからの同時アクセス）については運用ポリシーを検討してください。
- ETL 実行中に品質チェックで検出された問題は run_daily_etl の結果（ETLResult.quality_issues）に含まれます。致命的な問題判定は呼び出し側で行ってください（Fail-Fast ではありません）。

---

## ディレクトリ構成

（主要ファイル・モジュールの一覧）
- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch/save）
    - news_collector.py         — RSS ニュース収集・保存
    - schema.py                 — DuckDB スキーマ（DDL）と初期化
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — マーケットカレンダー管理（営業日判定等）
    - audit.py                  — 監査ログ（signal/order/execution テーブル）
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py               — 戦略関連（拡張ポイント）
  - execution/
    - __init__.py               — 発注 / ブローカ連携（拡張ポイント）
  - monitoring/
    - __init__.py               — モニタリング用（拡張ポイント）

各モジュールは「データ取得（data）」「戦略（strategy）」「発注（execution）」「監視（monitoring）」の責務に分離されています。strategy / execution / monitoring は拡張ポイントとして空の __init__ があるため、実運用の戦略や発注ロジックを実装できます。

---

## 今後の拡張ポイント（例）

- 実ブローカー（kabuステーション）との接続ラッパー実装（execution 層）
- 戦略の実装とバックテストツール（strategy 層）
- Slack や Prometheus による監視・アラート連携（monitoring）
- 複数ノードでの ETL 協調（分散ロック / ジョブスケジューラ対応）

---

質問や README の追加項目（例: デプロイ手順、CI 設定、細かい API 仕様の追記）があればお知らせください。README の内容を環境に合わせてカスタマイズして作り直します。