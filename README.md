# KabuSys

日本株向けの自動売買 / バックテスト基盤ライブラリ。  
ファクター計算・特徴量生成・シグナル生成・ポートフォリオ構築・バックテストシミュレータ、J‑Quants からのデータ収集やニュース収集などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は研究フェーズからバックテスト、運用（paper/live）までを想定した日本株アルゴリズムトレード基盤です。主な設計方針は以下です。

- ルックアヘッドバイアス回避（ターゲット日時のデータのみを使用）
- DuckDB ベースの時系列データ / メタデータ管理
- J‑Quants API 経由のデータ取得（レート制限、リトライ、トークン自動更新対応）
- 冪等な DB 書き込み（ON CONFLICT / UPSERT）
- 研究（research）モジュールと運用（strategy / backtest）モジュールの明確な分離
- 単体関数（純粋関数）で実装されたポートフォリオ構築ロジック（テスト容易性重視）

---

## 主な機能一覧

- データ取得・ETL
  - J‑Quants API クライアント（価格日足 / 財務 / 銘柄情報 / マーケットカレンダー）
  - RSS ニュース収集（SSRF対策、トラッキング除去、記事IDの冪等管理）
  - DuckDB への保存ユーティリティ（raw_prices, raw_financials, market_calendar, stocks, raw_news 等）

- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ

- 特徴量生成（feature_engineering）
  - ファクターの正規化（Z スコアクリップ）、ユニバースフィルタ適用、features テーブルへの UPSERT

- シグナル生成（signal_generator）
  - features + ai_scores を統合して final_score 計算
  - BUY / SELL シグナル生成（Bear レジーム抑制、ストップロス判定等）
  - signals テーブルへの冪等書き込み

- ポートフォリオ（portfolio）
  - 候補選定（スコア順）、等金額/スコア加重配分
  - リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイジング（risk_based / equal / score、lot 丸め、aggregate cap）

- バックテスト（backtest）
  - インメモリ DuckDB を作って本番 DB を汚さずにバックテスト実行
  - PortfolioSimulator による擬似約定（スリッページ・手数料モデル、部分約定、全量売却）
  - 日次スナップショット・トレードレコードの収集とメトリクス計算（CAGR, Sharpe, MaxDD, WinRate, Payoff 等）
  - CLI エントリポイントあり（python -m kabusys.backtest.run）

- 実行・監視（execution / monitoring）
  - パッケージ初期設計に名前空間あり（実稼働用フックや通知連携を想定）

---

## セットアップ手順

以下は開発 / 実行環境の基本手順例です。

1. リポジトリをクローンする
   ```
   git clone <repository-url>
   cd <repository>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 本コードベースで使用されている主な外部依存:
     - duckdb
     - defusedxml
   - pip パッケージ例:
     ```
     pip install duckdb defusedxml
     ```
   - パッケージを編集する場合は開発インストール:
     ```
     pip install -e .
     ```
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数の設定
   - ルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で停止可能）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J‑Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL — kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャネルID（必須）
     - DUCKDB_PATH — デフォルト DB パス（省略時 data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（省略時 data/monitoring.db）
     - KABUSYS_ENV — environment: development / paper_trading / live（省略時 development）
     - LOG_LEVEL — ログレベル: DEBUG/INFO/…（省略時 INFO）

   - .env ファイル例:
     ```
     JQUANTS_REFRESH_TOKEN=your_refresh_token_here
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     KABUSYS_ENV=development
     ```

5. DuckDB スキーマ初期化
   - プロジェクトには schema 初期化関数がある想定です（例: kabusys.data.schema.init_schema）。  
     DuckDB ファイルを作成して必要テーブル（prices_daily, raw_prices, raw_financials, features, signals, positions, ai_scores, market_regime, market_calendar, stocks, raw_news, news_symbols 等）を用意してください。
   - 例（仮）:
     ```py
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     # schema を作る/マイグレーションを実行する処理が init_schema に含まれている想定
     conn.close()
     ```

---

## 使い方

以下は代表的な利用例です。

- バックテスト（CLI）
  ```
  python -m kabusys.backtest.run \
    --start 2023-01-01 --end 2023-12-31 \
    --cash 10000000 \
    --db data/kabusys.duckdb \
    --allocation-method risk_based \
    --lot-size 100
  ```

  CLI の主なオプション:
  - --start / --end: 開始・終了日（YYYY-MM-DD, end は start より後であること）
  - --cash: 初期資金（円）
  - --slippage: スリッページ率（デフォルト 0.001）
  - --commission: 手数料率（デフォルト 0.00055）
  - --max-position-pct: 1銘柄上限比率（デフォルト 0.10）
  - --allocation-method: equal | score | risk_based（デフォルト risk_based）
  - --max-utilization: ポートフォリオ投下上限（デフォルト 0.70）
  - --max-positions: 保有上限（デフォルト 10）
  - --risk-pct / --stop-loss-pct: risk_based 方式用の設定
  - --lot-size: 単元株数（日本株は通常 100）

- プログラムからバックテストを呼ぶ（Python API）
  ```py
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.backtest.engine import run_backtest

  conn = init_schema("data/kabusys.duckdb")  # 読み取り用コネクション
  result = run_backtest(
      conn=conn,
      start_date=date(2023, 1, 4),
      end_date=date(2023, 12, 29),
      initial_cash=10_000_000,
      allocation_method="risk_based",
  )
  conn.close()

  print(result.metrics)
  ```

- 特徴量生成（build_features）
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import build_features

  conn = duckdb.connect("data/kabusys.duckdb")
  n = build_features(conn, target_date=date(2024, 1, 4))
  print(f"features upserted: {n}")
  conn.close()
  ```

