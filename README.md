# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
J-Quants からのデータ取得・ETL、データ品質チェック、マーケットカレンダー管理、監査ログ、ファクター計算、ニュースの NLP スコアリング（OpenAI 利用）など、研究・運用に必要な機能を提供します。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local を自動読み込み（必要に応じて無効化可能）
  - 必須環境変数の取得チェック、各種パスや閾値の設定を提供

- データ ETL（J-Quants）
  - 株価日足、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制御・リトライ・トークン自動リフレッシュ
  - DuckDB への冪等的保存（ON CONFLICT DO UPDATE）

- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合（未来日付・非営業日）の検出
  - QualityIssue による問題集約

- マーケットカレンダー管理
  - JPX カレンダー更新ジョブ、営業日判定、前後営業日の取得等
  - DB データがない場合は曜日ベースでフォールバック

- 監査ログ（トレーサビリティ）
  - シグナル→発注→約定までを UUID 階層で追跡する監査テーブル定義・初期化
  - DuckDB 初期化ユーティリティ（UTC タイムゾーン固定）

- 研究用ユーティリティ
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ

- ニュース収集・NLP（OpenAI）
  - RSS 取得／正規化／SSRF 対策／raw_news への保存支援
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメントスコアリング
  - マクロニュース + ETF MA200 ベースで市場レジーム判定（bull/neutral/bear）

---

## セットアップ手順

1. Python 環境を用意（推奨: 3.10+）

2. リポジトリをクローンしてインストール
   - 開発環境で編集する場合:
     - pip install -e .（プロジェクトがパッケージとして構成されている前提）
   - あるいは必要な依存を直接インストール:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは pyproject.toml / requirements.txt に基づいてインストールしてください。

3. 環境変数の設定
   - プロジェクトルートに `.env`（およびオプションで `.env.local`）を置くと自動で読み込まれます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を利用する場合）
   - KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
   - KABUSYS_ENV: environment: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

4. データディレクトリ作成
   - DUCKDB_PATH の親ディレクトリ等を作成しておく（例: data/）。

---

## 使い方（主な利用例）

以下はモジュール呼び出し例です。実行前に環境変数を設定してください（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）。

- 設定読み取り
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作って日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str("data/kabusys.duckdb"))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written scores: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査テーブルの初期化（監査用 DB を新規に作成）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # または別のパス
  ```

- ETL の個別ジョブを呼ぶ（例: 株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  ```

注意点:
- OpenAI 呼び出し、J-Quants API 呼び出しは外部ネットワーク依存のため、実行前に各 API キー・トークンを正しく設定してください。
- DuckDB 側のテーブルスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）が存在することが前提です。スキーマ初期化はプロジェクトの別モジュールまたはスキーマ定義スクリプトで行ってください。
- テストで自動 .env 読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 開発 / テストに関するヒント

- モジュールは外部 API 呼び出し部を差し替えやすく設計されています（例: news_nlp._call_openai_api を unittest.mock.patch で差し替え）。
- ETL は部分的失敗に強く、各ステップで例外をキャッチして結果オブジェクトにエラー情報を格納します。
- DuckDB の executemany は空リストに対応していないバージョンがあるため、空チェックが各所で入っています。

---

## ディレクトリ構成（主要ファイル）

（リポジトリのルートが src 配下パッケージ構成の典型である想定）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
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
    - (他の data 関連ユーティリティ)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research から参照する data.stats 等

各モジュールは上記の役割に沿って責務が分離されています。詳細は各ファイルの docstring を参照してください。

---

## ライセンスと貢献

- 本 README はコードベースの概要・使い方をまとめたものです。実運用する際は各 API の利用規約・料金体系に注意してください。
- 貢献する場合は、コードスタイル、一貫したロギング、外部通信のエラーハンドリング方針に従ってください。

---

何か追加で README に載せたい情報（例: 実際の .env.example のテンプレート、初期スキーマ作成スクリプト、CI 流れなど）があれば教えてください。必要に応じてサンプル .env.example や起動スクリプト例も作成します。