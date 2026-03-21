# KabuSys

日本株自動売買プラットフォームのコアライブラリです。データ収集（J-Quants）、ETL、特徴量生成、シグナル生成、ニュース収集、マーケットカレンダー管理、監査ログなど、アルゴリズムトレーディングに必要な共通機能を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（target_date 時点のデータのみを使用）
- DuckDB を中心としたローカルデータレイヤー（Raw / Processed / Feature / Execution）
- 冪等性（ON CONFLICT / トランザクション）と監査可能なデータ保存
- 外部依存は最小限（標準ライブラリ + 必須ライブラリのみ）

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - raw_prices / raw_financials / market_calendar などの生データ保存と冪等保存関数
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：市場カレンダー、株価、財務データの差分取得と品質チェック
  - 個別 ETL ジョブ（prices / financials / calendar）
- データスキーマ管理
  - DuckDB のスキーマ定義と初期化（init_schema）
- 研究（research）機能
  - モメンタム / ボラティリティ / バリュー等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 戦略（strategy）機能
  - 特徴量作成（build_features）: 生ファクターの正規化・フィルタリング・features テーブルへの保存
  - シグナル生成（generate_signals）: features と ai_scores を統合し BUY/SELL シグナルを作成して signals テーブルへ保存
- ニュース収集
  - RSS フィードから記事を取得して raw_news に保存、銘柄コード抽出と紐付け
  - SSRF/サイズ/XML Bomb 等の安全対策を実装
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days 等のユーティリティ
  - カレンダーの差分更新ジョブ
- 監査ログ（audit）
  - signal_events / order_requests / executions など監査用テーブル（トレース可能な UUID 階層）
- 汎用ユーティリティ
  - zscore_normalize 等の統計ユーティリティ

---

## 要件（Requirements）

- Python 3.10+
- 必須パッケージ（代表）
  - duckdb
  - defusedxml

（ネットワークは urllib を使用しているため requests は不要）

インストール例（pip）:
```
pip install duckdb defusedxml
```

---

## 環境変数（主なもの）

KabuSys は .env ファイル（プロジェクトルートにある .env / .env.local）または OS 環境変数から設定を読み込みます。自動ロードはデフォルトで有効（プロジェクトルートは .git または pyproject.toml を基準に探索）。テスト時などに自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須の環境変数:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live、デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

Settings は kabusys.config.settings から取得できます。未設定の必須変数にアクセスすると ValueError が発生します。

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動（.git または pyproject.toml が必要）
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール
   ```
   pip install duckdb defusedxml
   ```
4. 環境変数を用意（.env を作成）
   - プロジェクトルートに `.env` または `.env.local` を置く
   - 必須キーを設定（JQUANTS_REFRESH_TOKEN 等）
5. DuckDB スキーマ初期化（下記 Usage を参照）

---

## 使い方（基本例）

以下は最小限の使用例です。各関数は duckdb の接続オブジェクト（kabusys.data.schema.init_schema または get_connection が返す接続）を受け取ります。

- DB 初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```
":memory:" を指定するとインメモリ DB になります:
```
conn = init_schema(":memory:")
```

- 日次 ETL 実行（市場カレンダー・株価・財務データの差分取得と品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)  # target_date を省略すると今日
print(result.to_dict())
```

- 特徴量（features）を構築
```
from datetime import date
from kabusys.strategy import build_features
build_features(conn, date(2024, 1, 1))
```

- シグナル生成
```
from datetime import date
from kabusys.strategy import generate_signals
generate_signals(conn, date(2024, 1, 1))
```

- ニュース収集ジョブ
```
from kabusys.data.news_collector import run_news_collection
# known_codes を渡すとテキストから銘柄抽出して紐付けを行う
run_news_collection(conn, known_codes={"7203", "6758"})
```

- カレンダー差分更新ジョブ（夜間バッチ）
```
from kabusys.data.calendar_management import calendar_update_job
calendar_update_job(conn)
```

- J-Quants からのデータ取得（個別呼出し）
```
from kabusys.data import jquants_client as jq
records = jq.fetch_daily_quotes(date_from=..., date_to=...)
jq.save_daily_quotes(conn, records)
```

- 設定値の取得
```
from kabusys.config import settings
print(settings.duckdb_path, settings.env, settings.is_live)
```

注意点：
- build_features / generate_signals は target_date 時点のデータのみを使用するよう設計されています（ルックアヘッドバイアス対策）。
- 各種 DB 書き込みはトランザクション内で日付単位の置換（DELETE + INSERT）を行い冪等性を担保します。

---

## 重要な API / 関数（参照用）

- kabusys.data.schema
  - init_schema(db_path)
  - get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.research
  - calc_momentum(conn, target_date)
  - calc_volatility(conn, target_date)
  - calc_value(conn, target_date)
  - calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=0.6, weights=None)
- kabusys.config
  - settings (Settings インスタンス)

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - stats.py
  - features.py
  - calendar_management.py
  - audit.py
  - (その他データ系モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- execution/
  - __init__.py
- (monitoring モジュールが __all__ に含まれますが、実装が無い場合があります)

注: 上記は本リポジトリの主要ファイルを抜粋したものです。詳細はソースツリーを参照してください。

---

## 開発・運用上の注意

- 環境（KABUSYS_ENV）は "development" / "paper_trading" / "live" のいずれかを指定してください。live では実際の発注フローと接続する想定です（運用時は十分な安全確認を行ってください）。
- 自動ロードされる .env/.env.local はプロジェクトルート（.git または pyproject.toml を基準）で検出されます。テストで自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のスキーマは init_schema() で一括作成されます。既存テーブルはスキップされるため安全に呼べますが、バージョンアップ時の DDL 変更には注意してください。
- ニュース収集や外部 API 呼び出しはネットワークエラー・不正レスポンスを大量に投げる可能性があるため、本番運用ではリトライ方針や監視（Slack 通知等）を組み合わせてください。

---

この README はコードの概要と基本的な使い方をまとめたものです。詳細な仕様（StrategyModel.md / DataPlatform.md / Research 等）がリポジトリにある場合はそちらを参照してください。必要であれば、運用手順やサンプルスクリプト、unit test の書き方などの追加ドキュメントも作成します。