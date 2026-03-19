# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
DuckDB をデータ層に用い、J‑Quants API などからのデータ取得、ETL、品質チェック、ファクター計算、ニュース収集、監査ログなどを統合的に提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J‑Quants 等外部 API からの市場データ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution / Audit 層）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
- ニュースの RSS 収集と銘柄紐付け
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および評価ユーティリティ（IC, forward returns, summary）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）

設計上のポイント:
- DuckDB によるローカル永続化（冪等保存、ON CONFLICT による更新）
- API 呼び出しに対するレート制御・リトライ・トークン自動リフレッシュ
- News 収集に対する SSRF / XML Bomb 等の安全対策
- 外部依存を最小化する（研究 / 統計ユーティリティは標準ライブラリのみで実装）

---

## 主な機能一覧

- データ取得・保存
  - J‑Quants クライアント: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - DuckDB への冪等保存: save_daily_quotes / save_financial_statements / save_market_calendar
- ETL
  - 差分取得（最終取得日からの差分）・バックフィル対応
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、主キー重複、日付不整合の検出
- ニュース収集
  - RSS 収集（gzip 対応、最大サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
  - 記事ID は正規化 URL の SHA‑256（先頭32文字）
- 研究用ユーティリティ
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
  - Zスコア正規化: zscore_normalize
- スキーマ管理 / 監査
  - DuckDB スキーマ初期化: init_schema
  - 監査ログ用スキーマ初期化: init_audit_schema / init_audit_db

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 記法や forward reference を前提）
- ネットワーク接続（J‑Quants API / RSS など）

1. リポジトリをクローン / パッケージを配置
   - 例: git clone ... （またはソースを配置）

2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (UNIX)
   - .venv\Scripts\activate      (Windows)

3. 必要なパッケージをインストール
   - duckdb, defusedxml が主な依存です。pip でインストールしてください。
     例:
     pip install duckdb defusedxml

   - 開発時にパッケージ化している場合:
     pip install -e .

4. 環境変数の設定
   - ルートに .env / .env.local を置くと自動ロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API 用パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
   - オプション:
     - KABUSYS_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite 監視 DB パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   例（.env の一部）:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベーススキーマの初期化
   - Python REPL またはスクリプトから DuckDB を初期化します。

   サンプル:
   ```
   from kabusys.data import schema
   conn = schema.init_schema("data/kabusys.duckdb")
   ```

   監査ログ専用 DB を分けて用意する場合:
   ```
   from kabusys.data import audit
   aconn = audit.init_audit_db("data/kabusys_audit.duckdb")
   ```

---

## 使い方（代表的な例）

以下は代表的なモジュール呼び出し例です。実運用では例外処理・ロギング・スケジューリング（cron / airflow 等）を追加してください。

1) 日次 ETL を実行する
```
from datetime import date
from kabusys.data import schema, pipeline
from kabusys.config import settings

# DB 初期化（初回のみ）
conn = schema.init_schema(settings.duckdb_path)

# ETL 実行（今日を対象日とする例）
result = pipeline.run_daily_etl(conn)
print(result.to_dict())
```

2) ニュース収集ジョブを実行する
```
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（例）
res = news_collector.run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

3) 研究用ファクター計算
```
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
t = date(2024, 1, 31)

mom = calc_momentum(conn, t)
vol = calc_volatility(conn, t)
val = calc_value(conn, t)

# 将来リターンを取得して IC を計算
fwd = calc_forward_returns(conn, t, horizons=[1])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

4) J‑Quants から日足を直接取得して保存
```
from kabusys.data import jquants_client as jq
import duckdb
conn = duckdb.connect("data/kabusys.duckdb")
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
jq.save_daily_quotes(conn, records)
```

---

## 主要ディレクトリ構成

（ルートから src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数設定管理（自動 .env ロード、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py
      - J‑Quants API クライアント（取得・保存・認証・レート制御・リトライ）
    - news_collector.py
      - RSS 収集・前処理・DB への保存・銘柄抽出
    - schema.py
      - DuckDB スキーマ定義・init_schema / get_connection
    - stats.py
      - zscore_normalize 等統計ユーティリティ
    - pipeline.py
      - 日次 ETL（差分取得 / 保存 / 品質チェック）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定 / 更新ジョブ 等）
    - audit.py
      - 監査ログスキーマ（signal / order_request / executions）
    - etl.py
      - ETLResult の公開インターフェース
    - features.py
      - 特徴量ユーティリティの公開
  - research/
    - __init__.py
    - feature_exploration.py
      - forward returns, IC, factor_summary, rank
    - factor_research.py
      - calc_momentum, calc_volatility, calc_value
  - strategy/
    - __init__.py
    - （戦略実装用プレースホルダ）
  - execution/
    - __init__.py
    - （発注/ブローカー連携用プレースホルダ）
  - monitoring/
    - __init__.py
    - （監視 / メトリクス関連プレースホルダ）

---

## 実運用上の注意点 / 補足

- 環境変数自動ロード:
  - config.py はパッケージルート（.git または pyproject.toml を探索）から .env / .env.local を自動的に読み込みます。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB 初期化:
  - init_schema は冪等でテーブルを作成します。既存データは上書きされませんが、DDL による変更がある場合は注意が必要です。
- セキュリティ:
  - news_collector は SSRF 対策、XML パース時の安全対策（defusedxml）を実装していますが、運用環境での外部入力は常に監視してください。
- レート制御:
  - J‑Quants のレート制限（120 req/min）を守るため内部でスロットリングを行います。大量取得時は時間がかかります。
- テストとローカル実行:
  - デバッグ/テスト時は settings をイミュレートした .env に適切なテスト用トークンや :memory: の DuckDB を使うと便利です。

---

この README はコードベースにある各モジュールの主な用途と基本的な使い方を示した簡易ガイドです。詳細な設計意図・API仕様はソース内の docstring（各ファイル冒頭の説明）を参照してください。追加の使い方や運用手順を README に盛り込みたい場合は、どの部分を詳述するか教えてください。