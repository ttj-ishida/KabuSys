# KabuSys

KabuSys は日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
DuckDB をデータ層に利用し、J-Quants などの外部データを取り込み、特徴量生成・シグナル生成・バックテストまでを一貫して実行できる構成になっています。

主な設計方針：
- ルックアヘッドバイアスを避ける（対象日以前のデータのみ使用）
- DuckDB に対する冪等な保存（ON CONFLICT / DO UPDATE 等）
- テスト容易性のため関数に id_token 等を注入可能
- ネットワーク処理にリトライ・レートリミット・SSRF 対策を実装

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J-Quants API クライアント（株価、財務、マーケットカレンダー取得）
  - RSS ニュース収集（RSS -> raw_news、記事中の銘柄抽出）
  - ETL パイプライン（差分取得、保存、品質チェックフック）
  - DuckDB スキーマ初期化 / 接続ユーティリティ

- 研究支援
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ

- 戦略
  - 特徴量エンジニアリング（features テーブル生成）
  - シグナル生成（features + ai_scores → BUY/SELL signals）

- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - バックテストエンジン（データをインメモリにコピーして日次ループでシミュレーション）
  - メトリクス計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）
  - CLI 実行エントリポイント（python -m kabusys.backtest.run）

- 補助ユーティリティ
  - 簡易的な統計ユーティリティ（Zスコア正規化等）
  - 環境変数 / 設定読み込み（.env 自動ロード、必須キー取得）

---

## 動作環境 / 前提

- Python 3.10 以上（型注釈の union 演算子 `|` を使用）
- 必須ライブラリ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS）

※ requirements.txt はプロジェクトに含めていないため、実行環境に合わせて上記パッケージをインストールしてください。

例:
pip install duckdb defusedxml

---

## 環境変数 / 設定

環境変数は .env または OS 環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml を検出）を基準に行います。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な環境変数（Settings クラス参照）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack のチャンネル ID
- DUCKDB_PATH (任意) — デフォルト DB パス（data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 SQLite パス（data/monitoring.db）
- KABUSYS_ENV (任意) — {development, paper_trading, live} のいずれか（デフォルト: development）
- LOG_LEVEL (任意) — {DEBUG, INFO, WARNING, ERROR, CRITICAL}

README 配布時に .env.example を用意しておくことを推奨します（本コードは .env.example の存在を期待するメッセージを含みます）。

例 (.env):
JQUANTS_REFRESH_TOKEN=xxxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカルでの最小手順）

1. レポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml

   ※ 実運用では requirements.txt / Poetry 等で依存を管理してください。

4. 環境変数を設定
   - プロジェクトルートに .env を作成し上記の必要値を設定するか、OS 環境に設定します。

5. DuckDB スキーマを初期化
   - Python REPL やスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     conn.close()

   - これにより必要なテーブルが作成されます。

---

## 使い方（主要ワークフローの例）

1. データ取得（ETL）
   - prices（株価）や financials、market_calendar を差分更新するための ETL ヘルパー関数があります（kabusys.data.pipeline）。
   - 例（価格差分ETL を呼ぶ最小例）:
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.data.pipeline import run_prices_etl

     conn = init_schema("data/kabusys.duckdb")
     # target_date: 取得終了日（通常は当日）
     fetched, saved = run_prices_etl(conn, target_date=date.today())
     conn.close()

   - ニュース収集:
     from kabusys.data.news_collector import run_news_collection
     conn = init_schema("data/kabusys.duckdb")
     # known_codes は記事から抽出する銘柄コード集合（省略可）
     results = run_news_collection(conn, known_codes={"7203","6758"})
     conn.close()

2. 特徴量生成（features テーブル）
   - DuckDB 接続と日付を渡して実行:
     from datetime import date
     import duckdb
     from kabusys.strategy import build_features

     conn = duckdb.connect("data/kabusys.duckdb")
     count = build_features(conn, target_date=date(2024,1,31))
     conn.close()

3. シグナル生成（signals テーブル）
   - features / ai_scores / positions を参照して BUY/SELL を算出し signals テーブルへ保存:
     from datetime import date
     import duckdb
     from kabusys.strategy import generate_signals

     conn = duckdb.connect("data/kabusys.duckdb")
     total = generate_signals(conn, target_date=date(2024,1,31))
     conn.close()

   - weights をカスタムで渡すことも可能（自動的に正規化される）:
     generate_signals(conn, target_date, weights={"momentum":0.5,"value":0.2,"volatility":0.15,"liquidity":0.15,"news":0.0})