- シグナル生成（generate_signals）
  ```py
  from datetime import date
  import duckdb
  from kabusys.strategy import generate_signals

  conn = duckdb.connect("data/kabusys.duckdb")
  total = generate_signals(conn, target_date=date(2024, 1, 4))
  print(f"signals written: {total}")
  conn.close()
  ```

- ニュース収集ジョブ
  ```py
  import duckdb
  from kabusys.data.news_collector import run_news_collection

  conn = duckdb.connect("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄セット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: inserted_count, ...}
  conn.close()
  ```

- J‑Quants データ取得 / 保存（例）
  ```py
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes

  conn = duckdb.connect("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print(f"saved {saved} rows")
  conn.close()
  ```

---

## 重要な挙動メモ

- .env 自動読み込み:
  - デフォルトでパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在）を基に .env/.env.local を自動的に読み込みます。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（主にテスト用途）。
  - 読み込み順序: OS 環境 > .env.local（override=True）> .env（override=False）。既存の OS 環境は保護されます。

- 環境変数検証:
  - Settings クラスで `KABUSYS_ENV` と `LOG_LEVEL` の値検査が行われます。許容値外だと ValueError を送出します。

- Bear レジームの扱い:
  - signal_generator は market_regime / ai_scores を参照して Bear 判定を行い、Bear 相場では BUY シグナルを抑制します（ただし SELL 判定は行います）。

- 冪等性:
  - DB 書き込みは原則「日付単位で置換（DELETE → INSERT）」や ON CONFLICT を使って冪等に設計されています。

---

## ディレクトリ構成（抜粋）

（リポジトリの src/kabusys 以下に主要ファイルがあります）

- src/
  - kabusys/
    - __init__.py
    - config.py                          — 環境変数 / 設定管理
    - data/
      - jquants_client.py                — J‑Quants API client + 保存ロジック
      - news_collector.py                — RSS ニュース収集・保存
      - (schema.py, calendar_management.py 等が想定)
    - research/
      - factor_research.py               — Momentum / Volatility / Value 等
      - feature_exploration.py           — IC / forward returns / summary
    - strategy/
      - feature_engineering.py           — features テーブル作成
      - signal_generator.py              — final_score 計算と signals 生成
    - portfolio/
      - portfolio_builder.py             — 候補選定 / 重み計算
      - position_sizing.py               — 数量算出・aggregate cap
      - risk_adjustment.py               — セクターキャップ / レジーム乗数
    - backtest/
      - engine.py                        — バックテストループ（run_backtest）
      - simulator.py                     — PortfolioSimulator（擬似約定）
      - metrics.py                       — バックテスト評価指標計算
      - run.py                           — CLI エントリポイント
      - clock.py
    - execution/                          — 実行層（名前空間・拡張点）
    - monitoring/                         — 監視・通知（名前空間）

---

## 開発・貢献

- コードは関数ごとにドキュメンテーション文字列が付与されています。単体テストを追加する際は純粋関数部分（portfolio, research, backtest.metrics 等）を優先するとテストが容易です。
- 実運用接続（kabu API / Slack / J‑Quants）を必要としないユニットテストを作成すると CI での検証が簡単です（環境変数はテスト用にモック化 / KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください）。

---

## 参考・補足

- DuckDB を用いる設計のため、大量データを扱う ETL / バックテストのパフォーマンスは高い想定です。スキーマ定義（data/schema.py）とマイグレーションは本 README の範囲外ですが、init_schema の実装に従ってデータベースを初期化してください。
- J‑Quants の API レート制限（120 req/min）を遵守する仕組みが組み込まれています。大量取得時は適切な時間間隔でバッチを回してください。

---

必要であれば README に「スキーマ定義（schema.py）の概要」や「典型的な ETL ワークフローの手順（データ取得 → 保存 → feature ビルド → シグナル生成 → バックテスト）」を追記します。どの部分をより詳細に説明しますか？