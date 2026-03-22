# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォームです。  
DuckDB をデータストアとして用い、J-Quants API や RSS からデータを収集し、特徴量生成・シグナル生成・バックテスト・ニュース収集などを行えるモジュール群を提供します。

バージョン: 0.1.0

---


## プロジェクト概要

主な目的:
- J-Quants から株価・財務データ・市場カレンダーを取得して DuckDB に保存
- 取得データを加工して特徴量（features）を作成
- AI スコアやファクタースコアを統合して売買シグナルを生成
- バックテストフレームワークで戦略の検証を実施
- RSS ベースのニュース収集と銘柄紐付けを行う

設計方針の特徴:
- ルックアヘッドバイアス防止（target_date 時点のデータだけを使用）
- DuckDB を用いた冪等性のあるデータ永続化（ON CONFLICT を利用）
- API リクエストはレート制限・リトライ・トークン更新を考慮
- ETL／研究／実行の役割分離（data / research / strategy / backtest / execution 等）


## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（ページネーション・リトライ・トークン更新・保存関数）
  - news_collector: RSS フィードからニュース収集・正規化・保存・銘柄抽出
  - schema: DuckDB スキーマ定義と初期化（raw / processed / feature / execution 層）
  - pipeline: ETL 用ユーティリティ（差分更新・バックフィル等）
  - stats: Z スコア正規化などの統計ユーティリティ
- research/
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算・IC（Spearman）・統計サマリー
- strategy/
  - feature_engineering: raw factor を正規化して features テーブルへ投入
  - signal_generator: features と ai_scores を統合して BUY/SELL シグナルを生成
- backtest/
  - engine: バックテスト全体ループ（インメモリ DB を構築して日次ループを実行）
  - simulator: 擬似約定ロジック・ポートフォリオ管理（スリッページ・手数料考慮）
  - metrics: バックテスト評価指標（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run ...）
- execution/: 発注 / モニタリング周りのプレースホルダ（将来的な実装）

また、設定管理は `kabusys.config.Settings` で環境変数ベースに統一されています。


## セットアップ手順

前提:
- Python 3.9+（typing の一部構文を使用）
- システムにネットワークアクセスがあること（J-Quants / RSS 取得）

推奨インストール手順（プロジェクトルートで実行）:

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - pip install duckdb defusedxml
   - （このリポジトリをパッケージ化している場合は pip install -e . を併用してください）

   最低限必要なパッケージ:
   - duckdb (データベース)
   - defusedxml (RSS XML パース防御)
   - （ネットワーク用に標準ライブラリのみを用いているため追加は最小限です）

3. 環境変数 / .env の準備
   プロジェクトルートに `.env` を置くことで自動読み込みされます（自動ロードはデフォルトで有効）。
   必須の環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabu API パスワード（発注系を使う場合）
   - SLACK_BOT_TOKEN: Slack 通知に使用するトークン
   - SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID

   任意 / デフォルト:
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
   - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）

   注意:
   - テストやスクリプト実行で自動ロードを無効にしたい場合:
     KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB スキーマ初期化（サンプル）
   Python REPL またはスクリプトで:
   - from kabusys.data.schema import init_schema
   - conn = init_schema("data/kabusys.duckdb")
   - conn.close()

   ":memory:" を渡すとインメモリ DB を初期化できます（バックテストの内部処理で使用）。

5. ログ設定:
   各スクリプト実行時に logging.basicConfig 等でログレベルを設定してください。
   例: LOG_LEVEL=DEBUG を環境変数で設定するか、スクリプト側で logging.basicConfig(level=logging.INFO, ...)


## 使い方（よく使う操作例）

以下は主要機能の使い方サンプルです。実行は Python スクリプト内またはインタラクティブ環境で行います。

1) バックテストを CLI から実行
- 必要: DB が prices_daily / features / ai_scores / market_regime / market_calendar 等で事前に埋まっていること
- 実行例:
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

2) DuckDB スキーマ初期化（再掲）
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- conn.close()

