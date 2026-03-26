# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得 → DuckDB 保存）、ニュースセンチメント（OpenAI）による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注・約定トレース）などの機能を提供します。

---

## 主な機能

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・リトライ・レート制御対応）。
  - DuckDB に冪等保存（ON CONFLICT DO UPDATE）し品質チェックを実行。
- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策・トラッキングパラメータ除去・前処理）。
  - OpenAI（gpt-4o-mini）を使った銘柄単位のニュースセンチメント集約（ai_scores への書き込み）。
- 市場レジーム判定
  - ETF 1321（日経225連動）200日移動平均乖離 + マクロニュースセンチメントの合成による日次レジーム判定（bull / neutral / bear）。
- 研究用ツール
  - モメンタム / ボラティリティ / バリュー等のファクター計算。
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー、Zスコア正規化ユーティリティ。
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出。品質チェックは集約して結果を返す。
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 のトレーサビリティを保証する監査スキーマの初期化・管理。
- 設定管理
  - .env ファイルまたは環境変数からの設定読み込み（プロジェクトルート検出、.env/.env.local の優先順）。

---

## 必須環境変数（例）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- OPENAI_API_KEY — OpenAI API キー（news / regime スコアリングで使用）

任意 / デフォルト:
- KABUSYS_ENV — 環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: `data/kabusys.duckdb`）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（`1` をセット）

.config.Settings に定義されているプロパティ名と環境変数名を参照してください。

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. パッケージをインストール
   ```
   pip install -e .
   ```

4. .env の作成
   - プロジェクトルートに `.env` を作成し、必要な環境変数を設定します（上の必須環境変数を参照）。
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=your_openai_api_key
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=...
     ```

   - 自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（例）

以下は簡単な Python スクリプト例です。適切な環境変数と DuckDB ファイルパスを用意してください。

- 日次 ETL の実行（run_daily_etl）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OpenAI API キーは環境変数 OPENAI_API_KEY に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written} codes")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用 DuckDB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn を使って監査テーブルにアクセス・書き込みが可能になります
  ```

注意:
- OpenAI 呼び出しは API 費用が発生します。テスト時は該当関数をモックすることを推奨します。
- run_daily_etl は J-Quants からのデータ取得を行います。J-Quants が提供する API トークンが必要です。

---

## よく使う API / 関数

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...) → ETLResult
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別ジョブ）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.audit
  - init_audit_schema(conn)
  - init_audit_db(path)
- kabusys.research
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary
- kabusys.data.stats
  - zscore_normalize(records, columns)

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 / 設定の読み込みと Settings クラス
- ai/
  - __init__.py
  - news_nlp.py — ニュース→銘柄センチメントスコア付与（OpenAI）
  - regime_detector.py — 市場レジーム判定（ma200 + マクロニュース）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定など）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - jquants_client.py — J-Quants API クライアント（取得・保存機能）
  - news_collector.py — RSS ニュース収集
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ初期化・ユーティリティ
  - etl.py — ETLResult の公開（再エクスポート）
- research/
  - __init__.py
  - factor_research.py — ファクター計算（モメンタム・ボラ等）
  - feature_exploration.py — 将来リターン・IC・統計サマリー等
- monitoring/ (※ここには監視用ロジックが入る想定)
- execution/ (※発注実装はここに入れる想定)
- strategy/ (※戦略ロジックはここに入れる想定)

---

## 設計上の注意点

- Look-ahead bias（データの未来参照）を避ける設計が各モジュールに反映されています（datetime.today() を直接参照しない、データ取得時に対象日未満のデータのみ参照する等）。
- OpenAI・J-Quants への呼び出しはリトライ・バックオフ・フェイルセーフを備えています。API 失敗時に処理継続する設計箇所が多くあります（ログにより問題を検出）。
- DuckDB への保存は冪等（ON CONFLICT）になっているため、再実行が安全です。
- テスト時は外部 API 呼び出し関数をモックしてください（例: kabusys.ai.news_nlp._call_openai_api 等）。

---

## テスト・開発メモ

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI / テスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効にできます。
- OpenAI 呼び出し部分は JSON モードの応答想定および厳密なパースを行っています。テストではレスポンス整形の差分に注意してください。
- news_collector には SSRF / Gzip bomb 等の対策が実装されています。外部フィードを追加する際はホスト検証に注意してください。

---

## ライセンス / 貢献

（リポジトリにライセンス情報・CONTRIBUTING を追加してください）

---

README に記載してほしい追加情報（例: 実行スクリプト、CI 設定、Docker イメージ、サンプル .env.example 等）があれば教えてください。必要に応じてサンプル .env.example や運用手順（cron / Airflow でのスケジューリング例）も追記します。