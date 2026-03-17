# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ収集・ETL・品質チェック・監査ログ等を含むデータプラットフォームのコア機能を提供します。

---

## プロジェクト概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API から日本株の株価（OHLCV）、財務データ、JPX のマーケットカレンダーを取得するクライアント
- RSS フィードからニュースを収集して DuckDB へ保存するニュース収集器
- DuckDB スキーマの定義・初期化、ETL（差分取得・保存）パイプライン
- データ品質チェック（欠損・スパイク・重複・日付不整合）の実行
- 監査ログ（シグナル→注文→約定のトレーサビリティ）用スキーマと初期化ユーティリティ
- マーケットカレンダー管理（営業日判定、前後営業日取得、夜間バッチ更新）

設計上のポイントとして、API レート制御・再試行（リトライ）・idempotent（冪等）保存・Look-ahead バイアス対策などが組み込まれています。

---

## 主な機能一覧

- J-Quants API クライアント（jquants_client）
  - ID トークン自動リフレッシュ、ページネーション対応、レートリミット制御、リトライ（指数バックオフ）
  - データ取得: 株価日足、財務データ（四半期 BS/PL）、マーケットカレンダー
  - DuckDB へ冪等保存（ON CONFLICT で更新）

- ニュース収集（news_collector）
  - RSS 取得（SSRF 対策、リダイレクト検査、gzip 解凍上限チェック）
  - URL 正規化（トラッキングパラメータ除去）、SHA-256 ベースの記事 ID 生成（先頭32文字）
  - テキスト前処理、銘柄コード抽出（4桁コード）
  - DuckDB へ一括挿入（トランザクション、INSERT ... RETURNING を使用）および銘柄紐付け保存

- データベーススキーマ管理（schema）
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - インデックス最適化

- ETL パイプライン（pipeline）
  - 差分更新（最終取得日からの自動算出 + バックフィル）
  - 市場カレンダーの先読み（lookahead）
  - 品質チェックの実行（quality モジュール）

- 市場カレンダー管理（calendar_management）
  - 営業日判定、前後営業日・期間内営業日取得、夜間バッチ更新ジョブ

- 品質チェック（quality）
  - 欠損・スパイク（前日比）・主キー重複・日付不整合を検出し QualityIssue を返す

- 監査ログ（audit）
  - signal_events / order_requests / executions のテーブルとインデックスを提供
  - 発注トレーサビリティをサポート

---

## セットアップ手順

前提:
- Python 3.10+（ソースは型ヒントに union 表記などを使用）
- Git（.git や pyproject.toml を用いたプロジェクトルート検出のため）

1. リポジトリをクローンして開く
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - defusedxml
   - 例:
     - pip install duckdb defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   - 開発時には linters・テストツール等を追加でインストールしてください。

4. パッケージをインストール（任意）
   - 開発中であれば editable install:
     - pip install -e .

5. 環境変数を準備
   - プロジェクトルートの `.env` / `.env.local` を置くか、環境変数を直接設定します。
   - 自動ロードは OS 環境変数 > .env.local > .env の順で読み込まれます。
   - テスト等で自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須の環境変数:
- JQUANTS_REFRESH_TOKEN (J-Quants のリフレッシュトークン)
- KABU_API_PASSWORD (kabu API のパスワード)
- SLACK_BOT_TOKEN (Slack 通知用 Bot トークン)
- SLACK_CHANNEL_ID (Slack 通知先チャンネル ID)

オプション（デフォルト含む）:
- KABUSYS_ENV (development | paper_trading | live) - デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) - デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 で自動 .env 読み込みを無効化)
- KABU_API_BASE_URL - デフォルト: http://localhost:18080/kabusapi
- DUCKDB_PATH - デフォルト: data/kabusys.duckdb
- SQLITE_PATH - デフォルト: data/monitoring.db

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトで利用する基本的な操作例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ファイルを自動作成
```

2) 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data import pipeline
result = pipeline.run_daily_etl(conn)  # 今日を対象に実行
print(result.to_dict())
```

