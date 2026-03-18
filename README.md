# KabuSys

日本株自動売買プラットフォーム（ライブラリ）  
このリポジトリは、日本株のデータ収集・ETL・品質チェック・特徴量生成・監査ログ管理などを行う基盤モジュール群を提供します。DuckDB をデータストアとして使用し、J-Quants API や RSS ニュースを取り込むためのクライアント・ETL・保存ロジックを備えています。

主な設計方針:
- DuckDB を中心とした3層（Raw / Processed / Feature）スキーマ
- J-Quants API の呼び出しにレートリミット、リトライ、トークン自動更新を実装
- データ品質チェックを ETL 後に実行（Fail-Fast ではなく問題を収集）
- 外部への発注/約定等の実装は Execution / Audit 層で監査可能にする構造

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイル（および .env.local）を自動的に読み込む（無効化可）
  - 必須環境変数の検証
- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務、マーケットカレンダー）
  - レートリミット、リトライ、401 自動リフレッシュ対応
  - 保存時の冪等性（ON CONFLICT / DO UPDATE）
- ETL パイプライン
  - 差分取得（最終取得日からの差分）、バックフィル機能
  - 市場カレンダー / 株価 / 財務の統合 ETL（run_daily_etl）
- データ品質チェック
  - 欠損データ検出、重複、前日比スパイク、日付不整合チェック
  - QualityIssue オブジェクトによる詳細な問題報告
- データスキーマ管理
  - DuckDB 用スキーマ定義と初期化（init_schema）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）
- ニュース収集
  - RSS フィード取得、安全対策（SSRF 防止、gzip 制限、XML パース防御）
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）
  - 銘柄コード抽出・news_symbols への紐付け
- リサーチ / 特徴量
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、Zスコア正規化
- 監査（Audit）
  - signal_events / order_requests / executions などを含む監査ログテーブル群

---

## セットアップ手順

前提:
- Python 3.9+（typing の型構文が使用されているため互換性を確認してください）
- DuckDB をネイティブに利用できる環境

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```bash
   git clone <リポジトリURL>
   cd <リポジトリ>
   # 任意: 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate   # Unix
   .venv\Scripts\activate      # Windows

   # 必要ライブラリをインストール（例）
   pip install duckdb defusedxml
   # またはパッケージが setuptools/pip の依存に含まれていれば
   pip install -e .
   ```

2. 環境変数の準備
   - プロジェクトルートに `.env`（および任意で `.env.local`）を配置してください。
   - 自動読み込みはデフォルトで有効です（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須項目（例）
     - JQUANTS_REFRESH_TOKEN … J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD … kabu API のパスワード（必須）
     - SLACK_BOT_TOKEN … Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID … Slack 通知先チャンネルID（必須）
   - 任意 / デフォルト
     - KABUSYS_ENV … development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL … DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH … 監視DB などに（デフォルト: data/monitoring.db）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

3. DuckDB スキーマの初期化
   - アプリケーションで使う DB を初期化します。
   - Python から実行する例:
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")
     # 監査ログを追加したい場合
     from kabusys.data import audit
     audit.init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（簡単な例）

以下は典型的な利用フローの例です。

1) 日次 ETL を実行してデータを取得・保存・品質チェックする:
```python
from kabusys.data import schema, pipeline
from datetime import date

# DB 初期化（既に初期化済みならスキップして接続取得）
conn = schema.init_schema("data/kabusys.duckdb")

# J-Quants トークンを settings で取得（環境変数経由）
# 日次 ETL 実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date(2025, 3, 1))
print(result.to_dict())
```

2) J-Quants から日足を直接取得して保存する（テストや部分取得時）:
```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2025,1,1), date_to=date(2025,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

3) リサーチ（ファクター計算）:
```python
from kabusys.research import calc_momentum, calc_forward_returns
from kabusys.data import schema
from datetime import date

