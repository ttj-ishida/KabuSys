# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をデータストアとして使用し、J-Quants API からのデータ取得、ETL、品質チェック、特徴量生成、ニュース収集、監査ログなどデータプラットフォーム／リサーチワークフローに必要な機能を提供します。

---

## 主な特徴

- DuckDB ベースのスキーマ設計（Raw / Processed / Feature / Execution / Audit 層）
- J-Quants API クライアント（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- 市場カレンダー管理（JPX カレンダー取得・営業日判定）
- ニュース収集（RSS → 正規化 → DuckDB へ冪等保存、SSRF/サイズ制限対策）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ファクター算出（Momentum / Volatility / Value 等）、将来リターン・IC 計算、Z スコア正規化
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- 再利用しやすいモジュール設計（ETL 部分を外部から呼び出し可能）

---

## 動作環境 / 依存関係

- Python 3.10+
  - （型ヒントに `|` 記法を用いており、3.10 以上を想定）
- 必要なパッケージ（例）
  - duckdb
  - defusedxml

インストール例（仮にパッケージ化されている場合）:
```
python -m pip install -r requirements.txt
# または開発環境で
python -m pip install -e .
```

requirements.txt がない場合は最低限 `duckdb` と `defusedxml` を入れてください:
```
python -m pip install duckdb defusedxml
```

---

## 環境変数 / .env

このプロジェクトは環境変数または `.env` ファイルから設定を読み込みます。自動読み込みの順序は以下です（OS 環境変数が優先）:

1. OS 環境変数
2. .env.local（存在すれば上書き）
3. .env

自動読み込みを無効にする場合:
```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主要な環境変数（必須／任意）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 送信先チャンネル ID
- DUCKDB_PATH (任意) — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

簡単な .env 例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## セットアップ手順（概要）

1. Python（3.10 以上）と依存パッケージをインストールする
2. プロジェクトルートに `.env`（もしくは OS 環境変数）を用意する
3. DuckDB スキーマを初期化する

DuckDB スキーマ初期化（例: スクリプトまたは REPL）:
```python
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

監査ログ専用 DB を用いる場合:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（主要ユースケース）

以下は主要な API の利用例です。実運用時はログ設定や例外処理を適切に追加してください。

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.schema import init_schema
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース収集ジョブを実行する
```python
from kabusys.data.news_collector import run_news_collection
# known_codes を与えると記事中の銘柄コード抽出→紐付けを行う
known_codes = {"7203", "6758", "9984"}
saved_map = run_news_collection(conn, known_codes=known_codes)
print(saved_map)
```

3) ファクター / リサーチ関数を使う
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary

target = date(2024, 1, 4)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, columns=["mom_1m", "mom_3m", "ma200_dev"])
```

4) J-Quants から直接データを取得・保存する（テストやカスタム取得時）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
records = fetch_daily_quotes(date_from=date(2023,1,1), date_to=date(2023,12,31))
n = save_daily_quotes(conn, records)
print("saved", n)
```

5) カレンダー・営業日ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date
d = date(2024,1,4)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2024,1,1), date(2024,1,31)))
```

---

## 重要な設計／動作メモ

- J-Quants クライアントは 120 req/min のレート制限に従うため内部で固定間隔のスロットリングを実装しています。リトライやトークン自動更新（401 時）にも対応します。
- NewsCollector は SSRF 対策、応答サイズ制限、XML パースのセキュリティ対策（defusedxml）を備えています。
- ETL は差分取得（最終取得日ベース）とバックフィルを行い、ON CONFLICT を用いて冪等性を保ちます。
- データ品質チェックは Fail-Fast せず全問題を収集し、呼び出し側が対応を判断します。
- datetime / タイムゾーンは監査系では UTC 保存を想定しています（init_audit_schema は TimeZone を UTC に設定します）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py                       -- 環境変数 / 設定管理
- data/
  - __init__.py
  - jquants_client.py              -- J-Quants API クライアント（fetch/save）
  - news_collector.py              -- RSS ニュース収集・保存
  - schema.py                      -- DuckDB スキーマ定義・初期化
  - stats.py                       -- 統計ユーティリティ（zscore）
  - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
  - features.py                    -- features 公開インターフェース
  - calendar_management.py         -- 市場カレンダー管理・判定ユーティリティ
  - audit.py                       -- 監査ログスキーマ初期化
  - etl.py                         -- ETL 型の公開インターフェース
  - quality.py                     -- データ品質チェック
- research/
  - __init__.py
  - feature_exploration.py         -- 将来リターン / IC / factor_summary / rank
  - factor_research.py             -- momentum/value/volatility の算出
- strategy/                         -- 戦略層（拡張ポイント）
- execution/                        -- 発注・ブローカー連携（拡張ポイント）
- monitoring/                       -- 監視用モジュール（空の __init__）

上記以外にも各モジュール内に補助関数／ユーティリティがあります。README に載せた API 以外にも、モジュール内の細かな関数が利用可能です。

---

## 開発／拡張ポイント

- strategy/ と execution/ は戦略実装やブローカー接続のカスタム実装場所として準備されています。
- DuckDB のスキーマやインデックスは実行パターンに合わせて拡張可能です。
- Slack 通知や監視は用途に応じて追加実装してください（Slack トークンは設定で提供）。

---

## 問い合わせ / 貢献

この README はコードベースの主要機能をまとめた簡易ドキュメントです。実際の運用やデプロイ時はログ設定・エラーハンドリング・シークレット管理（Vault 等）を適切に行ってください。機能追加やバグ修正はソースツリーの該当モジュールに対して行い、ユニットテストと統合テストを追加してください。