# KabuSys

日本株向けの自動売買・研究フレームワーク (KabuSys)。  
ファクター計算・特徴量作成・シグナル生成・ポートフォリオ構築・バックテスト・データ収集（J-Quants, RSS）などの主要機能を含むモジュール群を提供します。

## プロジェクト概要
KabuSys は、研究（factor/backtest）と運用（データ収集→特徴量→シグナル→執行）を分離した設計の日本株向けシステムです。  
主な設計方針は以下の通りです。

- ルックアヘッドバイアスを防ぐ（target_date 時点のデータのみを使用）
- DuckDB を中心としたローカル DB でデータ管理（ETL → features / ai_scores / prices 等）
- 冪等性を重視した DB 操作（UPSERT / ON CONFLICT）とトランザクション
- バックテストは本番 DB を汚さないインメモリコピーで実行
- J-Quants API を使ったデータ取得、RSS ニュース収集、セキュリティ考慮（SSRF/サイズ上限 等）

## 主な機能一覧
- データ取得 / 保存
  - J-Quants API クライアント（株価、財務、上場情報、取引カレンダー）
  - RSS ニュース収集（前処理・記事ID生成・銘柄抽出・DB保存）
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns / IC / 統計サマリー）
  - Zスコア正規化ユーティリティ
- 戦略（strategy）
  - 特徴量ビルド（build_features）
  - シグナル生成（generate_signals）：最終スコア算出、BUY/SELL 判定、signals テーブル書込
- ポートフォリオ（portfolio）
  - 候補選定、重み計算（等配分・スコア加重）
  - リスク調整（セクターキャップ、レジーム乗数）
  - 発注株数計算（リスクベース / weight ベース、単元丸め・aggregate cap）
- バックテスト（backtest）
  - ポートフォリオシミュレータ（部分約定、スリッページ、手数料、時価評価）
  - バックテストエンジン（データコピー、1日ループ、シグナル→約定シミュレーション）
  - メトリクス計算（CAGR, Sharpe, MaxDD, 勝率, ペイオフ比 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- 実行層（execution）やモニタリング等の骨組みを提供（実装拡張可能）

## セットアップ手順（開発環境向け）
1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install -e .            # (パッケージ化されている場合)
   - 主要依存（プロジェクト内で使用されているものの一例）:
     - duckdb
     - defusedxml
     - ただし、実プロジェクトでは pyproject.toml / requirements.txt を確認してください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（config.py の自動ロード）。
   - 自動ロードを一時的に無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 必要な主な環境変数（README 内での簡易説明）:
     - JQUANTS_REFRESH_TOKEN : J-Quants API のリフレッシュトークン（必須）
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID（必須）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV           : 実行環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL             : ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - 例 (.env)
     JQUANTS_REFRESH_TOKEN=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB スキーマ初期化
   - プロジェクトでは schema 初期化ユーティリティが提供されています（data.schema 参照）。
   - 例:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   （schema ファイルが別途存在する前提です。初期データロード手順は別途 ETL スクリプトに従ってください）

## 使い方（代表的な実行例）

- バックテスト（CLI）
  - コマンド例:
    python -m kabusys.backtest.run \
      --start 2023-01-01 --end 2023-12-31 \
      --cash 10000000 --db path/to/kabusys.duckdb

  - 利用可能オプション:
    --slippage, --commission, --allocation-method (equal|score|risk_based), --max-positions, --lot-size など（詳細はヘルプ参照）

- バックテストを Python から実行
  - 例:
    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest
    conn = init_schema("data/kabusys.duckdb")
    result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000)
    conn.close()

- 特徴量構築（features テーブルに書き込む）
  - 例:
    from datetime import date
    import duckdb
    from kabusys.strategy.feature_engineering import build_features
    conn = duckdb.connect("data/kabusys.duckdb")
    n = build_features(conn, date(2024, 1, 31))
    conn.close()

- シグナル生成
  - 例:
    from kabusys.strategy.signal_generator import generate_signals
    n = generate_signals(conn, date(2024, 1, 31), threshold=0.6)

- J-Quants データ取得 & 保存
  - 例:
    from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
    records = fetch_daily_quotes(date_from=..., date_to=...)
    save_daily_quotes(conn, records)

- ニュース収集 (RSS)
  - 例:
    from kabusys.data.news_collector import run_news_collection, extract_stock_codes
    results = run_news_collection(conn, sources=None, known_codes=set_of_codes)

- 設定参照
  - 例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token
    duckdb_path = settings.duckdb_path

## 主要 API / エントリポイント（抜粋）
- kabusys.backtest.run — CLI エントリポイント
- kabusys.backtest.engine.run_backtest — バックテスト実行関数
- kabusys.strategy.feature_engineering.build_features — features 作成
- kabusys.strategy.signal_generator.generate_signals — signals 作成
- kabusys.data.jquants_client — J-Quants API クライアント（fetch / save 系）
- kabusys.data.news_collector — RSS 収集・保存ユーティリティ
- kabusys.portfolio — 候補選定 / 重み計算 / サイジング / リスク調整

## 設定・挙動上の注意
- config.Settings は環境変数を直接読む設計です。未設定で必須項目を参照すると ValueError を送出します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索して行われます。CI / テストなどで無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- バックテスト実行時、実 DB の signals / positions を汚さないために run_backtest はインメモリの DuckDB コピーを作成して使用します。
- J-Quants クライアントはレート制限（120 req/min）とリトライロジック、401 リフレッシュの処理を備えています。fetch_* 系はページネーションに対応しています。
- news_collector は SSRF 防止や応答サイズ上限、XML パースの安全対策（defusedxml）などを実装しています。

## ディレクトリ構成（src/kabusys の主要ファイル）
- kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理
  - data/
    - jquants_client.py — J-Quants API クライアント + DB 保存ユーティリティ
    - news_collector.py — RSS 収集 / 保存 / 銘柄抽出
    - ...（schema / calendar_management 等が参照される）
  - research/
    - factor_research.py — momentum / volatility / value の計算
    - feature_exploration.py — forward returns / IC / 統計サマリー
  - strategy/
    - feature_engineering.py — features 作成 (z-score 正規化・ユニバースフィルタ)
    - signal_generator.py — final_score 計算 / BUY/SELL 判定 / signals 書込
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・aggregate cap
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - backtest/
    - engine.py — バックテストエンジン（ループ・サイジング・約定フロー）
    - simulator.py — 擬似約定 / ポートフォリオ状態管理
    - metrics.py — バックテスト評価指標
    - run.py — CLI ランナー
  - execution/ — 実取引用のエンドポイント置き場（拡張向け）
  - monitoring/ — 監視・ログ周りのモジュール（拡張向け）

（上記は本リポジトリの主要ファイルを抜粋した概要です。実装ファイルはさらに細分化されています。）

## 開発・運用上のベストプラクティス（簡単な提案）
- DuckDB のバックアップとスナップショットを運用し、バックテストと本番データを分離する。
- J-Quants のトークンや Slack トークンは機密情報のため CI/CD のシークレットストアに保存し、.env は .gitignore に追加する。
- バックテストでは look-ahead を避けるためにデータ収集時刻（fetched_at）と target_date の扱いに注意する。
- ニュース抽出で使う known_codes は事前に stocks テーブルなどから用意する。

---

問題・バグ報告や使い方の相談はリポジトリの Issue を立ててください。README に書かれていない補足や、追加してほしい使い方があれば教えてください。