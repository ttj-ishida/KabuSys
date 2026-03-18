# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB をデータストアに、J-Quants API や RSS をデータソースとして利用し、ETL / データ品質チェック / ファクター計算 / ニュース収集 / 監査ログなどの機能を提供します。

## 主な特徴
- J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ・レート制限対応）
- DuckDB ベースのスキーマ管理（Raw / Processed / Feature / Execution 層）
- 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース（RSS）収集と記事→銘柄紐付け処理（SSRF 対策・トラッキングパラメータ除去）
- ファクター計算・研究ユーティリティ（モメンタム・ボラティリティ・バリュー・IC 計算など）
- 監査ログ（signal → order → execution のトレースを可能にする監査スキーマ）
- 環境変数ベースの設定管理（.env 自動読込対応、テスト時の自動読込無効化オプションあり）

---

## 機能一覧（モジュール別）
- kabusys.config
  - .env / 環境変数読み込み、自動ロード（プロジェクトルート検出）
  - settings: J-Quants トークン、kabu API パスワード、Slack 設定、DB パス、実行環境等を取得
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミッター・再試行・ID トークン自動更新
- kabusys.data.schema
  - DuckDB スキーマ定義（テーブル作成）と初期化関数 init_schema
- kabusys.data.pipeline / etl
  - 差分 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果オブジェクト（ETLResult）
- kabusys.data.quality
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - QualityIssue 型
- kabusys.data.news_collector
  - RSS 取得・パース（SSRF/サイズ制限/Gzip 対応）
  - raw_news への冪等保存、記事ID 生成（正規化 URL の SHA-256）
  - 銘柄コード抽出・news_symbols 保存・バルク登録
- kabusys.data.calendar_management
  - JPX カレンダー更新ジョブ（calendar_update_job）と営業日ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
- kabusys.data.audit
  - 監査ログ用スキーマ（signal_events / order_requests / executions）初期化関数（init_audit_schema / init_audit_db）
- kabusys.data.stats / features
  - zscore_normalize（クロスセクション Z スコア正規化）
- kabusys.research
  - calc_momentum / calc_volatility / calc_value（ファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索）

---

## 前提条件 / 必要環境
- Python 3.10 以上（Union 型表記 (A | B) を使用）
- 必要パッケージ（最低限）
  - duckdb
  - defusedxml

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
# またはプロジェクトに setup/requirements があればそれに従ってください
```

---

## セットアップ手順（開発用・最小構成）
1. リポジトリをクローンし、プロジェクトルートへ移動
2. Python 仮想環境を作成して有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env をプロジェクトルートに配置するのが便利）

必須環境変数（settings で _require されるもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack Bot トークン
- SLACK_CHANNEL_ID — 通知先 Slack チャンネル ID

任意（デフォルトあり）:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)。デフォルト: INFO
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある .env / .env.local が自動で読み込まれます。
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト用）。

例: .env（簡易）
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
KABUSYS_ENV=development
```

---

## 使い方（代表例）
以下は代表的な利用方法の抜粋です。実運用ではエラーハンドリングやログ出力、スケジューリングを適切に行ってください。

1) DuckDB スキーマ初期化
```python
from kabusys.data import schema
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = schema.init_schema(settings.duckdb_path)
```

2) 日次 ETL 実行（J-Quants から差分取得して保存、品質チェックまで）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
result = run_daily_etl(conn)  # target_date を渡すことも可
print(result.to_dict())
```

3) ニュース収集ジョブ（RSS 取得 → raw_news 保存 → 銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data import schema

conn = schema.get_connection(settings.duckdb_path)
# known_codes は有効な銘柄コードの集合（例: {"7203", "6758", ...}）
res = run_news_collection(conn, known_codes={"7203", "6758"})
print(res)  # {source_name: saved_count}
```

4) ファクター計算（研究用）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
target = date(2024, 1, 5)

mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
fwd = calc_forward_returns(conn, target)

# 例: mom と fwd を使って IC を計算
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
print("IC:", ic)

# Z スコア正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, columns=["mom_1m", "ma200_dev"])
```

5) 監査ログ用スキーマ初期化
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit_kabusys.duckdb")
```

6) 設定参照例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)
print(settings.is_live)
```

---

## よくある操作 / ヒント
- テストや CI で自動的な .env ロードを避けたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を ":memory:" にして一時的に使うことで単体テストしやすくなります（schema.init_schema(":memory:")）。
- J-Quants API はレート制限があるため、複数スレッドでの同時大量リクエストは避けるか RateLimiter の調整を検討してください。
- news_collector は外部 URL を扱うため、SSRF 対策やサイズ上限が実装されています。独自の RSS ソースを追加する場合は信頼性を確認してください。

---

## ディレクトリ構成（主要ファイル）
（プロジェクトルートが src/ を使用するパッケージ構成になっている想定）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - execution/                      — 発注・実行関連（空のパッケージプレースホルダ）
  - strategy/                       — 戦略関連（空のパッケージプレースホルダ）
  - monitoring/                     — モニタリング関連（空のパッケージプレースホルダ）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得・保存）
    - news_collector.py             — RSS 収集・保存・銘柄紐付け
    - schema.py                     — DuckDB スキーマ定義／初期化
    - pipeline.py                   — ETL パイプライン
    - etl.py                        — ETL インターフェース再エクスポート
    - features.py                   — 特徴量ユーティリティ公開
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py        — マーケットカレンダー更新・営業日ユーティリティ
    - audit.py                      — 監査ログスキーマ初期化
    - quality.py                    — データ品質チェック
  - research/
    - __init__.py
    - feature_exploration.py        — 将来リターン計算・IC・要約
    - factor_research.py            — モメンタム/ボラティリティ/バリュー計算

---

## ライセンス / 貢献
- このリポジトリのライセンス・貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（本 README には含まれていません）。

---

README に記載の機能や API の詳細は、コード内のドキュメンテーション文字列（docstring）を参照してください。追加の使用例やスクリプト化の要望があれば、どのユースケースを自動化したいかを教えてください。