# KabuSys

日本株向けの自動売買システム用ライブラリ群です。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、監査ログ／スキーマ管理など、量的運用に必要な主要コンポーネントを含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（サンプル）
- 環境変数（主要な設定）
- ディレクトリ構成（主要ファイルと説明）
- 補足（ライセンス／注意点）

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤のコアライブラリです。J-Quants API を利用した時系列データ／財務データの取得と DuckDB への保存、品質チェック、特徴量（features）生成、シグナル生成、ニュース収集、監査ログなどの機能を提供します。設計方針として以下を重視しています。

- 冪等性（DB への保存は ON CONFLICT/UPSERT を利用）
- ルックアヘッドバイアス防止（target_date 時点のデータのみを利用）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- DuckDB を中核とした軽量なデータレイヤ

---

## 機能一覧

主な提供機能（モジュールと代表的関数）

- 環境設定
  - kabusys.config.settings：環境変数ベースの設定管理、.env 自動読み込み機能
- データ取得 / 保存（J-Quants）
  - kabusys.data.jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
- データスキーマ管理
  - kabusys.data.schema.init_schema(db_path)：DuckDB スキーマ作成
  - get_connection(db_path)
- ETL パイプライン
  - kabusys.data.pipeline.run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- データ品質チェック（quality モジュール参照）
  - pipeline 内で品質チェックを呼出可能（run_quality_checks フラグ）
- 特徴量（Feature）計算
  - kabusys.strategy.build_features(conn, target_date)
  - 内部で research.factor_research の calc_momentum / calc_volatility / calc_value を呼出し標準化して features テーブルへ保存
- シグナル生成
  - kabusys.strategy.generate_signals(conn, target_date, threshold, weights)
  - features / ai_scores / positions を参照して BUY/SELL シグナルを作成し signals テーブルへ保存
- ニュース収集
  - kabusys.data.news_collector.fetch_rss / save_raw_news / run_news_collection
  - RSS の安全性チェック（SSRF、防爆、XML 攻撃防止）・URL 正規化・銘柄抽出
- 統計ユーティリティ
  - kabusys.data.stats.zscore_normalize：クロスセクション Z スコア正規化
- マーケットカレンダー管理
  - kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / calendar_update_job
- 監査ログ（audit）
  - signal_events / order_requests / executions 等のテーブル DDL と初期化（schema モジュールに統合）

---

## セットアップ手順

前提
- Python 3.9+ を想定（duckdb 等の互換性に基づく）
- ネットワーク経由で J-Quants API にアクセス可能な環境

1. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - pip install duckdb defusedxml
   - 実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt してください。

3. パッケージのインストール（開発モード）
   - プロジェクトルートで:
     - pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルートに .env を置くことで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数は下記参照。

5. DuckDB スキーマ初期化
   - Python コンソールやスクリプトで以下を実行：
     - from kabusys.data.schema import init_schema
       from kabusys.config import settings
       conn = init_schema(settings.duckdb_path)
   - これで必要なテーブルが作成されます。

---

## 環境変数（主要）

以下の環境変数がコード内で参照されます。必須のものは説明に「必須」と明記。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（get_id_token の元）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注周りで使用）
- KABU_API_BASE_URL (任意)
  - kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID (必須)
  - 通知先チャンネル ID
- DUCKDB_PATH (任意)
  - データ保存先の DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意)
  - 環境モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意)
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意)
  - 1 をセットすると .env の自動ロードを無効化（テスト向け）

例（.env のイメージ）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（サンプル）

以下は典型的なワークフローの簡単な例です。

1) DuckDB スキーマ初期化
```python
from kabusys.config import settings
from kabusys.data.schema import init_schema

conn = init_schema(settings.duckdb_path)
```

2) 日次 ETL を走らせる（J-Quants から取得して保存）
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

3) 特徴量の作成（features テーブルに書き込む）
```python
from datetime import date
from kabusys.strategy import build_features

cnt = build_features(conn, target_date=date.today())
print(f"features upserted: {cnt}")
```

4) シグナル生成（signals テーブルに書き込む）
```python
from kabusys.strategy import generate_signals

n = generate_signals(conn, target_date=date.today(), threshold=0.6)
print(f"signals generated: {n}")
```

5) ニュース収集（RSS から raw_news を作成し、銘柄紐付け）
```python
from kabusys.data.news_collector import run_news_collection

known_codes = {"7203", "6758", "9432"}  # 例: 有効な銘柄コードセット
results = run_news_collection(conn, known_codes=known_codes)
print(results)
```

6) J-Quants からの生データ取得（個別）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,2,1))
saved = save_daily_quotes(conn, records)
```

---

## ディレクトリ構成（主要ファイルと説明）

以下は src/kabusys 以下の主要モジュールとその簡単な説明です。

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数のラッパー）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - schema.py
      - DuckDB スキーマ定義と init_schema()
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - pipeline.py
      - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等の ETL ロジック
    - news_collector.py
      - RSS 取得、前処理、raw_news 保存、銘柄抽出
    - calendar_management.py
      - JPX カレンダー管理・営業日判定・calendar_update_job
    - features.py
      - data.stats の再エクスポート
    - audit.py
      - 監査ログ向け DDL（signal_events, order_requests, executions）
    - (その他: quality モジュール等が想定される)
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum / calc_volatility / calc_value（prices_daily, raw_financials を参照）
    - feature_exploration.py
      - forward returns, IC, factor_summary, rank 等の研究用ユーティリティ
  - strategy/
    - __init__.py
      - build_features, generate_signals の公開
    - feature_engineering.py
      - features を構築して features テーブルへ UPSERT
    - signal_generator.py
      - features / ai_scores 統合、final_score 計算、BUY/SELL 判定、signals へ書き込み
  - execution/
    - __init__.py
      - （発注周りの実装場所。今回コードベースでは空のプレースホルダ）
  - monitoring/
    - （監視用コード等を配置する想定、今回の抜粋では未表示）

（READMEではプロジェクト内の重要モジュールのみ抜粋しています。各モジュール内に詳細な docstring / 設計注釈がありますので参照してください。）

---

## 注意事項 / 補足

- DuckDB のバージョンや Python バージョンによる差異が影響する可能性があるため、実運用前にテスト環境でスキーマ初期化・ETL・特徴量計算・シグナル生成を一通り実行して動作確認してください。
- J-Quants API 利用時はレート制限・利用規約に従ってください。クライアント実装は 120 req/min のスロットリングとリトライ戦略を備えていますが、運用パターンに応じた調整が必要です。
- ニュース収集では SSRF 対策、XML の安全パーシング、応答サイズチェックなどを実施していますが、公開環境での追加のセキュリティ要件に応じた監査を推奨します。
- 環境変数の自動ロードはプロジェクトルート（.git または pyproject.toml を基準）を探索します。テストで自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 実取引（live モード）では入出金や証券会社 API（kabuステーション等）との連携テスト、監査ログの完全性チェックを必ず行ってください。

---

## 参考（よく使う API）

- DB スキーマ作成
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL
  - from kabusys.data.pipeline import run_daily_etl
  - run_daily_etl(conn)

- 特徴量 & シグナル
  - from kabusys.strategy import build_features, generate_signals
  - build_features(conn, date.today())
  - generate_signals(conn, date.today())

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, known_codes=known_codes)

---

必要であれば、README に稼働例スクリプト、CI 設定、ユニットテストの追加方法、運用チェックリストなども追記します。どの情報をさらに詳しく載せたいか教えてください。