conn = schema.get_connection("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2025,3,1))
fwd = calc_forward_returns(conn, target_date=date(2025,3,1))
# IC 計算等も可能
```

4) RSS ニュースの収集ジョブ:
```python
from kabusys.data import news_collector as nc
from kabusys.data import schema

conn = schema.get_connection("data/kabusys.duckdb")
results = nc.run_news_collection(conn, known_codes={"7203","6758"})
print(results)
```

---

## 環境変数一覧（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD: kabu API パスワード
  - SLACK_BOT_TOKEN: Slack ボット用トークン（通知）
  - SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（デフォルト）
- 自動 .env ロード:
  - プロジェクトルート（.git もしくは pyproject.toml を基準）から .env, .env.local を自動読み込みします。
  - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

config.Settings クラス経由でこれらにアクセスできます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## ディレクトリ構成

主要ファイル・モジュールを抜粋して示します（実際のファイル数に応じて追加してください）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                       # 環境変数・設定読み込み
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py            # J-Quants API クライアント + 保存
   │  ├─ news_collector.py            # RSS ニュース収集
   │  ├─ schema.py                    # DuckDB スキーマ定義・初期化
   │  ├─ pipeline.py                  # ETL パイプライン（run_daily_etl 等）
   │  ├─ etl.py                       # ETL 公開インターフェース（型再エクスポート）
   │  ├─ features.py                  # 特徴量ユーティリティ再エクスポート
   │  ├─ quality.py                   # データ品質チェック
   │  ├─ stats.py                     # 統計ユーティリティ（zscore 等）
   │  ├─ calendar_management.py       # 市場カレンダー管理
   │  ├─ audit.py                     # 監査ログ初期化関連
   │  └─ pipeline.py                  # ETL パイプライン（処理フロー）
   ├─ research/
   │  ├─ __init__.py
   │  ├─ factor_research.py           # モメンタム/ボラティリティ/バリュー計算
   │  └─ feature_exploration.py       # 将来リターン・IC・summary 等
   ├─ strategy/                        # 戦略関連（雛形/エントリポイント）
   ├─ execution/                       # 発注・約定管理（モジュール空の __init__ 有）
   └─ monitoring/                      # 監視用モジュール（空の __init__ 有）
```

---

## 注意点 / 実運用上のヒント

- DuckDB のファイルはデフォルトで data/kabusys.duckdb に保存されます。運用ではボリューム確保やバックアップを検討してください。
- J-Quants のレート制限や API 仕様は将来変更される可能性があります。リトライ / レート制御のパラメータは jquants_client 内で調整可能です。
- ニュース収集では SSRF 対策や XML の安全パーサ（defusedxml）を使用していますが、運用で扱うソースは信頼できるものに制限してください。
- ETL 実行中に品質チェックでエラーが検出されても、run_daily_etl は処理を続行して問題を収集します。結果の ETLResult を参照して適切に対処してください。
- 本パッケージは発注 / 約定 API を直接叩く部分（ブローカー固有の実装）は含まれておらず、kabu API 連携等は別途実装・注入する想定です（設定やパスワードは config で管理）。

---

## 掲載外だが参照に便利な API

- schema.init_schema(db_path) — DuckDB に全テーブルを作成して接続を返す
- schema.get_connection(db_path) — 既存 DB へ接続（スキーマ初期化は行わない）
- pipeline.run_daily_etl(conn, ...) — 日次 ETL の主要なエントリポイント
- jquants_client.fetch_daily_quotes / save_daily_quotes — データ取得・保存
- news_collector.run_news_collection — RSS 収集 + DB 保存 + 銘柄紐付け
- research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic — リサーチ用関数群
- data.stats.zscore_normalize — Zスコア正規化ユーティリティ

---

必要であれば、この README をベースに「運用手順」「cron / Airflow によるスケジューリング例」「監視／アラート設計」「テスト方針（ユニット/統合）」などのセクションも追加できます。どの追加情報が必要か教えてください。