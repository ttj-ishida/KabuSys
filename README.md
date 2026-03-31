# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。  
DuckDB をデータストアとし、J-Quants / RSS / OpenAI を組み合わせてデータ収集・品質管理・ニュース NLP・市場レジーム判定・監査ログを提供します。

---

## プロジェクト概要

KabuSys は日本株の研究・バックテスト・自動売買パイプラインを支援する共通コンポーネント群です。主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー等の差分ETL
- RSS ニュース収集と銘柄別ニュースセンチメント（LLM）評価
- マーケットレジーム判定（ETF + LLMを組み合わせ）
- データ品質チェック（欠損・重複・スパイク等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 研究用ファクター計算・特徴量探索ユーティリティ

パッケージはモジュールごとに分かれており、ETL / data / research / ai / monitoring / execution 等の機能群を提供します。

---

## 主な機能一覧

- data/
  - J-Quants クライアント（レート制限・リトライ・トークン自動更新）
  - 日次 ETL パイプライン（prices / financials / calendar）
  - market_calendar 管理（営業日判定・next/prev/get_trading_days）
  - RSS ニュース収集（SSRF対策・トラッキング除去・gzip制限）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログテーブルの初期化/DB 作成ユーティリティ
  - 汎用統計関数（Zスコア正規化）
- ai/
  - ニュース NLP（gpt-4o-mini を使った銘柄別センチメントスコア化）
  - レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM 結果の合成）
- research/
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 特徴量探索（将来リターン計算・IC・統計サマリー）
- monitoring / execution / strategy（インターフェース想定：監視や発注に関連するコンポーネント）
- 設定管理（.env 自動読み込み、Settings クラス）

---

## 動作要件（主な依存）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （標準ライブラリ多数）
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

適宜、プロジェクトの pyproject.toml / requirements を参照して追加依存をインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンし、パッケージをインストール（開発モード推奨）

   ```
   git clone <repo-url>
   cd <repo>
   pip install -e ".[dev]"   # または pip install -e .
   ```

2. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env`（および開発用に `.env.local`）を置くと自動でロードされます（モジュール起動時に自動読み込み、無効化は下記参照）。

   必須の環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
   - OPENAI_API_KEY — OpenAI API キー（score_news / regime_detector で使用）
   - KABU_API_PASSWORD — kabuステーション API パスワード（該当機能使用時）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - DUCKDB_PATH, SQLITE_PATH — DB ファイルパス（デフォルト値あり）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=passwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   自動 env ロードを無効化する場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

3. DuckDB 用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な呼び出し例）

以下は Python スクリプト / REPL からのサンプル利用法です。conn は duckdb.connect() の接続を想定しています。

- ETL（日次パイプライン）を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai_score の生成）

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数か api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / executions 等の運用が可能
  ```

- market_calendar 操作（営業日判定など）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- ファクター / 研究ユーティリティ

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

注意点：
- OpenAI への呼び出しはモデル（gpt-4o-mini）と JSON Mode を利用します。API 呼び出し回数やトークン使用に注意してください。
- DuckDB のバージョン差異に依存する SQL バインディングの振る舞い（executemany の空リストなど）に注意しています（コード内に互換処理あり）。

---

## 設定管理

- settings: `kabusys.config.settings` 経由で各種設定を参照できます（例: settings.jquants_refresh_token, settings.duckdb_path, settings.env）。
- .env の自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

---

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なモジュール構成を抜粋します（実際のファイル数は多少異なる可能性があります）。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news 等）
    - regime_detector.py          — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント（fetch/save 等）
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETL 結果型再エクスポート
    - calendar_management.py      — market_calendar 管理 / 営業日判定
    - news_collector.py           — RSS 収集・前処理
    - quality.py                  — データ品質チェック
    - stats.py                    — 統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum/value/volatility）
    - feature_exploration.py      — 将来リターン / IC / summary
  - research/（その他ファイル）
  - monitoring/, execution/, strategy/ （概念的に存在するモジュール領域）

---

## 開発・テストに関する注意

- .env の自動ロードはテストを行う際に影響するため、テスト実行時に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して外部環境の影響を排除できます。
- ai モジュールの OpenAI 呼び出しはユニットテストでモック可能（モジュール内の _call_openai_api を patch することを想定）。
- network IO（J-Quants / RSS）についてもモックして単体テストを実行することを推奨します。

---

必要であれば、README に以下を追記できます：
- より詳細な例（ETL スケジュール例 / cron systemd timers）
- DB スキーマの詳細（raw_prices / raw_financials / ai_scores 等のカラム）
- CI/CD / テスト実行方法
- 貢献ガイドライン

ご希望があれば追記します。