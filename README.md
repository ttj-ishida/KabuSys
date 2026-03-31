# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援を備えた自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ・発注トラッキング、マーケットカレンダーなどを含みます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要 API 例）
- ディレクトリ構成（主要ファイル説明）
- 環境変数一覧・挙動メモ
- 注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買システム構築のためのユーティリティ群を提供します。  
主に以下を扱います。

- J-Quants API からのデータ取得（株価日足・財務・上場銘柄情報・市場カレンダー）
- DuckDB を用いたローカルデータ格納（冪等保存）
- ニュース収集（RSS）と OpenAI を使ったニュースセンチメント分析
- 市場レジーム判定（ETF の MA とマクロニュースの LLM スコアの合成）
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）
- kabuAPI / Slack など実運用で必要な設定管理（環境変数）

設計上のポイント:
- ルックアヘッドバイアス防止（内部で date.today() を直接参照しない設計）
- 冪等性を重視した DB 書き込み（ON CONFLICT）
- API 呼び出しに対するリトライ・レート制御とフェイルセーフ

---

## 主な機能（抜粋）

- data.jquants_client: J-Quants API 取得・保存（fetch / save）
- data.pipeline: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl 等）
- data.news_collector: RSS 収集・前処理
- ai.news_nlp.score_news: OpenAI でニュースを銘柄ごとにスコアリングして ai_scores に書込
- ai.regime_detector.score_regime: ETF(1321) の MA200 とマクロニュースを統合して market_regime を判定
- research: ファクター計算（momentum, volatility, value）、特徴量探索（forward returns, IC 等）
- data.quality: データ品質チェック（欠損、スパイク、重複、日付整合性）
- data.audit: 監査用テーブル定義・初期化（signal_events / order_requests / executions）
- config: .env 自動読み込み（プロジェクトルートから .env / .env.local）と Settings オブジェクト

---

## セットアップ手順

推奨 Python バージョン: 3.9+

1. リポジトリをチェックアウト
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境の作成（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール  
   ※ requirements.txt は本リポジトリに含まれていない想定です。最低限必要なパッケージ例:
   pip install duckdb openai defusedxml

   (その他、テストや運用で必要なパッケージを追加してください)

4. 環境変数の設定  
   プロジェクトルート（.git があるディレクトリまたは pyproject.toml と同階層）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。  
   例 `.env`（必須キーは各機能で参照されます）:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id

   データベースパス等は任意で上書きできます（下記参照）。

5. DuckDB 等の初期化（監査DBの例）
   Python REPL で:
   >>> import duckdb
   >>> from kabusys.data.audit import init_audit_db
   >>> conn = init_audit_db("data/audit.duckdb")
   これで監査用テーブルが作成されます。

---

## 使い方（主要 API 例）

以下は Python コード例です。必要に応じて logging を設定してください。

- DuckDB 接続を作成して ETL を実行する（日次 ETL）

  >>> import duckdb
  >>> from kabusys.data.pipeline import run_daily_etl
  >>> from datetime import date
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> result = run_daily_etl(conn, target_date=date(2026,3,20))
  >>> print(result.to_dict())

- ニュースをスコアして ai_scores に保存する

  >>> from kabusys.ai.news_nlp import score_news
  >>> from datetime import date
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  >>> print(f"scored {n} codes")

  api_key を省略すると環境変数 OPENAI_API_KEY を使用します。

- 市場レジーム判定を実行する

  >>> from kabusys.ai.regime_detector import score_regime
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> score_regime(conn, target_date=date(2026,3,20), api_key=None)

  失敗時は macro_sentiment を 0.0 にフォールバックするなどフェイルセーフ設計です。

- 研究用ファクター計算

  >>> from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  >>> conn = duckdb.connect("data/kabusys.duckdb")
  >>> recs = calc_momentum(conn, target_date=date(2026,3,20))
  >>> print(len(recs))

- データ品質チェックを実行する

  >>> from kabusys.data.quality import run_all_checks
  >>> issues = run_all_checks(conn, target_date=None)
  >>> for i in issues: print(i)

- 監査スキーマ初期化（すでに DB 接続がある場合）

  >>> from kabusys.data.audit import init_audit_schema
  >>> init_audit_schema(conn, transactional=True)

---

## ディレクトリ構成（主要ファイル）

（パッケージは src/kabusys 以下）

- __init__.py
  - パッケージ初期化（version 等）
- config.py
  - 環境変数・.env 読み込みロジック、Settings オブジェクト
  - 自動でプロジェクトルートの .env / .env.local を読み込む（無効化可能）
- ai/
  - __init__.py
  - news_nlp.py — ニュース記事を OpenAI でスコアリングして ai_scores に書込
  - regime_detector.py — ETF の MA200 とマクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save／認証・レート制御・リトライ）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl, ...）, ETLResult
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 取得・前処理・raw_news への保存補助
  - calendar_management.py — マーケットカレンダー管理 / 営業日判定・更新ジョブ
  - stats.py — zscore_normalize 等統計ユーティリティ
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合）
  - audit.py — 監査ログテーブル DDL / 初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py — 将来リターン計算 / IC / 統計サマリー / ランク化ユーティリティ

（その他、strategy / execution / monitoring モジュール用のエクスポートが __all__ にありますが、今回のコードスニペットでは主に上記が実装されています）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY
  - OpenAI の API キー（ai.news_nlp, ai.regime_detector で使用）
- KABU_API_PASSWORD
  - kabu ステーション API 用のパスワード（実行コンポーネントが参照）
- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID
  - Slack 通知用
- DUCKDB_PATH (省略可)
  - デフォルト DB: data/kabusys.duckdb
- SQLITE_PATH (省略可)
  - 監視用 SQLite: data/monitoring.db
- PID_FILE_PATH / CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
  - 監視設定
- KABUSYS_ENV
  - 環境フラグ: development / paper_trading / live
- LOG_LEVEL
  - ログレベル（DEBUG/INFO/...）

自動 .env ロード
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある `.env` と `.env.local` を自動で読み込みます。OS 環境変数が優先され、`.env.local` は `.env` を上書きします。テスト時等に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 注意事項 / 運用メモ

- Look-ahead バイアス対策:
  - ほとんどの関数は内部で datetime.today() や date.today() を直接参照しない設計です。必ず明示的に target_date を渡してください。
- API レート制御とリトライ:
  - J-Quants クライアントは 120 req/min を守るための RateLimiter を実装しています。OpenAI コールには retry/backoff ロジックが含まれます。
- 応答パースに対する堅牢性:
  - OpenAI の JSON mode を使いつつ、余計な前後テキストが混入するケースに対して復元処理を入れていますが、必ずしも完全ではありません。API レスポンスのバリデーションが行われ、異常時はフェイルセーフ（多くの場合 0.0 にフォールバック）します。
- DB 書き込みはできるだけ冪等になるよう ON CONFLICT を多用していますが、スキーマ変更や外部からの不正な挿入等の影響を受ける可能性があります。ETL のログ・品質チェック結果を必ず監視してください。
- RSS 収集では SSRF 対策（スキーム検証・ホストのプライベート判定・リダイレクト検査）や受信サイズ制限（10MB）を実装しています。

---

もし README に追加したいサンプル CLI、CI 手順、依存関係の厳密な一覧（requirements.txt）やテスト方法（unittest/pytest）等があれば教えてください。README をプロジェクトの運用フローやデプロイ手順に合わせて拡張できます。