# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI を利用したセンチメント）、リサーチ用ファクター計算、監査ログ（トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日時を直接参照しない設計、ETL/スコアは target_date を明示）
- DuckDB をデータストアに利用（軽量で高速な分析向け）
- 冪等性とフェイルセーフ（ETL 保存は ON CONFLICT、API障害時はスキップまたはフォールバック）
- セキュリティ配慮（RSS の SSRF 対策、defusedxml 利用等）

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env ファイル自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）
  - 必須環境変数のラッピング（settings オブジェクト）
  - 自動読み込み無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- データ取得 / ETL
  - J-Quants API クライアント（差分取得、ページネーション、リトライ、トークン自動リフレッシュ）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）

- ニュース収集・NLP
  - RSS 取得と前処理（SSRF 対策、URL 正規化、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（news_nlp.score_news）
  - マクロニュース＋ETF MA 乖離からの市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - z-score 正規化ユーティリティ（data.stats.zscore_normalize）

- 監査・トレーサビリティ
  - 監査テーブル定義と初期化（signal_events, order_requests, executions）
  - init_audit_schema / init_audit_db による DuckDB 初期化

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. 仮想環境を作成・有効化：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール（最低限）：
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）
   また、ネットワーク周りの標準ライブラリを使うため他の依存は少ない設計です。

4. 開発インストール（プロジェクトルートで）:
   - pip install -e .

   （setuptools/poetry によるパッケージ化を行っている場合はそれに従ってください）

5. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（自動読み込みを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   - 必須例（名前はコード中の settings を参照）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...
     - （任意）KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL

   .env の書き方はシンプルな KEY=VALUE 形式 (export KEY=val も可)。.env.example を参照してください（リポジトリに含める想定）。

---

## 使い方（主要な API と利用例）

以下は Python REPL / スクリプトから利用する例です。事前に環境変数を設定し、DuckDB を用意してください（settings.duckdb_path がデフォルト "data/kabusys.duckdb"）。

- 設定の参照
  - from kabusys.config import settings
  - settings.jquants_refresh_token, settings.duckdb_path, settings.env など

- DuckDB 接続の作成
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を明示することも可能
  - print(result.to_dict())

- 個別 ETL ジョブ
  - from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  - fetched, saved = run_prices_etl(conn, target_date)

- ニュースセンチメント（銘柄別）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, date(2026, 3, 20))  # ai_scores テーブルへ書込み、戻りは書き込んだ銘柄数

- 市場レジーム判定（マクロ + MA200）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, date(2026, 3, 20))  # market_regime テーブルへ書き込み

- 監査 DB 初期化
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # ファイル作成・スキーマ初期化

- リサーチ用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - res = calc_momentum(conn, date(2026,3,20))

- カレンダー操作
  - from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  - is_trading_day(conn, date(2026,3,20))

注意点：
- OpenAI を用いる関数（score_news, score_regime）は OPENAI_API_KEY を参照します。引数で api_key を渡すことも可能です。
- settings の必須値が未設定だと ValueError が出ます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。
- .env の自動読み込みはプロジェクトルートの検出に __file__ を使って行うため、パッケージ配布後も動作するよう設計されています。テスト時に自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

---

## ディレクトリ構成

（抜粋・概略）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースの集約・OpenAI を使った銘柄別センチメント
    - regime_detector.py       — マクロ＋MA200 で市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save）
    - pipeline.py              — ETL パイプラインと run_daily_etl
    - etl.py                   — ETLResult のエクスポート
    - calendar_management.py   — マーケットカレンダー管理
    - news_collector.py        — RSS フィード取得・前処理
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore）
    - audit.py                 — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Volatility/Value ファクター
    - feature_exploration.py   — 将来リターン・IC・統計サマリー
  - research/...               — 研究用ユーティリティ群
  - (その他: execution, monitoring, strategy 等はパッケージ表明のみ)

上記は主要モジュールの一覧です。各モジュールはドキュメント文字列（docstring）で設計方針や処理フローを詳細に記載しています。

---

## トラブルシューティング

- ValueError: 環境変数が未設定
  - settings のプロパティは必須変数未設定時に ValueError を出します。必要な環境変数を .env に設定してください。

- OpenAI 関連の API エラー
  - 一時的なレート制限・ネットワーク障害はリトライします。何度も発生する場合は API キーやクォータを確認してください。

- J-Quants API エラー / 認証失敗
  - JQUANTS_REFRESH_TOKEN を .env に設定してください。get_id_token は期限切れ時に自動リフレッシュします。

- RSS 取得時の SSRF / 接続拒否
  - news_collector はリダイレクト先やプライベートアドレスをブロックします。外部公開の RSS を使用してください。

- DuckDB executemany の空引数
  - コード中で DuckDB 0.10 の仕様を考慮して空の executemany を回避する実装になっています。バージョンが古い/新しい場合に問題が出たら DuckDB のバージョンを合わせてください。

---

## 開発・テストのヒント

- 自動 env ロードを無効にする：
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト用にモックで環境を注入してください。

- OpenAI 呼び出しのモック：
  - kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えられるよう設計されています。

- DuckDB をインメモリで使う：
  - init_audit_db(":memory:") や duckdb.connect(":memory:") でテスト用 DB を作れます。

---

以上が README の概要です。プロジェクト内の各モジュール（特に docstring）に詳細な処理フローと設計方針が記載されていますので、実装・拡張時にはそちらも参照してください。必要であれば、特定モジュール（例: jquants_client の詳細挙動や news_nlp のプロンプト設計）についての追補ドキュメントを作成します。