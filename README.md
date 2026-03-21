# KabuSys

日本株自動売買システム用ライブラリ（KabuSys）のリポジトリ README。

このドキュメントはコードベース（src/kabusys 以下）の概要、機能、セットアップ手順、簡単な使い方、ディレクトリ構成を日本語でまとめたものです。

※ 本リポジトリはライブラリ／バッチ処理群であり、実運用前に設定（API トークン、DB 保存先等）と十分な検証が必要です。

---

## プロジェクト概要

KabuSys は日本株を対象としたデータ取得・ETL、ファクター計算、特徴量作成、シグナル生成、ニュース収集、監査ログ管理を行うためのコンポーネント群を提供します。主な設計方針は以下の通りです。

- データ基盤は DuckDB を採用（オンディスク／インメモリ両対応）
- J-Quants API から株価・財務・市場カレンダー等を取得（レート制御・リトライ・トークン自動刷新対応）
- 取得データは Raw → Processed → Feature → Execution の層で管理
- ルックアヘッドバイアス対策（計算は target_date 時点で利用可能な情報のみを使用）
- 冪等性（DB への保存は ON CONFLICT / upsert 等で重複を排除）
- ニュース収集における SSRF / XML Bomb 対策等の堅牢化

---

## 主な機能一覧

- データ取得・保存
  - J-Quants API クライアント（data/jquants_client.py）
    - 株価日足、財務データ、市場カレンダーの取得と DuckDB への保存（冪等）
    - レート制御、リトライ、トークン自動更新
  - ETL パイプライン（data/pipeline.py）
    - 日次 ETL（run_daily_etl）: カレンダー、株価、財務の差分取得・保存、品質チェック
  - 市場カレンダー管理（data/calendar_management.py）
    - 営業日判定、next/prev_trading_day、夜間更新ジョブ

- データスキーマ・初期化
  - DuckDB スキーマ定義と初期化（data/schema.py）
    - Raw / Processed / Feature / Execution 層のテーブルを作成
    - インデックス作成やトランザクションでの原子的初期化

- ニュース収集
  - RSS 取得・前処理・保存（data/news_collector.py）
    - URL 正規化、トラッキングパラメータ除去、SSRF 対策、XML 安全パーサ（defusedxml）利用
    - raw_news 保存・銘柄紐付け（news_symbols）

- ファクター・リサーチ
  - ファクター計算（research/factor_research.py）
    - Momentum / Volatility / Value 等の計算（prices_daily / raw_financials を参照）
  - 特性探索（research/feature_exploration.py）
    - 将来リターン、IC（Spearman）計算、統計サマリー

- 特徴量作成・シグナル生成（strategy）
  - 特徴量エンジニアリング（strategy/feature_engineering.py）
    - raw ファクターを正規化（Z スコア）し features テーブルへ保存
  - シグナル生成（strategy/signal_generator.py）
    - features + ai_scores を統合して final_score を計算、BUY／SELL シグナルを signals テーブルへ保存
    - Bear レジーム抑制、エグジット（ストップロス等）判定

- 統計ユーティリティ
  - zscore 正規化等（data/stats.py）

- 設定管理
  - 環境変数読み込み・設定管理（config.py）
    - .env / .env.local 自動読み込み（プロジェクトルート検出）や必須チェック

---

## 必要な環境・依存

- Python 3.10 以上（コード中での型注釈 union（A | B）等を使用）
- 主要依存パッケージ（pip でインストール）
  - duckdb
  - defusedxml

（その他は標準ライブラリで実装されています。将来的に slack 連携等で追加依存が必要になる可能性があります。）

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# 開発用にパッケージ化されている場合は pip install -e .
```

---

## 環境変数（主要）

config.Settings で参照される主な環境変数（.env に設定してください）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意、デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意、デフォルト: data/monitoring.db)
- KABUSYS_ENV (任意、allowed: development, paper_trading, live；デフォルト: development)
- LOG_LEVEL (任意、DEBUG/INFO/WARNING/ERROR/CRITICAL；デフォルト: INFO)

自動 .env 読み込みについて:
- プロジェクトルートはこのモジュールファイルから親階層を上がり `.git` または `pyproject.toml` を探索して判定します。
- 読み込み順序: OS 環境変数 > .env.local > .env
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト時に便利）。

---

## セットアップ手順（簡易）

1. リポジトリをクローンして仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install duckdb defusedxml
   ```

