# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）。  
データ取得・永続化（DuckDB）、監査ログ、データ品質チェック、戦略/注文基盤の骨組みを提供します。

## プロジェクト概要
KabuSys は日本株の自動売買プラットフォーム向けに設計された Python パッケージです。主な目的は次のとおりです。

- J-Quants API 等から市場データ・財務データ・カレンダー等を安全に取得する
  - API レート制御（120 req/min）
  - 再試行（指数バックオフ）、401 時のトークン自動リフレッシュ
  - Look-ahead bias を防ぐための fetched_at 記録
- DuckDB による永続化（生データ・加工データ・特徴量・実行関連テーブルを定義）
- 監査ログ（signal → order_request → execution のトレース）を別モジュールで初期化
- データ品質チェック（欠損・スパイク・重複・日付不整合など）
- 簡易的に戦略/実行/監視モジュールのプレースホルダを用意

## 主な機能一覧
- data/jquants_client.py
  - J-Quants API クライアント: 日足（OHLCV）、財務（四半期BS/PL）、マーケットカレンダー取得
  - rate limiting、retry、token refresh、pagination 対応
  - DuckDB へ冪等的に保存する save_* 関数
- data/schema.py
  - DuckDB のスキーマ定義と初期化（Raw / Processed / Feature / Execution 層）
  - インデックス定義
  - init_schema(), get_connection()
- data/audit.py
  - 監査ログ用スキーマ（signal_events / order_requests / executions）
  - init_audit_schema(), init_audit_db()
  - すべてのタイムスタンプは UTC 保存（SET TimeZone='UTC'）
- data/quality.py
  - データ品質チェック群（欠損、スパイク、重複、日付不整合）
  - run_all_checks() による一括実行
- config.py
  - 環境変数の読み込み（.env 自動ロード機能）
  - 各種必須設定のアクセスラッパ（settings オブジェクト）
  - KABUSYS_ENV / LOG_LEVEL 等のバリデーション

## 必要条件
- Python 3.10+
- 主要依存: duckdb（その他 urllib 等は標準ライブラリを使用）

（セットアップ時に他ライブラリが必要であればプロジェクトの requirements.txt に追加してください）

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ移動

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージと依存関係のインストール
   - pip install -U pip
   - pip install duckdb
   - （プロジェクトの配布形式によっては）pip install -e . など

4. 環境変数設定
   - プロジェクトルート (.git または pyproject.toml があるディレクトリ) に `.env` / `.env.local` を置くと自動読み込みされます（自動ロードは OS 環境変数 > .env.local > .env の優先度）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で利用）。

5. 必要な環境変数（代表）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuAPI のベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 動作環境（development / paper_trading / live。デフォルト: development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト: INFO）

   例 `.env`（最低限の例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 使い方（簡単なコード例）
以下は代表的な利用パターンの例です。

- DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

- J-Quants から日足を取得して保存
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes, get_id_token
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# 明示的にトークンを取得する場合（内部で settings.jquants_refresh_token を使うので省略可）
id_token = get_id_token()

records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=None, date_to=None)
n = save_daily_quotes(conn, records)
print(f"saved {n} records")
```

- 財務データ / マーケットカレンダーの取得・保存は fetch_financial_statements / save_financial_statements、fetch_market_calendar / save_market_calendar を同様に使用します。

- 監査ログテーブルの追加初期化（既存の DuckDB 接続へ）
```python
from kabusys.data.audit import init_audit_schema

# conn は init_schema() で得た接続でもよい
init_audit_schema(conn)
```

- 監査専用 DB を新規に作成する場合
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=None)
for issue in issues:
    print(issue.check_name, issue.table, issue.severity, issue.detail)
```

注意:
- jquants_client は内部的にレートリミッタと再試行ロジックを実装しています。多量リクエストを行う場合はレートに注意してください。
- 監査ログ関連はタイムゾーンを UTC に固定して保存します（init_audit_schema が SET TimeZone='UTC' を実行します）。

## ディレクトリ構成
（本 README に含まれるファイルに基づく抜粋）

- src/
  - kabusys/
    - __init__.py  — パッケージ定義（__version__ 等）
    - config.py    — 環境変数/設定管理（settings オブジェクト）
    - data/
      - __init__.py
      - jquants_client.py   — J-Quants API クライアント、取得・保存ロジック
      - schema.py          — DuckDB スキーマ定義・初期化
      - audit.py           — 監査ログスキーマ・初期化
      - quality.py         — データ品質チェック
      - (raw/others...)    — 将来的なデータ関連モジュール
    - strategy/
      - __init__.py        — 戦略関連（プレースホルダ）
    - execution/
      - __init__.py        — 発注/執行関連（プレースホルダ）
    - monitoring/
      - __init__.py        — 監視関連（プレースホルダ）
- pyproject.toml / setup.cfg (プロジェクトメタデータ等)

## 設計上の注意点
- DuckDB のテーブルは ON CONFLICT DO UPDATE 等を使って冪等化しています。ETL の再実行が安全になるよう考慮されています。
- J-Quants へのリクエスト回数は 120 req/min に制限されています（モジュール内で固定制御）。
- jquants_client は 401 を受けた場合にリフレッシュトークンから自動的に id_token を更新して再試行します（ただし無限ループは回避）。
- 監査ログは削除しない前提で設計され、FK は ON DELETE RESTRICT を使うため履歴が保証されます。
- すべての監査用 TIMESTAMP は UTC で保存します。

## よくある質問 / トラブルシューティング
- .env が読み込まれない  
  - 自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行います。プロジェクトルートが検出されない場合は自動ロードをスキップします。
  - 自動ロードを無効化している場合（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）も読み込まれません。
- J-Quants トークン周りのエラー  
  - settings.jquants_refresh_token が未設定だと get_id_token が失敗します。必須です。
- DuckDB ファイルの場所  
  - デフォルトは data/kabusys.duckdb。必要に応じて DUCKDB_PATH を設定してください。init_schema() は親ディレクトリを自動作成します。

---

詳細な設計書（DataSchema.md / DataPlatform.md 等）や運用手順がある場合は、それらに従って運用してください。README の内容は現状のソースコードから抽出した概要と使用例です。必要があれば実践的なチュートリアルや API リファレンスを追加いたします。