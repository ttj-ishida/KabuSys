# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
DuckDB を用いたデータ基盤、J-Quants API からのデータ取得、特徴量生成、シグナル生成、バックテストフレームワーク、ニュース収集などを含むモジュール群を提供します。

---

## 主な概要

- データ取得／保存（J-Quants 経由の株価・財務・市場カレンダー、RSS ニュース）
- データスキーマ（DuckDB）と ETL（差分更新、品質チェック）
- ファクター計算（モメンタム、ボラティリティ、バリューなど）
- 特徴量エンジニアリング（正規化・フィルタ）
- シグナル生成（複数コンポーネントの加重評価、BUY/SELL 判定）
- バックテスト（シミュレーション、メトリクス算出）
- ニュース収集／銘柄抽出（RSS → raw_news / news_symbols）

設計上の特徴：
- ルックアヘッドバイアスに配慮（target_date 時点のデータのみ利用）
- 冪等性（DB への保存は ON CONFLICT/DO UPDATE 等で重複を排除）
- API レート制御・リトライ・トークン自動更新（J-Quants クライアント）
- セキュリティ対策（RSS の SSRF 対策・XML 脆弱性対策等）

---

## 機能一覧（抜粋）

- data/:
  - jquants_client: J-Quants API クライアント（ページネーション、リトライ、保存関数）
  - news_collector: RSS 収集・正規化・DB保存・銘柄抽出
  - schema: DuckDB スキーマ定義と初期化 (init_schema)
  - pipeline: ETL ジョブ（差分取得、保存、品質チェックの統合）
  - stats: Z スコア正規化などの統計ユーティリティ
- research/:
  - factor_research: momentum / volatility / value のファクター計算
  - feature_exploration: 将来リターン計算、IC、統計サマリー
- strategy/:
  - feature_engineering: ファクターの正規化・フィルタ → features テーブルに保存
  - signal_generator: features + ai_scores から最終スコアを算出し signals テーブルに保存
- backtest/:
  - engine: run_backtest（DuckDB をコピーして日次ループでシミュレーション）
  - simulator: PortfolioSimulator（約定ルール、スリッページ・手数料モデル）
  - metrics: バックテスト評価指標計算（CAGR、Sharpe 等）
  - run: CLI エントリポイント（python -m kabusys.backtest.run）
- config:
  - 環境変数読み込み（.env, .env.local 自動ロード。テスト向けに無効化可能）

---

## 前提 / 要件

- Python 3.10 以上（型アノテーションの `X | Y` を使用）
- 必要な主要パッケージ（代表例）:
  - duckdb
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS 取得）
- J-Quants API のリフレッシュトークン等の環境変数

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、プロジェクトルートへ移動
   - .git または pyproject.toml をプロジェクトルート判定に使用します。

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb defusedxml
   - 開発インストール（パッケージ化されている場合）:
     - pip install -e .

4. 環境変数の設定
   - ルートに `.env` または `.env.local` を配置すると自動で読み込まれます（config モジュール）。
   - 自動ロードを無効にする場合:
     - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN = "<J-Quants の refresh token>"
- SLACK_BOT_TOKEN = "<Slack Bot Token>"（Slack 通知を使う場合）
- SLACK_CHANNEL_ID = "<Slack Channel ID>"（Slack 通知を使う場合）
- KABU_API_PASSWORD = "<kabu API 接続パスワード>"（発注連携を行う場合）

他の設定（任意／デフォルトあり）:
- KABUSYS_ENV = development | paper_trading | live  (default: development)
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL (default: INFO)
- KABU_API_BASE_URL = http://localhost:18080/kabusapi (kabu API の base)
- DUCKDB_PATH / SQLITE_PATH: 各種 DB ファイルパス（デフォルト設定あり）

---

## データベース初期化（DuckDB）

Python REPL やスクリプト内で DuckDB スキーマを作成できます。

例:
- from kabusys.data.schema import init_schema
- conn = init_schema("data/kabusys.duckdb")
- conn.close()

init_schema(":memory:") でインメモリ DB を作成できます（バックテスト等の用途）。

---

## ETL（データ取得）簡単な使い方

J-Quants から株価等を差分取得して DB に保存するワークフローは data.pipeline 経由で行います。代表的な関数:

- run_prices_etl(conn, target_date, id_token=None, date_from=None, backfill_days=3)
  - raw_prices を差分取得 → save_daily_quotes による保存
