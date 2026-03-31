# KabuSys

日本株向けのデータプラットフォーム・研究・自動売買補助ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー収集）・データ品質チェック・ニュースセンチメント解析（OpenAI）・市場レジーム判定・監査ログ（オーダー/約定トレース）などの機能を提供します。

目次
- プロジェクト概要
- 主な機能
- セットアップ
- 簡単な使い方（コード例）
- 環境変数（.env）一覧
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株投資システム向けの内部ライブラリ群です。  
主に以下の用途を想定しています。

- J-Quants API から株価/財務/カレンダーの差分取得と DuckDB への保存（ETL）
- raw_prices/raw_financials/raw_news 等のデータ品質チェック
- RSS を使ったニュース収集と記事の前処理
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）とマクロセンチメントを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- 発注・約定までのトレーサビリティを担保する監査ログ（DuckDB）

設計上の特徴：
- ルックアヘッドバイアスを避けるため、内部で date.today()/datetime.today() を不用意に参照しない実装
- 冪等性（DB insert/update）、堅牢なエラーハンドリング、リトライ・バックオフ、レートリミット制御を考慮
- 外部サービス呼び出し（OpenAI / J-Quants）は容易に差し替え可能（テスト用のモックを想定）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch_*/save_*）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days, calendar_update_job）
  - ニュース収集（RSS fetch + 前処理 + DB 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（銘柄別センチメント score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM 評価を組合せる score_regime）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, 統計サマリー 等）
- config.py
  - 環境変数の読み込み（.env / .env.local 自動ロード、上書きルール）と共通設定アクセス（settings オブジェクト）

---

## セットアップ手順

※ 以下は一般的なセットアップ手順の例です。環境や配布形態に合わせて適宜調整してください。

1. リポジトリをクローン／ダウンロード
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール（参考）
   - 本コードで使われている主な依存：
     - duckdb
     - openai
     - defusedxml
   - 例（pip）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt や pyproject.toml を参照してください。

4. 環境変数設定
   - プロジェクトルートに `.env`（と必要なら `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必要な環境変数は後述の「環境変数一覧」を参照してください。

5. DuckDB データベース用ディレクトリ作成（設定によりパスが変わります）
   ```
   mkdir -p data
   ```

---

## 重要な環境変数（.env）

以下はこのコードで参照される代表的な環境変数です。`.env.example` などを参照して設定してください。

- J-Quants / データ取得
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- kabu（発注・約定系）
  - KABU_API_PASSWORD: kabu API パスワード（必須）
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OpenAI / LLM
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime の呼び出しで使用）
- Slack（通知等）
  - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
  - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- データベースパス（デフォルト値あり）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト: INFO）
- 自動 .env ロード制御
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動的な .env 読み込みを無効化できます（テスト用途等）。

注意: settings オブジェクトは環境変数が未設定の場合に ValueError を投げます（必須設定項目）。

---

## 使い方（主要なコード例）

以下はライブラリの代表的な機能の呼び出し例です。実行前に環境変数が正しく設定され、DuckDB の接続先ディレクトリが存在することを確認してください。

- DuckDB 接続の作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（1日分の差分 ETL）を実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア付け（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news は raw_news / news_symbols テーブルを参照して ai_scores に書き込む
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使う
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM を組み合わせる）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ（オーダー／実行）スキーマの初期化（専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って発注ログや約定ログの永続化を行う
  ```

- 研究モジュールの利用（例: モメンタム計算）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs), recs[:3])
  ```

---

## 実行上の注意点 / 設計上のポイント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を起点）を探索して行われます。CI / テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装しています。大量取得時の実行時間に注意してください。
- OpenAI の呼び出しはリトライとバックオフを実装していますが、API 利用料やレートに注意してください。
- DuckDB に対する executemany の仕様（空リスト不可など）を考慮した実装がなされています。SQL 実行時のエラーは呼び出し元に伝播します（ETL ではステップごとに捕捉して継続する設計）。
- LLM を使う処理はレスポンスのバリデーション（JSON パース・スキーマチェック）やフェイルセーフ（失敗時スコアを 0 にする）を行っています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (re-export)
  - news_collector.py
  - calendar_management.py
  - quality.py
  - stats.py
  - audit.py
  - (その他: schema/clients など想定)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
  - (その他)

各モジュールの役割は上記「主な機能一覧」を参照してください。

---

## 追加情報 / トラブルシューティング

- OpenAI のレスポンスが期待した JSON でない場合、score_news / score_regime は失敗をログに残して該当チャンクをスキップまたは 0 にフォールバックします。ログを確認してプロンプトやモデル挙動を検討してください。
- J-Quants の API 認証で 401 が返る場合、get_id_token がリフレッシュを試みます。リフレッシュが失敗する場合は設定済みの JQUANTS_REFRESH_TOKEN を確認してください。
- DuckDB に関する問題（ファイルロック、バージョン差異）は使用している duckdb のバージョンに依存するため、環境での duckdb バージョンを揃えてください。
- テストを行う際は環境変数の自動読み込みをオフにするか、テスト用 .env を用意してください（KABUSYS_DISABLE_AUTO_ENV_LOAD を設定）。

---

必要であれば README を英語版や、CI/開発環境向けの実行例（Docker / GitHub Actions）付きで拡張できます。どの部分を詳しく出力するか指定してください。