# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、データ品質チェック、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。

---

## 目的（プロジェクト概要）

KabuSys は日本株の自動売買システムおよびデータプラットフォーム向けの共通ユーティリティ群です。主な目的は次のとおりです。

- J-Quants API を用いた株価・財務・カレンダーデータの差分 ETL と DuckDB への保存（冪等性）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- RSS ニュース収集と OpenAI を用いた記事/銘柄ごとのセンチメントスコアリング
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）および統計ユーティリティ
- 市場レジーム判定（ETF MA とマクロニュースを統合）
- 取引監査ログ（signal → order_request → execution のトレーサビリティ）
- kabuステーション 等の実行・監視用設定管理

---

## 機能一覧

- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - jquants_client: fetch/save（daily_quotes, financial_statements, market_calendar, listed_info）
- データ品質
  - quality.run_all_checks（missing_data / spike / duplicates / date_consistency）
- カレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
  - calendar_update_job（J-Quants からの夜間更新）
- ニュース収集
  - fetch_rss / news_collector（RSS の正規化、SSRF / トラッキング除去、raw_news 保存）
- ニュース NLP / AI
  - score_news: 銘柄ごとのニュースセンチメントを OpenAI で取得して ai_scores に保存
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースの LLM 結果を合成して market_regime を更新
- 研究（Research）
  - calc_momentum, calc_value, calc_volatility
  - calc_forward_returns, calc_ic, factor_summary, rank
  - zscore_normalize（data.stats）
- 監査ログ / トレーサビリティ
  - init_audit_schema / init_audit_db（監査テーブル・インデックスの初期化）
- 設定管理
  - settings（環境変数・.env 自動ロード、各種パス/フラグの管理）

---

## 前提 / 必要条件

- Python 3.10 以上（型ヒントの構文に依存）
- 必要なライブラリ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI 等）
- J-Quants リフレッシュトークン、OpenAI API キー等の環境変数設定

pip の依存ファイルは本リポジトリ内にないため、プロジェクトの pyproject.toml / requirements.txt に従ってください。最低限次をインストールします（例）:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発中:
     - pip install -e .
   - もしくは必要な依存を pip で個別インストール

2. 環境変数または .env を用意
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化可能）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に必要）
     - KABU_API_PASSWORD: kabuステーション API パスワード（注文連携用）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE: paper_trading 用のモック約定モード（instant|partial|never|reject）
   - .env の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基に行います。

3. DuckDB 初期スキーマ（必要に応じて）を作成
   - ETL / ペイロード保存のためのテーブル群を初期化するユーティリティがある場合はそれを実行してください（本コードベースでは schema 初期化機能は別に想定）。

4. 監査 DB の初期化（任意）
   - 監査ログ専用 DB を作る:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（主なサンプル）

以下は最小の利用例です。適宜ロギング設定や例外処理を追加してください。

- 日次 ETL を実行して DuckDB に保存する:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアリング（OpenAI 必須）:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究関数（例: モメンタム計算）:
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs), "銘柄のモメンタムを計算しました")

- 監査ログスキーマ初期化:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は監査用 DuckDB 接続

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants API のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で必要）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: ログレベル（デフォルト INFO）
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- PAPER_FILL_MODE: paper_trading 時のモック約定モード（instant|partial|never|reject）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 に設定すると .env の自動ロードを無効化

.env.example を参照して .env を作成してください。

---

## テスト / 開発メモ

- 自動 .env ロードは module import 時に行われます。テスト等でこれを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI への呼び出しは内部で _call_openai_api を経由しているため、ユニットテストでは monkeypatch / unittest.mock.patch で差し替えてレスポンスを制御できます。
  例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=mock_resp)
- jquants_client は HTTP リクエストとレートリミッター、再試行ロジックを備えています。実際の API 呼び出しが必要ないテストは fetch/save 関数をモックしてください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                    -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                -- ニュース NLP スコアリング（OpenAI）
    - regime_detector.py         -- 市場レジーム判定（ETF MA + マクロ）
  - data/
    - __init__.py
    - jquants_client.py          -- J-Quants API クライアント + DuckDB 保存
    - pipeline.py                -- ETL パイプライン（run_daily_etl 等）
    - etl.py                     -- ETLResult の再エクスポート
    - calendar_management.py     -- 市場カレンダー管理・ユーティリティ
    - news_collector.py          -- RSS 取得・正規化・保存
    - quality.py                 -- データ品質チェック
    - stats.py                   -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                   -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         -- momentum / value / volatility 等
    - feature_exploration.py     -- forward returns, IC, summary, rank
  - research/（その他の研究ユーティリティ）
  - (その他 strategy/execution/monitoring 等のパッケージは __all__ に用意)

---

## 設計上の注意点（重要なポイント）

- ルックアヘッドバイアス防止:
  - 多くの関数で datetime.today() / date.today() を直接参照せず、target_date を引数で受け取る設計です。バックテスト等では必ず明示的な target_date を渡してください。
- 冪等性:
  - DuckDB への保存は ON CONFLICT（UPSERT）や個別 DELETE→INSERT の形で実装されており、部分的な再実行に耐える設計です。
- フェイルセーフ:
  - OpenAI / HTTP エラー時は多くの箇所でフォールバック（スコア 0.0 として継続）やログ出力を行い、致命的な停止を回避します（ただし重要な設定不足は例外を投げます）。
- セキュリティ:
  - news_collector は SSRF 対策、トラッキングパラメータ除去、受信サイズ制限、defusedxml を利用した安全な XML パース等を行っています。

---

## 問い合わせ / コントリビューション

不具合や機能提案、ドキュメント改善のプルリクエストは歓迎します。実装の意図や設計方針は各モジュールの docstring に詳述していますので、まずはそちらを参照してください。

---

以上が KabuSys の概要と利用方法です。必要であれば具体的なユースケース（ETL の cron 設定、監視ルーチン、kabuステーションとの接続フロー等）について追記しますので教えてください。