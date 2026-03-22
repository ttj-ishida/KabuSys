# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ（研究・運用・バックテスト用）

このリポジトリは、J-Quants API を用いたデータ取得パイプライン、特徴量生成、シグナル生成、発注/バックテスト用のシミュレータを含む日本株自動売買プラットフォームのコア機能を提供します。

主な設計方針
- ルックアヘッドバイアス防止（各処理は target_date 時点で利用可能な情報のみを使用）
- DuckDB を中心としたローカルデータベース
- 冪等性（DB 書き込みは ON CONFLICT 等で上書きを抑制）
- テストしやすい構造（依存注入、明確な I/O 分離）

---

## 機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - RSS ベースのニュース収集（トラッキングパラメータ除去、SSRF 対策）
  - DuckDB への安全な保存（raw / processed / feature / execution 層のスキーマ）
- データ処理 / ETL
  - 差分取得を想定した ETL パイプライン（backfill 対応、品質チェックとの連携）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - ファクター探索（前方リターン計算、IC、統計サマリー）
  - Zスコア正規化などの統計ユーティリティ
- 戦略
  - 特徴量組み立て（feature_engineering.build_features）
  - シグナル生成（strategy.signal_generator.generate_signals）
- バックテスト
  - ポートフォリオシミュレータ（スリッページ・手数料モデル）
  - 日次ループベースのバックテストエンジン（run_backtest）
  - 評価指標計算（CAGR、Sharpe、MaxDD、勝率、Payoff 等）
  - CLI エントリポイント（python -m kabusys.backtest.run）
- 実行/モニタリング層（発注キュー、orders/trades/positions テーブルの定義を含む）

---

## システム要件

- Python 3.10+
- DuckDB（Python パッケージ）
- defusedxml（RSS パースの安全対策）
- その他標準ライブラリ

必要パッケージはプロジェクトの requirements.txt / pyproject.toml を参照してください（本コード例では省略）。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e .
   pip install duckdb defusedxml
   ```

2. 環境変数の準備
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くことで自動読み込みされます。
   - 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テスト用）。

   主要な環境変数（最低限設定が必要なもの）
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（必須）
   - KABUSYS_ENV           : 環境（development / paper_trading / live）デフォルト: development
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）デフォルト: INFO
   - KABU_API_BASE_URL     : kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 sqlite パス（デフォルト data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

3. DuckDB スキーマ初期化
   Python REPL またはスクリプトで schema を初期化します。
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   conn.close()
   ```
   - ":memory:" を指定するとインメモリ DB を作成します（バックテスト用に便利）。

---

## 使い方（代表的な操作例）

以下は主要なモジュールの使い方例です。各関数は DuckDB 接続と target_date（datetime.date）を受け取ることが多い点に注意してください。

1. J-Quants から株価を取得して保存
   ```python
   from datetime import date
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,12,31))
   saved = save_daily_quotes(conn, records)
   conn.close()
   ```

2. ニュース収集ジョブの実行
   ```python
   from kabusys.data.news_collector import run_news_collection
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   # known_codes に銘柄コードセットを渡すと記事と銘柄の紐付けを実行
   results = run_news_collection(conn, known_codes={"7203","6758"})
   conn.close()
   ```

