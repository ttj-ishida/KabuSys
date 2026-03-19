# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、特徴量エンジニアリング、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログ等のユーティリティを提供します。

---

## 主なポイント（概要）

- DuckDB をデータストアとして用いたローカル / バッチ中心のデータ基盤
- J-Quants API からの株価・財務・カレンダー取得（レート制限・リトライ・トークン自動更新実装）
- ETL（差分取得、バックフィル、品質チェック）を含む日次パイプライン
- 研究用（research）で算出した生ファクターを正規化して features に保存する特徴量エンジニアリング
- 正規化済みファクターと AI スコアを統合して売買シグナルを生成
- RSS ベースのニュース収集と銘柄紐付け（SSRF 対策、入力正規化、重複排除）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
- 監査ログ（signal → order → execution のトレーサビリティ）向けテーブル群

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック（settings）
- データ取得 / 保存（kabusys.data.jquants_client）
  - fetch / save for daily quotes, financial statements, market calendar
  - レートリミッタ、リトライ、トークン自動更新
- スキーマ管理（kabusys.data.schema）
  - DuckDB テーブル定義と初期化（raw / processed / feature / execution 層）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック
  - 差分取得・バックフィルロジック
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、正規化、raw_news 保存、銘柄コード抽出・紐付け
- カレンダー管理（kabusys.data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ）
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / volatility / value）
  - forward returns, IC 計算, factor summary, rank
- 特徴量生成（kabusys.strategy.feature_engineering）
  - build_features：研究側の raw factor を正規化・合成して features テーブルへ UPSERT
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals：features + ai_scores を統合して BUY/SELL シグナルを作成、signals テーブルへ保存
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の DDL と初期化ロジック
- その他
  - 統計ユーティリティ（zscore_normalize）
  - 多くの関数は DuckDB 接続を引数に取り、本番発注 API に直接依存しない設計

---

## 動作要件（推奨）

- Python >= 3.10（型ヒントで | ユニオン等を使用）
- 依存ライブラリ（最低限）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS フィード取得時）

インストール例（簡易）
```bash
python -m pip install duckdb defusedxml
```

プロジェクト全体で requirements ファイルがあればそちらを使用してください。

---

## 環境変数（.env）

config.Settings で参照される主要な環境変数例：

- JQUANTS_REFRESH_TOKEN  （必須）: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      （必須）: kabuステーション API パスワード
- KABU_API_BASE_URL      （任意）: デフォルト http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN        （必須）: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID       （必須）: Slack 通知先チャネル ID
- DUCKDB_PATH            （任意）: デフォルト data/kabusys.duckdb
- SQLITE_PATH            （任意）: デフォルト data/monitoring.db
- KABUSYS_ENV            （任意）: development / paper_trading / live（デフォルト development）
- LOG_LEVEL              （任意）: DEBUG / INFO / WARNING / ERROR / CRITICAL

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）配下の `.env` / `.env.local` を自動で読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例 .env
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / パッケージを入手
2. Python 3.10+ の仮想環境を作成・有効化
3. 必要な依存をインストール
   - duckdb, defusedxml 等
4. .env をプロジェクトルートに作成（.env.example を参考）
5. DuckDB スキーマを初期化

DuckDB スキーマ初期化（Python 例）
```python
from kabusys.data.schema import init_schema
from kabusys.config import settings

conn = init_schema(settings.duckdb_path)  # settings.duckdb_path は Path を返す
```

メモ:
- 初期化は idempotent（既存テーブルがあればスキップ）
- ファイルパスの親ディレクトリがなければ自動作成されます

---

## 使い方（主要な実行フロー例）

以下は典型的なバッチワークフローの例です。すべて DuckDB 接続（duckdb.DuckDBPyConnection）を渡して実行します。

1) DB 初期化（上記）

2) 日次 ETL の実行（市場カレンダー・株価・財務の差分取得）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量のビルド（features テーブル作成）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
n = build_features(conn, target_date=date.today())
print(f"features upserted: {n}")
```

4) シグナル生成（features と ai_scores を元に signals テーブルへ）
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {count}")
```

5) ニュース収集（RSS 取得 → raw_news / news_symbols 保存）
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# known_codes は銘柄抽出に使う既知コードのセット（例：prices_daily の code を取得して作る）
results = run_news_collection(conn, sources=None, known_codes=None)
print(results)  # {source_name: saved_count}
```

6) カレンダー更新バッチ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意点:
- 多くの関数は冪等（idempotent）に設計されています（DELETE→INSERT の日付単位置換や ON CONFLICT を利用）。
- 本ライブラリは発注 API（ブローカー）への直接通信を行わない層を分離することを想定しています（execution 層は別実装）。

---

## ディレクトリ構成（主要モジュール）

概要（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py                         : 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                : J-Quants API クライアント（取得・保存関数）
    - news_collector.py                : RSS 取得・raw_news 保存・銘柄抽出
    - schema.py                        : DuckDB スキーマ定義・初期化
    - stats.py                         : 統計ユーティリティ（zscore_normalize）
    - pipeline.py                      : ETL パイプライン（run_daily_etl 等）
    - features.py                      : features 便利ラッパー
    - calendar_management.py           : マーケットカレンダー管理・更新ジョブ
    - audit.py                         : 監査ログ DDL 定義
    - audit (続きがある可能性)...
  - research/
    - __init__.py
    - factor_research.py               : momentum / volatility / value の計算
    - feature_exploration.py           : forward returns / IC / summaries
  - strategy/
    - __init__.py
    - feature_engineering.py           : build_features（正規化・UPSERT）
    - signal_generator.py              : generate_signals（BUY/SELL 生成）
  - execution/                         : 発注・実行管理（インターフェース層、未実装箇所あり）
  - monitoring/                        : 監視・モニタリング用コード（未実装箇所あり）

（実際のリポジトリでは pyproject.toml や .env.example、スクリプト類がある場合があります）

---

## 開発 / テストのヒント

- unit tests を作成する際は、DuckDB の ":memory:" を使うと簡単にインメモリ DB でテストできます。
- config モジュールは自動で .env を読み込みますが、テスト中は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して読み込みを抑止し、必要な環境変数を明示的に注入してください。
- network I/O が絡む箇所（jquants_client, news_collector）は HTTP 通信部分をモック可能な実装になっています（関数レベルで id_token を注入したり、_urlopen を差し替えたり可能）。

---

## 補足 / 設計上の注意

- ルックアヘッドバイアス防止の考慮が各モジュールに組み込まれています（例えば target_date 時点で利用可能なデータのみを使用）。
- 多くの SQL は日付単位での置換（DELETE → INSERT）やトランザクションを利用し、原子性を確保します。
- news_collector は SSRF / XML 再帰攻撃 / gzip bomb 等の対策を組み込んでいます（defusedxml、受信最大サイズ、リダイレクト時のホスト検査など）。
- generate_signals 等は欠損値に対する保険（中立値で補完）や Bear レジーム抑制ロジックを備えています。

---

もし README に追加したいサンプルワークフロー、CI 設定、あるいは各モジュールの API ドキュメント（関数ごとの引数・戻り値）を詳述したい場合は、その要望を教えてください。必要に応じて README を拡張します。