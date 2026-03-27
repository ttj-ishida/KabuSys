# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP（OpenAI）、リサーチ用ファクター計算、監査ログ設計、マーケットカレンダー管理などを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けデータパイプラインとアルゴリズム取引基盤のためのツール群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダーデータの差分ETLと保存（DuckDB）
- RSS ニュース収集と記事の前処理／銘柄紐付け
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントによる市場レジーム判定
- 研究用途のファクター計算（モメンタム／バリュー／ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution）用スキーマの初期化ユーティリティ
- 設定管理（.env / 環境変数の自動読み込み、必須設定の検証）

設計方針のキーワード: ルックアヘッドバイアス回避、冪等性、フェイルセーフ、最小限の外部依存、DuckDB によるローカル永続化。

---

## 機能一覧

- config
  - 環境変数 / .env の自動読み込み（プロジェクトルートは .git または pyproject.toml で検出）
  - 必須設定の取得ラッパー（settings オブジェクト）
- data
  - jquants_client: J-Quants API 呼び出し・ページネーション・保存（raw_prices / raw_financials / market_calendar）
  - pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF対策、gzip制限、トラッキングパラメータ除去等）
  - calendar_management: 営業日判定・next/prev_trading_day・カレンダー更新ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用テーブル定義と初期化（監査DB初期化 helper）
  - stats: z-score 正規化ユーティリティ
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価し ai_scores に保存
  - regime_detector.score_regime: ETF(1321) の MA200乖離 + マクロニュースセンチメントで市場レジーム（bull/neutral/bear）を算出して保存
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順（開発向け）

1. リポジトリをクローン（プロジェクトルートには .git または pyproject.toml が必要です）

   git clone <リポジトリURL>
   cd <repo>

2. Python と仮想環境を用意

   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows

3. 依存ライブラリ（一例）

   pip install duckdb openai defusedxml

   ※実際の requirements.txt / pyproject の指示に従ってください。

4. パッケージをインストール（開発モード）

   pip install -e .

5. 環境変数 / .env の用意

   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます。
   自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabu ステーション API パスワード（発注周り）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID (必須)
   - OPENAI_API_KEY (推奨) — OpenAI API キー（score_news / score_regime の引数でも指定可）
   - DUCKDB_PATH (任意, default: data/kabusys.duckdb)
   - SQLITE_PATH (任意, default: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live)（default: development）
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)（default: INFO）

   例 .env（参考）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

---

## 使い方（主要なユースケース）

以下はライブラリ関数を直接呼ぶ簡単な例です。実行前に環境変数が設定されていることを確認してください。

- DuckDB 接続の作成

  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- ETL（日次パイプライン）を実行

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースのスコアリング（OpenAI を用いる）

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  # api_key を明示的に渡すことも可能
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込銘柄数: {n_written}")

- 市場レジーム判定

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- 研究用ファクター計算

  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))

- 監査ログDB の初期化

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対してアプリケーションから監査ログを書き込めます

- 設定取得

  from kabusys.config import settings
  print(settings.duckdb_path)   # Path オブジェクト
  print(settings.is_live)       # bool

注意事項:
- OpenAI 呼び出しは外部 API を使うため、API キーとネットワークの利用制限を確認してください。
- ETL は J-Quants からのデータ取得を含むため API レート制限や認証トークンの用意が必要です。
- news_collector は RSS フィードの取得・パースを行います。SSRF 等の対策を実装していますが、外部ネットワークへのアクセスに注意してください。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            — 銘柄別ニュースセンチメント解析（score_news）
  - regime_detector.py     — マクロ＋MA200で市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント、保存ロジック
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - news_collector.py      — RSS 収集・正規化
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - quality.py             — データ品質チェック
  - stats.py               — z-score 等の統計ユーティリティ
  - audit.py               — 監査ログスキーマ初期化
  - etl.py                 — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py     — モメンタム・バリュー・ボラティリティ
  - feature_exploration.py — 将来リターン・IC・統計サマリー
- research/*.py
- その他（strategy / execution / monitoring のプレースホルダは __all__ に定義）

簡単な説明:
- ai: OpenAI を用いた NLP/センチメント処理
- data: ETL・保存・ニュース収集・カレンダー・品質チェック・監査ログ
- research: バックテスト / ファクター研究用の純粋計算モジュール

---

## 自動 .env 読み込みの挙動

- プロジェクトルートは、src/kabusys/config.py の実装により実行ファイルの親階層から .git または pyproject.toml を探索して決定されます（カレントワーキングディレクトリに依存しません）。
- 読み込み優先順位は: OS 環境変数 > .env.local（上書き） > .env（未設定キーのみセット）
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## テスト・開発時のヒント

- OpenAI / J-Quants API の呼び出しは、各モジュール内の小さなラッパー関数（_call_openai_api 等）があるため、ユニットテストではこれらをモックして外部依存を切り離せます。
- DuckDB の挙動を模擬するには `duckdb.connect(":memory:")` を使うと便利です。
- ETL の各ステップは例外が発生しても他のステップに影響しないように実装されており、ETLResult で詳細を取得できます。

---

## ライセンス / 貢献

（ここにライセンス情報や貢献方法を記載してください。リポジトリに LICENSE ファイルがある場合は参照を追加してください。）

---

この README はコードベースの主要機能を抜粋して記載しています。詳細な API 仕様や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば、README に具体的なコマンド例や CI / デプロイ手順、requirements.txt や pyproject.toml に基づくインストール手順を追記できます。