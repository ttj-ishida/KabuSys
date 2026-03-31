# KabuSys

KabuSys は日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（LLM を使ったセンチメント）、市場レジーム判定、監査ログ（オーダー／約定トレース）、リサーチ用ファクター計算などの機能を含みます。

---

## プロジェクト概要

主な目的は「データの信頼性を担保しつつ日本株の自動運用ロジックを安全に実行・研究できる基盤」を提供することです。  
設計上の特徴：

- DuckDB を用いたオンディスクデータベース（軽量かつ高速）
- J-Quants API を使った差分 ETL（ID トークン自動更新・レートリミット対応）
- RSS ベースのニュース収集と LLM（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを統合）
- 監査（signal → order_request → executions）のための監査スキーマを提供
- 研究用ファクター計算・統計ユーティリティ（外部依存を最小化）

---

## 機能一覧

- config: 環境変数読み込み・設定管理 (.env / .env.local の自動読み込み、無効化可能)
- data:
  - jquants_client: J-Quants API クライアント（token refresh、pagination、保存処理）
  - pipeline: ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存ヘルパー
  - calendar_management: 市場カレンダー管理・営業日判定ヘルパー
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ用スキーマ初期化・DBユーティリティ
  - stats: 汎用統計（zscore_normalize）
- ai:
  - news_nlp.score_news: 銘柄ごとにニュースセンチメントを LLM で算出し ai_scores に保存
  - regime_detector.score_regime: 市場レジーム（bull/neutral/bear）を算出して market_regime に保存
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順

前提:
- Python 3.10+（typing の union 型などが利用されているため）
- DuckDB、openai、defusedxml 等の依存パッケージ

1. リポジトリをクローンし、開発用インストール（例）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"  # 実際の requirements に応じて調整
   ```
   ※このコードベースには requirements ファイルが付属していない想定のため、最低限以下をインストールしてください:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

2. 環境変数 (.env) の準備:
   プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（優先順位: OS 環境 > .env.local > .env）。  
   自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須の環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（発注連携等）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用する場合は引数でも渡せます）

   データベースパス（省略時のデフォルト）:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db

3. DuckDB 用初期スキーマ（監査ログなど）を作成:
   Python REPL やスクリプトから `kabusys.data.audit.init_audit_db()` を呼んで初期化できます（下の使用例参照）。

---

## 使い方（主要 API と実行例）

以下は最小限の利用例です。実際はロギング設定や例外処理を付加してください。

- DuckDB に接続して ETL を走らせる（日次 ETL）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に保存:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("written:", n_written)
  ```

  注意:
  - API キーは引数 `api_key` で渡せます。None の場合は環境変数 `OPENAI_API_KEY` を参照します。
  - モデルは現在 gpt-4o-mini + JSON Mode を使用する想定です。

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査 DB 初期化（監査専用 DB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS 取得（ニュース収集ユーティリティ）:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

- カレンダー・営業日判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- 研究用関数（例：モメンタム計算）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026,3,20))
  ```

---

## 環境変数（代表的な一覧）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (LLM 呼び出し用)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (通知)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live) — 実行モード。デフォルト: development
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — ログレベル。デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化します（テスト用）

.config モジュールの挙動：
- プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env / .env.local を自動で読み込みます。
- .env のパースはシェル風の export KEY=val やクォート・コメントを考慮した実装です。
- OS 環境変数が優先され、.env.local は .env を上書きします。

---

## ディレクトリ構成

主要なファイル・パッケージ構成（src 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           # ニュースセンチメント算出（score_news）
    - regime_detector.py    # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     # J-Quants API クライアント & 保存関数
    - pipeline.py          # ETL パイプライン（run_daily_etl 等）
    - etl.py               # ETLResult の公開
    - news_collector.py    # RSS 取得・前処理
    - calendar_management.py
    - quality.py           # 品質チェック
    - stats.py             # 統計ユーティリティ（zscore_normalize）
    - audit.py             # 監査スキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py   # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py
  - monitoring/            # (コードベースでは参照がある想定、monitoring 関連処理を配置)
  - strategy/              # (戦略・発注ロジックを配置する想定)
  - execution/             # (ブローカー連携の抽象化を配置する想定)

※実装済みのファイルは上記のコード一覧に準拠しています。プロジェクトは拡張可能なモジュール構成です。

---

## 注意事項・運用上のポイント

- Look-ahead バイアス防止:
  - 多くの関数（score_news, score_regime, ETL など）は内部で date.today() をルックアヘッドに使わない設計です。バックテスト用途では target_date を明示的に渡してください。
- OpenAI 呼び出し:
  - API 呼び出しはリトライやフェイルセーフ（失敗時は 0.0 を使う等）が実装されていますが、レートやコストに注意してください。
- J-Quants:
  - レート制限（120 req/min）を守るため内部で RateLimiter を使用しています。
  - 401 を受けた場合はリフレッシュトークンで id_token を再取得し自動リトライします。
- ニュース収集:
  - SSRF 対策・レスポンスサイズ制限・トラッキングパラメータ除去など安全処理を含みます。
- 監査スキーマ:
  - 監査用テーブルは削除前提ではなくトレーサビリティ確保のため永続化します。init_audit_db で初期化してください。
- テスト:
  - API 呼び出しやネットワーク関連はモックしやすいように抽象化・差し替えポイントが用意されています（例: _call_openai_api の差し替え）。

---

README はここまでです。必要であれば以下の追加情報を作成できます：
- .env.example のテンプレート
- requirements.txt / poetry / pyproject.toml の例
- 実行スクリプト（CLI）サンプル
- 詳細な API リファレンス（関数ごとの引数・戻り値の表）

どれを追加しますか？