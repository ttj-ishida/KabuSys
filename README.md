# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。J-Quants / kabuステーション / RSS / OpenAI を組み合わせて、データ収集（ETL）・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログを提供します。

---

## 概要

KabuSys は以下を目的とした Python モジュール群です。

- J-Quants API からの株価・財務・マーケットカレンダーの差分取得（ETL）と DuckDB への冪等保存
- RSS ベースのニュース収集とニュース -> 銘柄マッピング
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別、マクロ）評価
- 日次 ETL パイプライン、データ品質チェック、ファクター計算（モメンタム・バリュー・ボラティリティ等）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
- 発注 / 監査ログ用の監査テーブル初期化ユーティリティ（DuckDB）
- 市場カレンダー管理／営業日ヘルパー

設計上の特徴：
- ルックアヘッドバイアス回避（内部で date.today() を不用意に参照しない）
- API 呼び出しにはリトライ・バックオフ・レートリミットなどの堅牢化を実装
- DuckDB を用いたローカル永続化（ON CONFLICT による冪等処理）
- 外部依存を最小化（標準ライブラリ + 必要なパッケージのみ）

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - データ品質チェック（missing / duplicates / spike / date consistency）
  - ニュース収集（RSS の収集・前処理・SSRF 対策）
  - 監査ログ初期化（監査テーブル DDL / index の作成）
- ai
  - news_nlp.score_news(conn, target_date, api_key=None)：銘柄別ニュースセンチメントを ai_scores テーブルへ保存
  - regime_detector.score_regime(conn, target_date, api_key=None)：ETF 1321 の MA200 とマクロニュースで市場レジーム判定を market_regime テーブルへ保存
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析系ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
- utils
  - 設定管理（kabusys.config.Settings）：環境変数から各種設定を取得（JQUANTS_REFRESH_TOKEN など）
  - 統計ユーティリティ（zscore_normalize）

---

## 必要条件（推奨）

- Python 3.10+
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

requirements.txt がない場合は少なくとも上記パッケージをインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン

   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）

   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```

3. 依存パッケージをインストール

   例:

   ```
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用）

4. 環境変数設定

   ルートに `.env` / `.env.local` を置くか、OS 環境変数を設定します。自動ロードは以下の優先順位で行われます：

   - OS 環境変数
   - .env.local
   - .env

   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時等）。

   主な必須環境変数：
   - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
   - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必要に応じて）
   - SLACK_CHANNEL_ID      : Slack チャネル ID（必要に応じて）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必要に応じて）
   - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 呼び出し時に未指定なら参照）
   あると便利な環境変数：
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV           : environment (development | paper_trading | live)
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）

   .env のサンプル（説明用）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

以下はいくつかの代表的な使い方例です。すべて DuckDB 接続を生成して関数に渡すことが基本です。

- DuckDB 接続の作成（ファイルまたは :memory:）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path
  ```

- 日次 ETL 実行

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコア生成（OpenAI API キーは env 変数か api_key 引数で指定）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査用 DB を分けたい場合）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算例（研究用）

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 市場カレンダー・営業日ヘルパー

  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点：
- OpenAI 呼び出しを行う関数は api_key 引数を受け取ります（None の場合は環境変数 OPENAI_API_KEY を参照）。API 呼び出しは失敗時にフェイルセーフ（多くの場合 0.0 またはスキップ）する設計です。
- ETL / save 系は基本的に冪等（ON CONFLICT）を想定しています。

---

## ディレクトリ構成（主要ファイル）

（ルートはプロジェクトディレクトリ。実装は src/kabusys 以下に配置）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  # 銘柄別ニュースセンチメント
    - regime_detector.py           # 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            # J-Quants API クライアント（fetch/save）
    - pipeline.py                  # ETL パイプライン（run_daily_etl 等）
    - etl.py                       # ETLResult 再エクスポート
    - calendar_management.py       # 市場カレンダー管理 / 営業日ユーティリティ
    - news_collector.py            # RSS ニュース収集
    - quality.py                   # データ品質チェック
    - stats.py                     # 統計ユーティリティ（zscore_normalize）
    - audit.py                     # 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py           # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py       # forward returns / IC / summary / rank
  - ai/__init__.py
  - research/__init__.py
  - data/__init__.py

---

## 注意事項 / ベストプラクティス

- 環境変数の安全管理：J-Quants トークンや OpenAI キーは秘匿情報です。CI / 本番では秘密管理（Vault 等）を利用してください。
- バックテストでのデータ使用：Look-ahead バイアスを避けるため、バックテストでは ETL で保存された時点以前に取得可能なデータのみを使用してください（jquants_client.fetch_listed_info 等は取得日時を指定して使用することを推奨）。
- DuckDB executemany の空リスト制約：コード内でも扱われていますが、直接呼び出す場合は executemany に空リストを与えないよう注意してください。
- OpenAI 呼び出しはコストが発生します。ローカルテスト時はモック化するか api_key を無効化してください。テスト用に関数単位で _call_openai_api を patch できるよう設計されています。

---

## 追加情報 / 開発者向け

- 自動 .env ロードの挙動は src/kabusys/config.py に実装されています。プロジェクトルート判定は .git または pyproject.toml を基準とします。
- テスト時に自動 .env ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しと J-Quants 呼び出しはそれぞれリトライロジック・バックオフ・例外ハンドリングがあり、テスト時には HTTP / API 呼び出しをモックして下さい。

---

この README はコードベースの主要機能と使い方の概要をまとめたものです。詳細は各モジュールの docstring を参照してください（例: kabusys/data/pipeline.py, kabusys/ai/news_nlp.py など）。必要であれば運用手順（cron やジョブスケジューラでの ETL 実行、Slack 通知設定、監査DB 運用）についても追記できます。