4. バックテスト（CLI / プログラムから実行）
   - CLI:
     python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

   - プログラムから:
     from datetime import date
     import duckdb
     from kabusys.data.schema import init_schema
     from kabusys.backtest.engine import run_backtest

     conn = init_schema("data/kabusys.duckdb")
     result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
     conn.close()

     # 結果の参照
     history = result.history
     trades = result.trades
     metrics = result.metrics

5. 研究用ユーティリティ
   - 将来リターン / IC / ファクターサマリ:
     from kabusys.research import calc_forward_returns, calc_ic, factor_summary

     fwd = calc_forward_returns(conn, target_date, horizons=[1,5,21])
     ic = calc_ic(factors, fwd, factor_col="mom_1m", return_col="fwd_1d")
     summary = factor_summary(factors, ["mom_1m","mom_3m","per"])

---

## 実装上の注目点 / 注意事項

- 環境変数は Settings クラス経由で取得され、必須変数未設定時は ValueError を発生させます（JQUANTS_REFRESH_TOKEN 等）。
- J-Quants API クライアントはレート制限（120 req/min）に合わせた RateLimiter、リトライ・トークン自動更新を実装しています。
- news_collector は SSRF の対策（リダイレクト先検査 / プライベートアドレス拒否）や最大受信サイズ制限、gzip 解凍後のサイズチェック等の安全対策を入れています。
- DuckDB スキーマは init_schema(db_path) で作成。":memory:" を渡してインメモリ DB を作ることもできます（バックテストは本番 DB を汚さないためインメモリにコピーして実行します）。
- generate_signals / build_features は「日付単位の置換（DELETE + INSERT をトランザクション内で）」で冪等性を担保しています。
- バックテストエンジンは本番 DB から必要データをインメモリ DB にコピーし、daily loop でシミュレーションします（signals / positions の読み書きタイミングに注意）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py
  - 環境変数・設定の自動ロードと Settings 定義
- data/
  - __init__.py
  - jquants_client.py     — J-Quants API クライアント（取得 + 保存ヘルパ）
  - news_collector.py     — RSS取得・記事正規化・DB保存
  - pipeline.py           — ETL 差分更新 / ジョブの集約
  - schema.py             — DuckDB スキーマ定義 & init_schema
  - stats.py              — z-score 等の統計ユーティリティ
- strategy/
  - __init__.py
  - feature_engineering.py — features 作成（Z スコア正規化・ユニバースフィルタ）
  - signal_generator.py    — シグナル生成ロジック（final_score 計算, SELL 条件等）
- research/
  - __init__.py
  - factor_research.py     — Momentum / Volatility / Value の計算
  - feature_exploration.py — 将来リターン, IC, ファクター統計
- backtest/
  - __init__.py
  - engine.py              — バックテストエンジン（run_backtest）
  - metrics.py             — バックテスト評価指標計算
  - simulator.py           — 約定処理・ポートフォリオ状態管理
  - clock.py               — 模擬時計（将来的な拡張用）
  - run.py                 — CLI エントリポイント（python -m kabusys.backtest.run）
- execution/               — 発注関連（未詳細実装）
- monitoring/              — 監視関連（SQLite等、未詳細実装）
- backtest.run, other modules...

（上記はリポジトリ内の主要ファイルを抜粋した要約です）

---

## よくある操作例（まとめ）

- DB 初期化:
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  conn.close()

- 価格差分 ETL（当日分）:
  from datetime import date
  from kabusys.data.pipeline import run_prices_etl
  conn = init_schema("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, date.today())
  conn.close()

- 特徴量計算:
  from kabusys.strategy import build_features
  conn = duckdb.connect("data/kabusys.duckdb")
  build_features(conn, target_date=date(2024,1,31))
  conn.close()

- シグナル生成:
  from kabusys.strategy import generate_signals
  conn = duckdb.connect("data/kabusys.duckdb")
  generate_signals(conn, target_date=date(2024,1,31))
  conn.close()

- バックテスト（CLI）:
  python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

---

## 貢献 / 拡張ポイント（案）

- execution 層: kabuステーション等との接続実装、注文同期
- monitoring 層: Slack 通知・監視ダッシュボード連携
- テスト: 各モジュールのユニットテスト（HTTP クライアントのモック等）
- パラメタ最適化 / リスク管理ルールの拡張
- requirements.txt / Poetry による依存管理と CI 設定

---

この README は現在のコードベース（src/kabusys 以下）に基づいた概要と利用方法のガイドです。実運用前に .env の準備、DuckDB の初期投入データ（prices_daily 等）の準備、必要な API トークンの確保を行ってください。質問や追加で README に含めたい内容があれば教えてください。