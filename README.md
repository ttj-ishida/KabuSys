# KabuSys

KabuSys は日本株のデータプラットフォーム・リサーチ・AI 支援マーケットレジーム判定・監査ログ・ETL を含む日本株自動売買システム向けのライブラリ群です。DuckDB をデータ層に使い、J-Quants API からデータを取得して ETL/品質チェックを行い、OpenAI を用いたニュースセンチメント解析や市場レジーム判定、研究（ファクター計算・特徴量解析）機能を備えます。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境変数 / 設定管理
  - .env / .env.local の自動読み込み（OS 環境変数優先、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の検査（Settings クラス）
- データ取得・ETL
  - J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - daily quotes（株価日足）、financial statements、market calendar の差分取得と DuckDB への冪等保存
  - 日次 ETL パイプライン（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（quality モジュール）
- カレンダー管理
  - 営業日判定・前後営業日の取得・期間内営業日リスト取得・JPX カレンダー差分更新ジョブ
- ニュース収集
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、gzip 制限、XML ハードニング）
  - raw_news / news_symbols への冪等保存を想定
- AI（OpenAI）連携
  - ニュースセンチメント解析（ai.news_nlp.score_news：複数銘柄をバッチで解析、JSON モード利用）
  - 市場レジーム判定（ai.regime_detector.score_regime：ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）
  - API エラーやパース失敗時のフォールバック、リトライロジック
- 研究（Research）
  - momentum/value/volatility 等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Z スコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマ定義と初期化（DuckDB）
  - 監査テーブルの冪等初期化関数（init_audit_schema / init_audit_db）

---

## セットアップ手順（開発環境）

1. Python 3.10+ を用意（typing の union などを利用）。
2. 仮想環境を作成・有効化:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）:
   - pip install duckdb openai defusedxml
   - 追加で logging や urllib は標準ライブラリです。
   - （プロジェクト化する場合）pip install -e .

4. 環境変数 / .env を用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットしてください。

必須の主要環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（必要な場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime でも引数で渡せます）
- KABUSYS_ENV — 実行環境 ("development" / "paper_trading" / "live")（省略時 development）
- LOG_LEVEL — "DEBUG" / "INFO" / "WARNING" / "ERROR" / "CRITICAL"（省略時 INFO）
- DUCKDB_PATH — DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（省略時 data/monitoring.db）

.env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxx
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（代表的な API）

以下はライブラリを直接インポートして使う例です。実行前に必須環境変数を設定してください。

- DuckDB 接続の作成
  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL の実行（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())

- ニュースセンチメントスコア生成（OpenAI を利用）
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

  - score_news は target_date に対応するニュースウィンドウ（前日15:00 JST〜当日08:30 JST）を対象に raw_news / news_symbols を参照して ai_scores を更新します。
  - OpenAI API キーは環境変数 OPENAI_API_KEY、もしくは score_news の api_key 引数で指定可能です。

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))
  - ETF 1321（日経225連動ETF）の MA200 乖離とマクロニュース（LLM による評価）を組み合わせて market_regime テーブルへ書き込みます。

- 監査 DB の初期化（監査専用 DB を作る場合）
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  - transaction=True/False は内部で管理されます。init_audit_db はディレクトリを自動作成します。

- カレンダー操作例
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
  is_trade = is_trading_day(conn, date(2026,3,20))
  next_td = next_trading_day(conn, date(2026,3,20))
  days = get_trading_days(conn, date(2026,3,1), date(2026,3,31))

- 研究用 API
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])

注意点:
- 多くの関数は「Look-ahead bias」を防ぐため、内部で date.today() / datetime.today() を参照しない設計です。必ず target_date を明示するか呼び出し方を理解して利用してください。
- OpenAI 呼び出しは JSON Mode（response_format={"type": "json_object"}）を利用しており、レスポンスパースの保護とリトライ処理が含まれます。API 利用量とレートには注意してください。
- DuckDB の executemany に空のリストを渡すとエラーになるバージョンの互換性を考慮した実装になっています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定読み込みロジック（.env、自動ロード、Settings）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの LLM センチメント解析（score_news）
    - regime_detector.py — ETF + マクロニュースで市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（fetch / save / レート制御・リトライ）
    - pipeline.py        — ETL パイプライン（run_daily_etl 他）
    - etl.py             — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - stats.py           — 統計ユーティリティ（zscore_normalize）
    - quality.py         — データ品質チェック
    - news_collector.py  — RSS ニュース収集（SSRF 対策、XML 安全化）
    - audit.py           — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン / IC / 統計サマリ等

---

## 運用上の注意・ベストプラクティス

- 環境:
  - 本番（live）実行時は KABUSYS_ENV=live を設定してください。is_live / is_paper / is_dev プロパティで挙動を分岐できます。
- セキュリティ:
  - .env ファイルには機密情報（API キー）を含めるため、Git 管理対象から除外してください（.gitignore に設定）。
  - news_collector は SSRF 対策・プライベートホスト検査・レスポンスサイズ制限を実装していますが、運用ネットワークポリシーも併せて設計してください。
- テスト:
  - OpenAI 呼び出しなど外部 API はモックしやすいように内部の _call_openai_api を patch して差し替えられる設計です。
- ログ:
  - LOG_LEVEL を設定してログ出力を制御します。品質チェックや ETL のログを監視して異常検出に役立ててください。
- エラーハンドリング:
  - 多くの箇所でフェイルセーフ（失敗時はスキップ・デフォルト値）を採用しています。重大な失敗はログ・ETLResult.errors に記録されます。

---

この README はコードベースの主要機能と利用方法をまとめたもので、詳細な API 引数や DB スキーマの仕様は各モジュールの docstring を参照してください。質問やサンプルを使った具体的な使い方（例: ETL スケジュール設定、CI 用の簡易コマンド等）が必要であれば教えてください。