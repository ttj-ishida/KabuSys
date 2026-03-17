# KabuSys

バージョン: 0.1.0

日本株向けの自動売買・データプラットフォームのコアライブラリ群です。  
J-Quants API からのマーケットデータ収集、DuckDB を用いたスキーマ定義・ETL、RSS ニュース収集、マーケットカレンダー管理、データ品質チェック、監査ログ（発注〜約定トレース）などを含むモジュール群を提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- 前提 / 必要要件
- セットアップ手順
- 設定（環境変数）
- 使い方（簡単な例）
- ディレクトリ構成
- 開発メモ / 注意事項

---

## プロジェクト概要
KabuSys は日本株のデータ収集と自動売買のための基盤ライブラリです。  
設計上の方針として、以下を重視しています。
- API レート制限とリトライ処理（J-Quants クライアント）
- データの冪等性（DuckDB に ON CONFLICT を用いた保存）
- Look-ahead Bias 回避のためのフェッチ時刻記録
- ニュース収集に対する SSRF / XML 攻撃対策・サイズ制限
- データ品質チェックと監査トレース（シグナル→発注→約定）

---

## 主な機能
- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - レートリミッティング、指数バックオフによるリトライ、401 の自動トークンリフレッシュ
  - フェッチ時刻（UTC）記録
- DuckDB 用スキーマ管理
  - Raw / Processed / Feature / Execution 層などのテーブル定義と初期化
  - インデックス定義
- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、品質チェック
  - 日次 ETL の統合エントリポイント
- ニュース収集（RSS）
  - RSS 取得、URL 正規化、記事ID 生成（SHA-256 トリム）
  - SSRF 防止、gzip サイズ制限、defusedxml による XML セーフパース
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ用スキーマ（signal/events → order_requests → executions のトレーサビリティ）

---

## 前提 / 必要要件
- Python 3.10 以上（PEP 604 のユニオン型表記などを利用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml

その他、実際の発注連携や Slack 通知等を利用する場合は対象サービスの SDK や追加パッケージが必要になることがあります。

例:
pip install duckdb defusedxml

---

## セットアップ手順

1. リポジトリをクローン / コピーし、作業ディレクトリへ移動します。

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb defusedxml

4. 環境変数設定
   - プロジェクトルートの `.env` または `.env.local` を作成して必要なキーを設定します（下記「設定（環境変数）」参照）。
   - パッケージは起動時にプロジェクトルート（.git または pyproject.toml のある場所）を探し、自動的に `.env` / `.env.local` をロードします。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. DuckDB スキーマ初期化（例）
   - Python REPL またはスクリプトで以下を実行して DB を初期化します。
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 設定（環境変数）

主に以下の環境変数を利用します。必須のものは起動時にチェックされ、未設定だと例外を投げます。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン。get_id_token により id_token を取得します。

- KABU_API_PASSWORD (必須)  
  kabuステーションAPI のパスワード（execution モジュールで使用想定）。

- KABU_API_BASE_URL (任意)  
  kabu API のベース URL。デフォルト: http://localhost:18080/kabusapi

- SLACK_BOT_TOKEN (必須 if Slack used)  
  Slack 通知を行う場合の Bot トークン。

- SLACK_CHANNEL_ID (必須 if Slack used)  
  Slack 通知先のチャンネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視用 SQLite パス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  環境。development / paper_trading / live のいずれか（デフォルト: development）。

- LOG_LEVEL (任意)  
  ログレベル。DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）。

注:
- `.env.example` を参考に `.env` を作成してください（リポジトリ内にない場合は README のサンプルを参照）。
- 自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

簡単な `.env` サンプル:
JQUANTS_REFRESH_TOKEN=your_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（簡単な例）

以下はライブラリ内の主要機能を呼び出す最小例です。実運用前に各種環境変数と DB の初期化を行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL を実行（J-Quants トークンは settings から取得）
```python
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 今日を target_date として実行
print(result.to_dict())
```

3) RSS ニュース収集ジョブを実行
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
# known_codes は銘柄抽出に使う有効コードのセット（例: {'7203','6758',...}）
stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set())
print(stats)
```

4) マーケットカレンダーの夜間更新（差分取得）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn)
print(f"saved={saved}")
```

5) J-Quants の ID トークンを直接取得する場合
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
```

注意:
- run_daily_etl では内部でカレンダー取得→価格取得→財務取得→品質チェックの順に実行します。各ステップは独立したエラーハンドリングがなされ、失敗しても他ステップは継続しますが、結果は ETLResult.errors に蓄積されます。
- ニュース収集は RSS の XML をパースするため defusedxml を利用して安全に処理しています。

---

## ディレクトリ構成（主なファイル）
リポジトリの主要なファイル構成（src 配下）:

- src/kabusys/
  - __init__.py (パッケージ定義, __version__ = "0.1.0")
  - config.py (環境変数・設定管理、自動 .env ロード)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、保存関数)
    - news_collector.py (RSS 収集・保存・銘柄抽出)
    - schema.py (DuckDB スキーマ定義・初期化)
    - pipeline.py (ETL パイプライン)
    - calendar_management.py (マーケットカレンダー管理)
    - audit.py (監査ログテーブルの初期化)
    - quality.py (データ品質チェック)
  - strategy/
    - __init__.py (戦略層のための名前空間)
  - execution/
    - __init__.py (発注/執行層のための名前空間)
  - monitoring/
    - __init__.py (監視関連のための名前空間)

各モジュールは機能ごとに分離されており、テストや拡張がしやすい設計になっています。

---

## 開発メモ / 注意事項
- Python の型アノテーションで `X | None` を多用しているため Python 3.10 以上を推奨します。
- J-Quants の API レートは 120 req/min に制限しています。jquants_client では固定間隔スロットリング（RateLimiter）で制御していますが、複数プロセスで同時にアクセスする場合は更なる制御が必要です。
- ニュース収集時は SSRF や ZIP/XML ボム対策が組み込まれていますが、外部 URL を扱うため追加の運用監視が推奨されます。
- DuckDB のスキーマは冪等的（IF NOT EXISTS / ON CONFLICT）に定義しているため、スキーマ変更時は既存データとの互換性に注意してください。
- 環境変数は `.env` / `.env.local` から自動ロードされます（プロジェクトルートの検出は .git または pyproject.toml を基準）。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 実際の発注（kabu API 連携）や Slack 通知等はこのコアには含まれていないため、execution / monitoring 層での実装が必要です。

---

必要であれば README に「コマンドラインツールの使い方」「CI/テストの実行方法」「.env.example の完全なテンプレート」などを追加します。どの情報を追加しますか？