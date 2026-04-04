# KabuSys — 日本株自動売買プラットフォーム（README）

日本株のデータ取得・ETL・品質チェック・ファクター算出・ニュースNLP・市場レジーム判定・監査ログを統合するライブラリです。バックテストや実運用（kabuステーション連携）を意識した設計で、DuckDB をデータ層に用いることを前提としています。

主な設計方針：
- ルックアヘッドバイアス防止（date.today()/datetime.today() を直接参照しない等）
- 冪等性（DB 保存は ON CONFLICT / トランザクションで整合）
- フェイルセーフ（外部 API 失敗時は安全側にフォールバック）
- テスト容易性（API 呼び出し箇所は差し替え可能）

---

## 機能一覧
- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー
  - ページネーション・レートリミット・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得、バックフィル、品質チェック（欠損・重複・スパイク・日付整合性）
  - 日次一括実行エントリポイント（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への保存（冪等）
  - SSRF 対策、XML デフューズ処理、サイズ制限
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースセンチメント（score_news）
  - マクロニュース＋ETF MA200 乖離の合成による市場レジーム判定（score_regime）
  - JSON Mode を用いた堅牢なレスポンスパースとリトライ
- 研究用ユーティリティ
  - モメンタム・ボラティリティ・バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- 監査ログ（オーディット）
  - signal_events / order_requests / executions テーブル
  - UUID を使ったトレーサビリティ、監査用 DB 初期化ユーティリティ
- 設定管理
  - .env/.env.local または環境変数から設定を自動読み込み（パッケージ起点で探索）

---

## 動作要件（推奨）
- Python 3.10+
- パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース 等）
- J-Quants のリフレッシュトークン、OpenAI API キー、kabuAPI パスワードなど外部サービスの認証情報

（実際の requirements.txt / pyproject.toml の依存に合わせてインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、開発環境を準備
   - 仮想環境作成（例: venv）
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install --upgrade pip
     ```
2. 必要パッケージをインストール
   - 例：
     ```
     pip install duckdb openai defusedxml
     # 開発時: pip install -e .
     ```
   - 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news 等で使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
     - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
     - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
     - SQLITE_PATH: data/monitoring.db（デフォルト）
     - PID_FILE_PATH, KILL_FLAG_PATH など監視用パス
   - .env の例（プロジェクトルート/.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. DB の初期化（オプション）
   - 監査ログ用 DB を初期化するサンプル:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb 接続オブジェクト
     ```

---

## 使い方（簡易サンプル）

以下は最小限の使い方例です。実運用ではログ設定や例外ハンドリングを適切に追加してください。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの AI スコア）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → env を使用
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマ初期化（既存接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から株価だけ差分取得して保存
  ```python
  from kabusys.data.pipeline import run_prices_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  print(f"fetched={fetched}, saved={saved}")
  ```

---

## 設定と自動 .env ロードについて
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を自動で読み込みします。
  - 読み込み優先: OS 環境変数 > .env.local > .env
  - テストなどで自動ロードを抑止する場合:
    - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定参照例:
  ```python
  from kabusys.config import settings
  settings.jquants_refresh_token
  settings.kabu_api_base_url
  settings.duckdb_path
  ```

---

## 主要ディレクトリ構成（概要）
プロジェクトの主要モジュールと役割：

- src/kabusys/
  - __init__.py — パッケージ初期化、__version__
  - config.py — 環境変数 / 設定管理（.env 自動読み込み・Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄別に集約して OpenAI でスコア化（score_news）
    - regime_detector.py — ETF(1321) MA200 乖離 + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント + DuckDB への保存関数
    - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py — ETL 結果型の再エクスポート
    - news_collector.py — RSS 収集、前処理、raw_news 保存
    - calendar_management.py — JPX カレンダー管理 / 営業日判定
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー、rank 等

---

## ログ・監視
- Settings.log_level によりログレベルを制御します（環境変数 LOG_LEVEL）。
- 実行監視のため pid ファイル・kill フラグ等の設定を Settings で参照可能（PID_FILE_PATH / KILL_FLAG_PATH）。

---

## 注意事項・運用上のポイント
- OpenAI（news_nlp / regime_detector）は外部 API です。API 使用料とレート制限に注意してください。score_news/score_regime はリトライやフォールバックロジックを備えていますが、API キー設定（OPENAI_API_KEY）が必須です。
- J-Quants API の利用にはリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。get_id_token() を通じて id_token を取得し、ページネーション間でキャッシュされます。
- DuckDB スキーマやテーブルはプロジェクト内で使用される前提です。運用前に必要な初期スキーマの作成や監査スキーマの初期化を行ってください。
- 本ライブラリはバックテスト内から外部 API を直接呼び出すことを推奨していません（ルックアヘッドバイアス対策のポリシー参照）。

---

## 貢献・テスト
- テスト環境では環境変数の自動読み込みを抑止し、OpenAI / J-Quants 呼び出しをモックしてテストを行ってください。
  - 例: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - news_nlp/regime_detector の内部 API 呼び出しは差し替え可能（関数を patch することでモック可能）

---

必要であれば、README に実際のコマンドラインツール例（CLI）やユニットテストの実行手順、pyproject/依存情報、サンプル .env.example ファイルなどを追加で作成します。どの情報を優先して追記しますか？