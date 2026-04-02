# KabuSys — 日本株自動売買プラットフォーム（README）

簡潔な説明書を日本語でまとめています。開発者向けのリポジトリREADMEとして、プロジェクト概要・機能一覧・セットアップ手順・主な使い方・ディレクトリ構成を示します。

---

## プロジェクト概要

KabuSys は日本株の自動売買・データ基盤・リサーチ機能を統合したPythonパッケージです。  
主に以下を提供します。

- J-Quants API を用いた株価・財務・マーケットカレンダーの ETL（差分取得・保存・品質チェック）
- DuckDB を用いたデータ管理・監査ログ（監査テーブル初期化機能）
- ニュースの収集と LLM（OpenAI）によるニュースセンチメント解析（銘柄ごとの AI スコア）
- マーケットレジーム判定（ETF MA とマクロニュースの合成）
- 研究（ファクター計算、将来リターン、IC 計算、Zスコア正規化）ユーティリティ
- データ品質チェック、カレンダー管理、ニュース収集時の SSRF 対策などの堅牢な実装

パッケージは src/kabusys 配下のモジュール群で構成されています。

---

## 主な機能一覧

- config: 環境変数と .env 自動読み込み（.env.local の優先、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）
- data:
  - ETL パイプライン（daily_etl、prices / financials / calendar 個別ジョブ）
  - J-Quants API クライアント（ページネーション、レートリミット、トークン自動リフレッシュ）
  - market_calendar 管理（営業日判定／next/prev/get_trading_days）
  - news_collector（RSS 取得、記事前処理、SSRF 対策、raw_news 保存）
  - quality（欠損・スパイク・重複・日付不整合チェック）
  - audit（監査ログテーブル定義・初期化・監査DB初期化ユーティリティ）
  - stats（Zスコア正規化）
- ai:
  - news_nlp.score_news: ニュースを LLM で解析して ai_scores に書き込み
  - regime_detector.score_regime: ETF 200日MA とマクロニュースを組み合わせて market_regime に書き込み
- research:
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（依存関係）

最低限必要な Python パッケージ（install 時に明示的に追加してください）:

- Python 3.10+
- duckdb
- openai (openai-python)
- defusedxml

（実行環境や機能に応じて追加パッケージが必要になる場合あり）

---

## セットアップ手順

1. リポジトリをクローン（またはソースを取得）し、プロジェクトルートに移動
   - パッケージは `src/` 配下に配置されています。

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （開発用に `pip install -e .` が使えるよう packaging を整備している場合はそちらを利用）

4. 環境変数設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD を設定すると無効化されます）。
   - 必須の環境変数（config.Settings により要求）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - SLACK_BOT_TOKEN
     - SLACK_CHANNEL_ID
   - 任意/実行に必要なもの:
     - OPENAI_API_KEY（ai.news_nlp / regime_detector の API 呼び出しに必要。関数呼び出し時に api_key 引数で上書き可能）
     - KABUSYS_ENV（development / paper_trading / live; デフォルト: development）
     - LOG_LEVEL（DEBUG/INFO/...; デフォルト: INFO）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB; デフォルト: data/monitoring.db）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   ```

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要ユースケース例）

以下は Python REPL やスクリプト内での呼び出し例です。すべての操作は DuckDB 接続を渡して行います。

- DuckDB 接続
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日が対象
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュースセンチメントのスコアリング（AI）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # APIキーを引数で渡すか環境変数 OPENAI_API_KEY に設定しておく
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込んだ銘柄数:", count)
  ```

- マーケットレジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OpenAI APIキーは環境変数か api_key 引数で指定
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  val = calc_value(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))
  ```

- 将来リターン / IC 計算
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  fwd = calc_forward_returns(conn, target_date=date(2026, 3, 20), horizons=[1,5,21])
  ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- カレンダー操作（営業日判定）
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

- 監査ログ DB 初期化（監査テーブル作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は UTC タイムゾーン設定や DDL を作成します
  ```

- RSS ニュース収集（ニュースコレクタ）
  - ニュース収集は `kabusys.data.news_collector.fetch_rss()` を使って記事を取得し、DBへ保存するラッパー（保存処理）を実装して運用してください。fetch_rss は SSRF 対策・応答サイズ制限を行います。

---

## 注意事項 / 実装上のポイント

- .env 自動読み込み: プロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` をロードします。テストや明示的な設定で無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Look-ahead bias を避ける実装: 多くのモジュール（news_nlp, regime_detector, pipeline 等）は date 引数を明示的に受け取り、内部で date.today() を参照しない設計です。バックテスト時は意図しない未来情報参照を避けてください。
- J-Quants クライアント:
  - レート制限（120 req/min）を守る実装、ページネーション対応、401 の自動リフレッシュがあります。
- OpenAI 呼び出し:
  - gpt-4o-mini を使い JSON mode でレスポンスを期待します。API失敗時はフォールバックを行い、重大な例外は外へ投げる/ログを残す実装です。
- DuckDB バージョン差分:
  - 一部の実装（executemany の空リストバインドなど）は DuckDB バージョンに依存するため、DuckDB の互換性に注意してください。

---

## ディレクトリ構成（抜粋）

以下は主要ファイル・モジュールの構成です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                            — 環境設定 / .env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py                         — ニュース NLP スコアリング（score_news）
    - regime_detector.py                  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                         — ETL パイプライン run_daily_etl 等
    - etl.py                              — ETL 便利公開型（ETLResult）
    - jquants_client.py                   — J-Quants API クライアント（fetch_*, save_*）
    - calendar_management.py              — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py                   — RSS ニュース収集（SSRF 対策等）
    - quality.py                          — データ品質チェック
    - stats.py                            — zscore_normalize 等
    - audit.py                            — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py                  — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py              — calc_forward_returns / calc_ic / factor_summary / rank
  - research パッケージは data.stats に依存している箇所あり

（上記は主要なファイルのみ抜粋。実際のツリーには追加のヘルパー等があります）

---

## 開発者向けヒント

- 単体テストや CI では `.env` の自動ロードを無効化する場合があります： `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しや外部 API 呼び出しはモック可能なように個所ごとに分離されています（テスト時は unittest.mock.patch で差し替えが容易）。
- DuckDB のスキーマ作成・監査テーブル初期化は idempotent（何度実行しても安全）です。

---

もし README に追加したい具体的な例（.env.example、docker-compose 構成、CLI ラッパー等）があれば教えてください。必要に応じて追記・テンプレート化して提供します。