3. 特徴量の構築（features テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import build_features
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   count = build_features(conn, target_date=date(2024,1,15))
   conn.close()
   ```

4. シグナル生成（signals テーブルへ書き込み）
   ```python
   from datetime import date
   from kabusys.strategy import generate_signals
   from kabusys.data.schema import init_schema

   conn = init_schema("data/kabusys.duckdb")
   total = generate_signals(conn, target_date=date(2024,1,15))
   conn.close()
   ```

5. バックテスト（CLI）
   DB に前処理済みの prices_daily / features / ai_scores / market_regime / market_calendar が存在することを前提に実行します。
   ```
   python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2024-12-31 \
       --cash 10000000 --db data/kabusys.duckdb
   ```
   またはプログラムから:
   ```python
   from datetime import date
   from kabusys.data.schema import init_schema
   from kabusys.backtest.engine import run_backtest

   conn = init_schema("data/kabusys.duckdb")
   result = run_backtest(conn, start_date=date(2023,1,1), end_date=date(2023,12,31))
   print(result.metrics)
   conn.close()
   ```

6. ETL（差分取得）
   - ETL 用ユーティリティは `kabusys.data.pipeline` にあります。差分取得やバックフィル、品質チェックのフローを提供します（詳細は該当モジュールの docstring を参照）。

---

## ディレクトリ構成（概観）

- src/kabusys/
  - __init__.py
  - config.py                  -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py        -- J-Quants API クライアント（取得・保存）
    - news_collector.py        -- RSS ニュース収集 / 保存 / 銘柄抽出
    - pipeline.py              -- ETL パイプライン（差分取得・品質チェック）
    - schema.py                -- DuckDB スキーマ定義・初期化
    - stats.py                 -- Zスコア等の統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py   -- IC/forward returns/summary 等
  - strategy/
    - __init__.py
    - feature_engineering.py   -- 特徴量合成 & features テーブル書き込み
    - signal_generator.py      -- final_score 計算 & signals テーブル書き込み
  - backtest/
    - __init__.py
    - engine.py                -- バックテストループ / run_backtest
    - simulator.py             -- PortfolioSimulator（擬似約定）
    - metrics.py               -- バックテスト評価指標計算
    - clock.py                 -- 模擬時計（将来拡張用）
    - run.py                   -- CLI エントリポイント
  - execution/                 -- 発注周り（モジュール分割用の空パッケージ）
  - monitoring/                -- モニタリング関連（未記載詳細）
- src/kabusys/config.py        -- .env 自動ロード・設定アクセス（settings オブジェクト）

---

## 主要な実装上の注意点 / 動作仕様

- .env 自動読み込み
  - プロジェクトルートは __file__ の親ディレクトリ列を上へ辿り、`.git` または `pyproject.toml` の存在によって特定されます。
  - 自動ロード順序: OS環境変数 > .env.local > .env
  - テストなどで自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- J-Quants クライアント
  - 固定レート制限（120 req/min）を守るための RateLimiter 実装あり
  - 401 の場合は自動でトークンをリフレッシュして再試行
  - ページネーション対応（pagination_key）
  - ネットワークリトライ（指数バックオフ、最大 3 回）

- ニュース収集
  - URL 正規化（utm 等のトラッキングパラメータ削除）
  - SSRF 対策（スキームチェック・プライベートIPブロック・リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10 MB）や gzip 解凍後サイズチェック

- 戦略・シグナル生成
  - 欠損コンポーネントは中立値（0.5）で補完することで欠損銘柄の不当な降格を防止
  - Bear レジーム検出により BUY シグナルを抑制するロジックあり
  - signals テーブルは日付単位で置換（DELETE + bulk INSERT）して冪等性を担保

- バックテスト
  - 実行時に本番 DB から必要なデータをインメモリ DuckDB にコピーして実行（本番データを汚染しない）
  - SELL を先に約定、BUY を後に約定する（資金管理上の方針）
  - スリッページ・手数料モデルは engine/simulator に定義

---

## 開発 / 貢献

- コードベースはモジュールごとにドキュメント文字列（docstring）を豊富に含んでいます。新しい機能追加やバグ修正は該当モジュールの docstring に準拠する形で実装してください。
- テスト・CI の整備を推奨します（ユニットテストは DB をモックしたり ":memory:" 接続を使うことで簡素化できます）。

---

## ライセンス

- 本リポジトリのライセンスはリポジトリ内の LICENSE ファイルを参照してください（この README には明示していません）。

---

README の内容やサンプルの追加説明、特定モジュール（例: pipeline.run_prices_etl）の具体的な実行例や .env.example の雛形を追加したい場合は必要な情報（要求する出力形式や含めたい例）を教えてください。