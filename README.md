# KabuSys

日本株自動売買システム（KabuSys）のコードベースです。  
データ取得（J-Quants）・ETL・特徴量作成・シグナル生成・ニュース収集・DuckDBスキーマなど、戦略開発から実運用のデータ基盤までをカバーするモジュール群を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした自動売買プラットフォーム向けのライブラリ群です。主な責務は次の通りです。

- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータスキーマ定義・永続化（Raw / Processed / Feature / Execution レイヤ）
- ETL パイプライン（差分更新・バックフィル・品質チェック）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー 等）
- 特徴量エンジニアリング（正規化・ユニバースフィルタ・features テーブルへの保存）
- シグナル生成（複数コンポーネントを統合して BUY / SELL を決定）
- RSS ベースのニュース収集と記事 -> 銘柄紐付け
- 環境変数による設定管理（.env 自動読み込み機能あり）
- 発注・実行監査用スキーマ（監査ログトレース、オーダー/約定テーブル）

設計方針として、ルックアヘッドバイアスの排除、冪等性（ON CONFLICT / トランザクション）、外部ライブラリへの過度な依存回避（可能な限り標準ライブラリで実装）を重視しています。

---

## 機能一覧

- config
  - 環境変数管理（.env, .env.local の自動読み込み、必須値チェック）
- data.jquants_client
  - J-Quants API クライアント（レートリミット、リトライ、トークン自動更新、ページネーション対応）
  - 日足・財務・カレンダーの取得と DuckDB への保存（冪等）
- data.schema
  - DuckDB のテーブル定義と初期化（raw / processed / feature / execution）
- data.pipeline
  - 日次 ETL（差分更新・バックフィル・品質チェック統合）
- data.news_collector
  - RSS 取得・XML パース（defusedxml）・記事整形・ID 生成・raw_news 保存・銘柄抽出
- data.calendar_management
  - JPX カレンダー管理（営業日判定、next/prev_trading_day、calendar 更新ジョブ）
- data.stats / data.features
  - Z スコア正規化などの統計ユーティリティ
- research
  - factor_research: momentum / volatility / value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー
- strategy
  - feature_engineering: ファクター統合・Z スコア正規化・features テーブルへの UPSERT
  - signal_generator: final_score 計算、BUY / SELL シグナル生成、signals テーブルへの保存
- execution / monitoring
  - （実行/モニタリング層のためのプレースホルダ/スキーマあり）

---

## 動作環境 / 事前要件

- Python 3.10 以上（型注釈に `|` を利用）
- 必要パッケージ（代表例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS フィード等）

備考: 実際の requirements.txt / packaging はプロジェクトに合わせて用意してください。ここに挙げたパッケージはコードから明示的に参照されるものです。

---

## セットアップ手順

例: 仮想環境を利用してローカルで動かす手順

1. リポジトリをクローン・移動
   - git clone ...; cd <repo>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install --upgrade pip
   - pip install duckdb defusedxml
   - （必要に応じて他パッケージを追加）

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` を作成すると、自動で読み込まれます（.env.local は上書き優先で読み込み）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1  # 自動ロードを無効化する場合
   - 参考用に .env.example を用意してください（本リポジトリに含めるのがおすすめ）。

5. DuckDB スキーマ初期化（Python から）
   - 以下を実行して DB とスキーマを作成します（DUCKDB_PATH を適宜設定してください）:

   Python 例:
   - from kabusys.data.schema import init_schema, settings
   - conn = init_schema(settings.duckdb_path)

---

## 使い方（代表的なユースケース例）

以下は簡単な Python スニペット例です。プロダクション運用ではログ設定やエラーハンドリングを適切に行ってください。

- スキーマ初期化
  - from kabusys.data.schema import init_schema
  - conn = init_schema("data/kabusys.duckdb")

- 日次 ETL 実行（J-Quants トークンは環境変数で管理）
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - conn = init_schema("data/kabusys.duckdb")
  - result = run_daily_etl(conn, target_date=date.today())
  - print(result.to_dict())

- 特徴量作成（feature_engineering）
  - from datetime import date
  - from kabusys.strategy import build_features
  - conn = init_schema("data/kabusys.duckdb")
  - n = build_features(conn, target_date=date.today())
  - print(f"features upserted: {n}")

- シグナル生成
  - from datetime import date
  - from kabusys.strategy import generate_signals
  - conn = init_schema("data/kabusys.duckdb")
  - total = generate_signals(conn, target_date=date.today())
  - print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS）
  - from kabusys.data.news_collector import run_news_collection
  - conn = init_schema("data/kabusys.duckdb")
  - known_codes = {"7203", "6758", ...}  # 有効な銘柄コードセット
  - results = run_news_collection(conn, known_codes=known_codes)
  - print(results)

注意:
- 多くの関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取ります。init_schema / get_connection で取得した接続を渡してください。
- J-Quants API 呼び出しはレート制限や認証が必要です。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。
- ETL は差分取得を行います。最初のフルロードは run_prices_etl/run_financials_etl の date_from を適切に設定してください。

---

## 主要ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         # J-Quants API クライアント（取得 + 保存ユーティリティ）
  - news_collector.py         # RSS 抽出・保存・銘柄マッチング
  - schema.py                 # DuckDB スキーマ定義・init_schema
  - pipeline.py               # ETL パイプライン（run_daily_etl 等）
  - stats.py                  # 統計ユーティリティ（zscore_normalize）
  - features.py               # features 用公開 API（再エクスポート）
  - calendar_management.py    # マーケットカレンダー管理
  - audit.py                  # 監査ログスキーマ（order_requests / executions 等）
  - ...（quality / その他モジュールがある想定）
- research/
  - __init__.py
  - factor_research.py        # モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py    # 将来リターン / IC / 統計サマリ
- strategy/
  - __init__.py
  - feature_engineering.py    # features テーブル構築
  - signal_generator.py       # final_score 計算・signals 作成
- execution/
  - __init__.py               # 実行層（発注/モニタリング）用のプレースホルダ
- monitoring/
  - ...                       # 監視・アラート連携の実装想定

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネルID
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/...
- KABUSYS_DISABLE_AUTO_ENV_LOAD (任意) — 1 を設定すると .env の自動読み込みを無効化

欠落している必須変数があると Settings のプロパティ参照時に ValueError が発生します。

---

## トラブルシューティング（よくある問題）

- DuckDB 接続エラー
  - パスに対するディレクトリが存在しない場合、init_schema は親ディレクトリを作成しますが、ファイルパーミッション等を確認してください。
- J-Quants 認証エラー（401）
  - JQUANTS_REFRESH_TOKEN が正しいか、API レスポンスを確認してください。jquants_client は 401 受信時にトークンの自動リフレッシュを試みます。
- RSS 取得で XML 解析失敗
  - フィードが不正な形式の可能性があります。fetch_rss は解析失敗時に警告を出して空リストを返します。
- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定しているか、プロジェクトルート（.git または pyproject.toml を基準）を検出できない場合は自動読み込みをスキップします。

---

## 開発・貢献

- コードスタイル、テスト、CI 設定はプロジェクト標準に従ってください。
- 大きな設計変更や機能追加は Issue / PR を通じて提案してください。

---

以上がこのリポジトリの README です。必要であれば、セットアップ手順の自動化（requirements.txt / Poetry / setup.py）、サンプルスクリプト（cli 入口）や .env.example の追加、運用ガイド（監視・バックテスト手順）などの追記を行えます。どの部分を拡充したいか教えてください。