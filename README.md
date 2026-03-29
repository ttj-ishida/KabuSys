# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ。  
DuckDBベースのデータETL、ニュースNLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログスキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象とした研究・バックテスト・運用支援を目的とした内部ライブラリ群です。主な目的は次の通りです。

- J-Quants API からの差分ETL（価格・財務・市場カレンダー）
- RSS ベースのニュース収集と LLM による銘柄センチメント算出
- ETF ベースの市場レジーム判定（MA + マクロニュース）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ツール
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order → execution のトレーサビリティ）
- DuckDB を中心とした冪等処理・トランザクション管理

設計上、バックテストでのルックアヘッドバイアスを防ぐために日時取得やクエリでは厳格な取り扱いを行っています。

---

## 機能一覧（抜粋）

- ETL パイプライン
  - run_daily_etl：市場カレンダー・株価・財務の差分取得と品質チェック
  - jquants_client：API 呼び出し / 保存関数（save_daily_quotes 等）
- ニュース / NLP
  - news_collector：RSS からの収集・前処理・raw_news 登録
  - news_nlp.score_news：銘柄ごとの LLM センチメント算出 → ai_scores 書き込み
- 市場レジーム
  - regime_detector.score_regime：ETF 1321 の MA とマクロニュースを統合して regime を判定し market_regime に保存
- 研究支援（research）
  - calc_momentum / calc_value / calc_volatility：ファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量解析用ユーティリティ
  - zscore_normalize：クロスセクション正規化
- データ管理（data）
  - pipeline.ETLResult：ETL 実行結果
  - calendar_management：営業日判定 / calendar 更新ジョブ
  - quality：データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - audit：監査ログスキーマの初期化（init_audit_schema, init_audit_db）
- 設定管理
  - config.Settings：環境変数ベースの設定取得（自動 .env ロードあり）

---

## セットアップ手順

前提:
- Python 3.10+（typing | 構文に依存）
- DuckDB（Python パッケージとして利用）
- OpenAI API キー（news_nlp / regime_detector）
- J-Quants リフレッシュトークン
- 必要に応じて kabuステーション / Slack トークン

1. リポジトリをクローンして仮想環境を作成

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

2. パッケージをインストール（開発インストール）

   ```bash
   pip install -e ".[dev]"   # extras が設定されている場合
   # もし extras がない場合は必要パッケージを個別に pip install
   pip install duckdb openai defusedxml
   ```

3. 環境変数（.env）を作成
   - 自動ロードの挙動:
     - OS 環境変数 > .env.local > .env の順で優先読み込み
     - 自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 必須項目（最低限）:

     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要時）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必要時）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注を行う場合）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
     - Optional: KABUSYS_ENV (development | paper_trading | live), LOG_LEVEL, KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベースディレクトリ作成（DUCKDB_PATH のディレクトリ等）

   ```bash
   mkdir -p data
   ```

---

## 使い方（代表的な操作）

以下は Python スニペットによる利用例です。実行は仮想環境内で行ってください。

- 設定の利用

  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作成（ファイルまたは ":memory:"）

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print("scored:", n_written)
  ```

- 市場レジーム判定

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログスキーマ初期化

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # または既存 conn にスキーマを作る:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究用途、DB の prices_daily / raw_financials が必要）

  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs))
  ```

- データ品質チェックの実行

  ```python
  from kabusys.data.quality import run_all_checks
  from datetime import date

  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- OPENAI_API_KEY (必須 for NLP) — OpenAI API キー
- KABU_API_PASSWORD (必須 for 発注) — kabuステーション API パスワード
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると自動 .env ロードを無効化

設定は .env（および .env.local）に記載するとパッケージ起動時に自動読み込みされます（プロジェクトルートは .git または pyproject.toml で判定）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント / 保存関数
    - pipeline.py — ETL 実行（run_daily_etl 等） / ETLResult
    - etl.py — ETLResult 再エクスポート
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py — 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value ファクター
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - (strategy/, execution/, monitoring/ は __all__ に含まれますが、ここに示されている主要モジュールと連携します)

---

## 運用上の注意

- OpenAI 呼び出しは API 利用料が発生します。テスト時は API 呼び出し部分をモックすることを推奨します（module 内で _call_openai_api を patch 可能）。
- J-Quants API はレート制限やトークン管理が必要です。jquants_client はリトライ・固定間隔スロットリングを内蔵していますが、過負荷に注意してください。
- ETL・DB 書き込みは冪等性を考慮して実装されていますが、バックエンドファイルのバックアップを取る運用が推奨されます。
- 本ライブラリは研究・データ基盤用途が中心です。実際の売買（発注）を行う場合は追加の安全策（ポジション管理・二重発注防止・人的レビュー）を必須にしてください。
- KABUSYS_ENV により live / paper_trading / development の振る舞い分岐が可能です。live を使う場合は設定値と権限管理を十分に確認してください。

---

## 参考・開発ヒント

- 単体テスト / CI を導入する場合、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し環境依存を切り離すと便利です。
- OpenAI 呼び出しや HTTP 操作はネットワークの不確実性があるため、テストではモックを多用してください（関数単位で差し替え可能）。
- DuckDB の executemany は空リストを受け取れない箇所があるため、パラメータの空チェックに注意しています（pipeline / news_nlp 等の実装参照）。

---

README に書かれている操作例はライブラリ内部 API を直接呼ぶ方法です。CLI やワークフローのラッパーは別途用意してください。何か追加でドキュメント化してほしい部分（例: ETL のスケジューリング、Kabuステーション連携の実例、Slack 通知設定）などがあれば教えてください。