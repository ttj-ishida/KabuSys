# KabuSys

KabuSys は日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
J-Quants からのデータ取得（OHLCV / 財務 / 市場カレンダー）やニュース収集、LLM を用いたニュースセンチメント解析、マーケットレジーム判定、ファクター計算、ETL パイプライン、監査ログ（発注〜約定のトレース）など自動売買システム構築に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得 & ETL
  - J-Quants API からの株価日足・財務データ・市場カレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT で上書き）
  - データ品質チェック（欠損・スパイク・重複・日付不整合検出）
  - 日次 ETL パイプライン `run_daily_etl`

- ニュース & NLP / AI
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score を `ai_scores` へ）
  - マクロニュースと ETF（1321）の MA200 乖離を用いた市場レジーム判定（bull/neutral/bear）

- リサーチ（ファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal, order_request, execution を記録する監査テーブルの初期化ユーティリティ
  - DuckDB ベースの監査 DB 初期化関数

- 設定管理
  - .env / .env.local および OS 環境変数から設定を自動読み込み（プロジェクトルート判定）
  - 設定は `kabusys.config.settings` 経由で取得可能

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（typing | union 表記などを使用）
- ネットワークアクセス（J-Quants / OpenAI 等）

1. リポジトリをクローン（またはパッケージソースを取得）
2. 仮想環境作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```
3. 必要パッケージをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```bash
     pip install duckdb openai defusedxml
     # またはパッケージ化されている場合:
     pip install -e .
     ```
   - 実運用ではロギング・監視用の依存等を追加する場合があります。

4. 環境変数 / .env の準備
   プロジェクトルート（.git または pyproject.toml を基準）に `.env` または `.env.local` を配置すると自動で読み込みます（ただし自動読み込みを無効化することも可能）。
   - 自動読み込みを無効化するには:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数:
     - 必須（実運用で使用する場合）
       - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
       - KABU_API_PASSWORD: kabu ステーション API パスワード
       - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）
     - 任意 / 既定値あり
       - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
       - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知を使う場合）
       - DUCKDB_PATH (default: data/kabusys.duckdb)
       - SQLITE_PATH (default: data/monitoring.db)
       - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
       - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
       - KABUSYS_ENV (development | paper_trading | live) — 環境モード
       - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   サンプル .env（最低限の例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベース初期化（監査テーブルなど）
   - 監査用 DuckDB を初期化する:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")  # :memory: も可能
     ```
   - 必要なスキーマはライブラリの関数で生成することを推奨します（`init_audit_schema` など）。

---

## 使い方（簡単な例）

以下は一般的なユースケースの抜粋です。実行は仮想環境内で行ってください。

- 設定値の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)   # Path オブジェクト
  ```

- DuckDB 接続を作って日次 ETL を走らせる
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 AI スコア）の算出
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("regime scoring done:", res)
  ```

- 研究用途のファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注: OpenAI を呼ぶ機能（score_news / score_regime）は API 呼び出しと JSON mode に依存します。テスト環境ではモック化（unittest.mock.patch）を利用して外部呼び出しを差し替える設計になっています。

---

## 自動環境変数読み込みの挙動

- プロジェクトルートは `__file__` から親ディレクトリを辿り `.git` または `pyproject.toml` を検知して特定します。特定できない場合は自動ロードをスキップします。
- 読み込み順序:
  1. OS 環境変数（既存）
  2. .env（プロジェクトルート）
  3. .env.local（.env を上書き）
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 自動ロードでは OS で既に設定されているキーは保護され、.env.local の override は可能ですが保護済みキーは上書きされません。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールと役割の概観（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを集約し OpenAI でセンチメント解析 → ai_scores に保存
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロニュース LLM 得点を合成してレジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py
      - ETL パイプライン（run_daily_etl など）
    - etl.py
      - ETLResult の再エクスポート
    - quality.py
      - データ品質チェック群（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - news_collector.py
      - RSS 取得・前処理・raw_news への保存補助
    - calendar_management.py
      - JPX カレンダー管理・営業日判定
    - audit.py
      - 監査ログテーブル（signal / order_request / executions）の DDL と初期化
  - research/
    - __init__.py
    - factor_research.py
      - momentum/value/volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン・IC・ファクターサマリー等

（実際のプロジェクトルートには pyproject.toml / requirements.txt / tests / などがある想定）

---

## テストとモック化のポイント

- OpenAI 呼び出しは内部で `_call_openai_api` のような関数をラップしており、ユニットテストではこれらを patch してレスポンスを制御できます。
- ネットワークや外部 API（J-Quants / RSS / OpenAI）を使う処理は、テスト時にモック化して副作用を防ぐことを推奨します。
- 環境変数の自動ロードはテストで邪魔になる場合があるため、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して無効化できます。

---

## 運用上の注意

- OpenAI や J-Quants などの API キーは厳重に管理してください。ログ等にキーを出力しないよう注意が必要です。
- 実口座での発注や「live」環境モードを使用する際は、必ず少額での検証や監査ログの確認など運用プロセスを整えてください。
- DuckDB ファイルやローカルデータはバックアップ/アクセス制御を行ってください。
- レート制限（J-Quants: 120 req/min）や OpenAI のレート制限に注意してバッチスケジュールを設計してください。

---

この README はコードベースの主要な使い方と設計上の留意点をまとめたものです。詳細な API（各関数の引数・戻り値）やスキーマはソースコード中の docstring を参照してください。必要であれば、利用者向けの操作手順（起動スクリプト、cron 設定例、Docker 化手順等）を別途追加できます。