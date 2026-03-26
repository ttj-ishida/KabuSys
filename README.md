# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集と NLP スコアリング・市場レジーム判定・リサーチ用ファクター計算・監査ログ（オーダー追跡）など、取引システムで必要となる基盤機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄一覧、JPX マーケットカレンダーなどの差分取得とページネーション対応
  - レートリミット・リトライ・トークン自動リフレッシュ対応
  - DuckDB へ冪等に保存（ON CONFLICT / UPDATE）

- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分更新・バックフィル機能・品質チェック統合（欠損・スパイク・重複・日付不整合）

- ニュース収集 / NLP
  - RSS フィードの安全な収集（SSRF 防止・gzip 上限・XML セーフパーサ）
  - 記事前処理（URL 除去・正規化）と raw_news / news_symbols への冪等保存
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（score_news）

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュース LLM センチメントを合成して日次レジーム（bull / neutral / bear）を判定（score_regime）

- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等ファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリー、Z スコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブルを作成・初期化するユーティリティ（init_audit_schema / init_audit_db）

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（settings）で環境変数を型的に取得

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. リポジトリをチェックアウトし、パッケージをインストール（開発モード）します。
   - （プロジェクトルートに pyproject.toml 等がある想定）
   ```
   pip install -e .
   ```

3. 環境変数の準備
   - プロジェクトルートに `.env` （および必要なら `.env.local`）を作成してください。自動読み込みの優先順は OS 環境変数 > .env.local > .env です。
   - 自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - SLACK_BOT_TOKEN — （通知機能を使う場合）Slack ボットトークン
     - SLACK_CHANNEL_ID — Slack チャネル ID
     - KABU_API_PASSWORD — kabuステーション API を使う場合のパスワード
     - OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）を呼ぶ際に必要（引数でも渡せます）
   - 任意 / デフォルト値:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト: INFO
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db

4. （任意）DuckDB 初期化
   - アプリケーションが期待するスキーマを作るユーティリティ（data.schema 系）がある想定です。監査ログ専用 DB を作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```

5. 依存関係
   - OpenAI SDK（openai）、duckdb、defusedxml などが必要です。pyproject.toml / requirements を参照してインストールしてください。
   - 例:
   ```
   pip install duckdb openai defusedxml
   ```

---

## 使い方（主要な API と実行例）

以下は代表的な利用例です。すべての関数は duckdb の接続（duckdb.connect(...)）を受け取ります。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングする
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")  # api_key を渡せる
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  ```

- 研究（ファクター計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（発注トレーサビリティ）を初期化する
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect("data/audit.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- 設定取得（Settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)       # Path オブジェクト
  print(settings.is_live)          # bool
  ```

注意:
- OpenAI を使う機能は環境変数 OPENAI_API_KEY を参照します（引数で上書き可能）。
- ETL / 保存処理は DuckDB 上での所定のテーブルスキーマを前提とします（既存スキーマ管理ユーティリティを利用してください）。
- .env の自動読み込みは、プロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定します。

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下に主要モジュールを配置しています。主要ファイルを抜粋すると以下のようになります。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（score_news）
    - regime_detector.py            — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch_*/save_*）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開型（ETLResult）
    - news_collector.py             — RSS 収集と前処理
    - calendar_management.py        — マーケットカレンダー管理
    - quality.py                    — データ品質チェック
    - stats.py                      — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py        — 将来リターン / IC / 統計サマリ
  - ai/、data/、research/ に関連するその他ファイル

（上記は主要モジュールの一覧であり、細かいファイルはリポジトリ内を参照してください。）

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策の徹底
  - 多くの処理で datetime.today() などを直接参照せず、外部から target_date を渡す設計になっています（バックテストで必須）。
- フェイルセーフ設計
  - LLM API 失敗時はスコアを中立（0.0）にフォールバックしたり、処理を継続する設計です。つまり一部 API エラーが全体停止を引き起こさないようになっています。
- 冪等性
  - J-Quants から取得したデータの DB 保存は ON CONFLICT DO UPDATE を使い冪等にしています。
- セキュリティ対策
  - RSS 収集での SSRF 対策、defusedxml による XML 安全化、レスポンスサイズの上限設定などを行っています。
- DuckDB を前提
  - 内部ストレージ / テーブルは DuckDB を使う設計です。接続は duckdb.connect() を使用してください。

---

必要であれば README に以下を追加できます：
- 詳細な依存関係（requirements/poetry）
- スキーマ初期化スクリプト（テーブル DDL）
- CI / テスト実行方法
- 典型的な運用フロー（Cron で run_daily_etl → score_news → regime 判定 → 戦略 → 発注）
要望があれば追記します。