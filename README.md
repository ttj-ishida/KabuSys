# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ収集）、ニュース収集・NLP（OpenAI 経由のセンチメント）、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたモジュール群です。主な目的は以下です。

- J-Quants API からの株価・財務・市場カレンダーの差分取得と DuckDB への蓄積（ETL）
- RSS を用いたニュース収集と前処理 → OpenAI（gpt-4o-mini）を用いた記事／銘柄ごとのセンチメント付与
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution の追跡）用スキーマ初期化ユーティリティ

設計上の特徴：
- DuckDB を中心に SQL + Python で処理（外部ライブラリへの依存を最小化）
- Look-ahead バイアス回避の配慮（内部で date.today()/datetime.today() を直接使わない等）
- 冪等性（ON CONFLICT / UPSERT）やリトライ／バックオフ、API レート制御を備える
- セキュリティ考慮（RSS の SSRF 検査、XML の安全パース等）

---

## 機能一覧（抜粋）

- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: トークン管理、ページネーション、保存関数
- ニュース関連
  - RSS フェッチと前処理（kabusys.data.news_collector）
  - ニュースセンチメントスコア（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - kabusys.ai.regime_detector.score_regime（MA200 とマクロニュースを合成）
- 研究ツール
  - ファクター計算（kabusys.research.*）: calc_momentum, calc_value, calc_volatility
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（kabusys.data.stats.zscore_normalize）
- データ品質・カレンダー管理
  - market_calendar 管理、is_trading_day / next_trading_day 等（kabusys.data.calendar_management）
  - 品質チェック（kabusys.data.quality.run_all_checks）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db（kabusys.data.audit）

---

## セットアップ手順

前提
- Python 3.9+（typing の記法に合わせてください）
- DuckDB（Python パッケージ duckdb）を使います
- OpenAI の Python SDK（openai）を利用する箇所があります

1. リポジトリをクローン・インストール（編集開発向け）
   - pip editable install（プロジェクトに setup/pyproject がある想定）
     pip install -e .

2. 依存パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （必要に応じて他の依存を追加）
   例:
     pip install duckdb openai defusedxml

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（kabusys.config）。
   - 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`

必須環境変数（少なくとも使いたい機能に応じて設定）

- J-Quants / データ ETL
  - JQUANTS_REFRESH_TOKEN
- kabuステーション（発注系）
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- Slack 通知
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- OpenAI
  - OPENAI_API_KEY（score_news / score_regime の引数で代替可）
- システム設定
  - KABUSYS_ENV (development | paper_trading | live) — デフォルトは development
  - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) — デフォルト INFO
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト data/monitoring.db）

例 .env（必要最小限）
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
    SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxx
    SLACK_CHANNEL_ID=C01234567
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方（代表例）

以下は Python スクリプトや対話環境での利用例です。いずれも DuckDB 接続を作成して渡します。

- DuckDB 接続例
    from datetime import date
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントの付与（前日15:00 JST ～ 当日08:30 JST のウィンドウ。target_date は評価日）
    from kabusys.ai.news_nlp import score_news
    n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"書き込み銘柄数: {n_written}")

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 03, 20), api_key="sk-...")

- 研究用ファクター計算の例
    from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    mom = calc_momentum(conn, date(2026, 3, 20))
    vol = calc_volatility(conn, date(2026, 3, 20))
    val = calc_value(conn, date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を別ファイルで用意する場合）
    from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # init_audit_db はスキーマを作成し UTC タイムゾーンを設定します

- カレンダー更新ジョブ
    from kabusys.data.calendar_management import calendar_update_job
    updated = calendar_update_job(conn, lookahead_days=90)
    print(f"保存レコード数: {updated}")

注意点:
- score_news / score_regime は OpenAI キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は内部で datetime.today() を直接参照しない設計（look-ahead バイアス防止）です。target_date を明示して実行することを推奨します。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py  — 環境変数処理と Settings
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM スコア付与（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存関数
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETL 型の再エクスポート（ETLResult）
  - calendar_management.py— カレンダー判定・更新ジョブ
  - news_collector.py     — RSS 取得と前処理
  - stats.py              — zscore_normalize 等の統計ユーティリティ
  - quality.py            — データ品質チェック
  - audit.py              — 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py    — calc_momentum / calc_value / calc_volatility
  - feature_exploration.py— calc_forward_returns, calc_ic, factor_summary, rank

（上記は抜粋。実装済みのユーティリティや補助モジュールが含まれます）

---

## ベストプラクティス・運用上の注意

- 環境ごとの切り替えには KABUSYS_ENV を使用（development / paper_trading / live）。
- 本番運用（live）では is_live フラグにより安全処理を切り替える実装を検討してください。
- ETL 実行はバッチ化して cron / Airflow 等でスケジュールすると良いです。run_daily_etl は idempotent な設計を心がけています。
- OpenAI の利用はコスト・レイテンシを考慮してバッチ実行（news_nlp は銘柄をチャンク処理）してください。
- RSS の取得では SSRF・XML 攻撃・大容量レスポンスに対する防御を実装済みですが、運用時も信頼できるフィードのみを追加することを推奨します。
- データ品質チェック（quality.run_all_checks）の結果は ETLResult に集約されます。重大なエラーがあれば自動停止やアラートを設定してください。

---

## トラブルシューティング

- .env が読み込まれない
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認。自動検索はプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。
- OpenAI 呼び出しでエラーが出る（RateLimit 等）
  - score_news / score_regime はリトライとバックオフを実装しています。頻発する場合は呼び出し頻度を下げるかバッチサイズを調整してください。
- J-Quants API の 401
  - jquants_client はリフレッシュトークンから id_token を再取得するロジックがあります。JQUANTS_REFRESH_TOKEN の値を確認してください。
- DuckDB 操作でエラーが出る
  - スキーマが存在しない場合は ETL でテーブル作成処理が必要です。audit.init_audit_db/ init_audit_schema のような初期化ユーティリティを活用してください。

---

## 開発に関する補足

- ユニットテストの際は外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックしてください。モジュール内で _call_openai_api や _urlopen を差し替えられるように設計されています。
- DuckDB への executemany に空リストを渡すとエラーとなるバージョンがあるため、実装では空チェックを行っています。

---

必要に応じて README に具体的な例や CI / デプロイ手順、requirements.txt の内容、DB スキーマ（DDL）サンプルなどを追記できます。どの項目を詳しく追加しましょうか？