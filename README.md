# KabuSys

日本株の自動売買プラットフォーム向けライブラリ（モジュール群）。データ取得 / ETL / 特徴量生成 / シグナル生成 / ニュース収集 / カレンダー管理 / DuckDB スキーマなど、戦略実行に必要な基盤処理を提供します。

> 本リポジトリはライブラリ形式のコードベースで、実稼働の自動売買ボットの一部（データ基盤・戦略ロジック・監査）を担います。

概要
- 言語: Python 3.8+（型注釈あり）
- DB: DuckDB を主な永続化エンジンとして利用
- 外部 API: J-Quants（株価・財務・カレンダー等取得）
- 主要機能は idempotent（冪等）設計：ON CONFLICT / トランザクションで重複挿入や途中失敗からの整合性を保つ

主な機能一覧
- data
  - jquants_client: J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レートリミット、保存ユーティリティ）
  - pipeline: 日次 ETL（市場カレンダー、株価、財務）と差分更新ロジック
  - schema: DuckDB のスキーマ定義と初期化（Raw/Processed/Feature/Execution 層）
  - news_collector: RSS 収集 → raw_news, news_symbols の保存（SSRF/サイズ/トラッキング除去等に配慮）
  - calendar_management: JPX カレンダー管理と営業日ロジック（next/prev/is_trading_day 等）
  - stats: 汎用統計ユーティリティ（Z スコア正規化）
- research
  - factor_research: momentum / volatility / value のファクター計算（prices_daily / raw_financials を参照）
  - feature_exploration: 将来リターン算出、IC（Spearman）計算、統計サマリー等（研究用）
- strategy
  - feature_engineering.build_features: 生ファクターを正規化し features テーブルへ保存（ユニバースフィルタ、Zスコア、クリップ）
  - signal_generator.generate_signals: features と ai_scores を統合して final_score を算出、BUY/SELL シグナルを signals テーブルへ書き込む（Bear レジーム抑制・エグジット判定含む）
- config
  - 環境変数読み込み（.env 自動ロード）と settings オブジェクト
- audit / execution / monitoring（監査・発注・モニタリング層の土台）

セットアップ手順（開発環境向け）
1. リポジトリをチェックアウト
   git clone <repository-url>
   cd <repository>

2. Python 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows (PowerShell)

3. 必要パッケージのインストール（最低限）
   pip install duckdb defusedxml

   注: 実行環境によっては追加パッケージ（requests 等）が必要になる可能性があります。パッケージ管理ファイルがある場合はそちらを参照してください。

4. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある階層）に .env/.env.local を置くことで自動ロードされます（config モジュール参照）。
   - 自動ロードを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（settings で参照）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

サンプル .env
# .env (例)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx-xxxxxxxxxxxxx
SLACK_CHANNEL_ID=C0123456789
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（基本的な操作例）
- DuckDB スキーマ初期化
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  res = run_daily_etl(conn, target_date=date.today())
  print(res.to_dict())

- 特徴量（features）を構築
  from kabusys.strategy import build_features
  from datetime import date
  n = build_features(conn, target_date=date(2024, 1, 31))
  print(f"upserted features: {n}")

- シグナルを生成
  from kabusys.strategy import generate_signals
  from datetime import date
  total = generate_signals(conn, target_date=date.today(), threshold=0.6)
  print(f"signals generated: {total}")

- ニュース収集ジョブ（RSS から raw_news 保存と銘柄紐付け）
  from kabusys.data.news_collector import run_news_collection
  known_codes = {"7203", "6758", "9984"}  # 有効銘柄コードセット（抽出用）
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存数, ...}

- カレンダー先読み更新ジョブ（夜間バッチ想定）
  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"market_calendar saved: {saved}")

API / ユーティリティの注意点
- J-Quants クライアントはレート制限（120 req/min）とリトライ・トークン自動更新を実装しています。
- ETL は差分取得を行い、backfill_days により末尾を再取得して API 側の後出し修正を吸収します。
- 各種 save_* 関数は冪等に設計されています（ON CONFLICT / トランザクション）。
- features / signals などは「日付単位で DELETE → INSERT」することで日次処理の原子性を担保します。
- NewsCollector は SSRF / XML Bomb / レスポンスサイズなどの安全対策を実装しています。

ディレクトリ構成（主要ファイル）
（src ディレクトリを起点）
- src/kabusys/
  - __init__.py
  - config.py               # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント + 保存
    - schema.py             # DuckDB スキーマ定義・初期化
    - pipeline.py           # ETL パイプライン
    - news_collector.py     # RSS 収集・保存・銘柄抽出
    - calendar_management.py# カレンダー管理 / 営業日ロジック
    - stats.py              # 統計ユーティリティ（zscore_normalize 等）
    - features.py           # data.stats の再エクスポート
    - audit.py              # 監査ログ用 DDL（signal_events, order_requests, executions）
    - audit/ ...            # （将来的な監査補助モジュール）
  - research/
    - __init__.py
    - factor_research.py    # momentum/volatility/value の計算
    - feature_exploration.py# 将来リターン / IC / 統計サマリ
  - strategy/
    - __init__.py
    - feature_engineering.py# 生ファクターを正規化して features に保存
    - signal_generator.py   # final_score 計算と signals 生成
  - execution/               # 発注・注文管理（骨格）
  - monitoring/              # 監視・アラート用のモジュール群（骨格）

簡単なツリー（概略）
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py
   ├─ data/
   │  ├─ jquants_client.py
   │  ├─ schema.py
   │  ├─ pipeline.py
   │  ├─ news_collector.py
   │  ├─ calendar_management.py
   │  └─ stats.py
   ├─ research/
   │  ├─ factor_research.py
   │  └─ feature_exploration.py
   └─ strategy/
      ├─ feature_engineering.py
      └─ signal_generator.py

運用上の注意 / ベストプラクティス
- 本コードは実稼働の売買に用いる前に十分なテスト（バックテスト・ペーパートレード）を行ってください。特に generate_signals の重みや閾値は戦略依存です。
- KABUSYS_ENV を適切に設定し（development / paper_trading / live）、ログレベルや通知先を環境に合わせて設定してください。
- DuckDB ファイルは定期バックアップを推奨します。監査ログや約定データは削除しない方針で設計されています。
- ニュース収集時の known_codes は過検出を避けるため実際の上場銘柄コードセットを用意してください。

トラブルシューティング（よくある問題）
- 環境変数未設定で ValueError が発生する: settings が必須キーを参照しています。 .env を確認してください。
- DuckDB が見つからない / import エラー: pip install duckdb を実行してください。
- RSS 取得が失敗する: フィード URL のスキーム（http/https）やホストがプライベートネットワークでないかを確認してください（SSRF 防止ロジックが働きます）。

貢献・拡張
- strategy、execution、monitoring 層は拡張ポイントが多く残されています。発注連携（ブローカー API）、リスク管理モジュール、ポートフォリオ最適化などを追加してください。
- research モジュールは外部解析やバックテストに使えるように拡張できます（追加の統計指標や可視化機能など）。

ライセンス / 著作権
- 本 README はコードベースに基づくドキュメントです。実際のリポジトリに適切な LICENSE ファイルを用意してください。

補足
- さらに詳細な利用例や運用手順、CI ワークフロー、デプロイ方法が必要であれば、目的（例: Docker 化、cronでのETL実行、複数環境管理）を教えてください。具体的な手順・テンプレートを作成します。