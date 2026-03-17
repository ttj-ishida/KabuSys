# KabuSys

KabuSys は日本株の自動売買プラットフォームのライブラリ群です。  
J-Quants や kabuステーション 等の外部 API から市場データを取得して DuckDB に保存し、品質チェック・特徴量生成・シグナル→発注→約定の監査ログまでをサポートすることを目的としています。

主な設計方針は「再現性・冪等性・セキュリティ」です。API 呼び出しはレート制限・リトライ・トークン自動更新を考慮し、RSS ニュース取得は SSRF／XML Bomb 等の攻撃対策を行っています。

---

## 主な機能

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー
  - レート制御（120 req/min）、指数バックオフによるリトライ、401 時のトークン自動リフレッシュ
  - ページネーション対応、取得時刻（fetched_at）を UTC で保存

- ETL パイプライン
  - 差分更新（最終取得日からの範囲計算、バックフィル）
  - 品質チェック（欠損、スパイク、重複、日付不整合）
  - 日次 ETL エントリ run_daily_etl によりカレンダー→株価→財務→品質チェックを実行

- ニュース収集
  - RSS フィードから記事を収集し raw_news に冪等保存
  - URL 正規化（トラッキングパラメータ除去）→ SHA-256 ハッシュで記事 ID 生成
  - SSRF 対策、受信サイズ上限、defusedxml による XML セキュリティ対策
  - 銘柄コード抽出と news_symbols への紐付け

- データベース管理（DuckDB）
  - Raw / Processed / Feature / Execution 層にまたがるスキーマ定義
  - init_schema() でテーブルとインデックスを冪等に作成
  - 監査ログ（signal_events / order_requests / executions）を初期化する init_audit_schema

- 監視・監査
  - 監査テーブルによりシグナル→発注→約定のトレースを保証
  - Slack 等への通知連携（設定ベース）

---

## 前提・依存

- Python >= 3.10（Union 型の `|` や TypedDict を利用）
- 外部ライブラリ（少なくとも次をインストールしてください）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS ソース 等）

（プロジェクトの packaging / requirements は別途用意してください）

---

## 環境変数 / 設定

以下はアプリで参照される主な環境変数です（kabusys.config.Settings により参照）。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（自動売買用）
- SLACK_BOT_TOKEN — Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID — Slack チャネル ID（通知先）

任意（デフォルト有り）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

自動 .env ロード:
- パッケージはパッケージルート（.git または pyproject.toml のある親ディレクトリ）から自動的に `.env` と `.env.local` を読み込みます。テスト等で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンしてワークディレクトリに移動
2. 仮想環境を作成・有効化（例: python -m venv .venv, source .venv/bin/activate）
3. 必要なパッケージをインストール
   - 例: pip install duckdb defusedxml
   - またはパッケージ化されている場合は: pip install -e .
4. 環境変数を用意（.env / .env.local）
5. DuckDB スキーマ初期化（下記「使い方」を参照）

---

## 使い方（基本例）

以下はプログラムからの利用例です。各スニペットは Python スクリプト内から実行します。

- DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 監査ログテーブル初期化（既存接続に追加）
```
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn)
```

- 日次 ETL を実行
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```
run_daily_etl は内部で market_calendar → prices → financials → 品質チェック を順次実行し、ETLResult を返します。結果には取得数・保存数・品質問題の一覧・エラー概要が含まれます。

- ニュース収集ジョブを実行
```
from kabusys.data.news_collector import run_news_collection
# known_codes は銘柄コードの集合（例: データベースから取得）
known_codes = {"7203", "6758", ...}
results = run_news_collection(conn, known_codes=known_codes)
print(results)  # {source_name: 新規保存件数}
```

- J-Quants データの直接取得（テストやユーティリティ用途）
```
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()
records = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

注意点:
- get_id_token は settings.jquants_refresh_token を利用するため、環境変数が必須です。
- jquants_client は内部でレートリミッタ・リトライ・401 自動リフレッシュを実装しています。

---

## セキュリティ・運用に関する注意

- J-Quants のレート制限（120 req/min）を順守するための固定間隔スロットリングを実装していますが、外部から無制限に呼ぶと制限に達するため運用ではスケジューラ設計に注意してください。
- NewsCollector は SSRF 対策（ホストのプライベートアドレス判定、リダイレクト検査）、XML パースに defusedxml、受信サイズ上限（10MB）を組み込んでいます。外部の未検証 URL をそのまま渡さないでください。
- 全ての TIMESTAMP は UTC を基本としています（監査用スキーマは接続に SET TimeZone='UTC' を実行します）。
- 本番環境では KABUSYS_ENV を `live` に設定してください。挙動の差分（paper/live）に関しては実装の別モジュールでの分岐が想定されています。

---

## ディレクトリ構成

（リポジトリのサンプル構成。主要ファイルを抜粋）

- src/kabusys/
  - __init__.py                  — パッケージ定義（version）
  - config.py                    — 環境変数／設定管理（Settings）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py         — RSS ニュース収集・保存ロジック
    - schema.py                 — DuckDB スキーマ定義と init_schema()
    - pipeline.py               — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    — 市場カレンダー管理（営業日判定、更新ジョブ）
    - audit.py                  — 監査ログ（signal/order/execution）の初期化
    - quality.py                — データ品質チェック
  - strategy/
    - __init__.py                — 戦略モジュール領域（未実装部分）
  - execution/
    - __init__.py                — 発注／約定処理領域（未実装部分）
  - monitoring/
    - __init__.py                — 監視関連（未実装）

---

## 開発・テストのヒント

- .env の自動ロードはプロジェクトルート（.git か pyproject.toml のあるディレクトリ）を基準に行われます。テストで自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 外部 API 呼び出し部分（_urlopen や jquants の _request）はテスト時にモック可能な設計になっています。ユニットテストではネットワークアクセスを行わずに動作確認できます。
- DuckDB の接続は ":memory:" を渡してインメモリ DB にすることで一時的なテストを行えます。

---

もし README に追加したい内容（例: セットアップ用 requirements.txt、CI の設定例、Slack 通知のサンプル、戦略テンプレートなど）があれば教えてください。それらに合わせて README を拡張します。