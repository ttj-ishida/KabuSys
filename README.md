# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）

軽量な DuckDB ベースのデータレイク、J-Quants API クライアント、ETL パイプライン、ニュース収集、ファクター計算・リサーチ用ユーティリティ、監査ログなどを含むモジュール群です。実運用（live）・ペーパー取引（paper_trading）・開発（development）を考慮した設計になっています。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須パラメータを Settings オブジェクト経由で取得

- データ取得 / 保存
  - J-Quants API クライアント（取得・ページネーション・トークン自動更新・リトライ・レート制限対応）
  - DuckDB へ冪等的に保存する save_* 関数群（ON CONFLICT DO UPDATE / DO NOTHING）

- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
  - 市場カレンダーの先読み / 更新ジョブ（calendar_update_job）
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）

- データスキーマ管理
  - Raw / Processed / Feature / Execution 層の DuckDB テーブル定義と初期化（init_schema）
  - 監査ログ用スキーマ（init_audit_schema / init_audit_db）

- データ品質チェック
  - 欠損・重複・スパイク・日付不整合検出（quality モジュール）

- ニュース収集
  - RSS フィード収集（fetch_rss / run_news_collection）、SSRF 対策、トラッキングパラメータ除去、記事正規化、銘柄抽出、DuckDB へ冪等保存

- リサーチ / ファクター計算
  - モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
  - Zスコア正規化ユーティリティ

- その他
  - 監査ログ（signal_events / order_requests / executions）の初期化・管理
  - 柔軟なログレベル / 実行環境（KABUSYS_ENV）管理
  - 発注・実行管理用のデータモデル（Execution / Orders 等）を用意

---

## 必要な環境変数（主要）

以下は必須（Settings._require により未設定時にエラー）または利用推奨の環境変数です。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API 用パスワード（発注機能使用時）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env 自動読み込みを無効化
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — テスト時などに自動ロードを無効にする

プロジェクトルートに置く .env(.local) を用意してください（.env.example を参照する想定）。

---

## セットアップ手順

1. Python 環境（3.9+ 推奨）を用意します。

2. 依存パッケージをインストールします（プロジェクトの pyproject.toml / requirements.txt に従ってください）。主要な依存例:

```bash
pip install duckdb defusedxml
```

3. リポジトリをクローンしてパッケージをインストール（開発モード）:

```bash
git clone <repo-url>
cd <repo-dir>
pip install -e .
```

4. 環境変数を設定:
   - .env または OS 環境変数で上記の必須値を設定します。
   - 自動読み込みを一時的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. 初期スキーマを作成（DuckDB ファイルの親ディレクトリは自動作成されます）:

```python
from kabusys.data import schema
conn = schema.init_schema("data/kabusys.duckdb")
```

監査ログ専用 DB を作る場合:

```python
from kabusys.data import audit
conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
```

---

## 使い方（簡易ガイド・コード例）

以下は代表的な使い方の例です。詳細は各モジュールの docstring を参照してください。

- 日次 ETL の実行（市場カレンダー取得 → 株価/財務差分取得 → 品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data import schema, pipeline

# DB 初期化済みまたは既存 DB に接続
conn = schema.init_schema("data/kabusys.duckdb")

# 日次 ETL を実行（target_date を省略すると今日）
result = pipeline.run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集ジョブの実行:

```python
from kabusys.data import news_collector, schema
conn = schema.get_connection("data/kabusys.duckdb")
# known_codes: 銘柄抽出時に有効とみなす銘柄コードのセット（例: 全上場コード）
known_codes = {"7203", "6758", ...}
res = news_collector.run_news_collection(conn, sources=None, known_codes=known_codes)
print(res)  # {source_name: saved_count}
```

- J-Quants から日足を取得して保存（テスト用・手動）:

```python
from kabusys.data import jquants_client as jq
from kabusys.data import schema
conn = schema.get_connection("data/kabusys.duckdb")

# id_token を省略するとモジュールでキャッシュ / 自動リフレッシュされる
records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
saved = jq.save_daily_quotes(conn, records)
print(f"saved: {saved}")
```

- ファクター計算 / リサーチ関数の利用:

```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, factor_summary

conn = duckdb.connect("data/kabusys.duckdb")
target = date(2024, 1, 31)

mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
summary = factor_summary(mom, ["mom_1m", "ma200_dev"])
```

- マーケットカレンダー関連ユーティリティ:

```python
from datetime import date
from kabusys.data import calendar_management as cm
conn = schema.get_connection("data/kabusys.duckdb")
cm.calendar_update_job(conn)  # 先読み分を更新
cm.is_trading_day(conn, date(2024,1,1))
cm.next_trading_day(conn, date(2024,1,1))
```

---

## 重要な設計上の注意

- DuckDB への INSERT は冪等性を担保するため ON CONFLICT を使用していますが、外部から直接 DB を編集する場合は注意してください。
- J-Quants API のレート制限（120 req/min）に従う実装になっています。大量取得時は pipeline の差分ロジック / ページネーションを活用してください。
- ニュース収集では SSRF や XML BOM、gzip bomb 等の攻撃対策を実装していますが、第三者公開サービスでの利用時は追加の監査を推奨します。
- ETL は Fail-Fast にはせず、品質チェックで検出した問題を一覧として返す設計です。運用側で重大度に応じたアクションを取ってください。
- audit モジュールは監査証跡を重視しており、テーブルの削除や FK の扱いについて DuckDB のバージョン制限を考慮した設計になっています。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定管理
    - data/
      - __init__.py
      - jquants_client.py             — J-Quants API クライアント（fetch / save）
      - news_collector.py             — RSS ニュース収集・保存
      - schema.py                     — DuckDB スキーマ定義・初期化
      - stats.py                      — 統計ユーティリティ（zscore_normalize）
      - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
      - quality.py                    — データ品質チェック
      - calendar_management.py        — market_calendar 管理・ジョブ
      - audit.py                      — 監査ログテーブル定義・初期化
      - features.py                   — 特徴量ユーティリティ再エクスポート
      - etl.py                        — ETL 公開インターフェース再エクスポート
    - research/
      - __init__.py
      - feature_exploration.py        — 将来リターン・IC・サマリー
      - factor_research.py            — momentum/volatility/value 等のファクター
    - strategy/                        — 戦略関連（パッケージ）
    - execution/                       — 発注 / 実行関連（パッケージ）
    - monitoring/                      — 監視関連（パッケージ）

---

## ログ & デバッグ

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- library 内の多くの処理は logger を使用して詳細ログを出力します。運用時は INFO、開発時は DEBUG を推奨します。

---

## テスト / 開発時のヒント

- 自動 .env ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。
- DuckDB でインメモリ DB を使う場合は db_path として ":memory:" を指定できます（init_schema(":memory:")）。
- ネットワーク呼び出しを伴う関数（jquants_client._request / news_collector._urlopen 等）はモックしやすい設計になっています（id_token 注入、内部ヘルパ関数の差し替え）。

---

## ライセンス / 貢献

（リポジトリに応じてライセンスやコントリビューションガイドをここに追記してください）

---

README はここまでです。各モジュールの詳細な使い方・パラメータはソースコードの docstring（各関数の説明）をご参照ください。必要であれば、具体的な実行スクリプトや運用手順（cron / CI ワークフロー例、バックアップ手順等）を別途作成します。