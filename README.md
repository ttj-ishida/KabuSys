# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株向けに設計されたデータプラットフォームおよび研究／運用ユーティリティの集合です。主な目的は以下です。

- J-Quants API から株価・財務・マーケットカレンダー等を取得して DuckDB に保存する ETL パイプライン
- RSS を収集してニュース記事を保存するニュースコレクタ
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用のスキーマと初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の特徴として、ルックアヘッドバイアスの防止、API 呼び出しのリトライ／レート制御、DuckDB を用いた冪等保存、外部ライブラリへの過度な依存を避ける（標準ライブラリ優先）などを重視しています。

---

## 主な機能一覧

- data/
  - jquants_client: J-Quants API クライアント（差分取得、ページネーション、保存関数）
  - pipeline: ETL パイプライン（run_daily_etl など）
  - calendar_management: 市場カレンダー管理・営業日判定・夜間更新ジョブ
  - news_collector: RSS 収集・前処理・Raw 保存（SSRF 対策・gzip/サイズ制限）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログテーブルの DDL と初期化（init_audit_schema / init_audit_db）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄別ニュースセンチメントを OpenAI に投げて ai_scores を更新
  - regime_detector.score_regime: ETF (1321) の MA 乖離とマクロセンチメントを合成して market_regime を更新
- research/
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: 環境変数 / .env 読み込みと Settings（自動 .env ロードあり）
- audit, execution, strategy, monitoring 等の公開パッケージ名（パッケージ __all__ に含む）

---

## 必要条件

- Python >= 3.10
- 必要パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml
  - typing-extensions（古い環境で型互換が必要な場合）
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

（プロジェクトの packaging に合わせて requirements.txt / pyproject.toml に依存関係を追加してください）

---

## セットアップ手順

1. リポジトリをチェックアウト

   git clone ...  
   cd <repo>

2. 仮想環境を作成して有効化（推奨）

   python -m venv .venv  
   source .venv/bin/activate  # macOS / Linux  
   .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール（例）

   pip install duckdb openai defusedxml

   開発インストール（ソースを editable にする）:

   pip install -e .

4. 環境変数の準備

   プロジェクトルートに `.env` として必要なキーを設定してください。パッケージは起動時にプロジェクトルート（.git または pyproject.toml）を検出して自動で `.env` / `.env.local` をロードします（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連で使用）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（通知用）
   - SLACK_CHANNEL_ID: Slack チャンネル ID（通知用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視 DB 等、デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_pwd
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 使い方（主なユースケース）

以下は Python インタープリタやスクリプトから直接呼び出す例です。

- 日次 ETL の実行（株価・財務・カレンダー取得＋品質チェック）

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントスコアの計算（OpenAI API 必須）

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")

- 市場レジームの判定（ETF 1321 の MA とマクロニュースを合成）

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ用 DuckDB の初期化

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は内部で呼ばれるため、テーブルが作成されます

- カレンダー更新ジョブ（夜間バッチ）

  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import calendar_update_job

  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")

注意点:
- score_news / score_regime は OpenAI API を呼び出すため、OPENAI_API_KEY を渡すか環境変数を設定してください。
- DuckDB の接続はアプリ側で管理してください。run_daily_etl 等は既存接続を使います。
- API 呼び出しはレート制御・リトライを備えていますが、キーや料金には注意してください。

---

## 簡単な開発ヒント

- 設定の自動ロード: kabusys.config はプロジェクトルートの `.env` / `.env.local` を自動ロードします。テスト時や CI で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のパスデフォルト: settings.duckdb_path は `data/kabusys.duckdb`。必要に応じて DUCKDB_PATH 環境変数で変更可能です。
- OpenAI 呼び出しは `OpenAI` client の chat.completions.create を JSON mode で利用しています。テスト時はモジュール内部の `_call_openai_api` をモックして挙動を差し替えられます。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / .env 管理 (Settings)
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースのセンチメント解析と ai_scores 書き込み
    - regime_detector.py  -- 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py         -- J-Quants API クライアント（fetch / save）
    - pipeline.py               -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py    -- 市場カレンダー管理・営業日ロジック
    - news_collector.py         -- RSS 収集と raw_news 保存（SSRF 対策等）
    - quality.py                -- データ品質チェック（欠損・スパイク等）
    - stats.py                  -- zscore_normalize 等の統計ツール
    - audit.py                  -- 監査ログ DDL と初期化ユーティリティ
    - etl.py                    -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py       -- calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   -- forward returns / IC / summary / rank
  - research/*.py              -- その他リサーチユーティリティ
  - (その他 strategy / execution / monitoring 等のパッケージ名が __all__ に定義されている)

---

## その他・注意事項

- ルックアヘッドバイアスの防止: 本ライブラリは多くの箇所でバックテスト用にルックアヘッドを避ける実装（target_date 未満のデータのみ使用等）になっています。研究用途で関数を呼ぶ際はドキュメント通り target_date を明示してください。
- テスト／モック: OpenAI 呼び出しやネットワーク I/O は内部で交換可能な関数設計になっており、ユニットテスト時はモックが可能です。
- ロギング: settings.log_level を設定してログ出力を調整してください。

---

もし README に追加したい具体的なセットアップ手順（docker-compose 例、CI 設定、サンプル .env.example）や、各モジュールのより詳細な API ドキュメント（関数シグネチャの列挙など）が必要であれば教えてください。