2. 環境変数を準備
   - プロジェクトルートに `.env` を作成（.env.example があれば参照）
   - 必須トークン等を設定
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=xxxx
     SLACK_BOT_TOKEN=xxxx
     SLACK_CHANNEL_ID=xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

3. DuckDB スキーマ初期化
   - Python REPL やスクリプトから:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - init_schema は必要なディレクトリを作成し、全テーブルとインデックスを作成します（冪等）。

4. 必要なパッケージや OS 権限等を適切に整備してください（ネットワークアクセス、ファイル書き込み等）。

---

## 使い方（主要 API と実行例）

以下はライブラリを直接利用する際の典型的な流れの例です。実運用ではこれらをスクリプトやバッチ（cron / Airflow 等）で実行します。

1. DB 初期化 / 接続
   ```python
   from kabusys.data.schema import init_schema, get_connection
   conn = init_schema("data/kabusys.duckdb")
   # 既存 DB に接続する場合:
   # conn = get_connection("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（市場カレンダー、株価、財務の差分取得）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   result = run_daily_etl(conn)  # target_date を指定可能
   print(result.to_dict())
   ```

3. 特徴量（features）構築
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   count = build_features(conn, target_date=date(2024, 1, 31))
   print(f"features upserted: {count}")
   ```

4. シグナル生成
   ```python
   from kabusys.strategy import generate_signals
   total = generate_signals(conn, target_date=date(2024, 1, 31))
   print(f"signals written: {total}")
   ```

5. ニュース収集ジョブ（RSS）
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   # known_codes は銘柄抽出に使う有効コードセット
   res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes={"7203","6758"})
   print(res)
   ```

6. カレンダー更新ジョブ（夜間）
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

これらの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を引数に取るため、バッチの実行環境で接続を共有・管理してください。

---

## 注意事項 / 運用上のポイント

- 全ての ETL / 保存処理は冪等化（ON CONFLICT 等）されていますが、運用時は DB バックアップやログを適切に保持してください。
- J-Quants API のレート制限を遵守するため、クライアント側でスロットリング・リトライを実装済みです。大量取得時は実行間隔に注意してください。
- ニュース収集は外部フィードの多様性に依存するため、fetch_rss の失敗は個別ソース単位でハンドリングされます。SSRF や XML 攻撃対策を組み込んでいますが、運用監視は必要です。
- signals → 発注 → 約定 のフローは audit モジュール等でトレーサビリティを確保する設計になっています。実際のブローカー連携（kabuステーション API など）は execution 層での実装が必要です（このコードベース内では execution パッケージはプレースホルダになっています）。

---

## ディレクトリ構成（主要ファイル）

（ルート: src/kabusys 以下）

- kabusys/
  - __init__.py
  - config.py                -- 環境変数／設定管理
  - data/
    - __init__.py
    - jquants_client.py      -- J-Quants API クライアント（fetch/save）
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - schema.py             -- DuckDB スキーマ定義・初期化
    - news_collector.py     -- RSS 収集・保存・銘柄抽出
    - calendar_management.py-- 市場カレンダー管理・更新ジョブ
    - features.py           -- data.stats の再エクスポート
    - stats.py              -- zscore_normalize 等統計ユーティリティ
    - audit.py              -- 監査ログ用スキーマ（signal_events, order_requests 等）
    - execution/            -- 発注関連（将来的実装場所、空 __init__）
  - research/
    - __init__.py
    - factor_research.py    -- Momentum/Volatility/Value の計算
    - feature_exploration.py-- 将来リターン・IC・summary
  - strategy/
    - __init__.py
    - feature_engineering.py-- features 作成（build_features）
    - signal_generator.py   -- signals 作成（generate_signals）
  - monitoring/             -- 監視周り（モジュール群のためのプレースホルダ）
  - execution/              -- 発注/ブローカー連携（空のパッケージ）

---

## 追加情報 / 開発メモ

- 型注釈やドキュメンテーション文字列（docstring）が豊富に含まれているため、各モジュールの関数説明・設計意図を参照してください。
- テストや CI、runtime 用の CLI ラッパーは本リポジトリに含まれていない可能性があるため、運用用スクリプトやジョブスケジューラと組み合わせて使用してください。
- 本 README は現状のコードスニペットに基づく要約です。実運用前にセキュリティ（API キー管理、ネットワーク制限）、監査、バックテスト、モニタリングの整備を行ってください。

---

必要であれば、README に含める具体的な .env.example やサンプル運用スクリプト（cron / systemd / Airflow 向け）を作成します。どの形式が必要か教えてください。