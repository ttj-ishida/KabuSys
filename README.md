# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤（バックテスト・データプラットフォーム・特徴量／シグナル生成）です。  
DuckDB をデータストアに用い、J-Quants API や RSS ニュースを取り込み、特徴量計算→シグナル生成→（実運用は execution 層）という流れを想定したモジュール群を備えています。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定読み込み
  - .env / .env.local / OS 環境変数から設定を読み込む（自動ロード、無効化フラグあり）
- データ収集（J-Quants）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの取得・保存（ページネーション・リトライ・レート制御）
- ニュース収集
  - RSS から記事取得、前処理、記事保存、銘柄コード抽出と紐付け（SSRF 対策・gzip・XML 安全パーサ）
- ETL パイプライン
  - 差分取得（バックフィル考慮）、保存、品質チェック呼び出しの枠組み
- スキーマ管理
  - DuckDB 用のスキーマ初期化・接続ユーティリティ（raw / processed / feature / execution 層）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Spearman）計算、ファクターの統計サマリー
  - Z スコア正規化ユーティリティ
- 特徴量エンジニアリング
  - research 側の生ファクターを正規化・合成して features テーブルへ保存（冪等）
- シグナル生成
  - features と ai_scores を統合し最終スコアを算出、BUY/SELL シグナルを signals テーブルへ保存（冪等）
  - Bear レジーム抑制、エグジット（ストップロス等）判定
- バックテスト
  - インメモリ DuckDB にデータをコピーして日次ループでシミュレーション
  - ポートフォリオシミュレータ（擬似約定、スリッページ・手数料モデル）、メトリクス計算
  - CLI エントリポイント（python -m kabusys.backtest.run）
- ニュース記事 → 銘柄紐付け（news_symbols）などのユーティリティ群

---

## 前提条件 (ソフトウェア)

- Python 3.10+（型アノテーションに | を使用）
- 必要な主要パッケージ（例）
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS）

プロジェクトで使用している標準モジュール以外の依存は環境に応じて requirements.txt を用意してください。最低限の例:

requirements.txt（例）
- duckdb
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt

4. 環境変数の準備
   - プロジェクトルートに `.env` と必要なら `.env.local` を配置してください。
   - 自動ロードはデフォルトで有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
     - KABUSYS_ENV (任意, development|paper_trading|live)
     - LOG_LEVEL (任意, DEBUG|INFO|WARNING|ERROR|CRITICAL)

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   - Python REPL またはスクリプトから:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
   - :memory: でインメモリ DB を使うことも可能:
     conn = init_schema(":memory:")

---

## 使い方（主要なワークフロー例）

※ 以下は最小限の呼び出し例です。実運用ではログ/例外処理・品質チェック等を組み合わせてください。

1. データ取得（J-Quants）→ 保存
   - ID トークン自動管理が組み込まれています。サンプル:
     from kabusys.data import jquants_client as jq
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     records = jq.fetch_daily_quotes(date_from=..., date_to=...)
     jq.save_daily_quotes(conn, records)

2. ニュース収集
   - RSS 取得 → raw_news / news_symbols に保存
     from kabusys.data.news_collector import run_news_collection
     run_news_collection(conn, sources=None, known_codes=set_of_codes)

3. ETL（差分更新）パイプライン
   - kabusys.data.pipeline モジュールの run_prices_etl 等の関数を利用してください（関数群が用意されています）

4. 特徴量作成（features テーブルへ）
   - research 側の生ファクターを正規化して features に投入:
     from kabusys.strategy import build_features
     build_features(conn, target_date)

5. シグナル生成（signals テーブルへ）
   - features と ai_scores, positions などを読んで BUY/SELL を生成:
     from kabusys.strategy import generate_signals
     generate_signals(conn, target_date)

6. バックテスト（CLI）
   - DB が事前に必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）を持っていることを確認。
   - 実行例:
     python -m kabusys.backtest.run \
       --start 2023-01-01 --end 2023-12-31 \
       --cash 10000000 --db data/kabusys.duckdb

   - この CLI は内部でインメモリ DB に必要データをコピーし、日次ループで generate_signals を呼び出してシミュレーションを行います。実行後、CAGR・Sharpe・MaxDD 等のメトリクスを出力します。

7. バックテストのプログラム利用例
   - from kabusys.backtest.engine import run_backtest
     result = run_backtest(conn, start_date, end_date)

---

## 実装上の注意点 / 設計ポリシー（要約）

- ルックアヘッドバイアス対策：target_date 時点のデータのみを使用して計算する設計。
- 冪等性：DB 保存は基本的に ON CONFLICT / トランザクションを用いて冪等に実装。
- エラー耐性：API 呼び出しはリトライ・指数バックオフを実装。RSS は XML の安全パーサ（defusedxml）を使用。
- セキュリティ：RSS 取得では SSRF 対策、受信サイズ制限、リダイレクト検査等を実施。
- テスト容易性：id_token の注入や一部ネットワーク関数のモック可能設計。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（取得・保存）
  - news_collector.py        — RSS 収集・前処理・DB 保存
  - pipeline.py              — ETL パイプライン／差分更新ロジック
  - schema.py                — DuckDB スキーマ定義 / init_schema
  - stats.py                 — zscore 等統計ユーティリティ
- research/
  - __init__.py
  - factor_research.py       — Momentum/Volatility/Value 等のファクター計算
  - feature_exploration.py   — IC / forward returns / summary 等
- strategy/
  - __init__.py
  - feature_engineering.py   — features テーブル構築
  - signal_generator.py      — final_score 計算と signals 生成
- backtest/
  - __init__.py
  - engine.py                — run_backtest（主要ロジック）
  - simulator.py             — PortfolioSimulator（擬似約定・スナップショット）
  - metrics.py               — バックテスト評価指標計算
  - run.py                   — CLI エントリポイント
  - clock.py                 — 将来拡張用模擬時計
- execution/                  — 発注/実行層（パッケージとして存在）
- monitoring/                 — 監視用（パッケージとして存在）

---

## よくある質問 / トラブルシューティング（簡易）

- .env 読み込みされない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 が設定されていないか確認。プロジェクトルートは .git または pyproject.toml を基準に自動検出します。
  - 手動で os.environ に設定するか、アプリ起動前に環境変数をエクスポートしてください。

- DuckDB のテーブルが作成されない
  - init_schema() を明示的に呼んでください。ファイルパスの親ディレクトリは自動作成されます。

- J-Quants API で 401 が返る
  - jquants_client は自動でリフレッシュを試みますが、refresh token が無効な場合は JQUANTS_REFRESH_TOKEN を確認してください。

---

README はここまでです。必要であれば以下を追加で用意できます：
- requirements.txt のサンプル（具体的バージョン含む）
- .env.example
- より詳細な CLI / API 使用例（スクリプト単位）
- データベース／テーブルのサンプル初期データ作成スクリプト

ご希望があれば上記のいずれかを生成します。