- run_news_collection(conn, sources=None, known_codes=None)
  - RSS 収集 → raw_news と news_symbols に保存

サンプル（概念）:
- from kabusys.data.schema import init_schema
- from kabusys.data.pipeline import run_prices_etl
- conn = init_schema("data/kabusys.duckdb")
- result = run_prices_etl(conn, target_date=date.today())
- conn.close()

注意:
- J-Quants への認証は settings.jquants_refresh_token（環境変数）を使用します。
- 大量 API 呼び出しは rate limit を尊重します（クライアントは内部で制御）。

---

## 特徴量生成 / シグナル生成

特徴量生成:
- from kabusys.strategy import build_features
- build_features(conn, target_date)

シグナル生成:
- from kabusys.strategy import generate_signals
- generate_signals(conn, target_date, threshold=0.60, weights=None)

これらは DuckDB 上のテーブル（prices_daily, raw_financials, features, ai_scores, positions 等）を参照・更新します。各処理は target_date 分を日付単位で置換（冪等）します。

---

## バックテストの実行（CLI）

提供済みの CLI:
- python -m kabusys.backtest.run --start YYYY-MM-DD --end YYYY-MM-DD --db path/to/kabusys.duckdb [--cash ...] [--slippage ...] [--commission ...] [--max-position-pct ...]

例:
- python -m kabusys.backtest.run --start 2023-01-01 --end 2023-12-31 --db data/kabusys.duckdb

内部で行われる処理:
- 本番 DB からテーブルを日付範囲でインメモリ DuckDB にコピー
- 日次ループで generate_signals → シミュレータで約定 → positions を書き戻し → mark_to_market → 次日シグナル生成 の順に実行
- 戻り値は履歴・約定履歴・メトリクス（CAGR, Sharpe, MaxDD, WinRate 等）

---

## ニュース収集（RSS）

- fetch_rss(url, source, timeout=30) : RSS を収集し、記事リストを返す
- save_raw_news(conn, articles) : raw_news テーブルへ保存（INSERT ... RETURNING を用いて新規挿入IDを返す）
- extract_stock_codes(text, known_codes) : テキスト中の 4 桁銘柄コードを検出
- run_news_collection(conn, sources=None, known_codes=None) : 全ソースを巡回して保存・紐付け

セキュリティ上の注意:
- RSS の取得には SSRF 対策・圧縮バッファチェック・XML の安全パーサを使用しています（defusedxml）。

---

## 開発者向け Tips

- 環境変数自動ロード:
  - プロジェクトルートに .env / .env.local がある場合、config モジュールが自動で読み込みます。
  - .env.local は .env を上書きします（OS 環境変数は保護）。
  - テストで自動ロードを避けるには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- DB スキーマ変更:
  - schema.init_schema() は既存テーブルがあればスキップするため冪等です。
  - 大きな DDL 変更時はマイグレーション手順を用意してください（本リポジトリにはマイグレーション機構は含まれていません）。

- ログ:
  - 設定で LOG_LEVEL を変更できます。デフォルトは INFO。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- data/
  - __init__.py
  - jquants_client.py
  - news_collector.py
  - pipeline.py
  - schema.py
  - stats.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- strategy/
  - __init__.py
  - feature_engineering.py
  - signal_generator.py
- backtest/
  - __init__.py
  - engine.py
  - metrics.py
  - simulator.py
  - clock.py
  - run.py
- execution/
  - __init__.py
- (monitoring)  # __all__ に含まれるがコード一覧に未掲示（存在する場合は monitoring モジュールを配置）

各フォルダ内のファイルはそれぞれの責務に沿って設計されています（Data / Research / Strategy / Execution / Backtest）。

---

## 注意事項・運用上の留意点

- 本ライブラリは実運用での発注・資金移動を扱うため、各種トークン・パスワードは安全に管理してください。
- J-Quants API の利用規約・レート制限を守ってください（クライアントは内部で制御しますが、過度な並列呼び出しは避けること）。
- バックテスト結果はパラメータやデータ品質に依存します。ETL の品質チェックを実行してから評価を行ってください。
- DuckDB ファイルは単一ファイルで管理されます。バックアップとロックに注意してください（並行書き込み・複数プロセスの使用は環境による）。

---

この README はリポジトリ内のコード構成と主要 API をベースに作成しています。詳細な関数引数や戻り値、内部アルゴリズムの仕様はソースコードの docstring を参照してください。必要があれば、README に追加したい使用例や CI / デプロイ手順を教えてください。