# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュース収集・NLP、ファクター計算、監査ログ管理、J-Quants / kabu ステーション連携など、アルゴリズムトレードの基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能をモジュールごとに提供します。

- データ取得・ETL（J-Quants API 経由で株価・財務・カレンダー取得、DuckDB に保存）
- ニュース収集（RSS）と自然言語処理（OpenAI を用いたセンチメント評価）
- 市場レジーム判定（ETF のMA乖離 + マクロニュースの LLM 評価の合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ / トレーサビリティ（signal → order → execution をトレースするテーブル定義）
- kabu ステーション等の実行・監視（将来的な実行モジュール向け基盤）

設計上の方針として、バックテストやフェアな評価のために「Look-ahead バイアス」を避ける実装や、外部 API 呼び出しのリトライ・フェイルセーフ処理、DuckDB による冪等保存（ON CONFLICT）を重視しています。

---

## 主な機能一覧

- data:
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_* / save_*）
  - market_calendar 管理、営業日判定ユーティリティ
  - news_collector（RSS 取得、前処理、安全対策付き）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - audit（監査テーブルの初期化、audit DB 作成）
  - 統計ユーティリティ（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存
  - regime_detector.score_regime: マクロ + ETF MA200 を統合して market_regime を保存
- research:
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- config:
  - Settings: 環境変数読み取り（自動でプロジェクトルートの .env / .env.local を読み込む）

---

## 要件

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK の利用を想定）
- defusedxml
- （標準ライブラリの urllib 等も使用）

実行環境によっては追加パッケージが必要です。requirements.txt 等がある場合はそちらを参照してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージをチェックアウト

2. 仮想環境を作成・有効化し依存をインストール

   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt

3. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（少なくとも ETL / AI を実行する場合）:

   - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時）
   - KABU_API_PASSWORD — kabuステーション API パスワード（発注などで使用）
   - SLACK_BOT_TOKEN — Slack 通知を使う場合
   - SLACK_CHANNEL_ID — Slack 通知を使う場合

   オプション（デフォルト値あり）:

   - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
   - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化 (値をセットすれば無効)
   - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH — デフォルト `data/monitoring.db`

   .env の例（.env.example を参考に作成してください）:

   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb

4. データベース用ディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL またはスクリプトでの利用例です。各例では duckdb 接続を渡します。

- ETL（日次 ETL 実行）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコアの計算（OpenAI API キーが環境変数に設定されているか、api_key 引数を渡す）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込み銘柄数: {n_written}")

- 市場レジーム判定（1321 の MA200 とマクロニュースを合成）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査テーブルの作成）

  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/kabusys_audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます

- 研究向けファクター計算例

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))

---

## 自動環境変数読み込みの挙動

- パッケージ import 時に config モジュールがプロジェクトルートを探索し、ルートに `.env` と `.env.local` があれば順に読み込みます（OS 環境変数 > .env.local > .env）。
- 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定することで無効化可能です（テスト時に便利）。
- ルート検出はこのパッケージのファイル位置を起点に `.git` または `pyproject.toml` を親ディレクトリで探索します。見つからない場合は自動ロードをスキップします。

.env のパースやクォート、コメント処理は細かい仕様に対応しています。

---

## ロギング・エラーハンドリング

- 多くの外部 API 呼び出し（J-Quants / OpenAI）にはリトライロジックと指数バックオフが組み込まれており、429 / ネットワーク断 / タイムアウト / 5xx 等の回復可能なエラーに対してリトライします。
- 重大な失敗は例外として上位に伝播しますが、多くの処理（news scoring や ETL の一部）はフェイルセーフ（部分失敗を許容して継続）設計になっています。
- ログレベルは環境変数 `LOG_LEVEL` で制御できます。

---

## テスト・開発メモ

- OpenAI（LLM）呼び出しやネットワーク I/O はユニットテストでモックする設計になっています。例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api") 等の差し替えが想定されています。
- auto env load を無効にしてテスト用に明示的に settings を設定することを推奨します。
- DuckDB に対する executemany の空リスト送信など、バージョン差異に配慮した実装がされています（テスト時に空パラメータを送らないよう注意）。

---

## ディレクトリ構成

(主要ファイルのみ抜粋)

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースセンチメント取得（score_news）
    - regime_detector.py               — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                      — ETL パイプライン（run_daily_etl 他）
    - jquants_client.py                — J-Quants API クライアント（fetch/save）
    - news_collector.py                — RSS ニュース収集
    - calendar_management.py           — 市場カレンダー管理 / 営業日判定
    - quality.py                       — データ品質チェック
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査テーブル定義・初期化
    - etl.py                           — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py               — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py           — calc_forward_returns, calc_ic, factor_summary, rank
  - research/... （その他の研究用ユーティリティ）
  - (将来的に) strategy/, execution/, monitoring/ などを公開予定（__all__ に記載）

---

## 追加情報 / 注意点

- DuckDB スキーマ（テーブル定義）は外部に提供されているドキュメント (DataPlatform.md / StrategyModel.md) に基づいて設計されています。初回使用時は関連テーブルが存在することを確認してください（ETL の一部はテーブル存在を前提とします）。
- ニュース収集は RSS のパースやネットワークリダイレクトについて SSRF 対策（ホストのプライベート検査、スキーム検証）を行っています。
- OpenAI 呼び出しは JSON Mode を想定し、応答のバリデーションとクリップ（スコアを -1.0〜1.0 に制限）を行います。API レスポンスの欠陥はログ出力し、フォールバック値で継続します。
- ライブ発注機能を有効にする場合は、kabu ステーション API の認証情報および安全なリスク管理の実装が必須です（本コードはデータ取得・解析・監査基盤を主に提供します）。

---

問題が発生したり、特定の機能の使い方を詳しく知りたい場合は、どのモジュール（例: ETL / news_nlp / regime_detector / jquants_client）のサンプルを見たいかを教えてください。追加の使用例やスクリプトを用意します。