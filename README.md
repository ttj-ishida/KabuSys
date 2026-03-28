# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォームと自動売買支援ライブラリです。J-Quants API を用いたデータ ETL、ニュース収集・NLP によるセンチメントスコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）機能などを備え、研究（research）や運用（execution）で利用できるユーティリティ群を提供します。

主な設計方針:
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を直接参照しない設計）
- DuckDB を中心としたローカル DB にデータを保存・参照
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える
- 冪等性を重視（ETL / 保存処理は ON CONFLICT で上書き）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API 経由で株価（日次 OHLCV）、財務データ、上場情報、マーケットカレンダーを差分取得・保存
  - run_daily_etl を中心とした日次 ETL パイプライン（品質チェック含む）
  - レートリミッタ、トークン自動リフレッシュ、ページネーション対応、指数バックオフ

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック

- マーケットカレンダー管理
  - JPX カレンダーの差分取得、営業日判定、前後営業日の取得など

- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、gzip 上限チェック）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を合成して市場レジームを判定（score_regime）

- 研究支援（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、統計サマリー、Zスコア正規化ユーティリティ

- 監査ログ（audit）
  - シグナル → 発注 → 約定までのトレーサビリティテーブル（冪等キー・タイムスタンプ等）
  - init_audit_db / init_audit_schema による初期化

- J-Quants クライアント
  - fetch_* / save_* 系ユーティリティ（raw_prices / raw_financials / market_calendar など）
  - レート制御・リトライ・ID トークン管理

---

## セットアップ手順

前提:
- Python 3.9+（typing の機能を利用）
- ネットワーク接続（J-Quants / OpenAI / RSS へのアクセス）

1. リポジトリを取得し、仮想環境を作成・有効化します。

   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（例）。

   ```bash
   pip install duckdb openai defusedxml
   ```

   （上記は最低限の依存。実運用では logging 設定や Slack 連携など別パッケージが必要になる場合があります。）

3. 環境変数を設定します。
   - リポジトリルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただしテスト等で無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須な環境変数（少なくとも以下を設定してください）:

     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD：kabuステーション API パスワード（発注等で利用する場合）
     - SLACK_BOT_TOKEN：Slack ボットトークン（通知利用時）
     - SLACK_CHANNEL_ID：通知先 Slack チャネル ID
     - OPENAI_API_KEY：OpenAI API キー（score_news / score_regime などで使用）

   - その他オプション:
     - KABUSYS_ENV：development / paper_trading / live（デフォルト development）
     - LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
     - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH：監視用 SQLite パス（デフォルト data/monitoring.db）

4. データディレクトリを作成（必要に応じて）。

   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な関数と実行例）

以下は Python REPL / スクリプトからの利用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect が返す接続）を受け取ります。

- DuckDB 接続の作成（設定済みパスの使用例）

  ```python
  from kabusys.config import settings
  import duckdb

  db_path = str(settings.duckdb_path)
  conn = duckdb.connect(db_path)
  ```

- 日次 ETL の実行（run_daily_etl）

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略すると今日になります）
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

  run_daily_etl はカレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順に実行し、ETLResult を返します。

- ニュースセンチメントのスコア化（score_news）

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーを env にセットしておくか api_key を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n_written}")
  ```

  score_news は raw_news と news_symbols を参照して ai_scores テーブルへ書き込みます。

- 市場レジーム判定（score_regime）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

  ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ保存します。OpenAI API キーは環境変数または引数で渡してください。

- 監査ログスキーマの初期化（audit）

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以降、audit_conn を用いて audit テーブルへアクセスできます
  ```

- 研究用ファクター計算（例: モメンタム）

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は dict のリスト: [{"date":..., "code":..., "mom_1m":..., ...}, ...]
  ```

- 設定の確認例

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.env, settings.log_level)
  ```

ログレベルや環境に応じて動作が変わる箇所があるため、設定値は事前に確認してください。

---

## 重要な実装・運用上の注意

- 環境変数自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）を自動検出し、.env / .env.local を順に読み込みます。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定してください。

- OpenAI 呼び出し:
  - news_nlp / regime_detector は gpt-4o-mini を想定し、JSON Mode を用いて厳密な JSON を受け取る前提で実装されています。
  - API 失敗時はフェイルセーフとして部分スコアスキップや既定値（0.0）にフォールバックします。エラーはログに記録されます。

- J-Quants クライアント:
  - rate limit（120 req/min）を守るため固定間隔のスロットリングを実装しています。
  - 401 が返った場合はリフレッシュトークンで ID トークンを自動更新して再試行します。

- ニュース収集:
  - RSS の取得では SSRF 対策（リダイレクト先のスキーム・プライベートアドレスチェック）を実装しています。
  - レスポンスサイズは上限を設け、Gzip 解凍後も上限を再検査します。

- DuckDB 実行時の互換性:
  - 一部の executemany/リストバインドは DuckDB のバージョン差分に対応する実装になっています（空リスト渡しを回避）。

---

## ディレクトリ構成

主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュース NLP（score_news）
    - regime_detector.py             — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（fetch/save）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult 再エクスポート
    - calendar_management.py         — マーケットカレンダー管理
    - news_collector.py              — RSS ニュース収集
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore 等）
    - audit.py                       — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等
    - feature_exploration.py         — forward returns, IC, summary, rank
  - ai/ (上記)
  - research/ (上記)
  - ほか: strategy, execution, monitoring 等のサブパッケージは __all__ に含まれる（コードベース拡張想定）

---

## 開発・貢献

- テスト: 各モジュールは外部 API 呼び出し部分を差し替えやすいよう設計されています（関数の patch / dependency injection がしやすい）。
- コード品質: ログ出力・例外ハンドリング・フェイルセーフを重視しています。PR の際はユニットテストと簡潔なリグレッションチェックをお願いします。

---

README では主要な使い方と注意点をまとめました。より詳細な API 仕様やスキーマ、運用手順（cron/ワーカ設定、Slack 通知等）は別途ドキュメントにまとめることを推奨します。必要であれば README に実運用時の systemd / Kubernetes / Airflow 連携例なども追記します。