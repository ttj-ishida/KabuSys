# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。本リポジトリはデータ収集（J‑Quants）、DuckDB ベースのデータスキーマ、ETL パイプライン、ニュース収集、特徴量／リサーチ用ユーティリティ、監査ログ（発注〜約定のトレース）などを提供します。

主な設計方針
- DuckDB を中心としたローカルデータベース（分析・履歴保存）
- J‑Quants API からの差分取得（レート制限・リトライ・トークン自動リフレッシュ対応）
- ETL は冪等（ON CONFLICT / DO UPDATE）で安全に再実行可能
- リサーチ系は本番API（注文等）へアクセスしない設計（解析専用）
- ニュース収集での SSRF / XML Bomb 対策や入出力サイズ制限など安全対策実装

バージョン: 0.1.0

---

## 機能一覧

- データ取得・保存
  - J‑Quants API クライアント（株価日足、四半期財務、マーケットカレンダー）
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（raw / processed / feature / execution 層のDDLを定義）

- ETL パイプライン
  - 差分更新（最終取得日を元に未取得分だけ取得）
  - backfill 処理（API 側の後出し修正を吸収）
  - 品質チェック（欠損、スパイク、重複、日付不整合など）

- ニュース収集
  - RSS フィード取得（gzip 対応）、XML パース、記事正規化、URL 正規化、トラッキングパラメータ除去
  - SSRF 対策（リダイレクト先の検証・プライベートIPブロック）
  - raw_news / news_symbols への冪等保存

- リサーチ（Research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー 等）
  - 将来リターン計算、IC（Spearman）の計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ

- カレンダー管理
  - market_calendar を使った営業日判定、前後営業日の取得、カレンダー更新ジョブ

- 監査ログ（Audit）
  - signal_events, order_requests, executions など監査用テーブル、トレーサビリティ保持

---

## セットアップ手順

前提
- Python 3.10 以上（typing の新しい構文を使用）
- duckdb
- defusedxml

1. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール
   最低限必要なライブラリ:
   ```
   pip install duckdb defusedxml
   ```
   （プロジェクトが公開パッケージ化されている場合は requirements.txt / setup.py を利用）

3. 環境変数設定
   プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動読込されます（コードは .git または pyproject.toml をプロジェクトルート判定に使用します）。

   代表的な環境変数:
   - JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
   - KABU_API_BASE_URL: kabu API のベース URL（既定: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - DUCKDB_PATH: DuckDB ファイルパス（既定: data/kabusys.duckdb）
   - SQLITE_PATH: （モニタリング用）SQLite のパス（既定: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（既定: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   自動ロードを無効にする場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ初期化
   Python REPL やスクリプトで以下を実行して初期テーブルを作成します:
   ```python
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   ```

   監査ログ専用に別 DB を作る場合:
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   ```

---

## 使い方（例）

以下は主要ユースケースの簡単な例です。適宜ログ設定や例外ハンドリングを追加してください。

1. 日次 ETL を実行する（市場カレンダー取得 → 株価・財務差分取得 → 品質チェック）
   ```python
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.data.schema import init_schema, get_connection
   from kabusys.data.pipeline import run_daily_etl

   conn = init_schema(settings.duckdb_path)
   # または既存接続を取得: conn = get_connection(settings.duckdb_path)

   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())
   ```

2. ニュース収集ジョブを実行する
   ```python
   from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
   from kabusys.data.schema import init_schema
   from kabusys.config import settings

   conn = init_schema(settings.duckdb_path)
   known_codes = {"7203", "6758", "9984"}  # 既知の銘柄コードセット
   summary = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
   print(summary)
   ```

3. リサーチ用ファクター計算（例: モメンタム）
   ```python
   from datetime import date
   from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
   from kabusys.data.schema import get_connection
   from kabusys.config import settings

   conn = get_connection(settings.duckdb_path)
   target = date(2024, 1, 31)
   mom = calc_momentum(conn, target)
   fwd = calc_forward_returns(conn, target, horizons=[1,5,21])

   ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
   print("IC (mom_1m vs fwd_1d):", ic)

   normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
   ```

4. J‑Quants から日足を直接フェッチして保存
   ```python
   from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
   from kabusys.data.schema import get_connection
   from kabusys.config import settings
   from datetime import date

   conn = get_connection(settings.duckdb_path)
   records = fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
   saved_count = save_daily_quotes(conn, records)
   print("saved:", saved_count)
   ```

---

## 主要モジュール・API の概要

- kabusys.config
  - settings: 環境変数から設定値を取得するオブジェクト（必須環境変数は _require でエラー）
  - 自動でプロジェクトルートの .env / .env.local をロード（無効化可）

- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token / 内部でレート制御・リトライを実装

- kabusys.data.schema
  - init_schema(db_path): DuckDB の全テーブルを作成（冪等）
  - get_connection(db_path)

- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): 日次 ETL 実行
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL 関数
  - ETLResult: 実行結果を表すデータクラス

- kabusys.data.news_collector
  - fetch_rss(url, source): RSS 取得・前処理
  - save_raw_news / save_news_symbols / run_news_collection

- kabusys.data.quality
  - run_all_checks(conn, ...): 欠損、重複、スパイク、日付不整合のチェック
  - QualityIssue クラスで検出結果を集約

- kabusys.research
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（data.stats から再エクスポート）

- kabusys.data.calendar_management
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days
  - calendar_update_job（夜間バッチ用）

- kabusys.data.audit
  - init_audit_schema / init_audit_db: 監査ログ用スキーマ初期化

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要ファイル配置は次の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                          # 環境変数・設定管理
  - data/
    - __init__.py
    - jquants_client.py                # J‑Quants API クライアント
    - news_collector.py                # RSS → raw_news
    - schema.py                        # DuckDB スキーマ定義 / init_schema
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - features.py                      # 特徴量ユーティリティ公開
    - stats.py                         # 統計ユーティリティ（zscore_normalize）
    - calendar_management.py           # market_calendar 管理
    - audit.py                         # 監査ログ（signal/order/execution テーブル）
    - etl.py                           # ETL 公開インターフェース
    - quality.py                       # 品質チェック
  - research/
    - __init__.py
    - factor_research.py               # モメンタム等のファクター計算
    - feature_exploration.py           # 将来リターン計算, IC, summary
  - strategy/                           # 戦略（将来的に実装）
  - execution/                          # 発注系（将来的に実装）
  - monitoring/                         # 監視・メトリクス（将来的に実装）

---

## 注意事項 / 運用上のヒント

- 本ライブラリはデータ取得・保存を行いますが、実際の発注（broker 連携）を行うモジュールは別途安全設計が必要です。実口座での運用前に十分なテストを行ってください。
- settings.jquants_refresh_token は機密情報のため `.env.local`（.gitignore に追加）などで管理してください。
- DuckDB ファイルはバックアップ・ローテーションを考慮してください。大容量のデータを扱う場合はストレージ要件を確認してください。
- run_daily_etl の品質チェックで重大な問題（severity="error"）が返った場合は、原因調査後に手動で修正または ETL ロジックを調整してください。
- news_collector は外部 URL をフェッチするため、ネットワークポリシーやプロキシ設定に注意してください。SSRF 対策は実装されていますが、運用環境に合わせた追加制約が必要なことがあります。

---

必要であれば、README に具体的な CLI 実行例や systemd / cron 用の設定例、ユニットテストの実行手順、依存関係の pinned requirements.txt（バージョン指定）なども追記できます。どの情報を追加しますか?