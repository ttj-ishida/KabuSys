KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買プラットフォームのコアライブラリです。  
DuckDB をデータストアとして用い、リサーチ（ファクター算出）、シグナル生成、ポートフォリオ構築、バックテスト、およびニュース収集／J‑Quants API 統合などの機能を提供します。  
設計は「バックテストと本番運用で同じロジックを再利用する」ことを重視しており、DB 参照を分離した純粋関数群や、冪等性・ルックアヘッドバイアス対策、レートリミット／リトライ対策など堅牢性を考慮した実装が含まれます。

主な機能一覧
--------------
- データ取得 / ETL
  - J‑Quants API クライアント（認証・ページネーション・保存機能）
  - RSS ニュース収集と記事 → 銘柄紐付け
- リサーチ / 特徴量
  - Momentum / Volatility / Value などのファクター計算（research.module）
  - Z スコア正規化、ユニバースフィルタ、features テーブルへの書き出し（strategy.feature_engineering.build_features）
- シグナル生成
  - 正規化済みファクターと AI スコアを統合して final_score を計算、BUY/SELL を生成（strategy.signal_generator.generate_signals）
  - Bear レジーム抑制、エグジット判定（ストップロス等）
- ポートフォリオ構築
  - 候補選定、等配分・スコア配分、リスクベースサイジング、セクター集中制限、レジーム乗数（portfolio パッケージ）
- バックテストフレームワーク
  - 日次ループの再現、擬似約定モデル（スリッページ・手数料）、履歴・トレード記録、メトリクス算出（CAGR・Sharpe・MaxDD 等）
  - CLI ランナー（python -m kabusys.backtest.run）
- モジュール単位の安全対策
  - 環境変数自動ロード（.env/.env.local）
  - 冪等な DB 書き込み（ON CONFLICT / INSERT ... DO UPDATE 等）
  - SSRF 対策、XML パース安全化（defusedxml）など

セットアップ手順
----------------

前提
- Python 3.10+（typing の Union | 等を利用）
- DuckDB（Python パッケージ duckdb）
- defusedxml（ニュース収集時）
- その他、requirements.txt / pyproject.toml があればそちらに従ってください

1. リポジトリをクローン（例）
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - 必要最低限の例:
     - pip install duckdb defusedxml
   - もし pyproject.toml / requirements.txt があれば:
     - pip install -e .        # 開発インストール（setup があれば）
     - または pip install -r requirements.txt

4. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml を基準）に .env / .env.local を配置すると自動でロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（Settings 参照）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
   - 任意（デフォルト有り）:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト data/monitoring.db）
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     KABU_API_PASSWORD=your_kabu_pass
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

DB スキーマ準備
- 本ライブラリは DuckDB の特定テーブル（prices_daily, features, ai_scores, market_regime, market_calendar, stocks 等）を前提に動作します。  
- データベース初期化用のヘルパ（kabusys.data.schema.init_schema）が参照されていますので、実運用ではこの関数でスキーマを作成し、外部 API から取得したデータを投入してください。

使い方（主要ユースケース）
------------------------

1) バックテスト実行（CLI）
- 事前準備: DuckDB ファイルに prices_daily / features / ai_scores / market_regime / market_calendar が存在している必要があります。
- 実行例:
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 --db path/to/kabusys.duckdb \
    --allocation-method risk_based --max-positions 10

- オプション:
  - --slippage, --commission, --max-position-pct, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size などを指定可能

2) プログラムからバックテストを呼ぶ
- 例（スクリプト内）:
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("path/to/kabusys.duckdb")
  result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
  conn.close()

  # result.history / result.trades / result.metrics を利用

3) 特徴量構築（features テーブル）
- duckdb 接続と target_date を渡して実行:
  from kabusys.strategy.feature_engineering import build_features
  count = build_features(conn, target_date)

4) シグナル生成
- features / ai_scores / positions を参照して signals テーブルへ書き込む:
  from kabusys.strategy.signal_generator import generate_signals
  cnt = generate_signals(conn, target_date)

5) J‑Quants からのデータ取得と保存
- トークン取得:
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()

- 日足取得・保存:
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  records = fetch_daily_quotes(date_from=..., date_to=...)
  save_daily_quotes(conn, records)

6) ニュース収集
- RSS フィードを取得して DB に保存:
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=set_of_codes)

API（主要関数）
- kabusys.config.settings — 環境設定アクセサ
- kabusys.data.jquants_client: get_id_token, fetch_daily_quotes, fetch_financial_statements, save_daily_quotes, save_financial_statements, fetch_market_calendar, fetch_listed_info
- kabusys.data.news_collector: fetch_rss, save_raw_news, save_news_symbols, run_news_collection
- kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.strategy: build_features, generate_signals
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                — パッケージ定義（バージョン 0.1.0）
- config.py                  — 環境変数/設定読み込みロジック
- data/
  - jquants_client.py        — J‑Quants API クライアント、保存ユーティリティ
  - news_collector.py        — RSS 取得・正規化・DB 保存
  - (その他データ関連モジュール: schema, calendar_management 等参照)
- research/
  - factor_research.py       — Momentum / Volatility / Value ファクター計算
  - feature_exploration.py   — forward return, IC, 統計サマリ
- strategy/
  - feature_engineering.py   — features テーブル作成パイプライン
  - signal_generator.py      — final_score 計算と signals 書き込み
- portfolio/
  - portfolio_builder.py     — 候補選定・重み計算
  - position_sizing.py       — 株数決定（risk_based / equal / score）
  - risk_adjustment.py       — セクターキャップ・レジーム乗数
- backtest/
  - engine.py                — バックテストループ（run_backtest）
  - simulator.py             — 擬似約定・ポートフォリオ管理
  - metrics.py               — バックテスト評価指標
  - run.py                   — CLI エントリポイント
  - clock.py                 — 将来拡張用の模擬時計
- execution/                  — 発注/実行レイヤー（骨組み）
- monitoring/                 — 監視・メトリクス（骨組み）
- portfolio/__init__.py
- strategy/__init__.py
- research/__init__.py
- backtest/__init__.py

設計上の注意点 / 動作に関する重要事項
------------------------------------
- ルックアヘッドバイアス防止: features・signals 等は target_date 時点の情報のみを使う設計です。データ取得・ETL 時に fetched_at 等のメタ情報を記録し、バックテスト用に過去時点のデータのみを使用することが重要です。
- 冪等性: DB への書き込みは可能な限り冪等（ON CONFLICT / トランザクション）にしてありますが、ETL パイプライン運用時はトランザクション管理を厳密に行ってください。
- 環境変数の自動ロード: プロジェクトルートの .env（→ .env.local の順）を自動で読み込みます。テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- レジーム／AI スコア: signal_generator は ai_scores テーブルの regime_score を集計して Bear 判定を行います。AI スコア未登録時の扱いやサンプル不足時の挙動に注意してください。

貢献 / 拡張
------------
- 新しいデータソース追加、単元株サイズの銘柄別対応、より詳細な注文実行ロジック（部分利確/追跡ストップ等）などが想定されます。コードはモジュール化されているため、各レイヤーごとにテストを追加して拡張してください。

ライセンス
----------
- このリポジトリのライセンス情報（LICENSE ファイル等）に従ってください（本 README には含まれていません）。

お問い合わせ
------------
実装や API 仕様に関する質問があれば、リポジトリの Issue または内部ドキュメント（PortfolioConstruction.md, StrategyModel.md, DataPlatform.md, BacktestFramework.md 等）を参照してください。README に含めきれない詳細はこれらの設計文書に記載されています。