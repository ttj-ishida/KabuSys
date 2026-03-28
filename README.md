# KabuSys

日本株向けのデータプラットフォーム兼研究・自動売買基盤のコアライブラリです。  
J-Quants や RSS ニュース、OpenAI を用いたデータ取得・前処理・AIスコアリング・ETL・監査ログなどの機能を提供します。  
本リポジトリはトレード実行まで含む構成を想定していますが、モジュールはデータ取得・研究用途と運用用途を分離して実装されています。

---

## 主な概要

- データ収集（J-Quants API 経由の株価・財務・上場情報、RSS ニュース）
- ETL（差分取得 / バックフィル / 品質チェック）
- ニュースの LLM（OpenAI）による銘柄センチメント算出（ai.news_nlp）
- 市場レジーム判定（ETF の MA とマクロニューススコアの合成）（ai.regime_detector）
- 研究用ファクター計算（momentum / value / volatility 等）（research）
- データ品質チェック（欠損・重複・スパイク・日付整合性）（data.quality）
- 監査ログ（signal → order_request → execution のトレーサビリティ）（data.audit）
- DuckDB を中心としたローカル DB 管理（設定可能なパス）

---

## 機能一覧（抜粋）

- kabusys.config: .env / 環境変数のロードと設定ラッパー
  - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む（無効化可）
- kabusys.data.jquants_client: J-Quants API クライアント（取得・保存・認証・レートリミット・リトライ）
- kabusys.data.pipeline: 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ（prices / financials / calendar）
- kabusys.data.quality: データ品質チェック（run_all_checks）
- kabusys.data.news_collector: RSS 取得・前処理（SSRF 対策、トラッキング除去、サイズ制限）
- kabusys.ai.news_nlp: ニュースを銘柄別にまとめて OpenAI へ送信し ai_scores テーブルへ書込む（score_news）
- kabusys.ai.regime_detector: ETF とマクロニュースから市場レジームを判定して market_regime テーブルへ書込む（score_regime）
- kabusys.research: ファクター計算 / 将来リターン / IC・統計サマリー等
- kabusys.data.audit: 監査用テーブル定義と初期化ヘルパー（init_audit_db / init_audit_schema）

---

## 動作要件（概略）

- Python 3.10 以上（型アノテーションの union 表記などを利用しています）
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS フィード）

実際の運用ではパッケージ管理（requirements.txt / poetry 等）を用意してください。

---

## 環境変数（主なもの）

必須（少なくとも ETL / AI 機能を動かす場合）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- KABU_API_PASSWORD: kabu ステーション API のパスワード（取引系で使用）
- SLACK_BOT_TOKEN: Slack 通知の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知先のチャネル ID

任意 / デフォルトあり:

- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live; デフォルト: development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:

- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（例）

1. Python と依存パッケージのインストール（例: virtualenv / venv を推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

   （実際の運用では requirements.txt / poetry をご利用ください）

2. プロジェクトルートに `.env` を作成（.env.example を参考に）

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

3. DuckDB の初期化（監査用 DB を作る例）

   Python REPL やスクリプトで:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # これで監査ログ用テーブル群が作成されます
   conn.close()
   ```

4. ETL を実行してデータを取得・保存する（簡易例）

   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   conn.close()
   ```

5. OpenAI を利用したニューススコアリング（例）

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
   print("ai_scores written:", n_written)
   conn.close()
   ```

6. レジーム判定（例）

   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を使用
   conn.close()
   ```

---

## 使い方のポイント / 注意事項

- Look-ahead バイアス対策
  - 多くの関数は内部で date.today() を参照せず、呼び出し側が明示的に target_date を渡す設計です。バックテスト・研究用途では target_date を明示して使用してください。

- OpenAI の呼び出し
  - score_news / score_regime は OpenAI の JSON Mode を使う想定です。API キーは関数引数 (`api_key`) または環境変数 `OPENAI_API_KEY` で渡してください。
  - OpenAI の呼び出しで失敗した場合はフォールバック動作（スコア=0）をする実装が多く、堅牢性を重視しています。

- J-Quants API
  - jquants_client は自動リフレッシュ・レート制御・リトライを実装しています。J-Quants 用の `JQUANTS_REFRESH_TOKEN` を `.env` に設定してください。

- ニュース収集
  - RSS の処理は SSRF 防止やサイズ上限、トラッキング除去など安全対策を実装済みです。独自ソースを追加する場合はソースの整合性に注意してください。

- DB 書き込みは基本的に冪等（ON CONFLICT を利用）を重視していますが、運用時のトランザクション設計は呼び出し側での管理が必要な場合があります。

---

## 主要な公開 API（抜粋）

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)

- AI / NLP
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None) -> int
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None) -> int

- 研究
  - kabusys.research.calc_momentum(conn, target_date)
  - kabusys.research.calc_volatility(conn, target_date)
  - kabusys.research.calc_value(conn, target_date)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)

- カレンダー / ヘルパー
  - kabusys.data.calendar_management.is_trading_day(conn, d)
  - next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job(conn, lookahead_days=...)

- 監査ログ
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)
  - kabusys.data.audit.init_audit_db(db_path)

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数と設定の管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを銘柄毎に集約し OpenAI でスコア化
    - regime_detector.py     — MA とマクロニュースの合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント・保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - news_collector.py      — RSS 取得と前処理
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ / 初期化
    - stats.py               — 汎用統計ユーティリティ（zscore 正規化等）
    - etl.py                 — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — 将来リターン, IC, 要約統計 等

（上記は主なファイルの抜粋です。実際のプロジェクトではさらにモジュールが存在します。）

---

## 開発・運用上の注意

- シークレット管理は必ず安全に行ってください（.env を Git 管理しない、CI シークレット利用など）。
- 本コードは ETL / 研究用途と取引実行を分離していますが、実際に「ライブ取引」を行う際は十分なテストとリスク管理（紙トレード→ペーパートレード→ライブ）を行ってください。
- DuckDB のバージョンや OpenAI SDK バージョンに依存する箇所があるため、運用環境でのバージョン管理を推奨します。
- ロギングレベルや KABUSYS_ENV によって挙動（ログ出力や安全チェック）を切り替えられます。

---

必要であれば README に以下を追加できます：
- フルな requirements.txt / poetry 設定例
- .env.example ファイルテンプレート
- CI/CD や定期実行（cron / GitHub Actions）での ETL ワークフロー例
- 各テーブルスキーマのドキュメント（DuckDB DDL 抜粋）

追加の要望があれば教えてください。