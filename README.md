KabuSys — 日本株向け自動売買 / データ基盤ライブラリ
=================================================

概要
----
KabuSys は日本株のデータ収集・加工・特徴量生成・監査・ETL を想定した内部ライブラリ群です。
主な目的は、J-Quants 等の外部データソースから株価・財務・市場カレンダー・ニュースを取得して
DuckDB に保存し、戦略（research/strategy）や発注（execution）で利用可能な形に整えることです。

設計方針の主なポイント
- DuckDB を中心とした軽量オンプレ/ローカル DB を想定
- J-Quants API のレート制限・リトライ・トークンリフレッシュを内包
- ETL は差分更新・バックフィル・品質チェックを実行
- News 集約は RSS 取得 → 正規化 → 銘柄抽出 → 冪等保存の流れ
- 本番発注 API へ直接アクセスしないモジュールは Research / Data 層で独立している

主な機能一覧
--------------
- 環境設定管理
  - .env 自動読み込み（プロジェクトルート検出、.env/.env.local 優先度制御）
  - 必須環境変数を強制チェック（settings オブジェクト）
- Data 層
  - J-Quants API クライアント（fetch/save, ページネーション・リトライ・レート制御）
  - News RSS 収集・正規化・保存（SSRF 対策・XML 防御・トラッキング除去）
  - DuckDB スキーマ定義 / 初期化（init_schema / init_audit_schema）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログスキーマ（signal → order → execution のトレーサビリティ）
  - 基本的な統計ユーティリティ（Zスコア正規化 等）
- Research 層
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
- その他
  - News の銘柄抽出ロジック（4桁コードマッチ）
  - ETL 実行結果の構造化（ETLResult）

セットアップ手順
----------------

1. Python バージョン
   - Python 3.10+ を推奨（typing の | 演算子・型注釈を使用）

2. インストール（プロジェクトをローカルで使う場合）
   - 任意の仮想環境を用意して activate
   - 必要パッケージをインストール（例: duckdb, defusedxml）
     pip install duckdb defusedxml
   - 開発配布を想定している場合:
     pip install -e .

   注: このリポジトリに setup.py / pyproject.toml がある想定で記載しています。実際の配布方法に合わせてください。

3. 環境変数 / .env
   - プロジェクトルートに .env または .env.local を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN — （通知等で使用する場合）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル
     - KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード
   - 任意:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

使い方（主要な API / 例）
-----------------------

以下はライブラリを直接インポートして使う最小例です。CLI は提供していないためスクリプトやタスクランナーから呼び出します。

1) DuckDB スキーマ初期化
- 初回は DB を初期化してテーブルを作成します（冪等）。
```python
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")  # ":memory:" も可
```

2) 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得と品質チェック）
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.data.pipeline import run_daily_etl

conn = init_schema("data/kabusys.duckdb")
result = run_daily_etl(conn)  # 引数で target_date, id_token 等を指定可
print(result.to_dict())
```

3) ニュース収集ジョブの実行（RSS の収集と銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import init_schema

conn = init_schema("data/kabusys.duckdb")
# known_codes は extract_stock_codes に使用する有効コード集合（例: 全上場銘柄）
res = run_news_collection(conn, sources=None, known_codes={"7203","6758"})
print(res)  # {source_name: saved_count}
```

4) J-Quants からのデータ取得（クライアント利用例）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
from kabusys.config import settings

id_token = get_id_token()  # settings.jquants_refresh_token を使用して ID トークンを取得
records = fetch_daily_quotes(id_token=id_token, date_from=date(2024,1,1), date_to=date(2024,1,31))
```

5) Research（ファクター計算・IC 等）
```python
from kabusys.research import calc_momentum, calc_forward_returns, calc_ic
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
factor_recs = calc_momentum(conn, date(2024,1,31))
fwd_recs = calc_forward_returns(conn, date(2024,1,31))
ic = calc_ic(factor_recs, fwd_recs, factor_col="mom_1m", return_col="fwd_1d")
```

主要な注意点 / 運用上のヒント
- J-Quants のレート制限（120 req/min）をクライアント内で制御していますが、大量のページネーションを伴う処理では時間がかかります。
- fetch 系 API はページネーションに対応しており、ID トークンをモジュールキャッシュで共有します。401 を受けた場合は自動リフレッシュ→再実行を試みます。
- News RSS 取得は SSRF・XML Bomb 対策を組み込んでいますが、運用時は監視とログを有効にしてください。
- DuckDB のファイルパーミッションやバックアップ運用（スナップショット）を考慮してください。
- auto .env ロードを無効にしたいテスト時等は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（抜粋）
-----------------------

src/kabusys/
- __init__.py — パッケージ初期化、公開 API
- config.py — 環境変数/設定管理（settings）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save, rate limiter, retry）
  - news_collector.py — RSS 収集・正規化・保存ロジック
  - schema.py — DuckDB スキーマ定義と init_schema/get_connection
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — market_calendar 管理、営業日判定ユーティリティ
  - quality.py — データ品質チェック
  - etl.py — ETL 公開インターフェース（ETLResult 再エクスポート）
  - audit.py — 監査ログスキーマ（信頼トレース用）
  - stats.py — 統計ユーティリティ（zscore_normalize）
  - features.py — features 公開インターフェース（zscore_normalize 再エクスポート）
- research/
  - __init__.py — 研究用公開 API（calc_momentum 等）
  - feature_exploration.py — forward returns / IC / factor_summary 等
  - factor_research.py — momentum/value/volatility 計算
- strategy/ — 戦略実装用パッケージ（空の __init__ が存在）
- execution/ — 発注/約定関連（空の __init__ が存在）
- monitoring/ — 監視関連（空の __init__ が存在）

ファイルごとの主要機能は README 内の「主な機能一覧」やコード内の docstring を参照してください。

依存関係
--------
- duckdb — データベース（必須）
- defusedxml — RSS/XML の安全なパース
- 標準ライブラリで実装されているユーティリティ群（urllib, hashlib, datetime 等）

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実際のリポジトリに LICENSE ファイルを追加してください。
- 貢献は PR ベースで行ってください。大きな設計変更は事前に Issue にて議論してください。

サポート / 問い合わせ
--------------------
- 実行時のログは標準の logging を用いています。運用環境ではハンドラを設定してファイルや外部ロギングに流してください。
- 環境変数や DB 初期化で問題がある場合は、該当モジュールの docstring とログを参照してください。

補足
----
- README に書かれている関数や挙動の詳細は各モジュール内の docstring を参照してください。特に ETL / quality / jquants_client は運用上の重要な振る舞い（リトライ・バックフィル・品質スコア）を持ちます。
- 実際の自動売買を行う場合は、必ず paper_trading 環境で十分に動作確認し、監査ログ・二重発注防止・手動停止手順を整備してください。