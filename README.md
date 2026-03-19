# KabuSys

日本株向けの自動売買基盤（ライブラリ）です。  
データ収集（J‑Quants）、DuckDB を用いたデータレイクの管理、特徴量生成、研究用ユーティリティ、ニュース収集、ETL パイプライン、監査ログ（発注〜約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群を含むパッケージです。

- J‑Quants API から市場データ（株価・財務・カレンダー）を取得して DuckDB に保存する ETL
- RSS 等からニュースを収集して前処理・DB 保存するニュースコレクター
- 価格データを元にしたファクター（Momentum / Volatility / Value 等）計算
- 研究用のユーティリティ（forward returns / IC / z-score 正規化 等）
- データ品質チェック、マーケットカレンダー管理、監査ログ用スキーマ
- 将来的な戦略・発注レイヤーの骨組み（schema / audit / execution 等）

設計上の特徴：
- DuckDB を中心としたオンプレミス／ローカル DB を想定
- 冪等性（ON CONFLICT）・ページネーション・レート制御・リトライ・トークン自動リフレッシュを考慮
- Research / Data 層は本番発注 API へはアクセスしない（安全な分離）

---

## 主な機能一覧

- data/jquants_client.py
  - J‑Quants から日足・財務・カレンダーを取得（ページネーション対応）
  - 保存用 API（save_daily_quotes, save_financial_statements, save_market_calendar）
  - レートリミッタ、リトライ、トークン自動リフレッシュ
- data/schema.py
  - DuckDB 用のスキーマ定義と init_schema(db_path)
- data/pipeline.py
  - 差分 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - 品質チェック呼び出し（data.quality）
- data/news_collector.py
  - RSS 取得、前処理、記事ID 正規化、raw_news 保存、銘柄抽出・紐付け
  - SSRF ガード、gzip/サイズチェック、XML パース安全化（defusedxml）
- data/quality.py
  - 欠損・スパイク・重複・日付不整合等の品質チェック
- research/factor_research.py, research/feature_exploration.py
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）、統計サマリー
- data/stats.py
  - zscore_normalize：ファクターのクロスセクション正規化
- audit.py
  - 発注〜約定をトレースする監査ログスキーマの初期化ユーティリティ

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 型や __future__.annotations を使用）
- 仮想環境を推奨

例（UNIX 系）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクトを pip install で使う場合は適宜 setup/pyproject に従ってインストール）

3. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（settings から読み込む）:
     - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード（将来的な注文連携用）
     - SLACK_BOT_TOKEN: Slack 通知用トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
   - 任意:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development|paper_trading|live、デフォルト development）
     - LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト INFO）

例 .env（抜粋）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（簡単な流れ・コード例）

以下は代表的なユースケースの例です。duckdb を使って DB を初期化し、日次 ETL を実行する流れ。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema

# ファイル DB を初期化
conn = schema.init_schema("data/kabusys.duckdb")
# または :memory: を使う
# conn = schema.init_schema(":memory:")
```

2) 日次 ETL を実行（J‑Quants トークンは settings から自動取得）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)  # target_date を指定可能
print(result.to_dict())
```

3) ニュース収集ジョブ
```python
from kabusys.data.news_collector import run_news_collection

# known_codes: 銘柄コード集合を与えると記事とコードを紐付けします
known_codes = {"7203", "6758", "9984"}  # 例
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: 新規保存件数}
```

4) ファクター計算（研究用）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns

d = date(2024, 1, 4)
mom = calc_momentum(conn, d)
vol = calc_volatility(conn, d)
val = calc_value(conn, d)
fwd = calc_forward_returns(conn, d, horizons=[1,5,21])
```

5) IC（Information Coefficient）計算
```python
from kabusys.research import calc_ic
# factor_records と forward_records は上の関数から得られる形式
ic = calc_ic(factor_records, forward_records, factor_col="mom_1m", return_col="fwd_1d")
```

注意点：
- research / data の関数群は DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照します。
- 本番発注機能（execution 等）は別途実装・証券会社 API 連携が必要です。
- ニュース収集は defusedxml を用いて XML の安全性に配慮しています。

---

## 環境変数と設定 (settings)

- 自動読み込み:
  - パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml）を探索し、`.env` → `.env.local` の順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は上書き可能（`.env` は上書きしない）。
  - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 主要な設定プロパティ（Settings クラス）:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url
  - slack_bot_token, slack_channel_id
  - duckdb_path, sqlite_path
  - env（development|paper_trading|live）, log_level

---

## ディレクトリ構成

主要ファイル・モジュール（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py  — J‑Quants API クライアント & 保存ユーティリティ
    - news_collector.py  — RSS 取得・記事保存・銘柄抽出
    - schema.py  — DuckDB スキーマ定義 / init_schema
    - pipeline.py  — ETL パイプライン（run_daily_etl 等）
    - features.py / stats.py  — 統計ユーティリティ・正規化
    - calendar_management.py — マーケットカレンダー管理
    - audit.py  — 監査ログスキーマ初期化
    - etl.py  — ETL 公開インターフェース（ETLResult 等）
    - quality.py  — データ品質チェック
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Volatility / Value 等の計算
    - feature_exploration.py — 将来リターン・IC・サマリー
  - strategy/  — 戦略層（未実装の雛形）
  - execution/ — 発注関連（インターフェース用空モジュール）
  - monitoring/ — 監視系（雛形）

---

## 注意事項 / 運用上のヒント

- Python バージョン: 3.10 以上を推奨（型アノテーションに | を使用）。
- DuckDB のファイルパスは設定（DUCKDB_PATH）で指定。":memory:" によるテスト利用も可能。
- J‑Quants API のレート制限（120 req/min）を client が守る設計になっていますが、大量データ取得時は運用で間隔を制御してください。
- ETL は品質チェックで警告／エラーを返します。運用では ETLResult.has_quality_errors / has_errors を参照してアラートや手動確認を行ってください。
- ニュース収集は外部 URL を扱うため、プロキシやネットワーク制約のある環境では SSRF 制御や DNS の挙動に注意してください。

---

## 貢献 / 開発

- テスト: 各モジュールは DuckDB のインメモリ DB（":memory:"）で単体テストしやすい設計です。settings の自動ロードを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 新しい機能追加や外部 API 連携（証券会社・kabuステーション等）を行う際は、監査ログ（audit）と冪等性を保つ設計を継承してください。

---

README は以上です。必要であれば以下を作成します：
- .env.example の完全テンプレート
- 簡易 Dockerfile / docker-compose 例（DuckDB + 実行ジョブ）
- サンプルスクリプト（ETL cron ジョブ / news collector CLI）