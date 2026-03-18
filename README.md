# KabuSys

日本株向け自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ取得・ETL、マーケットカレンダー管理、ニュース収集、品質チェック、ファクター計算（リサーチ）、
および DuckDB ベースのスキーマ・監査ログを提供します。戦略・発注・監視周りの実装はモジュール単位で分離されており、
プロジェクト固有の戦略やブローカー連携を組み込める設計になっています。

バージョン: 0.1.0

---

## 主要機能

- 環境変数/設定管理
  - .env / .env.local の自動ロード（プロジェクトルートを探索）
  - 必須環境変数を Settings 経由で取得

- データ収集（J-Quants API クライアント）
  - 日次株価（OHLCV）、財務データ、JPX カレンダーの取得（ページネーション対応）
  - 率制御（120 req/min 固定間隔スロットリング）、リトライ、トークン自動リフレッシュ
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE 相当の実装）

- ETL パイプライン
  - 差分更新（最終取得日ベース）、バックフィル、品質チェックのワンストップ実行
  - pipeline.run_daily_etl で日次処理を実行可能

- データ品質チェック
  - 欠損、重複、スパイク（前日比）、日付不整合（未来日・非営業日）を検出
  - 問題は QualityIssue オブジェクトのリストで返却

- ニュース収集
  - RSS フィード収集、URL 正規化、トラッキングパラメータ除去、SSRF 対策、gzip 対応
  - raw_news / news_symbols への冪等保存
  - 銘柄コード抽出（4桁数字の候補を known_codes でフィルタ）

- DuckDB スキーマ管理
  - Raw / Processed / Feature / Execution / Audit 層のテーブル定義と初期化
  - init_schema/db 初期化ユーティリティ、監査ログ専用スキーマ init_audit_schema／init_audit_db

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算関数
  - 将来リターン計算、IC（Spearman）計算、カラム統計・Zスコア正規化

- カレンダー管理
  - is_trading_day や next_trading_day 等の営業日判定ユーティリティ
  - calendar_update_job による夜間更新ジョブ

- その他
  - 軽量で外部依存を最小化（標準ライブラリ + 必要最小限のパッケージ）
  - モジュール構造により戦略・発注・監視ロジックを独立して実装可能

---

## 必要環境 / 依存

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がある場合はそれを使用してください。最低限は上記パッケージが必要です。）

インストール例:
```bash
python -m pip install "duckdb" "defusedxml"
```

---

## 環境変数（主なもの）

KabuSys は環境変数で設定を管理します。必須のものは実行前に設定してください。

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注がある場合）
- SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先のチャネル ID

オプション／既定値:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト: INFO
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

プロジェクトルート（.git または pyproject.toml を探索）に `.env` / `.env.local` を置くと自動で読み込まれます。

.env の簡単な例:
```
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（早見）

1. Python 環境を用意 (3.10+)
2. 依存パッケージをインストール（duckdb, defusedxml 等）
3. プロジェクトルートに `.env` を作成して必要な環境変数を設定
4. DuckDB スキーマを初期化

例（Python スクリプトでの初期化）:
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

# settings.duckdb_path は環境変数 DUCKDB_PATH の値を参照
conn = init_schema(settings.duckdb_path)
```

監査ログ用スキーマの初期化:
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

---

## 使い方（代表的な例）

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
```python
from datetime import date
from kabusys.config import settings
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema(settings.duckdb_path)  # まだ作っていなければ初期化
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース収集（RSS）と銘柄紐付け
```python
from kabusys.data.news_collector import run_news_collection

# known_codes は抽出時に有効な銘柄コードのセット（例: DB から取得）
known_codes = {"7203", "6758", "9984"}
res = run_news_collection(conn, known_codes=known_codes)
print(res)  # {source_name: saved_count, ...}
```

- ファクター計算（リサーチ用）
```python
from datetime import date
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

target = date(2024, 1, 10)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)

# Zスコア正規化の例
normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- 将来リターン・IC 計算
```python
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=target, horizons=[1,5,21])
# factor_records は事前に calc_momentum 等で得たリスト
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- カレンダー更新ジョブ（夜間バッチ）
```python
from kabusys.data.calendar_management import calendar_update_job
saved = calendar_update_job(conn, lookahead_days=90)
```

---

## 注意点 / 実運用における留意事項

- 本ライブラリは J-Quants のデータ取得を行います。API トークン管理とレート制御に注意してください。
- 発注（execution）やブローカー連携部分はプロジェクト固有の実装が必要です。現在の execution/strategy/monitoring パッケージは拡張ポイントです。
- DuckDB のトランザクションやタイムゾーン（監査ログは UTC で保存）について実運用では挙動確認をしてください。
- ニュース取得は外部 RSS を読み込むため SSRF 対策・タイムアウトを適切に設定することを推奨します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py
  - 環境変数の読み込み・Settings クラス
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント、fetch_* / save_* 関数
  - news_collector.py
    - RSS 取得、前処理、raw_news 保存、銘柄抽出
  - schema.py
    - DuckDB スキーマ定義・init_schema, get_connection
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - pipeline.py
    - ETL の差分更新ロジック、run_daily_etl 等
  - features.py
    - data.stats の再エクスポート
  - calendar_management.py
    - market_calendar 管理、営業日ユーティリティ、calendar_update_job
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）初期化
  - etl.py
    - ETLResult の公開
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
- research/
  - __init__.py
    - 主要研究関数の再エクスポート
  - feature_exploration.py
    - 将来リターン、IC、factor_summary、rank
  - factor_research.py
    - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
- strategy/
  - __init__.py  （戦略ロジックの置き場／拡張ポイント）
- execution/
  - __init__.py  （発注・ブローカー連携の置き場／拡張ポイント）
- monitoring/
  - __init__.py  （監視・メトリクスの置き場／拡張ポイント）

---

## 拡張ポイント

- strategy パッケージに独自のシグナル生成・ポートフォリオ最適化を実装する
- execution パッケージに各ブローカー（kabuステーション等）への送信ライブラリや
  再送／冪等制御を実装する
- monitoring パッケージで Prometheus や Slack 通知などの監視を実装する

---

この README はコードベースから抽出した主要情報をまとめたものです。詳細な API 使用方法や運用手順は各モジュールの docstring を参照してください。質問やサンプルの追加が必要であればお知らせください。