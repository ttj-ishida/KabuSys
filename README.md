# KabuSys

日本株向け自動売買・データプラットフォーム用ライブラリ（モジュール群）
（内部利用向けのユーティリティとドメインロジックを含む）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants / RSS）、データ品質チェック、ファクター計算、ニュースによる AI スコアリング、マーケットレジーム判定、監査ログ（発注→約定トレーサビリティ）などを備えたバックエンドライブラリ群です。DuckDB をメインのデータストアとして想定し、OpenAI（gpt-4o-mini）と J-Quants API を利用する機能を含みます。

設計方針の要点:
- ルックアヘッドバイアスに注意（内部で date.today() を不用意に参照しない）
- DuckDB + SQL を中心に実装（外部ライブラリへの過度な依存を抑制）
- API 呼び出しは再試行とフェイルセーフを備える（部分失敗を許容）
- 冪等性（ETL・保存処理）を重視

---

## 主な機能一覧

- 環境変数/設定の自動ロードと管理（kabusys.config）
- J-Quants API クライアント（データ取得・保存・レートリミット付き）
  - 株価日足、財務データ、JPX カレンダー、上場銘柄情報
- ETL パイプライン（差分取得・保存・品質チェック一括実行）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS → raw_news 保存、SSRF/大きさ対策）
- ニュース NLP（OpenAI を使った銘柄ごとのセンチメント ai_score を生成）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースで bull/neutral/bear 判定）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログスキーマの初期化（signal_events / order_requests / executions 等）
- 各種ユーティリティ（カレンダー管理、統計関数、監視設定）

---

## セットアップ手順

前提:
- Python 3.9+ を推奨（型ヒントに Union 代替表記を使用）
- DuckDB、OpenAI SDK、defusedxml 等の依存をインストール

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してインストールしてください。

4. 環境変数の設定
   - プロジェクトルートに `.env` を作成すると自動で読み込まれます（.env.local は override）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   代表的な環境変数（例）
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易例）

ここでは主要なユースケースの例を示します。実行は Python スクリプトから行います。

- DuckDB 接続を取得して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄別センチメント）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数に設定しているなら api_key は省略可
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", count)
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)  # transactional=True 内部で実行
  ```

注意点:
- OpenAI API 呼び出しを行う関数は api_key 引数を受け取る場合があります。環境変数 OPENAI_API_KEY を設定しておくと省略できます。
- ETL やスコア処理は外部 API（J-Quants / OpenAI）に依存するため、テスト時は該当関数をモックすることを推奨します。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（gpt-4o-mini を利用）
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合に 1 を設定

（その他、監視／プロセス制御用の環境変数あり。詳細は kabusys.config のドキュメント参照）

---

## ディレクトリ構成（概観）

以下は src/kabusys 以下の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを LLM でスコアリングして ai_scores へ書き込む
    - regime_detector.py — マーケットレジーム判定（ETF 1321 の MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py  — RSS 取得・前処理・保存
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（Zスコア等）
    - audit.py           — 監査ログテーブル初期化
    - etl.py             — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（Momentum / Value / Volatility）
    - feature_exploration.py — 将来リターン・IC・統計サマリーなど
  - ai、data、research の間で明確に責務分離がなされています（LLM 呼出しはモジュール内で再試行/フェイルセーフを実装）。

---

## 運用上の注意 / ベストプラクティス

- 機微な API キー（OpenAI / J-Quants）は .env などで安全に管理し、リポジトリにコミットしないでください。
- 本ライブラリの ETL / 取得処理はネットワーク I/O を伴い、レート制限や API の一時エラーを考慮しているものの、運用環境では監視と再実行戦略を用意してください。
- DuckDB のスキーマ管理・初期化はアプリ側で制御してください（audit.init_audit_db 等のヘルパーを活用）。
- テスト時は外部 API 呼び出し（network, OpenAI, J-Quants）をモックしてください。モジュール内で API 呼び出しを差し替えられるように設計されています（例: news_nlp._call_openai_api を patch）。

---

もし README に加えて、別途「.env.example」や「requirements.txt」のテンプレートが必要であれば作成します。ご希望があればお知らせください。