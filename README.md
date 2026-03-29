# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ。  
DuckDB をデータレイヤーに、J-Quants / kabuステーション / OpenAI 等を利用してデータ収集（ETL）・品質チェック・特徴量計算・AIニュース解析・市場レジーム判定・監査ログ管理までを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つ内部ライブラリ群をまとめたコードベースです。

- J-Quants API から株価・財務・市場カレンダー等を差分取得・保存する ETL
- raw_prices / raw_financials 等に対するデータ品質チェック
- ニュース収集（RSS）と LLM を使った銘柄別ニュースセンチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの LLM 評価を合成）
- 研究用途のファクター計算（モメンタム・ボラティリティ・バリュー等）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）用のスキーマ初期化ユーティリティ

設計上の特徴:
- Look-ahead bias を避ける設計（内部で date.today() を直接使わない等）
- DuckDB を利用した冪等な保存（ON CONFLICT DO UPDATE）とトランザクション制御
- OpenAI 呼び出しは JSON モードを用いた厳密なレスポンス検証とリトライ処理
- ネットワークや外部 API に対する堅牢なエラーハンドリングと指数バックオフ

---

## 主な機能一覧

- data/
  - ETL: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント: fetch / save 関数群（daily_quotes, financials, market_calendar, listed_info）
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - news_collector: RSS 取得・前処理・raw_news 保存支援
  - quality: 欠損・重複・スパイク・日付不整合チェック
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等共通統計ユーティリティ
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None): 銘柄ごとのニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime(conn, target_date, api_key=None): マクロセンチメント + ETF MA で market_regime を書込
- research/
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 要件

- Python 3.10+
- 必須ライブラリ（例）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトに requirements.txt がある想定で、適宜インストールしてください）

---

## セットアップ手順

1. リポジトリをチェックアウト / クローン

   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトが pip パッケージ化されている場合）
   pip install -e .

4. 環境変数 / .env の準備

   プロジェクトルート（pyproject.toml や .git がある階層）に `.env` / `.env.local` を置くと起動時に自動読み込みされます。自動ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要となる代表的な環境変数（最低限）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注関連）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI を使う場合の API キー（news_nlp / regime_detector）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視等に使う SQLite（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-....
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

5. データベース初期化（オプション）

   監査ログ用 DuckDB を初期化する例:

   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

   既存の DuckDB 接続に監査スキーマだけ追加する場合:

   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要 API の例）

以下はライブラリの主要なユースケースのサンプルです。実行コンテキスト（仮想環境、.env 設定、依存インストール）が整った上でご利用ください。

- DuckDB 接続の取得

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL の実行

  run_daily_etl は市場カレンダー→株価→財務→品質チェックまで一括実行します。

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント算出（AI）

  OpenAI API キーが環境変数 `OPENAI_API_KEY` にあることを確認してください。

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定（AI）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算 / 研究用ユーティリティ

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  fwd = calc_forward_returns(conn, date(2026, 3, 20), horizons=[1,5,21])
  ic = calc_ic(momentum, fwd, factor_col="mom_1m", return_col="fwd_1d")
  ```

- 品質チェックを個別に実行

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

---

## 注意点 / 運用時の留意事項

- OpenAI 呼び出しは API コストとレート制限に注意してください。レスポンスは厳密な JSON を期待するため、プロンプト設計やモデルの互換性に留意してください。
- J-Quants API はレート制限と認証トークンの更新ロジックを内蔵していますが、rate-limit に達した場合はモジュール側でバックオフします。API トークンと利用契約を遵守してください。
- DuckDB への書き込みは多くの関数で冪等設計（ON CONFLICT）を採用していますが、ETL 実行時にトランザクションのロールバック等を行うため、運用スクリプトでログと監査結果を残すことを推奨します。
- テスト時は環境変数自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用できます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースを LLM でスコア化（ai_scores へ）
    - regime_detector.py           — MA とマクロ LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（fetch/save）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL の公開インターフェース
    - news_collector.py            — RSS 取得と前処理
    - calendar_management.py       — 市場カレンダー管理 / 営業日判定
    - quality.py                   — データ品質チェック
    - audit.py                     — 監査ログスキーマ初期化 / DB 初期化
    - stats.py                     — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py           — momentum / value / volatility 等
    - feature_exploration.py       — forward returns, IC, summary
  - research/ ... (他ユーティリティ)

---

## ライセンス・貢献

（ここにプロジェクトのライセンスや貢献ルールを記載してください。リポジトリ側で定義されているものに従って下さい。）

---

README の補足・改善希望があれば、どの点を詳しく書いてほしいか（セットアップの OS 固有手順、CI/テストの実行方法、具体的な env.example のテンプレートなど）を教えてください。