# KabuSys

日本株のデータプラットフォーム & 研究・自動売買補助ライブラリ

この README は、提供されたコードベース（kabusys パッケージ）の使い方、セットアップ、主要機能、ディレクトリ構成を日本語でまとめたものです。

---

## 概要

KabuSys は日本株向けのデータ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定、研究用ファクター計算などを提供するライブラリ群です。内部的には DuckDB を主要なデータストアとして使用し、冪等性・フェイルセーフ・ルックアヘッドバイアス対策を考慮した設計になっています。

主な用途例:
- 日次 ETL（株価・財務・マーケットカレンダー）の自動化
- ニュース記事の収集と銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（MA とマクロニュースの組合せ）
- 研究用ファクター（モメンタム・バリュー・ボラティリティ等）の計算
- 監査ログ（シグナル→発注→約定の追跡）用スキーマ初期化

---

## 機能一覧（抜粋）

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務、JPX カレンダー等）
  - 差分 ETL / バックフィル / 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL の統合エントリポイント（run_daily_etl）

- ニュース収集・NLP
  - RSS フィードからのニュース取得（SSRF・gzip・サイズ保護）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメントスコアリング（score_news）
  - マクロニュース + ETF MA200 乖離を使った市場レジーム判定（score_regime）

- 研究（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算
  - IC（Information Coefficient）・ランク付け・統計サマリー
  - z-score 正規化ユーティリティ

- データ管理
  - DuckDB への保存ユーティリティ（冪等保存）
  - 市場カレンダー管理（営業日判定・next/prev/get_trading_days）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）

- 設定管理
  - 環境変数 / .env 自動読み込み（プロジェクトルートの .env / .env.local。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 設定はこちらを通じて参照: `from kabusys.config import settings`

---

## 前提条件

- Python 3.10 以降（PEP 604 型表記などを使用）
- 必要なパッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外はインストールが必要）

※ 依存関係はプロジェクトルートに requirements.txt がある場合はそちらを利用してください。無ければ上記パッケージを個別にインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン（プロジェクトルートに README / pyproject.toml 等がある想定）

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Linux/macOS)
   - .\.venv\Scripts\activate   (Windows PowerShell)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   開発インストール（プロジェクトを編集しながら使う場合）:
   - pip install -e .

4. 環境変数 (.env) を作成
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  → J-Quants のリフレッシュトークン
     - SLACK_BOT_TOKEN        → Slack Bot トークン（Slack 通知を行う機能がある場合）
     - SLACK_CHANNEL_ID       → Slack チャンネル ID
     - OPENAI_API_KEY         → OpenAI API キー（score_news/score_regime で使用）
     - KABU_API_PASSWORD      → kabuステーション API パスワード（必要に応じて）
   - オプション:
     - KABUSYS_ENV            → development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              → DEBUG / INFO / ...
     - KABU_API_BASE_URL      → kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH            → DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            → 監視用 SQLite パス（デフォルト data/monitoring.db）

   サンプル `.env`（プロジェクトルート）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C0123456789
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な関数・ユーティリティ例）

以下は Python REPL やスクリプトから呼ぶ例です。事前に必要な環境変数を設定し、依存パッケージをインストールしておいてください。

- DuckDB 接続の生成例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイルが無ければ作成されます
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # 今日の日付で実行する（必要なら target_date に任意日を渡す）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定しておくか、
  # api_key 引数で渡すこともできます
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  r = score_regime(conn, target_date=date(2026, 3, 20))
  print("OK" if r == 1 else "failed")
  ```

- 監査ログ DB 初期化（監査用 DuckDB を新規に作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # テーブルが作成された接続が返る
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- z-score 正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。環境変数 OPENAI_API_KEY を設定するか、api_key 引数でキーを渡してください。
- ETL / データ保存処理は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）が必要です。スキーマ初期化ロジックはプロジェクト内別モジュールで管理されている想定です（この README に含まれるコードはスキーマの DDL を含むモジュールもあります。必要に応じて初期化処理を実行してください）。

---

## 環境変数自動読み込み

- kabusys.config モジュールはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます（OS 環境変数を上書きしない挙動。`.env.local` は上書き可）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の設定値は Settings プロパティで `_require` によりチェックされ、未設定時は ValueError が発生します（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD など）。

---

## 開発向けメモ / 設計方針（抜粋）

- ルックアヘッドバイアス対策: 日付関連処理（ETL / ニュースウィンドウ / レジーム判定 / ファクター計算）は内部で date.today() を不用意に参照せず、明示的に target_date を受け取る設計になっています。
- 冪等性: 多くの保存関数は ON CONFLICT DO UPDATE を用い、再実行可能な設計。
- フェイルセーフ: API 呼び出し失敗時は完全停止せず、部分的に続行する実装が多い（LLM API 失敗時はスコアを 0 にフォールバックなど）。
- セキュリティ: ニュース収集は SSRF 対策（ホストのプライベート判定、リダイレクト検査）、XML の defusedxml 使用、レスポンスサイズ制限 等が実施されています。

---

## ディレクトリ構成（抜粋）

以下は主要なファイル・モジュールのツリー（実際のリポジトリはさらにファイルがある可能性があります）。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - pipeline.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - calendar_management.py
      - stats.py
      - quality.py
      - audit.py
      - etc.
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他の研究用ユーティリティ）
    - (その他のモジュール)

各モジュールはドキュメンテーション文字列（docstring）で目的・入力・出力・設計方針が明示されています。コード内の docstring を参照するとより詳細な動作が分かります。

---

## トラブルシューティング

- DuckDB にテーブルが無い場合、ETL / その他処理は動かないことがあります。まずスキーマ初期化やサンプルデータ投入を行ってください。
- OpenAI 周りでエラーが出る場合は API キーやレート制限に注意してください。score_* 関数はリトライ・フォールバックロジックを持っていますが、権限の問題や無効なキーは例外になります。
- J-Quants API の認証はリフレッシュトークンを使用して ID トークンを取得します。`JQUANTS_REFRESH_TOKEN` を正しく設定してください。

---

この README はコード内の docstring を元に作成しています。詳細な API や運用手順、CI/CD、プロダクション運用ガイド等は別途ドキュメント（Project の Design docs: DataPlatform.md / StrategyModel.md など）を参照してください。必要であれば README に追加したい実行例や運用手順を教えてください。