# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
DuckDB をデータ層に採用し、J-Quants API や RSS ニュースからのデータ収集、ETL、品質チェック、ファクター計算（リサーチ用）や監査ログ等のユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

このパッケージは以下の役割を持つモジュール群で構成されています。

- data: J-Quants クライアント、DuckDB スキーマ/初期化、ETL パイプライン、ニュース収集、品質チェック、統計ユーティリティ
- research: ファクター計算（モメンタム・ボラティリティ・バリュー等）、特徴量探索（将来リターン計算、IC 計算等）
- strategy / execution / monitoring: （名前空間を確立。将来の戦略・発注・監視ロジックを配置する想定）
- config: 環境変数 / 設定読み込みロジック（.env 自動読み込み対応）

設計方針として、DuckDB を中心に「生データ（Raw）→ 整形（Processed）→ 特徴量（Feature）→ 実行（Execution）/ 監査（Audit）」の階層化を行い、ETL は差分更新・冪等保存（ON CONFLICT）・品質チェックを組み合わせて実行します。

---

## 主な機能一覧

- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、マーケットカレンダーの取得（ページネーション対応）
  - レート制限遵守・リトライ・トークン自動リフレッシュ・取得時刻（fetched_at）記録
  - DuckDB への冪等保存ユーティリティ（raw_prices, raw_financials, market_calendar）
- DuckDB スキーマ定義と初期化
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義
  - インデックス作成、init_schema / get_connection API
- ETL パイプライン
  - 差分更新（最終取得日を基に自動算出）、バックフィル、品質チェック統合（run_daily_etl など）
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、将来日付・非営業日の検出（QualityIssue を返す）
- ニュース収集
  - RSS フィード取得、前処理、記事IDの生成（URL 正規化 + SHA-256）、DuckDB への冪等保存、銘柄コード抽出
  - SSRF 対策、gzip サイズ制限、XML の安全パース（defusedxml）
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（スピアマン順位相関）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）
- 監査ログ
  - signal_events, order_requests, executions 等の監査テーブルを初期化する init_audit_schema / init_audit_db

---

## セットアップ手順

前提:
- Python 3.9+ を想定（typing の一部記法により）
- duckdb を使用（ローカルの DuckDB ファイル、または ":memory:"）
- ネットワーク経由で J-Quants API を利用する場合は適切な API トークンが必要

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 必須: duckdb, defusedxml
   - pip install duckdb defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. ソースをインストール（開発用）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数 / .env の設定
   - 以下の環境変数が重要です（必須は明記）:

     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン（利用する場合）
     - SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意, default: development) — 有効値: development, paper_trading, live
     - LOG_LEVEL (任意, default: INFO)

   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password_here
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（簡単な例）

以下は主要 API の利用例です。実際は適切なエラーハンドリングとログ設定を行ってください。

1. DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2. 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3. ニュース収集ジョブの実行（RSS を DB に保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う有効なコード集合（省略可）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # ソースごとの新規保存件数
```

4. リサーチ：モメンタム / ボラティリティ / IC の計算例
```python
import duckdb
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_forward_returns, calc_ic

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 5)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

# 例: mom の mom_1m と fwd_1d の IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC (mom_1m vs fwd_1d):", ic)
```

5. 監査ログ用スキーマ初期化（別 DB に分けることも可能）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 主要モジュール / 関数一覧（抜粋）

- kabusys.config
  - settings: 各種環境変数プロパティ（jquants_refresh_token, kabu_api_password, slack_bot_token 等）

- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token

- kabusys.data.schema
  - init_schema(db_path), get_connection(db_path)

- kabusys.data.pipeline
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl
  - ETLResult クラス（結果集約）

- kabusys.data.news_collector
  - fetch_rss, save_raw_news, save_news_symbols, run_news_collection

- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - QualityIssue クラス

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats から再エクスポート）

- kabusys.data.audit
  - init_audit_schema(conn), init_audit_db(db_path)

---

## ディレクトリ構成

（プロジェクトルートの src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - __init__.py
    - jquants_client.py
    - news_collector.py
    - schema.py
    - stats.py
    - pipeline.py
    - features.py
    - calendar_management.py
    - audit.py
    - etl.py
    - quality.py
  - research/
    - __init__.py
    - feature_exploration.py
    - factor_research.py
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

各ファイルの詳細はソースコメントに設計方針・注意点が記載されています。ファイル名から機能を辿ると理解しやすいです。

---

## 運用上の注意点

- 環境変数は .env / .env.local に置いておくと自動読み込みされます（プロジェクトルートの検出は .git または pyproject.toml を基準にしています）。
- J-Quants のレート制限（デフォルト 120 req/min）はコード内で明示的に制御されていますが、大量バックフィル時は API ポリシーに注意してください。
- DuckDB のトランザクションや ON CONFLICT 処理は実装済みですが、外部からの直接書き込みがある場合は品質チェックを定期的に実行することを推奨します。
- RSS フィードの取得は外部 URL に依存します。SSRF / XML Bomb / 大容量レスポンス対策が組み込まれていますが、カスタムソースを追加する際は注意してください。
- 本パッケージは発注実行ロジック（実際のブローカー送信）を内包していません。execution / strategy 名前空間は将来の拡張用に用意されています。実売買を行う際は十分なテストとリスク管理を行ってください。

---

## 貢献・拡張

- 追加機能例:
  - strategy モジュールに具体的なポートフォリオ最適化・リスク管理ロジックを実装
  - execution 層で証券会社 API（kabuステーション連携）の実装と冪等性の確保
  - monitoring に Prometheus / Slack 通知の統合
- リポジトリに PR を送る前に、既存のユニットテスト（存在する場合）を実行し、コードスタイルに従ってください。

---

この README はソースコードの主要な用途と使い方を短くまとめたものです。詳細は各モジュールの docstring（ソース内コメント）を参照してください。必要であれば、サンプルスクリプトや運用手順書（Runbooks）を別途追加できます。