# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。データ収集（J-Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、ファクター計算（リサーチ用ユーティリティ）、監査ログなどを提供します。

主に内部で使う Python モジュール群として設計されており、戦略実装・発注・モニタリング等の上位レイヤーから利用します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（コード例）
- 環境変数（設定項目）
- ディレクトリ構成（主要ファイルの説明）
- 注意事項

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群です。

- J-Quants API から株価・財務・カレンダー等のデータを取得して DuckDB に格納する ETL パイプライン
- RSS によるニュース収集と記事を DuckDB に保存・銘柄紐付け
- 研究（Research）用のファクター計算（モメンタム、ボラティリティ、バリュー等）と特徴量評価（IC・統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- 設定管理（.env 自動ロード、環境変数ラッパー）

設計上、DuckDB をメイン DB として想定し、外部依存は最小限（標準ライブラリ + 一部ライブラリ）に抑えられています。

---

## 機能一覧

- 環境設定
  - .env / .env.local 自動読み込み（プロジェクトルートの判定は .git または pyproject.toml）
  - 必須設定の取得（未設定時は例外）
  - KABUSYS_ENV / LOG_LEVEL バリデーション
- データ取得・保存（J-Quants）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar（ページネーション対応）
  - save_daily_quotes / save_financial_statements / save_market_calendar（DuckDB への冪等保存）
  - RateLimiter、リトライ、トークン自動リフレッシュ等の堅牢化
- ETL パイプライン
  - 差分取得（最終取得日を基準に差分を取得）
  - backfill（後出し修正を吸収するための再取得）
  - run_daily_etl：カレンダー→価格→財務→品質チェックの一括実行
- スキーマ管理
  - DuckDB 用スキーマ定義・初期化（init_schema, get_connection）
  - 監査ログ用スキーマ（init_audit_schema, init_audit_db）
- ニュース収集
  - RSS 取得（SSRF / gzip / XML Bomb 対策）
  - テキスト前処理・URL 正規化・記事ID生成（SHA-256）
  - raw_news 保存、news_symbols 紐付け（冪等）
  - run_news_collection：複数ソースの一括収集
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（run_all_checks）
- 研究用ユーティリティ
  - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats）
- その他
  - カレンダー管理（営業日判定 / next/prev trading day）
  - 監査ログ（signal_events / order_requests / executions）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の | 記法などを使用）
- Git 等でリポジトリをクローンできること

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   KabuSys のコードは標準ライブラリ中心ですが、以下のパッケージが必要です。
   - duckdb
   - defusedxml

   例:
   ```
   pip install duckdb defusedxml
   ```

   （プロジェクトに requirements.txt がある場合はそれを利用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（.git または pyproject.toml を基準にプロジェクトルートを探索）。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB スキーマ初期化
   - Python REPL やスクリプトで次を実行して DB を初期化します（デフォルトパスは settings.duckdb_path）。
   ```
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)  # data/kabusys.duckdb を作成・初期化
   ```

---

## 使い方（基本的なコード例）

以下は主要 API の使用例です。

- 設定取得
```
from kabusys.config import settings

token = settings.jquants_refresh_token
db_path = settings.duckdb_path
```

- DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)
```

- 日次 ETL 実行（J-Quants から差分取得して保存、品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
print(result.to_dict())
```

- ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES

# known_codes は銘柄抽出に使う有効な銘柄コードの集合（例: {'7203','6758',...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={'7203','6758'})
print(res)  # {source_name: 新規保存数}
```

- J-Quants からの日足取得（低レベル）
```
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
saved = save_daily_quotes(conn, records)
```

- ファクター計算（研究用）
```
from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

mom = calc_momentum(conn, target_date=date(2024,2,1))
vol = calc_volatility(conn, target_date=date(2024,2,1))
val = calc_value(conn, target_date=date(2024,2,1))

