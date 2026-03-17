# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（KabuSys）。  
J-Quants API や RSS を用いたデータ収集、DuckDB ベースのスキーマ、ETL パイプライン、品質チェック、監査ログ（発注→約定のトレーサビリティ）などを提供します。

## 主な特徴
- J-Quants API クライアント
  - 日次株価（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制御（120 req/min）、リトライ（指数バックオフ）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）記録による Look-ahead Bias の抑止
- DuckDB ベースの多層スキーマ
  - Raw / Processed / Feature / Execution / Audit 層を想定したテーブル定義
  - 冪等性を保った INSERT（ON CONFLICT）や RETURNING による正確な挿入判定
- ETL パイプライン
  - 差分取得（最終取得日からの差分、バックフィル対応）
  - 品質チェック（欠損、重複、スパイク、日付整合性）
  - 日次 ETL エントリ run_daily_etl を提供
- ニュース収集（RSS）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、記事 ID は SHA-256 切り出し
  - SSRF／XML Bomb などの防御（defusedxml、リダイレクト検査、受信サイズ制限）
  - raw_news / news_symbols への冪等保存
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal_events / order_requests / executions）
  - UUID ベースのトレース、order_request_id を冪等キーとして二重発注防止

---

## 動作要件
- Python 3.10+
- 主な依存パッケージ
  - duckdb
  - defusedxml

（その他の依存は標準ライブラリ中心。必要に応じて requirements ファイルを用意してください）

---

## セットアップ手順（開発環境向け）

1. レポジトリをクローンして仮想環境を作成
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール
   ```bash
   pip install -U pip
   pip install duckdb defusedxml
   # 開発インストール（setup.py / pyproject.toml がある場合）
   pip install -e .
   ```

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動読み込みされます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
   - 必須環境変数（少なくともETLやAPIアクセスに必要なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - データベースパス（任意、デフォルト値あり）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)

   例: `.env.example`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 基本的な使い方

以下は Python スクリプト/REPL から利用するサンプルです。`kabusys` パッケージ内の API を直接呼び出します。

1. DuckDB スキーマ初期化（ファイル DB）
```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")  # ディレクトリがなければ自動作成
```

2. 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# conn は上で初期化した DuckDB 接続
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. ニュース収集ジョブの実行（RSS → raw_news）
```python
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄コード抽出（例: 上場銘柄コードのセット）
known_codes = {"7203", "6758", "9432", ...}

results = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(results)  # {source_name: 新規保存数}
```

4. カレンダー更新ジョブ（夜間バッチ向け）
```python
from kabusys.data.calendar_management import calendar_update_job

saved = calendar_update_job(conn, lookahead_days=90)
print(f"saved: {saved}")
```

5. 監査ログ（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
# audit_conn に対して order_requests 等の記録を行う
```

6. 設定参照（環境変数）
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
```

---

## 利用できる主な API（概観）
- kabusys.config
  - settings: 環境変数ラッパー（必須項目は _require でチェック）
  - 自動 .env ロード: プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を読み込み。`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
- kabusys.data.schema
  - init_schema(db_path): DuckDB スキーマを初期化して接続を返す
  - get_connection(db_path): 既存 DB へ接続
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl(...) — 日次 ETL の統合エントリポイント
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.data.calendar_management
  - is_trading_day(conn, d), next_trading_day, prev_trading_day, get_trading_days
  - calendar_update_job(conn, lookahead_days)
- kabusys.data.quality
  - run_all_checks(conn, target_date=None, ...)

各関数の詳細はコード内の docstring を参照してください。

---

## 注意点 / 実装上の設計方針（抜粋）
- J-Quants API のレート制限（120 req/min）を厳守するため固定間隔スロットリングを実装。
- 取得したデータには fetched_at を記録し、いつシステムがデータを知り得たかを追跡可能にする。
- DB 書き込みは可能な限り冪等（ON CONFLICT）で実装し、二重挿入や更新で整合性を保つ。
- ニュース収集では SSRF 対策・XML の安全パース・応答サイズ制限を実装。
- 日次 ETL は各ステップを独立してエラーハンドリング（1 ステップ失敗でも他を継続）する設計。

---

## ディレクトリ構成（抜粋）
リポジトリの主要ファイル・モジュール構成は以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py                   （環境変数 / 設定読み込み）
  - data/
    - __init__.py
    - jquants_client.py         （J-Quants API クライアント）
    - news_collector.py         （RSS ニュース収集・保存）
    - schema.py                 （DuckDB スキーマ定義・初期化）
    - pipeline.py               （ETL パイプライン）
    - calendar_management.py    （マーケットカレンダー操作・更新ジョブ）
    - quality.py                （データ品質チェック）
    - audit.py                  （監査ログスキーマ、監査DB初期化）
  - strategy/
    - __init__.py               （戦略関連モジュールのエントリ）
  - execution/
    - __init__.py               （発注/実行関連のエントリ）
  - monitoring/
    - __init__.py               （監視関連エントリ）

（README に載せたのは主要モジュール。細部はソースツリーを参照してください）

---

## ロギング・デバッグ
- 各モジュールは標準 logging を利用しています。環境変数 LOG_LEVEL でログレベルを制御可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
- ETL やコレクション処理は情報・警告・エラーをログ出力します。運用時はファイルへリダイレクトするか監視システムに連携してください。

---

## 開発・拡張のヒント
- テスト時は環境変数自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- ネットワークコールをモックしやすいよう、news_collector._urlopen など一部の低レイヤを差し替え可能に実装しています。
- DuckDB はインメモリ（":memory:"）で初期化可能なのでユニットテストでの利用が簡単です。

---

この README はライブラリの主要な使い方/設計をまとめたものです。より細かな動作や引数、返り値の仕様については各モジュールの docstring を参照してください。問題や改善提案があれば issue を立ててください。