# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（設定）
- 使い方（主要なコード例）
- ディレクトリ構成（主要ファイル説明）
- 開発時の補足・注意事項

---

## プロジェクト概要

KabuSys は日本株のデータ収集・前処理・特徴量生成・シグナル生成・監査を念頭に置いたライブラリ群です。  
J-Quants API から市場データや財務データを取得し、DuckDB に保存・整形した上で、戦略の特徴量作成（feature engineering）やシグナル生成を行うためのモジュールを提供します。ニュース収集（RSS）やマーケットカレンダー管理、ETL パイプライン、発注・実行ログのスキーマなども含みます。

設計方針の一部：
- ルックアヘッドバイアスを防ぐため「対象日時点のデータのみ」を使用
- DuckDB によるローカル永続化（冪等性を重視）
- J-Quants のレート制限・リトライ・トークン自動更新に対応
- 外部依存を最小化（可能な箇所は標準ライブラリ実装）

---

## 機能一覧

主な機能：
- J-Quants API クライアント（取得・保存用の fetch/save 関数）
- DuckDB スキーマ定義と初期化（init_schema）
- ETL パイプライン（差分取得・保存・品質チェック）
- 特徴量エンジニアリング（build_features）
- シグナル生成（generate_signals）
- ニュース収集（RSS -> raw_news 保存・銘柄抽出）
- マーケットカレンダー管理（営業日判定や更新ジョブ）
- 統計ユーティリティ（Zスコア正規化、IC計算など）
- 監査ログ／発注監査テーブル定義

---

## 前提条件

- Python 3.10+
  - 型注釈で `X | Y` の表記を利用しているため 3.10 以降を想定しています。
- 必要なパッケージ（例）
  - duckdb
  - defusedxml
  - （環境に応じて）その他 HTTP/JSON の標準ライブラリを使用

パッケージはプロジェクトに requirements ファイルがなければ次のようにインストールできます：
pip install duckdb defusedxml

（実際の配布パッケージがあれば pip install -e . 等を推奨）

---

## セットアップ手順

1. リポジトリをクローン（またはパッケージを入手）
2. Python 環境（venv など）を作成・有効化
3. 依存パッケージをインストール
   - pip install duckdb defusedxml
4. 環境変数を設定（下記「環境変数」節参照）
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードはデフォルトで有効）
5. DuckDB スキーマの初期化（例を参照）

---

## 環境変数（設定）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須（Settings による取得）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション等の API パスワード
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID

任意（デフォルト値あり）:
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...。デフォルト INFO）

.env の書き方は一般的な KEY=VALUE 形式に対応しており、export プレフィクスやクォートも扱えます。

---

## 使い方（主要な例）

以下は Python スニペット例です。実行する前に環境変数をセットし、必要なら仮想環境を有効にしてください。

1) DuckDB スキーマ初期化
```python
from kabusys.data.schema import init_schema, get_connection
from kabusys.config import settings

# デフォルトパスを使う例
db_path = settings.duckdb_path
conn = init_schema(db_path)
# もしくはインメモリ
# conn = init_schema(":memory:")
```

2) 日次 ETL 実行（J-Quants からデータを差分取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.data.schema import init_schema
from kabusys.config import settings
from datetime import date

conn = init_schema(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

3) 特徴量作成（feature layer への保存）
```python
from kabusys.strategy import build_features
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
count = build_features(conn, target_date=date(2024, 1, 15))
print(f"features upserted: {count}")
```

4) シグナル生成
```python
from kabusys.strategy import generate_signals
from kabusys.data.schema import get_connection
from datetime import date

conn = get_connection("data/kabusys.duckdb")
total = generate_signals(conn, target_date=date(2024, 1, 15))
print(f"signals written: {total}")
```

5) ニュース収集（RSS）ジョブ
```python
from kabusys.data.news_collector import run_news_collection
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
# sources を省略するとデフォルトの RSS ソースが使われる
results = run_news_collection(conn, known_codes={"7203", "6758"})  # known_codes は既知銘柄コード集合
print(results)
```

6) カレンダー更新ジョブ
```python
from kabusys.data.calendar_management import calendar_update_job
from kabusys.data.schema import get_connection

conn = get_connection("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print(f"calendar saved: {saved}")
```

注意:
- これらはライブラリ API を直接呼ぶ例です。運用ではジョブスケジューラ（cron / Airflow など）から呼び出すことを想定しています。
- ETL は差分取得を行います。初回ロード時はデータ量に注意してください。

---

## ディレクトリ構成（主要ファイルと説明）

（src/kabusys 配下の主要モジュール）

- kabusys/
  - __init__.py
    - パッケージ初期化。公開モジュールを __all__ で定義。
  - config.py
    - 環境変数／設定管理。`.env` 自動ロード、必須パラメータ検証、Settings クラスを提供。
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・リトライ・レート制御・トークン管理）
    - news_collector.py
      - RSS 取得、記事前処理、記事 ID 生成、raw_news 保存、銘柄抽出
    - schema.py
      - DuckDB のスキーマ定義と初期化 / 接続ユーティリティ（init_schema, get_connection）
    - stats.py
      - zscore_normalize などの統計ユーティリティ
    - pipeline.py
      - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
    - calendar_management.py
      - 市場カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
    - audit.py
      - 発注・監査ログ用 DDL（トレーサビリティ）
    - features.py
      - データ層の特徴量ユーティリティ公開インターフェース
    - quality.py (参照されるが抜粋内では未表示)
      - 品質チェック実装（ETL 後の欠損・スパイク検出などを想定）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）
    - feature_exploration.py
      - IC 計算、将来リターン、統計サマリー（研究用ユーティリティ）
  - strategy/
    - __init__.py
      - build_features, generate_signals を公開
    - feature_engineering.py
      - 研究で得られた raw factor を正規化・合成して features テーブルに保存
    - signal_generator.py
      - features と ai_scores を用いて final_score を計算し signals テーブルへ保存
  - execution/
    - __init__.py
      - 発注・実行層（スケルトン、実装は環境に応じて拡張）
  - monitoring/ (参照される想定のモジュール群)
    - （監視・アラート送信等を想定）

---

## 開発時の補足・注意事項

- 自動 `.env` 読み込み:
  - config モジュールはパッケージの位置からプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を自動で読み込みます。テスト時などに自動読み込みを避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 型 / Python バージョン:
  - 3.10 以降を想定（ユニオン型 `X | Y` を利用）。
- DuckDB ファイル:
  - デフォルトは data/kabusys.duckdb。init_schema は親ディレクトリがなければ自動作成します。
- 冪等性:
  - save_* 系関数は ON CONFLICT を使って冪等にデータを保存します。ETL を複数回実行しても重複は回避される設計です。
- レート制御・リトライ:
  - J-Quants API 呼び出しは固定間隔のスロットリングとリトライ（指数バックオフ）を備えています。401 時は自動でトークンを更新します。
- セキュリティ:
  - news_collector には SSRF 対策や XML パーサの防御（defusedxml）・gzip 上限チェック等の実装があります。外部 URL を扱う箇所では追加の検証を推奨します。
- 運用:
  - ETL / calendar_update_job / news_collection 等は scheduler（cron / systemd timer / Airflow 等）で定期実行することを想定しています。
- ログ:
  - LOG_LEVEL 環境変数で制御可能。production（live）では適切なログ出力先（ファイル or 外部ログ収集）を用意してください。

---

必要に応じて README に具体的な CLI ラッパー、systemd ユニット、Dockerfile、CI/CD 手順などを追加できます。ほかに README に載せたい使い方や運用例（cron、Airflow、Docker 運用など）があれば教えてください。