3) ETL（株価差分取得）の実行（pipeline の関数を使用）
- from datetime import date
- from kabusys.data.schema import init_schema
- from kabusys.data.pipeline import run_prices_etl
- conn = init_schema("data/kabusys.duckdb")
- result = run_prices_etl(conn, target_date=date.today())
- print(result.to_dict())
- conn.close()

4) J-Quants からのデータ取得 & 保存（低レベル）
- from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- records = fetch_daily_quotes(date_from=..., date_to=...)
- saved = save_daily_quotes(conn, records)
- conn.close()

5) ニュース収集ジョブの実行
- from kabusys.data.news_collector import run_news_collection
- conn = init_schema("data/kabusys.duckdb")
- known_codes = {"7203", "6758", ...}  # 抽出に使う銘柄コード集合（任意）
- stats = run_news_collection(conn, known_codes=known_codes)
- conn.close()

6) 特徴量作成 → シグナル生成（strategy モジュールを直接利用）
- from datetime import date
- import duckdb
- from kabusys.strategy import build_features, generate_signals
- conn = duckdb.connect("data/kabusys.duckdb")
- d = date(2024, 1, 10)
- n = build_features(conn, target_date=d)        # features テーブルの更新
- s = generate_signals(conn, target_date=d)      # signals テーブルの更新
- conn.close()

7) バックテストを Python API で呼ぶ
- from datetime import date
- from kabusys.data.schema import init_schema
- from kabusys.backtest.engine import run_backtest
- conn = init_schema("data/kabusys.duckdb")
- res = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
- print(res.metrics)
- conn.close()

ログや例外メッセージを参考に、環境変数や DB 中身を点検してください。


## 環境変数一覧（主要なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須 for execution) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（任意）
- SLACK_BOT_TOKEN (必須 if Slack notifications used)
- SLACK_CHANNEL_ID (必須 if Slack notifications used)
- DUCKDB_PATH — デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH — モニタリング用 SQLite（data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env 自動読み込みを無効化

※ .env.example を用意しておくと設定が楽です（config モジュール内の説明をご参照ください）。


## ディレクトリ構成

リポジトリの主要ファイル / モジュール構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + 保存関数
    - news_collector.py            — RSS ニュース収集・保存・銘柄抽出
    - pipeline.py                  — ETL パイプラインユーティリティ
    - schema.py                    — DuckDB スキーマ定義 / init_schema
    - stats.py                     — zscore_normalize 等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py           — Momentum / Volatility / Value の計算
    - feature_exploration.py       — 将来リターン, IC, summary, rank
  - strategy/
    - __init__.py
    - feature_engineering.py       — features テーブル生成
    - signal_generator.py          — final_score 計算と signals 生成
  - backtest/
    - __init__.py
    - engine.py                    — run_backtest（全ループ）
    - simulator.py                 — PortfolioSimulator、擬似約定
    - metrics.py                   — バックテスト評価指標
    - clock.py                     — SimulatedClock（将来拡張用）
    - run.py                       — CLI エントリポイント
  - execution/                      — 発注 / 実行関連（未実装/プレースホルダ）
  - monitoring/                     — 監視関連（将来実装想定）

メインの API は上記モジュール群の公開関数（例: data.schema.init_schema、strategy.build_features、strategy.generate_signals、backtest.run_backtest）です。


## 開発・拡張メモ

- DuckDB の SQL 定義（schema.py）に依存しているため、スキーマ変更は注意深く行ってください。
- research と strategy 層は DB の prices_daily / raw_financials / features を直接参照します。データの時系列一貫性（fetched_at / report_date）を保つことが重要です。
- ニュース収集は外部 RSS に依存するため SSRF 対策・受信サイズ制限・XML パース防御を組み込んでいます。
- 発注実装（kabu ステーション連携）は execution 層の実装が必要です。KABU_API_PASSWORD と KABU_API_BASE_URL を利用します。
- 自動環境変数ロードが動作しない/テスト用に無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

不明点や README の追記希望（例:追加の CLI、セットアップスクリプト、requirements.txt など）があれば教えてください。必要に応じてサンプル .env.example を作成します。