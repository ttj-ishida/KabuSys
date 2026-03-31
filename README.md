# KabuSys

日本株自動売買・データプラットフォーム用ライブラリ KabuSys の README（日本語）。

このドキュメントはコードベース（src/kabusys）をもとにプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けのデータ取得（J-Quants 等）、ETL、データ品質チェック、ニュースセンチメント（LLM）評価、マーケットレジーム判定、リサーチ向けファクター計算、監査ログ（トレーサビリティ）などを行うモジュール群を含むライブラリです。  
主に以下用途を想定しています：

- 日次 ETL による株価・財務・カレンダーの取得・永続化（DuckDB）
- ニュース収集・前処理・LLM による銘柄センチメント算出
- 市場レジーム（bull/neutral/bear）判定（MA と マクロニュースの組合せ）
- 研究（ファクター計算・将来リターン・IC 等）
- 監査ログ用スキーマ初期化（発注/約定トレース）
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上の特徴として、ルックアヘッドバイアスを避ける形で日付に依存する実装、LLM/API 呼び出し時の堅牢なリトライ・フォールバック、DuckDB を主体としたローカルデータ管理があります。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（取得・保存関数、ID トークン管理、レート制限）
  - ニュース収集（RSS -> raw_news、SSRF 対策、テキスト前処理）
  - マーケットカレンダー管理 / 営業日判定ユーティリティ
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）のスキーマ初期化
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースを合わせた score_regime）
  - LLM 呼び出しに対するリトライ・フォールバックロジック
- research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）calc_momentum, calc_volatility, calc_value
  - 特徴量探索ヘルパー（forward returns, IC, summary, rank）
- config
  - 環境変数 / .env の自動ロードと設定ラッパー（settings）

---

## セットアップ手順

以下は開発環境での一般的なセットアップ手順の一例です。プロジェクトが pyproject.toml / setup を持つ前提で説明します。

1. Python 環境を用意
   - 推奨: Python 3.10+（コードは型注釈で新しい構文を利用しています）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限必要そうなパッケージ（コードから推定）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってインストールしてください。
   - 開発用やテスト用の追加パッケージはプロジェクトに依存します。

3. パッケージをローカルにインストール（編集可能モード）
   - pip install -e .

4. 環境変数 / .env の準備
   - ルートプロジェクトに `.env` / `.env.local` を置くと、自動的に読み込まれます（ロード順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必要な環境変数（代表）:
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - OPENAI_API_KEY (推奨) — OpenAI API キー（score_news / score_regime 実行時に指定可能）
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 通知用 Slack
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV — development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）

   - 例 (`.env`):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主要な呼び出し例）

以下は Python スクリプトや REPL から使う際の基本例です。すべて DuckDB 接続（duckdb.connect）を用います。

1. 設定の参照
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)  # Path オブジェクト
   ```

2. DuckDB に接続
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

3. ETL（日次パイプライン）を実行
   ```python
   from kabusys.data.pipeline import run_daily_etl

   # target_date を省略すると今日（date.today()）が使われます
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

4. ニュースを LLM でスコアリング（score_news）
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   # OPENAI_API_KEY を環境変数に設定していれば api_key は省略可能
   n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
   print(f"書き込んだ銘柄数: {n_written}")
   ```

5. 市場レジーム判定（score_regime）
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

6. 監査ログ（Audit）スキーマ初期化
   ```python
   from kabusys.data.audit import init_audit_db
   from kabusys.config import settings

   # 監査用 DB を初期化して接続を取得（ファイルがあれば上書きはしない）
   audit_conn = init_audit_db(settings.duckdb_path)
   ```

7. 研究用ファクター計算
   ```python
   from kabusys.research import calc_momentum, calc_value, calc_volatility
   from datetime import date

   date0 = date(2026, 3, 20)
   momentum = calc_momentum(conn, date0)
   volatility = calc_volatility(conn, date0)
   value = calc_value(conn, date0)
   ```

注意点:
- score_news / score_regime は OpenAI API をコールするため API キー（OPENAI_API_KEY）を環境変数または api_key 引数で与える必要があります。未設定の場合は ValueError を発生させます。
- ETL / J-Quants クライアントは settings.jquants_refresh_token を使用して id_token を取得します。必須です。
- 実行時は DuckDB のスキーマ（テーブル定義）が事前に準備されていることが前提です（ETL 側の保存関数は既定のテーブルを使います）。スキーマ準備スクリプトはプロジェクトに別途ある想定です。

---

## 自動 .env ロードの動作

config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、以下順序で自動読み込みします（OS 環境変数が優先されます）:

1. OS 環境変数
2. .env.local（存在する場合、OS を保護しつつ上書き）
3. .env

自動ロードを無効化する場合:
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

.env のパーサはシェルスタイル（export KEY=val、クォート、コメント）に対応しています。

---

## テスト・モックポイント

- OpenAI 呼び出しは内部で _call_openai_api 関数を使っています。テストでは unittest.mock.patch により下記関数を差し替えられます:
  - kabusys.ai.news_nlp._call_openai_api
  - kabusys.ai.regime_detector._call_openai_api
- news_collector のネットワーク I/O は _urlopen をモックできます:
  - kabusys.data.news_collector._urlopen
- J-Quants クライアント内部の HTTP 呼び出しは urllib を直接使うため、外部呼び出しはモックやテスト用トークンを用いて隔離してください。

---

## ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュール一覧）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (その他 ETL/クライアント関連モジュール)
    - (strategy/ execution/ monitoring 等のパッケージ名が __all__ に含まれている想定)

各モジュールの役割:
- config.py: 環境変数読み込み・Settings クラス
- data/jquants_client.py: J-Quants API クライアント（取得・保存）
- data/pipeline.py: ETL 上位制御（run_daily_etl など）
- data/quality.py: 品質チェック
- data/news_collector.py: RSS 収集・前処理
- ai/news_nlp.py: ニュース -> 銘柄センチメント（LLM）
- ai/regime_detector.py: 市場レジーム判定（MA200 + マクロニュース）
- research/*: ファクター計算・統計解析ユーティリティ

---

## 運用上の注意

- 本ライブラリは実際の発注を行うモジュール（strategy / execution 等）がある想定ですが、誤操作で実際の注文を送らないように live 環境の取り扱いに注意してください（KABUSYS_ENV が 'live' の場合は特に）。
- OpenAI・J-Quants 等の外部 API はレート制限があるため、プロダクション運用時にはキーや呼び出し頻度に注意してください（jquants_client にレート制限ガードあり）。
- DuckDB ファイルのパスや Slack トークンなどの機密情報は .env/local や環境変数で安全に管理してください。
- ETL 実行は idempotent を目指した設計（ON CONFLICT 等）ですが、スキーマやバージョンの変更時にはバックアップを推奨します。

---

必要があれば README に以下を追加できます：
- 詳細な .env.example（フルリスト）
- 実行可能なデータベーススキーマ作成スクリプト例
- CI / デプロイ手順
- よくあるエラーと対処法

追加で欲しい情報（例: .env.example の完全版、pyproject ベースのインストール手順、実運用チェックリストなど）があれば教えてください。