# Zスコア正規化の例
normed = zscore_normalize(mom, columns=['mom_1m','mom_3m','mom_6m'])
```

- IC 計算（ファクター有効性評価）
```
from kabusys.research import calc_forward_returns, calc_ic

fwd = calc_forward_returns(conn, target_date=date(2024,2,1), horizons=[1,5])
ic = calc_ic(factor_records=mom, forward_records=fwd, factor_col='mom_1m', return_col='fwd_1d')
```

---

## 環境変数（主な設定項目）

設定は .env または OS の環境変数から読み込まれます。自動読み込みはプロジェクトルートが見つかった場合に行われ、優先順位は OS 環境 > .env.local > .env です。

必須（未設定時は ValueError が発生）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注周りで必要）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack チャンネル ID

任意（デフォルト値あり）
- KABUSYS_ENV           : environment。development / paper_trading / live（デフォルト development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env 自動ロードを無効化
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH           : monitoring 用 SQLite パス（デフォルト data/monitoring.db）
- KABU_API_BASE_URL     : kabu API base URL（デフォルト http://localhost:18080/kabusapi）

例（.env）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: .env のパースはシェル風の quoted 値やコメントをサポートしています（.env/.env.local の読み込みロジックを参照）。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要ファイル／モジュールと役割です（パスは src/kabusys 以下）。

- __init__.py
  - パッケージのバージョン定義と公開サブパッケージ一覧

- config.py
  - 環境変数の自動ロード（.env/.env.local）と Settings クラス（設定アクセサ）

- data/
  - jquants_client.py : J-Quants API クライアント（取得 / 保存 / 認証 / リトライ / レート制御）
  - news_collector.py : RSS ベースのニュース収集・前処理・保存・銘柄抽出
  - schema.py         : DuckDB スキーマ定義と init_schema / get_connection
  - stats.py          : zscore_normalize 等の統計ユーティリティ
  - pipeline.py       : ETL パイプライン（run_daily_etl 等）
  - features.py       : 特徴量ユーティリティの公開インターフェース
  - calendar_management.py : market_calendar の管理（営業日判定 / 更新ジョブ）
  - audit.py          : 監査ログ（signal/events/order/exec）スキーマと初期化
  - etl.py            : ETL 関連型の再エクスポート（ETLResult）
  - quality.py        : データ品質チェック（欠損／スパイク／重複／日付不整合）

- research/
  - feature_exploration.py : 将来リターン計算 / IC / 統計サマリー
  - factor_research.py     : momentum / volatility / value ファクター計算
  - __init__.py            : 研究用ユーティリティの再エクスポート（calc_momentum など）

- strategy/、execution/、monitoring/
  - パッケージプレースホルダ（将来的な戦略実装や発注周り、監視機能向け）

---

## 注意事項 / 運用上のポイント

- API レート・リトライ
  - J-Quants クライアントは 120 req/min を想定した固定間隔スロットリングとリトライロジックを実装しています。過負荷を避けるため、本モジュール外からの呼び出しでも配慮してください。
- データの整合性
  - ETL は差分更新・バックフィル戦略を採用していますが、初回は過去全期間をロードすることになります（_MIN_DATA_DATE = 2017-01-01 が初期値）。
- セキュリティ
  - news_collector は SSRF 対策、gzip 解凍サイズ検査、defusedxml による XML パース保護等を行っています。外部 URL を扱う際は設定と運用に注意してください。
- 監査ログ
  - 監査スキーマはトレーサビリティ重視で設計されています。発注の冪等キー（order_request_id 等）を必ず活用してください。
- テスト / 開発
  - 自動 .env 読み込みはテストで邪魔な場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- Python バージョン
  - typing の | 演算子等を使用しているため Python 3.10 以上を推奨します。

---

必要に応じて README を拡張して、運用ガイド（cron での ETL スケジュール、Slack 通知の統合、実際の発注フローの注意点）や CLI 実行例、ユニットテストの実行方法などを追加してください。必要であれば、README に含めるサンプル .env.example や systemd / cron の実行例も作成します。