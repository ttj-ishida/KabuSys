# KabuSys

KabuSys は日本株向けの自動売買・研究フレームワークです。データ収集（J-Quants / RSS）、ファクター計算、特徴量エンジニアリング、シグナル生成、ポートフォリオ構築、バックテスト、簡易シミュレーションまでを含むモジュール群を提供します。

本ドキュメントはリポジトリ内のコードを基にした README です。

## 概要

- データ取得: J-Quants API クライアント（株価・財務・カレンダー）、RSS ベースのニュース収集
- 研究: ファクター計算（モメンタム / ボラティリティ / バリュー）、特徴量探索（IC など）
- 特徴量処理: Z スコア正規化、ユニバースフィルタ、features テーブル書き込み
- シグナル生成: features + ai_scores を統合して BUY / SELL シグナルを生成
- ポートフォリオ構築: 候補選定・重み付け・ポジションサイジング・セクター制限・レジーム乗数
- バックテスト: 日次ループでの擬似約定・スリッページ・手数料モデル、評価指標算出（CAGR, Sharpe, MaxDD 等）
- 実行環境: DuckDB を利用したデータ永続化（スキーマ管理は data/schema モジュール想定）

## 主な機能一覧

- kabusys.config
  - .env 自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ヘルパー
- kabusys.data.jquants_client
  - J-Quants API 呼び出し（レート制御、リトライ、トークン自動更新）
  - データ取得 & DuckDB へ保存ユーティリティ
- kabusys.data.news_collector
  - RSS フィード取得、記事の前処理、raw_news への保存、記事→銘柄紐付け
  - SSRF 対策、受信サイズ制限、トラッキングパラメータ除去 等
- kabusys.research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量解析ユーティリティ（calc_forward_returns / calc_ic / factor_summary）
- kabusys.strategy
  - build_features(conn, target_date): features テーブルを構築
  - generate_signals(conn, target_date, ...): signals テーブルに BUY/SELL を挿入
- kabusys.portfolio
  - 候補選定、等金額／スコア重み、ポジションサイジング、セクター制限、レジーム乗数
- kabusys.backtest
  - run_backtest(...): 指定期間でのバックテスト実行
  - PortfolioSimulator: 擬似約定・マークツーマーケット・トレード履歴記録
  - metrics: バックテスト評価指標計算
  - CLI エントリポイント: python -m kabusys.backtest.run

## 必要条件 / 推奨環境

- Python 3.10+
- 必須（想定）パッケージ:
  - duckdb
  - defusedxml
- その他（使用する機能により）:
  - 標準ライブラリ以外の依存は limited（J-Quants クライアントは urllib を使用）

※ requirements.txt はリポジトリにない場合があります。プロジェクトで必要なパッケージを追加してください。

## 環境変数

（config.Settings が参照する主なキー）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）が検出されると、ルートにある `.env` と `.env.local` を自動的に読み込みます。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

## セットアップ手順（例）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （プロジェクト固有の requirements.txt があれば pip install -r requirements.txt）
4. 環境変数を設定
   - ルートに .env を作成するか、必要な環境変数をシェルに export してください。
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=xxxx
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
5. DuckDB スキーマ初期化
   - data/schema モジュールの init_schema 関数を使って DuckDB ファイルを初期化します（schema 実装があることを想定）。
   - 例（Python REPL）:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

## 使い方（代表例）

- バックテスト実行（CLI）
  - 必要データ（prices_daily, features, ai_scores, market_regime, market_calendar 等）が DuckDB に存在する前提
  - コマンド例:
    python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb
  - 主なオプション: --cash, --slippage, --commission, --allocation-method, --max-positions, --lot-size

- 特徴量構築
  - Python から:
    from kabusys.strategy import build_features
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    build_features(conn, target_date=date(2024, 1, 31))
    conn.close()

- シグナル生成
  - Python から:
    from kabusys.strategy import generate_signals
    import duckdb
    conn = duckdb.connect("data/kabusys.duckdb")
    generate_signals(conn, target_date=date(2024, 1, 31))
    conn.close()

- J-Quants データ取得 & 保存（例）
  - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  - id_token = None  # 通常は内部でリフレッシュトークンから取得される
  - recs = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  - save_daily_quotes(conn, recs)

- ニュース収集
  - from kabusys.data.news_collector import run_news_collection
  - run_news_collection(conn, sources=None, known_codes=set_of_codes)

- バックテストの Python 呼び出し
  - from kabusys.backtest.engine import run_backtest
  - result = run_backtest(conn, start_date, end_date, initial_cash=10_000_000, ...)

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - data/
    - jquants_client.py — J-Quants API クライアント、保存ユーティリティ
    - news_collector.py — RSS 収集・前処理・DB 保存ロジック
    - （その他: calendar_management, schema などを想定）
  - research/
    - factor_research.py — calc_momentum, calc_volatility, calc_value
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - strategy/
    - feature_engineering.py — build_features（features テーブル生成）
    - signal_generator.py — generate_signals（features + ai_scores → signals）
  - portfolio/
    - portfolio_builder.py — select_candidates, calc_equal_weights, calc_score_weights
    - position_sizing.py — calc_position_sizes（等金額 / スコア / リスクベース）
    - risk_adjustment.py — apply_sector_cap, calc_regime_multiplier
  - backtest/
    - engine.py — run_backtest（バックテストのコアループ）
    - simulator.py — PortfolioSimulator（擬似約定）
    - metrics.py — バックテスト評価指標の計算
    - run.py — CLI エントリポイント
    - clock.py — SimulatedClock（将来拡張用）
  - execution/
    - （発注 / kabu ステーション連携周りを想定）
  - monitoring/
    - （モニタリング・通知等を想定）

ファイルごとに docstring／コメントで設計方針や入出力を明示しています。各モジュールは「DuckDB 接続を受け取る」「DB 参照を最小限にする」などの設計原則に従っています。

## 既知の注意点 / TODO

- news_collector.py の末尾が未完（本リポジトリで切れている可能性があります）。実運用前にファイルが完全であることを確認してください。
- schema（テーブル定義）モジュールが存在することが前提です。init_schema 関数で DuckDB スキーマを作る想定です。
- 実稼働での発注（kabu API）や Slack 通知は認証情報・ネットワークアクセスが必要です。必ずテスト環境で十分に検証してください。
- レジーム判定やシグナルポリシーの詳細は StrategyModel.md / PortfolioConstruction.md 等の仕様書を参照すべき箇所が多く、実装はそれらに基づいています（これらのドキュメントが別途必要です）。

## 開発・貢献

- 変更の追加やバグ報告は Pull Request / Issue を作成してください。
- テストや CI を整備するときは、KABUSYS_DISABLE_AUTO_ENV_LOAD を使って .env 自動ロードを無効化すると便利です。

---

この README はソースコードの docstring とコメントを基に作成しています。実際の運用手順や schema の詳細はリポジトリ内の対応ドキュメント（例: .env.example, schema 定義, StrategyModel.md 等）をあわせてご確認ください。必要であれば README にさらに実行例（テストデータでのバックテスト実行手順、スキーマ SQL 等）を追加できます。