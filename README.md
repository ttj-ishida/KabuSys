# KabuSys

KabuSys は日本株のデータプラットフォームと研究・AI評価・監査・ETL を備えた自動売買支援ライブラリです。J-Quants API や RSS ニュース、OpenAI（LLM）を利用してデータ収集・品質チェック・ファクター計算・ニュースセンチメント・市場レジーム判定を行い、監査ログ・発注トレーサビリティを保持します。

主な用途
- 日次 ETL（株価・財務・カレンダー）の差分取得・保存・品質チェック
- ニュースの収集と LLM による銘柄別センチメント算出（ai_score）
- マクロニュース＋ETF MA を用いた市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム/バリュー/ボラティリティ等）と特徴量探索
- 監査テーブル（signal/order/execution）を用いたトレーサビリティ基盤

---

## 機能一覧

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート検出）、無効化フラグあり
- データ ETL（kabusys.data.pipeline）
  - J-Quants API から差分取得（株価・財務・市場カレンダー）
  - DuckDB への冪等保存（ON CONFLICT）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / 前後営業日取得 / カレンダー更新ジョブ
- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制限、リトライ、トークン自動リフレッシュ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、前処理、SSRF 対策、トラッキングパラメータ除去
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査スキーマ初期化
- AI（kabusys.ai）
  - score_news: 銘柄別ニュースセンチメントを OpenAI で算出して ai_scores に保存
  - score_regime: ETF（1321）200日MA乖離＋マクロニュースセンチメントで市場レジーム判定
- 研究ツール（kabusys.research）
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank
- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）

---

## セットアップ手順

前提
- Python 3.10+（型注釈に | 型を使用）
- DuckDB が利用可能
- OpenAI API キー（LLM を使う場合）
- J-Quants のリフレッシュトークン（ETL を使う場合）

1. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate (macOS/Linux) または .venv\Scripts\activate (Windows)

2. 依存パッケージをインストール
   - 必須（最小例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動で読み込まれます（.env.local は .env を上書き）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主な環境変数
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須: ETL）
   - OPENAI_API_KEY: OpenAI API キー（必須: AI 機能）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注連携がある場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知（必要に応じて）
   - DUCKDB_PATH: デフォルト DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite 等（必要に応じて）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

4. DuckDB ファイルと監査スキーマの初期化例
   Python REPL またはスクリプトから:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
   conn.close()

---

## 使い方（基本例）

以下は代表的な API の使い方例です。

- 設定の参照
  from kabusys.config import settings
  settings.jquants_refresh_token
  settings.duckdb_path

- DuckDB 接続と日次 ETL の実行
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()

- ニュースセンチメント（AI）スコア算出
  # score_news: raw_news / news_symbols / ai_scores テーブルを参照・更新します
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → OPENAI_API_KEY を使用
  print("書き込み銘柄数:", n_written)
  conn.close()

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()

- ファクター計算・研究ユーティリティ
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))

- 監査 DB 初期化（スクリプトから）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")

注意点
- OpenAI 呼び出しはネットワーク/レートの影響を受けます。API キーは環境変数 OPENAI_API_KEY に設定するか関数引数に渡してください。
- J-Quants へのリクエストは認証トークン（refresh token）を必要とします（settings.jquants_refresh_token）。
- ETL / AI 関数はルックアヘッドバイアスを避ける設計です（target_date 未満 / 前日ベースのウィンドウを使用）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースから銘柄別センチメントを算出（OpenAI）
  - regime_detector.py  — ETF MA + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理 / 営業日判定
  - etl.py                 — ETL の公開インターフェース（ETLResult）
  - pipeline.py            — 日次 ETL の本体（prices/financials/calendar）
  - stats.py               — 統計ユーティリティ（zscore_normalize）
  - quality.py             — データ品質チェック（欠損・重複・スパイク・日付）
  - audit.py               — 監査ログスキーマと初期化（signal/order/execution）
  - jquants_client.py      — J-Quants API クライアント（取得＋保存関数）
  - news_collector.py      — RSS 収集・前処理・SSRF 対策
- research/
  - __init__.py
  - factor_research.py     — モメンタム/バリュー/ボラティリティの計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリ等
- research/* 他の研究ユーティリティ

（注意: repository によっては strategy / execution / monitoring モジュールが別途存在する場合があります。本コードベースでは data / ai / research / config が中心です）

---

## 環境変数の自動読み込みについて

- パッケージインポート時に .env / .env.local を自動で読み込む仕組みがあります（プロジェクトルートは .git または pyproject.toml を基準に検出）。
- 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストでの利用を想定）。

---

## 開発上の注意

- DuckDB の executemany は空リストを受け付けないバージョン制約に配慮した実装がされています（空チェックを行っています）。
- OpenAI 呼び出しは JSON mode（response_format）を利用し、厳密な JSON パースを期待する設計です。レスポンスパース失敗時はフォールバック動作があります。
- J-Quants クライアント側はレート制御（120 req/min）とリトライ・トークンリフレッシュに対応しています。
- すべてのタイムスタンプは UTC を基本とする設計方針があります（監査ログなど）。

---

もし README に追加したい内容（例: CLI の使い方、CI / テスト手順、具体的な .env.example のテンプレート、発注フローのサンプル等）があれば教えてください。必要に応じて追記・テンプレート作成を行います。