パラメータ例:
- target_date: 特定日を指定
- id_token: J-Quants の id_token を注入してテスト可能
- run_quality_checks: 品質チェックを実行するか
- backfill_days, calendar_lookahead_days, spike_threshold などを調整可能

3) ニュース収集（RSS）
```python
from kabusys.data import news_collector
articles = news_collector.fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
new_ids = news_collector.save_raw_news(conn, articles)
# known_codes を渡して銘柄紐付けを行う場合:
# news_collector.run_news_collection(conn, sources=None, known_codes=set_of_codes)
```

4) 監査ログスキーマの初期化（既存の conn に追加）
```python
from kabusys.data import audit
audit.init_audit_schema(conn)
# または専用DBを作る場合:
# audit_conn = audit.init_audit_db("data/audit.duckdb")
```

5) カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data import calendar_management
saved = calendar_management.calendar_update_job(conn)
print(f"saved calendar rows: {saved}")
```

6) J-Quants の id_token を直接取得（テスト等）
```python
from kabusys.data.jquants_client import get_id_token
id_token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を利用
```

---

## ディレクトリ構成

リポジトリの主要ファイル／ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                       : 環境変数・設定管理（.env 自動ロード）
    - data/
      - __init__.py
      - jquants_client.py             : J-Quants API クライアント（取得・保存）
      - news_collector.py             : RSS ニュース収集器
      - schema.py                     : DuckDB スキーマ定義・初期化
      - pipeline.py                   : ETL パイプライン（差分更新・品質チェック）
      - calendar_management.py        : マーケットカレンダー管理
      - audit.py                      : 監査ログスキーマ・初期化
      - quality.py                    : データ品質チェック
    - strategy/
      - __init__.py                    : 戦略関連モジュール（拡張ポイント）
    - execution/
      - __init__.py                    : 発注・約定関連（拡張ポイント）
    - monitoring/
      - __init__.py                    : モニタリング関連（拡張ポイント）

DuckDB スキーマは Raw / Processed / Feature / Execution / Audit の層で定義されています。  
ニュース・価格・財務・カレンダー等は raw_* テーブルへ保存され、必要に応じて加工テーブルや特徴量テーブルが用意されています。

---

## 実装上の注意点 / 振る舞い

- 環境変数の自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に .env → .env.local を読み込みます。
  - OS 環境変数は保護され、.env の内容で上書きされません（.env.local は override=True として上書き可能だが OS 環境変数は保護）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます（テスト用途）。

- J-Quants クライアントの振る舞い
  - レート制限: 120 req/min を固定インターバルで守ります
  - 再試行: 408/429/5xx 系で最大 3 回の指数バックオフリトライを行います
  - 401 の場合はリフレッシュトークンで id_token を自動更新して 1 回だけリトライします
  - 取得したデータには fetched_at（UTC）を付与して「いつ知り得たか」をトレース可能にします

- ニュース収集の安全対策
  - defusedxml で XML 攻撃を防止
  - URL スキーム検証（http/https のみ）、リダイレクト時のプライベートアドレスブロック（SSRF 対策）
  - レスポンスサイズ制限（10MB）と gzip 解凍後の再検査

- データ保存は冪等化を重視
  - DuckDB への INSERT は ON CONFLICT DO UPDATE / DO NOTHING を使い二重登録を防ぎます
  - news_collector / save_* 系ではトランザクションでまとめて保存し、INSERT RETURNING により実挿入件数を取得します

---

## 開発・貢献

- 戦略（strategy）、実行（execution）、監視（monitoring）は拡張ポイントとして設計されています。実取引ロジックや外部ブローカー連携はここに実装してください。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にし、環境依存を排除すると良いです。
- DuckDB のインメモリ（":memory:"）を使えばユニットテストで DB 作成が容易です。

---

必要があれば README に実行スクリプト例、CI 実行例、Docker イメージ作成手順、さらに詳細な環境変数一覧（.env.example 形式）を追加できます。ご希望を教えてください。