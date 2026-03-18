# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
J-Quants や RSS などから市場データ・ニュースを収集し、DuckDB に保存・整形、戦略用の特徴量計算や品質チェック、監査ログ、ETL パイプラインなどを提供します。

主な設計方針：
- DuckDB をデータストアとして使用し、SQL と Python を組み合わせて効率的に処理
- 外部 API（J-Quants）へはレート制御・リトライ・トークン自動更新を含む堅牢なクライアント実装
- ETL は差分更新・バックフィル対応、品質チェックは Fail-Fast ではなく全件収集
- Research 用のファクター計算は本番発注系にアクセスせず、純粋にデータのみを参照

---

## 機能一覧

- 環境設定管理
  - .env/.env.local から自動で環境変数を読み込む（プロジェクトルート自動検出）
  - 必須変数チェック（例: JQUANTS_REFRESH_TOKEN 等）
- データ取得 / 保存（data.jquants_client）
  - J-Quants API クライアント（株価日足、財務データ、マーケットカレンダー）
  - レート制御、リトライ、401 時のトークン自動リフレッシュ
  - DuckDB へ冪等に保存する save_* 関数
- ニュース収集（data.news_collector）
  - RSS フィード取得・前処理（URL 除去、正規化）
  - SSRF・XML 攻撃対策（スキーム検査、defusedxml、応答サイズ制限）
  - raw_news / news_symbols への冪等保存
- スキーマ管理（data.schema）
  - Raw / Processed / Feature / Execution / Audit 層の DuckDB DDL 定義
  - init_schema(), get_connection() を提供
- ETL パイプライン（data.pipeline）
  - 差分更新（backfill 対応）、カレンダー先読み、品質チェック統合
  - run_daily_etl により日次 ETL を一括実行
- データ品質チェック（data.quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合の検出
- 監査ログ（data.audit）
  - signal / order_request / executions 等、トレーサビリティ用テーブルと初期化
- 研究用（research）
  - ファクター計算: momentum / volatility / value（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン）算出、統計サマリー
  - zscore_normalize（data.stats から再エクスポート）
- ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - マーケットカレンダー管理（trading day 判定、next/prev など）

---

## 動作環境 / 依存

- Python 3.10+
  - 型アノテーション（X | None など）を使用しているため Python 3.10 以上を推奨
- 必要パッケージ（例）
  - duckdb
  - defusedxml
- 標準ライブラリ: urllib, datetime, logging, math, hashlib, ipaddress, socket など

（プロジェクトに requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存ライブラリをインストール
   - pip install duckdb defusedxml

   （パッケージ配布形態に合わせて `pip install -e .` 等を行ってください）

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを検出）
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（使用する場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack チャンネル ID を使う場合
   - データベースのパス（任意、デフォルト値）:
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
   - 自動 .env ロードを無効化する場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. DuckDB スキーマ初期化
   - Python REPL やスクリプトで以下を実行:
     - from kabusys.data.schema import init_schema
     - conn = init_schema("data/kabusys.duckdb")

---

## 基本的な使い方

以下は代表的な操作の例です。

- 設定値を参照する
```python
from kabusys.config import settings

token = settings.jquants_refresh_token
duckdb_path = settings.duckdb_path  # Path オブジェクト
```

- DuckDB の初期化
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl

# conn は init_schema で作成した接続
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュース収集を実行して DB に保存
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は有効な銘柄コードのセット（例: {"7203", "6758", ...}）
res = run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- 研究用ファクター計算
```python
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
from datetime import date

d = date(2024, 1, 10)
mom = calc_momentum(conn, d)           # モメンタム (list[dict])
vol = calc_volatility(conn, d)         # ボラティリティ / 流動性
val = calc_value(conn, d)              # PER / ROE
fwd = calc_forward_returns(conn, d)    # 将来リターン（1/5/21日）
ic = calc_ic(mom, fwd, "mom_1m", "fwd_1d")
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

- スキーマに監査ログを追加（監査層初期化）
```python
from kabusys.data.audit import init_audit_schema
# conn は init_schema() 等で得た接続
init_audit_schema(conn, transactional=True)
```

---

## 主要 API / 関数一覧（抜粋）

- kabusys.config
  - settings: Settings オブジェクト（環境変数アクセス）
- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - fetch_daily_quotes(...), save_daily_quotes(...)
  - fetch_financial_statements(...), save_financial_statements(...)
  - fetch_market_calendar(...), save_market_calendar(...)
  - get_id_token(...)
- kabusys.data.pipeline
  - run_daily_etl(...)
  - run_prices_etl(...), run_financials_etl(...), run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source), save_raw_news(conn, articles), run_news_collection(...)
  - extract_stock_codes(text, known_codes)
- kabusys.data.quality
  - run_all_checks(conn, ...)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.stats
  - zscore_normalize

---

## ディレクトリ構成

（リポジトリ内の主要ファイル / モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 -- 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py       -- J-Quants API クライアント（取得/保存）
      - news_collector.py       -- RSS 収集・前処理・保存
      - schema.py               -- DuckDB スキーマ定義と初期化
      - pipeline.py             -- ETL パイプライン（run_daily_etl 等）
      - features.py             -- 特徴量ユーティリティ（再エクスポート）
      - stats.py                -- 統計ユーティリティ（zscore_normalize）
      - calendar_management.py  -- 市場カレンダー更新/判定ユーティリティ
      - audit.py                -- 監査ログテーブル定義 / 初期化
      - etl.py                  -- ETL 結果型の公開インターフェース
      - quality.py              -- データ品質チェック
    - research/
      - __init__.py
      - factor_research.py      -- Momentum / Value / Volatility 計算
      - feature_exploration.py  -- 将来リターン / IC / 統計サマリー
    - strategy/                  -- 戦略層（骨組み）
    - execution/                 -- 発注 / 実行管理（骨組み）
    - monitoring/                -- 監視関連（骨組み）

---

## 開発・運用上の注意

- 環境変数は .env / .env.local から自動ロードされます。テスト等で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants のレート制限（120 req/min）に対応するためクライアント側でスロットリングを行います。大量取得時は注意してください。
- DuckDB に対する DDL は冪等（CREATE TABLE IF NOT EXISTS 等）です。init_schema は何度実行しても既存テーブルを壊しません。
- ニュース収集は外部 URL へのアクセスを伴うため、SSRF や大容量レスポンスに対する防御ロジックが組み込まれていますが、運用環境ではネットワーク設定やプロキシ等の確認を推奨します。
- 監査ログ（audit）層はトレーサビリティ確保のため削除を想定していません。運用ポリシーに応じた永続化設計を行ってください。

---

README はここまでです。必要であれば以下を追加で作成できます：
- examples ディレクトリ内の実行スクリプト例（ETL 実行、ニュース収集、ファクター計算）
- requirements.txt / pyproject.toml のテンプレート
- .env.example（必要な環境変数の雛形）