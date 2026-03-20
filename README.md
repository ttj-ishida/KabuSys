# KabuSys

日本株向けの自動売買フレームワーク（プロトタイプ）

KabuSys は J-Quants 等のデータソースから市場データ・財務データ・ニュースを収集し、
DuckDB 上で加工 → 特徴量作成 → シグナル生成 → 発注／監視へつなぐためのモジュール群を提供します。
研究（research）用のファクター計算や、ETL／データ品質チェック、ニュース収集、戦略ロジックの基盤を含みます。

---

## 主要な特徴（機能一覧）

- データ収集
  - J-Quants API クライアント（差分取得・ページネーション・自動トークンリフレッシュ・レートリミット）
  - RSS ベースのニュース収集（SSRF 対策・トラッキングパラメータ除去・記事IDは正規化 URL のハッシュ）
- データ基盤
  - DuckDB スキーマ定義・初期化（Raw / Processed / Feature / Execution 層）
  - ETL パイプライン（差分更新・バックフィル・品質チェック）
  - マーケットカレンダー管理（営業日判定 / next/prev / 期間内営業日取得）
- 研究・特徴量
  - ファクター計算（モメンタム / バリュー / ボラティリティ / 流動性 等）
  - 特徴量正規化（Z スコア、クロスセクション）
  - 研究用ユーティリティ（将来リターン・IC・統計サマリー）
- 戦略
  - 特徴量の構築（ユニバースフィルタ、Z スコアクリップ、features テーブルへの UPSERT）
  - シグナル生成（コンポーネントスコアの統合、Bear レジーム抑制、BUY/SELL 判定、signals テーブル書込）
- ニュースと銘柄紐付け
  - RSS 取得 → raw_news 保存 → テキストから銘柄コード抽出 → news_symbols 保存
- 発注・監査（基盤）
  - Execution / audit 用スキーマを含み、監査ログ／冪等性設計を考慮

---

## 要件（主な依存パッケージ）

最低限の依存（ソース中で参照されているもの）：
- Python 3.9+
- duckdb
- defusedxml

（実行環境や追加機能によって他のパッケージが必要になる可能性があります。setup.cfg / pyproject.toml がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

2. 依存パッケージをインストールします（例）:
   - pip install -r requirements.txt
   - または必要な最小パッケージ: pip install duckdb defusedxml

3. 環境変数を設定します:
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（`kabusys.config` の自動ロード）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB スキーマを初期化します（例↓）:
   - Python REPL やスクリプトから呼び出す:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

---

## 環境変数一覧（主な設定）

以下の環境変数は `kabusys.config.Settings` から参照されます。必須項目は README記載の通りです。

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- kabuステーション API（発注連携等）
  - KABU_API_PASSWORD (必須)
  - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- 通知（Slack 等）
  - SLACK_BOT_TOKEN (必須)
  - SLACK_CHANNEL_ID (必須)
- データベースパス
  - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- 実行モード / ログ
  - KABUSYS_ENV (任意, デフォルト: development)
    - 有効値: development / paper_trading / live
  - LOG_LEVEL (任意, デフォルト: INFO)
    - 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL

注意: 必須変数が設定されていない場合、Settings のプロパティアクセスで ValueError が発生します。

---

## 使い方（代表的な API）

以下は主要な操作を行う Python スニペット例です。

- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 の差分取得）
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())

- 特徴量（features）作成
  from datetime import date
  from kabusys.strategy import build_features
  cnt = build_features(conn, date(2025, 1, 31))
  print(f"upserted features: {cnt}")

- シグナル生成
  from datetime import date
  from kabusys.strategy import generate_signals
  total = generate_signals(conn, date(2025, 1, 31))
  print(f"signals written: {total}")

- RSS ニュース収集と保存（銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9432"}  # 事前に収集した銘柄リスト等
  res = run_news_collection(conn, known_codes=known_codes)
  print(res)

- カレンダー更新バッチ
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)
  print(f"calendar rows saved: {saved}")

- 設定値にアクセス
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)

---

## 主要モジュール / API 一覧（抜粋）

- kabusys.config
  - Settings（環境変数管理、自動 .env ロード）
- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch_* / save_*）
  - schema: DuckDB スキーマ定義・init_schema / get_connection
  - pipeline: ETL 実行（run_daily_etl, run_prices_etl, ...）
  - news_collector: RSS 取得・raw_news 保存・news_symbols 紐付け
  - calendar_management: 営業日判定 / calendar_update_job
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy
  - feature_engineering.build_features
  - signal_generator.generate_signals
- kabusys.execution
  - 発注／実行ロジック用（パッケージプレースホルダ）
- kabusys.monitoring
  - 監視・メトリクス関連（パッケージプレースホルダ）

---

## ディレクトリ構成

以下はソースツリー（主要ファイルのみ）の抜粋です:

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - schema.py
  - pipeline.py
  - features.py
  - calendar_management.py
  - stats.py
  - audit.py
  - pipeline.py
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
- monitoring/  (パッケージ未収録または実装ファイルは別途)

（実際のリポジトリには追加のユーティリティ / ドキュメント / テストが含まれる場合があります）

---

## 運用上の注意・設計上のポイント

- ルックアヘッドバイアスの防止:
  - ファクター計算・シグナル生成は target_date 時点で観測可能なデータのみを用いるよう設計されています。
  - J-Quants 取得時に fetched_at を記録し、いつデータが既知となったかを追跡できます。
- 冪等性:
  - DB への保存は ON CONFLICT / UPSERT を用いて冪等に実行します（save_* 系）。
  - features / signals は日付単位で削除→挿入することで置換（冪等）を保証します。
- ネットワーク安全性:
  - RSS 取得では SSRF 対策（ホストのプライベート判定・リダイレクト検査）を行っています。
- エラー・再試行:
  - J-Quants クライアントはリトライ（指数バックオフ）・トークン自動更新・レート制限を備えています。

---

## 開発・拡張

- strategy / execution 層は切り離されているため、シグナル生成 → 実際の発注モジュール（kabu API 等）を別モジュールで実装して統合できます。
- research モジュールは外部ライブラリに依存せず純粋な Python/SQL で実装されているため、実験や可視化用に容易に呼び出せます。
- テスト時は環境変数自動ロードを無効化したり、DuckDB のインメモリ(":memory:") を利用して検証できます。

---

## 問い合わせ / 貢献

- バグ報告や機能要望はリポジトリの Issue に記載してください。
- コントリビュートの際は既存の設計方針（ルックアヘッド回避・冪等性・トレース性）に沿って実装してください。

---

以上。README に含めたい追加情報（例: .env.example のテンプレート、より詳細な API 使用例、CI / テスト方法など）があれば教えてください。必要に応じて追記・調整します。