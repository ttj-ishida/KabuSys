# KabuSys

日本株自動売買システムのコアライブラリです。データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、監査ログ（発注→約定のトレーサビリティ）など、戦略や発注エンジンの下支えをする機能群を提供します。

主な設計方針：
- データ取得は冪等（ON CONFLICT）で保存し再実行可能
- API レート制限・リトライ・トークン自動リフレッシュ対応
- Look-ahead bias を避けるため取得時刻（UTC）を記録
- ニュース収集は SSRF・XML Bomb 等の対策を内蔵
- DuckDB をデフォルトストレージに採用し高速な分析を想定

---

## 機能一覧

- data/jquants_client.py
  - J-Quants API クライアント
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB への保存（冪等）

- data/news_collector.py
  - RSS からニュースを収集して raw_news に保存
  - URL 正規化・トラッキングパラメータ削除・記事ID は SHA-256 のハッシュ（先頭32文字）
  - SSRF 対策、gzip サイズ上限、XML の安全パース（defusedxml）

- data/schema.py / audit.py
  - DuckDB のスキーマ定義・初期化（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ（signal_events / order_requests / executions）初期化

- data/pipeline.py
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）の実行
  - 差分更新、バックフィル、品質チェック統合

- data/quality.py
  - 欠損、スパイク、重複、日付不整合などの品質チェック

- data/calendar_management.py
  - 営業日判定・前後営業日の検索・JPX カレンダー更新バッチジョブ

- execution/, strategy/, monitoring/
  - （本リポジトリの骨組みとして存在。各種戦略・実行ロジックを実装する入口）

- config.py
  - .env ファイル / 環境変数読み込み（プロジェクトルート自動検出）
  - 必須環境変数の列挙と検証（Settings クラス）

---

## セットアップ手順

前提
- Python 3.10 以上（型記法 (A | B) を使用しているため）
- Git が利用可能（.env 自動読み込みのプロジェクトルート検出に利用）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-dir>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt があればそれを利用してください）
   - pip install -r requirements.txt

4. 環境変数（.env）を用意する
   プロジェクトルートに `.env`（および必要なら `.env.local`）を配置します。自動ロードはデフォルトで有効です。自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（最低限設定が必要なもの）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
   - SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID (必須) — Slack の投稿先チャンネルID

   任意 / デフォルト値あり:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化する場合に "1" をセット
   - KABUSYS_API_BASE_URL — kabu API のベース URL を変更する場合

   データベースパス（デフォルト値）
   - DUCKDB_PATH (例: data/kabusys.duckdb)
   - SQLITE_PATH (例: data/monitoring.db)

---

## 使い方（簡単なコード例）

以下はライブラリを用いて DB 初期化・日次 ETL を実行する最小例です。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化（親ディレクトリがなければ自動作成）
conn = schema.init_schema("data/kabusys.duckdb")
# 監査ログ用スキーマを同じ接続に追加する場合
from kabusys.data import audit
audit.init_audit_schema(conn)
```

2) 日次 ETL 実行
```python
from kabusys.data import pipeline
from datetime import date

# 既に init_schema で作成した conn を渡す
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes を渡すと記事に現れた銘柄コードで紐付けを行う
# 例: 既知の銘柄コードセットを DB から取得して渡す
known_codes = {"7203", "6758", "9984"}  # 例

res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

4) J-Quants の ID トークン取得（テスト・確認用）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を利用してトークンを取得
print(token)
```

注意点：
- ETL の id_token は注入可能（引数で渡せる）ためテスト時はモックトークンを使ってください。
- 自動で .env をロードしますが、ユニットテスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src/kabusys 配下）のおおまかな構成：

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存）
    - news_collector.py      — RSS ニュース収集・保存・銘柄抽出
    - schema.py              — DuckDB スキーマ定義・init
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — カレンダー更新・営業日判定
    - audit.py               — 監査ログ（signal / order / execution）
    - quality.py             — データ品質チェック
  - strategy/
    - __init__.py            — 戦略モジュール（拡張ポイント）
  - execution/
    - __init__.py            — 発注・注文管理（拡張ポイント）
  - monitoring/
    - __init__.py            — 監視関連（拡張ポイント）

各ファイル内に詳細なドキュメント文字列（docstring）があり、関数・クラスの挙動や引数・返り値の仕様が記載されています。まずは data/schema.init_schema で DB を作成してから pipeline.run_daily_etl を動かす流れが基本です。

---

## 注意点・運用上のヒント

- レート制限: J-Quants は 120 req/min を想定。jquants_client は内部で固定間隔スロットリングを行いますが、外部からの大量並列呼び出しには注意してください。
- トークン管理: get_id_token はリフレッシュトークンから idToken を取得します。401 受信時は自動的に一回リフレッシュしてリトライします。
- DuckDB: ファイルパスの親ディレクトリが存在しない場合は自動作成されます。テスト時は ":memory:" を指定してインメモリ DB を使用可能です。
- ニュース収集: レスポンスサイズや gzip 解凍後のサイズは上限（10MB）で制限しています。RSS の安全パース（defusedxml）を行います。
- 品質チェック: run_daily_etl の実行後に quality.run_all_checks を呼び出し、欠損やスパイク等を検出できます。検出された問題は ETL の判定材料として利用してください（自動停止はしません）。

---

もし README に追加したい内容（CI、デプロイ方法、具体的な戦略実装テンプレート、UnitTest の実行方法など）があれば教えてください。それに合わせてサンプルや手順を追加します。