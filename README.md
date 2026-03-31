# KabuSys

日本株自動売買・データ基盤ライブラリ（Python）

このリポジトリは日本株向けのデータ取得・品質管理・研究・AIスコアリング・監査ログ等を提供するライブラリ群です。主に DuckDB をデータストアとし、J-Quants / RSS / OpenAI（LLM）など外部サービスと連携する ETL / 解析 / スコアリング機能を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API の例）
- 環境変数 / .env の取り扱い
- ディレクトリ構成

---

プロジェクト概要
- 日本株のデータパイプライン（株価・財務・市場カレンダー）を J-Quants API から差分取得して DuckDB に保存する ETL。
- RSS ベースのニュース収集と LLM を用いたニュースセンチメント（銘柄別）スコアリング。
- ETF（1321）を使った市場レジーム判定（MA200 と マクロニュースセンチメントの合成）。
- データ品質チェック（欠損・スパイク・重複・日付整合性）。
- 監査ログ（シグナル → 発注 → 約定）用のスキーマ初期化ユーティリティ。
- 研究用途のファクター計算・特徴量検証ユーティリティ（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）。

機能一覧（抜粋）
- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants 用クライアント（kabusys.data.jquants_client）: 認証、ページネーション、レート制御、保存関数
- ニュース:
  - RSS 収集（kabusys.data.news_collector）: セキュアな取得・正規化・前処理・冪等保存
  - ニュース NLP スコアリング（kabusys.ai.news_nlp::score_news）: gpt-4o-mini を用いた銘柄別センチメント
- レジーム判定:
  - kabusys.ai.regime_detector::score_regime（ETF MA200 と マクロニュースを合成）
- 研究:
  - kabusys.research: calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- データ品質:
  - kabusys.data.quality: 欠損・スパイク・重複・日付不整合チェック
- 監査ログ:
  - kabusys.data.audit: 監査用テーブルの初期化（init_audit_schema / init_audit_db）
- 設定管理:
  - kabusys.config: 環境変数読み込み（.env/.env.local 自動ロード）、Settings オブジェクト

セットアップ手順（ローカル開発）
1. リポジトリをクローン
   - git clone ...; cd repo

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - 必須（例）:
     - duckdb
     - openai
     - defusedxml
   - 実際の requirements.txt はプロジェクトに応じて用意してください。
   - 例:
     - pip install duckdb openai defusedxml

4. （任意）パッケージを開発モードでインストール
   - pip install -e .

5. データディレクトリを作成（デフォルトの DuckDB パスなど）
   - mkdir -p data

環境変数 / .env の取り扱い
- 設定は環境変数またはプロジェクトルートの .env / .env.local から読み込まれます。
- 自動ロードの仕組み:
  - パッケージ読み込み時にカレントワーキングディレクトリに依存せず、パッケージファイル位置から親ディレクトリを探索して .git または pyproject.toml を検出した位置をプロジェクトルートと判断します。
  - 読み込み順: OS 環境 > .env.local (上書き) > .env（上書きしない）
  - 自動ロードを無効化するには環境変数を設定:
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主な環境変数（必須項目は呼び出し先でチェックされる）
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
  - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector で使用）
  - KABU_API_PASSWORD : kabuステーション API パスワード（required where applicable）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知用
  - DUCKDB_PATH : デフォルト "data/kabusys.duckdb"
  - SQLITE_PATH : 監視用 SQLite データベースパス（例 "data/monitoring.db"）
  - KABUSYS_ENV : development / paper_trading / live（デフォルト development）
  - LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL

簡単な .env.example（参考）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（主要な使い方例）
- 設定オブジェクトの参照
  - from kabusys.config import settings
  - token = settings.jquants_refresh_token

- DuckDB 接続を作って日次 ETL を実行する
  - 例:
    - import duckdb, datetime
      from kabusys.data.pipeline import run_daily_etl
      conn = duckdb.connect(str(settings.duckdb_path))
      result = run_daily_etl(conn, target_date=datetime.date(2026,3,20))
      print(result.to_dict())

- ニューススコアリング（AI）
  - from kabusys.ai.news_nlp import score_news
  - score_news(conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

  戻り値: 書き込み済み銘柄数（int）。OpenAI キーが必要。

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date, api_key=os.environ.get("OPENAI_API_KEY"))

  戻り値: 1（成功）。market_regime テーブルに書き込みます。

- 監査ログ DB の初期化
  - from kabusys.data.audit import init_audit_db
  - conn = init_audit_db("data/audit.duckdb")
  - これにより監査用テーブルとインデックスが作成されます（UTC タイムゾーン固定）。

- 研究用のファクター計算
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
  - results = calc_momentum(conn, target_date)

- データ品質チェック全実行
  - from kabusys.data.quality import run_all_checks
  - issues = run_all_checks(conn, target_date=some_date)
  - issues は QualityIssue のリスト（check_name, table, severity, detail, rows）を返します。

注意点 / 設計上のポイント
- Look-ahead バイアス防止: 内部では datetime.today() / date.today() を不用意に参照せず、明示的な target_date を受け取る設計の関数が多数あります（スコアリング / ETL / 研究）。
- 外部 API 呼び出しはリトライやバックオフを備え、API キーの自動リフレッシュ機能（J-Quants）やレート制御を実装しています。
- DuckDB への書き込みは冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を考慮しています。
- RSS 取得では SSRF 対策・gzip サイズ上限・XML インジェクション対策（defusedxml）など安全に配慮しています。

ディレクトリ構成（主なファイル）
- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / Settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（score_news）
    - regime_detector.py              — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント、保存関数
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL 関連の公開インターフェース
    - news_collector.py               — RSS 取得、前処理、保存
    - calendar_management.py          — 市場カレンダー管理（is_trading_day 等）
    - quality.py                      — データ品質チェック
    - stats.py                        — zscore_normalize など統計ユーティリティ
    - audit.py                         — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary / rank
  - ai/（上記）
  - research/（上記）
  - （戦略 / 実行 / 監視系のパッケージ名は __init__ に含まれるが実装は別モジュールで管理）

ライセンス / 貢献
- この README にはライセンス情報を含めていません。プロジェクトルートの LICENSE を参照してください。
- バグ報告 / 機能追加の提案は Issue を立ててください。

最後に
- 本ライブラリはデータ取得・整備・分析・AIスコアリングを組み合わせており、実取引（特に live 環境）で使用する場合は事前に十分なテストとリスク管理（paper_trading モードの活用）を行ってください。

-- End of README --