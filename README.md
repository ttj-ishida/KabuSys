# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース NLP（OpenAI）・市場レジーム判定・リサーチ用ファクター計算・監査ログ（発注〜約定トレース）などの機能を持ち、DuckDB をデータレイクとして利用する設計になっています。

---

## 主要な特徴（概要）

- J-Quants API からの差分 ETL（株価 / 財務 / カレンダー）と id/token 管理、レートリミット・リトライ対応
- DuckDB に対する冪等保存（ON CONFLICT DO UPDATE）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）とニュースの NLP スコアリング（OpenAI を利用）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースセンチメント）
- 研究（Research）用ユーティリティ：モメンタム/ボラティリティ/バリュー等のファクター計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（signal / order_request / executions）のテーブル定義と初期化ユーティリティ
- 環境変数/.env による設定管理（自動ロード機能あり）

---

## 機能一覧（主要 API）

- 設定
  - kabusys.config.settings — 環境変数から各種設定を取得
- ETL / データ
  - kabusys.data.pipeline.run_daily_etl — 日次 ETL パイプライン（カレンダー・株価・財務・品質チェック）
  - kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl — 個別 ETL
  - kabusys.data.jquants_client — J-Quants API クライアント（fetch / save / get_id_token 等）
  - kabusys.data.quality — データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks）
  - kabusys.data.news_collector.fetch_rss — RSS 取得 / 正規化 / raw_news への保存に使えるユーティリティ
  - kabusys.data.audit.init_audit_db / init_audit_schema — 監査ログテーブル初期化
  - kabusys.data.calendar_management.* — 営業日判定やカレンダー更新ジョブ
  - kabusys.data.stats.zscore_normalize — Z スコア正規化
- AI（OpenAI）
  - kabusys.ai.news_nlp.score_news — ニュースをまとめて銘柄別センチメント（ai_scores）を作成
  - kabusys.ai.regime_detector.score_regime — 市場レジーム判定（bull/neutral/bear）を market_regime テーブルへ保存
- Research
  - kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value
  - kabusys.research.feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件（推奨）

- Python 3.10+
- 必要 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリを使用）
- インターネット接続（J-Quants / OpenAI を使う場合）
- J-Quants / OpenAI の API キー

（プロジェクト配布に requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 開発中に便利なパッケージ（任意）
   - pip install pytest black isort

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を作成できます（config.py が自動で読み込みます）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

6. 主要な環境変数（必須/任意）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
   - OPENAI_API_KEY (必須 for AI functions) — OpenAI API キー（score_news / score_regime 等）
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
   - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
   - DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH (任意) — SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV (任意) — environment: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（よく使う例）

- 設定取得
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（OpenAI API キーが必要）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査用に別 DB を作成する例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants クライアントを直接使う（トークン管理はライブラリが行います）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  records = fetch_daily_quotes(date_from=date(2026,1,1), date_to=date(2026,3,20))
  ```

注意:
- AI モジュール（news_nlp / regime_detector）は OpenAI に対する呼び出しを行います。API キーが必要で、レスポンスの扱いやレート制限に注意してください。
- 多くの関数は外部 API を呼びます（J-Quants / OpenAI）。テスト時は内部の _call_openai_api や HTTP 部分をモックすることを推奨します。

---

## ディレクトリ構成（重要ファイルの抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数/.env ロードと設定オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコア生成（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py — ETL パイプライン（run_daily_etl 等） / ETLResult
    - quality.py — データ品質チェック
    - news_collector.py — RSS 取得・記事前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - audit.py — 監査ログ DDL と初期化ユーティリティ
    - etl.py — ETLResult 再エクスポート
    - stats.py — zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - research/*（その他）
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートにある想定。パッケージインストール用）

---

## 実装上の注意点 / 設計メモ

- Look-ahead bias を避けるため、内部処理は target_date を明示的に渡し、datetime.today()/date.today() を不必要に参照しない設計です（一部関数では today を使うが ETL 入口で制御）。
- DuckDB に対する INSERT は冪等（ON CONFLICT DO UPDATE）で保存することを前提にしています。
- J-Quants API はレート制限があるため内部に RateLimiter を実装しています。fetch 関数はページネーションに対応しています。
- OpenAI 呼び出しはリトライとサーバーエラー処理を実装しています。テストでは _call_openai_api をモックして振る舞いを制御してください。
- news_collector は SSRF / XML Bomb / gzip bomb 等のセキュリティ対策を入れています（defusedxml 使用、受信サイズ上限、プライベート IP ブロックなど）。

---

もし README に追記したいサンプルスクリプトや CI / Docker / デプロイ手順、あるいは requirements.txt の具体的な内容が必要であれば教えてください。README の文言や例をプロジェクト実態に合わせて調整します。