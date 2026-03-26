# KabuSys

日本株向けの自動売買 / 研究プラットフォーム（ライブラリ）。データ収集（J‑Quants）、特徴量計算、シグナル生成、ポートフォリオ構築、バックテスト、ニュース収集までの主要コンポーネントを含みます。

---

## プロジェクト概要

KabuSys は以下の機能を想定したモジュール群を提供します。

- J‑Quants API から株価・財務・カレンダーデータを取得・保存
- RSS ニュースの収集と記事→銘柄の紐付け
- 研究用のファクター計算（モメンタム、ボラティリティ、バリュー等）
- 特徴量正規化（Z スコア）、features テーブルへの書き出し
- シグナル生成（ファクター + AI スコアの統合、BUY/SELL 判定）
- ポートフォリオ構築（候補選定・重み付け・株数算出・セクターキャップ・レジーム調整）
- バックテストフレームワーク（擬似約定・手数料/スリッページモデル・メトリクス算出）

設計上の注意点：
- ルックアヘッドバイアスに配慮（target_date 時点のデータのみ使用）
- DuckDB を利用したローカル DB スキーマ想定
- 発注 API / 実際の約定層とは分離された純粋な計算モジュール群

---

## 主な機能一覧

- data/
  - J-Quants クライアント（認証・取得・保存関数）
  - RSS ニュース収集・前処理・DB 保存
- research/
  - ファクター計算（momentum / volatility / value）
  - ファクター探索・IC / forward returns / 統計サマリー
- strategy/
  - feature_engineering.build_features(conn, target_date)
  - signal_generator.generate_signals(conn, target_date, ...)
- portfolio/
  - 候補選定（select_candidates）
  - 重み計算（calc_equal_weights, calc_score_weights）
  - ポジションサイジング（calc_position_sizes）
  - リスク調整（apply_sector_cap, calc_regime_multiplier）
- backtest/
  - バックテストエンジン run_backtest(...)
  - ポートフォリオシミュレータ（約定モデル・履歴・トレード記録）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate など）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- config.py
  - .env / 環境変数の読み込み・管理（自動ロード・必須チェック）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の `|` 記法を利用）
- DuckDB を使用（ローカル DB ファイル）
- ネットワーク経由の機能（J‑Quants / RSS）を使う場合は外部アクセスが必要

1. リポジトリをクローン（例）
   - git clone <repo-url>

2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリをインストール
   - pip install duckdb defusedxml
   - （パッケージ化されている場合は pip install -e . など）

   ※ 上記は主要依存のみ。実際の requirements.txt があればそちらを使用してください。

4. 環境変数（.env）の準備
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` または `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（最低限設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

   （.env.example が存在する場合はそれをコピーして編集してください）

5. DB スキーマの初期化
   - 本コードベースは内部で `kabusys.data.schema.init_schema` を参照します（スキーマ定義ファイルを用意して呼び出してください）。
   - DuckDB ファイルを事前に用意して prices_daily, features, ai_scores, market_regime, market_calendar 等のテーブルを準備した状態でバックテストを行う想定です。

---

## 使い方

以下は代表的な操作例です。

1. バックテスト（CLI）
   - 事前に DuckDB ファイルに必要なテーブル（prices_daily 等）を用意しておく必要があります。
   - 例:
     - python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   - 利用可能オプション（抜粋）:
     - --start, --end（必須、YYYY-MM-DD）
     - --cash（初期資金）
     - --slippage, --commission（取引コスト）
     - --allocation-method（equal | score | risk_based）
     - --max-positions, --max-utilization, --risk-pct, --stop-loss-pct, --lot-size
     - --db（DuckDB ファイルパス、必須）

2. Python API からバックテストを実行
   - from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest
     import datetime
     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=datetime.date(2023,1,1), end_date=datetime.date(2023,12,31))
     conn.close()

3. データ取得（J‑Quants）
   - J‑Quants トークン等を環境変数で設定済みであること
   - 例（株価取得→DB保存）:
     - from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
       import duckdb, datetime
       conn = duckdb.connect("data/kabusys.duckdb")
       recs = fetch_daily_quotes(date_from=datetime.date(2023,1,1), date_to=datetime.date(2023,1,31))
       save_daily_quotes(conn, recs)
       conn.close()

4. ニュース収集ジョブ
   - from kabusys.data.news_collector import run_news_collection
     conn = duckdb.connect("data/kabusys.duckdb")
     results = run_news_collection(conn, sources=None, known_codes=set_of_codes)
     conn.close()
   - 内部で RSS フィードを取得 → 正規化 → raw_news に保存 → news_symbols に銘柄紐付け

5. 特徴量構築 / シグナル生成（研究ワークフロー）
   - build_features(conn, target_date) — features テーブルへ Z-score 正規化済み特徴量を挿入
   - generate_signals(conn, target_date, threshold=0.6) — signals テーブルへ BUY/SELL を出力

6. ライブラリ関数の利用例（ポートフォリオ構築等）
   - kabusys.portfolio.select_candidates(...)
   - kabusys.portfolio.calc_equal_weights(...)
   - kabusys.portfolio.calc_position_sizes(...)

---

## 環境変数の自動読み込みについて（config.py）

- 自動的にプロジェクトルート（.git または pyproject.toml により判定）を探索して `.env` → `.env.local` の順に読み込みます。
- OS 環境変数の値が存在する場合は上書きされません（.env.local は override=True のため上書きされますが保護された OS 環境変数は上書きされません）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須値が欠けている場合（例: JQUANTS_REFRESH_TOKEN）が参照されると ValueError を送出します。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - data/
    - jquants_client.py
    - news_collector.py
    - (schema.py 等を想定)
  - research/
    - factor_research.py
    - feature_exploration.py
  - strategy/
    - feature_engineering.py
    - signal_generator.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - backtest/
    - engine.py
    - simulator.py
    - metrics.py
    - run.py
    - clock.py
  - execution/ (エントリと実装の分離想定)
  - monitoring/ (監視・アラート用モジュール想定)

（ファイル一覧は本リポジトリに含まれる実際のファイル構成に従ってください）

---

## 開発上の注意点 / 動作要件

- Python 3.10 以上を推奨（型注釈と union 記法 `|` を利用）
- DuckDB を利用するためローカル DB ファイルを用意してください
- J‑Quants API を利用する機能は API キー（refresh token）が必須
- RSS 取得は外部ネットワークを行うため、SSRF 対策・HTTP タイムアウトに留意
- バックテストでは look‑ahead を避ける設計になっていますが、DB に投入するデータの準備（取得時刻や fetched_at の扱い）は慎重に行ってください
- 単体テスト・モック化のしやすさを考えて、ネットワーク呼び出し部分はモック可能な設計になっています（例: news_collector の _urlopen を差し替え）

---

## よくある操作例（短いまとめ）

- 仮想環境作成 + 依存インストール
  - python -m venv .venv && source .venv/bin/activate
  - pip install duckdb defusedxml
  - pip install -e .   （プロジェクトがパッケージ化されている場合）

- バックテストを実行
  - python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

- 特徴量計算（Python）
  - from kabusys.strategy import build_features
    build_features(conn, date(2024,1,1))

- シグナル生成（Python）
  - from kabusys.strategy import generate_signals
    generate_signals(conn, date(2024,1,1))

---

必要があれば、README に含めるサンプル .env.example、DB スキーマ初期化手順（schema.py の説明）、または具体的な CLI / API 利用例（より多くのコード例）を追加で作成します。どの情報を優先して追加しましょうか？