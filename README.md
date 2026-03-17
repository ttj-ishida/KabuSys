# KabuSys

日本株自動売買プラットフォームのコアライブラリ（データ収集・ETL・品質チェック・監査ログ等）

本リポジトリは、J-Quants 等からマーケットデータ・財務データ・ニュースを取得して DuckDB に保存し、
戦略層・実行層に渡すための基盤処理群を提供します。設計は冪等性・トレーサビリティ・セキュリティを重視しています。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務諸表（四半期）、マーケットカレンダー取得
  - レート制限（120 req/min）に従ったスロットリング
  - リトライ（指数バックオフ）、401時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス対策
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）
  - RSS フィードの取得・前処理・正規化
  - 記事IDは正規化 URL の SHA-256（先頭32文字）で冪等性を担保
  - SSRF 対策（スキーム検証 / プライベートIP拒否 / リダイレクト検査）
  - レスポンスサイズ上限と gzip 解凍の検査（Gzip bomb 対策）
  - DuckDB へのバルク挿入（トランザクション、INSERT ... RETURNING）
  - テキストから銘柄コード（4桁）抽出と紐付け
- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、外部キー、制約を含む初期化 API
  - 監査ログ（signal/events/order_requests/executions）用スキーマ初期化
- ETL パイプライン
  - 差分更新（最終取得日からの差分取得）、バックフィルによる後出し修正の吸収
  - カレンダー先読み、品質チェック（欠損・スパイク・重複・日付不整合）
  - 各ステップは独立して例外処理（1ステップ失敗でも他は継続）
- データ品質チェック
  - 欠損データ検出、スパイク検出、主キー重複、日付不整合検出
  - QualityIssue オブジェクトで結果を返す（severity に応じて処理可）

---

## 動作要件（想定）

- Python 3.10+
- 依存ライブラリ（例）
  - duckdb
  - defusedxml

pip でインストールしてください（例）:
pip install duckdb defusedxml

プロジェクトに setup / pyproject があれば pip install -e . で開発インストールできます。

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   pip install duckdb defusedxml
4. 環境変数設定
   プロジェクトルートの `.env` または `.env.local` に必要なキーを設定できます。
   自動読み込みはデフォルトで有効（configモジュールがプロジェクトルートを検出すると .env を読み込みます）。
   自動読み込みを無効にする場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）

オプション / デフォルト:
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 で .env 自動読み込みを無効化
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C1234567890
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 初期化・使い方

以下はライブラリ関数を直接呼ぶ例です。プロダクションでは CLI やジョブ管理から呼び出してください。

- DuckDB スキーマを初期化（例: data/kabusys.duckdb を作成）
python - <<'PY'
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
print("Initialized:", conn)
PY

- 監査ログスキーマを追加（既存接続に追加）
python - <<'PY'
import duckdb
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect("data/kabusys.duckdb")
init_audit_schema(conn)
print("Audit schema initialized")
PY

- J-Quants から株価をフェッチして保存（サンプル）
python - <<'PY'
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
# トークンは settings を経由して自動取得されます
records = jq.fetch_daily_quotes(date_from=None, date_to=None)  # パラメータ適宜
saved = jq.save_daily_quotes(conn, records)
print("saved:", saved)
PY

- RSS ニュースの収集と保存
python - <<'PY'
from kabusys.data.news_collector import run_news_collection
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
# known_codes は銘柄コードの集合（抽出用）。省略すると紐付けをスキップ。
results = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print("collection results:", results)
PY

- 日次 ETL パイプライン実行（品質チェック付き）
python - <<'PY'
from kabusys.data.pipeline import run_daily_etl
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
res = run_daily_etl(conn)
print(res.to_dict())
PY

注意点:
- run_daily_etl などは内部で settings（環境変数）を参照します。必須環境変数が未設定だと ValueError が発生します。
- テストや CI では、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットし、自前で環境変数を注入してください。

---

## ログ・デバッグ

- 各モジュールは標準の logging を利用しています。環境変数 LOG_LEVEL でログレベルを制御できます。
- jquants_client はレート制御の挙動やリトライの警告を出力します。
- news_collector は取得失敗・XMLパース失敗・SSRF検知などを警告/エラーで記録します。

---

## セキュリティ設計の要点

- RSS フィード取得での SSRF 対策（スキーム検証、プライベートIP拒否、リダイレクト検査）
- defusedxml による XML パース（XML Bomb 等の防御）
- レスポンスサイズ上限（MAX_RESPONSE_BYTES）でメモリ DoS を軽減
- J-Quants クライアントはトークン管理・自動リフレッシュ・リトライ制御を実装
- DuckDB 側のテーブルに厳格な制約（CHECK / PRIMARY KEY / FOREIGN KEY）を付与

---

## ディレクトリ構成

リポジトリ内の主要ファイル/モジュール（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数管理（.env 自動ロード、Settings）
    - data/
      - __init__.py
      - jquants_client.py       -- J-Quants API クライアント（取得・保存）
      - news_collector.py       -- RSS ニュース収集・前処理・DB格納
      - schema.py               -- DuckDB スキーマ定義・初期化
      - pipeline.py             -- ETL パイプライン（差分更新・品質チェック）
      - audit.py                -- 監査ログ（signal/order/execution）スキーマ
      - quality.py              -- データ品質チェック
    - strategy/
      - __init__.py             -- 戦略層（プレースホルダ）
    - execution/
      - __init__.py             -- 実行層（プレースホルダ）
    - monitoring/
      - __init__.py             -- 監視機能（プレースホルダ）

---

## その他・開発メモ

- 型ヒントは Python 3.10 の組合せ型（|）が使われているため、3.10 以降を想定しています。
- .env 読み込みはプロジェクトルートの検出（.git または pyproject.toml を基準）に依存します。パッケージ配布後も __file__ 基準で探索するためcwdに依存しません。
- 自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください（テストで便利）。
- DB 初期化は冪等化されています。既存テーブルがあればスキップします。
- ニュースやデータの重複は DB 側の制約（ON CONFLICT 等）で処理していますが、上位での重複検出やリトライ設計は適宜行ってください。

---

追加で README に入れたい内容（例: CI / テスト方法、開発フロー、デプロイ手順、具体的な戦略例）があれば教えてください。必要に応じてサンプルスクリプトや CLI ラッパーの雛形も作成します。