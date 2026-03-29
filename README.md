KabuSys — 日本株自動売買／データプラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
主な目的は以下のとおりです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集（RSS）と LLM によるニュースセンチメント算出
- 市場レジーム判定（MA と LLM を組み合わせた手法）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ 等）
- データ品質チェック、監査ログ（トレーサビリティ）管理
- DuckDB を用いたローカルデータベース保存と idempotent な保存ロジック

このリポジトリは「データ収集 → 品質検査 → 解析（研究） → シグナル／監査」までのパイプライン実装を提供します。発注（ブローカー）連携用の抽象も想定されていますが、実際の発注接続は別実装です。

主な機能一覧
-------------
- ETL
  - 日次差分 ETL（株価 / 財務 / カレンダー）: kabusys.data.pipeline.run_daily_etl
  - J-Quants API クライアント（認証・リトライ・レート制御含む）
- データ管理
  - DuckDB に対する保存関数（生データ raw_* テーブル、market_calendar 等）
  - 監査ログスキーマの初期化（audit テーブル群・インデックス）
- ニュース
  - RSS フェッチ（SSRF 防止、gzip 上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存設計
- AI（LLM）関連
  - ニュースセンチメント集約 score_news (gpt-4o-mini)
  - 市場レジーム判定 score_regime（1321 MA200 乖離 と マクロニュース）
  - エラー時にフォールバックする堅牢なリトライ・パースロジック
- 研究（Research）
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー
- 品質チェック
  - 欠損、重複、スパイク、日付不整合チェック（quality モジュール）
- ユーティリティ
  - クロスセクション Z スコア正規化、カレンダー管理（営業日判定、next/prev）

セットアップ手順
----------------

前提
- Python 3.10 以上を想定（型注釈に union 型などを使用）。
- DuckDB が利用できること（Python パッケージ duckdb）。
- OpenAI API を利用する場合は OpenAI の API キーが必要。

インストール（開発）
1. リポジトリをクローンしてプロジェクトルートへ移動。
2. 仮想環境を作成して有効化（任意）:
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)
3. パッケージをインストール:
   - 推奨: プロジェクトが pyproject.toml を持つ想定で editable install:
     - pip install -e .
   - 依存最低例（必要に応じて追加）:
     - pip install duckdb openai defusedxml

環境変数 / .env
- 設定は環境変数またはプロジェクトルートの .env / .env.local から自動読み込みされます。
- 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。

重要な環境変数（主な一覧）
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD : kabuステーション API パスワード（必須: 発注連携時）
- KABU_API_BASE_URL : kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID : Slack 通知設定
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH : 監視用 SQLite のパス（デフォルト data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト development）
- LOG_LEVEL : DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY : OpenAI API キー（score_news / score_regime 実行時に使用）

（例 .env の断片）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

使い方（代表例）
----------------

共通: 設定読み込み
- Python からは kabusys.config.settings を参照してください。自動で .env をルートから読み込むように設計されています。

例: DuckDB 接続と設定取得
- from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

ETL を日次で実行（run_daily_etl）
- from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date=None → 今日（カレンダー調整あり）
  print(result.to_dict())

ニュースセンチメント算出（score_news）
- from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings
  import duckdb
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date = スコア生成日（例: date(2026,3,20)）
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を参照
  print(f"written {n_written} scores")

市場レジーム判定（score_regime）
- from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20))

監査ログスキーマ初期化
- from kabusys.data.audit import init_audit_db, init_audit_schema
  # DB ファイル作成 + スキーマ適用
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  # ある接続に対してスキーマだけ適用する場合:
  # init_audit_schema(conn, transactional=True)

ニュース RSS 取得（個別ユーティリティ）
- from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])

研究向けユーティリティ（例）
- from kabusys.research.factor_research import calc_momentum
  result = calc_momentum(conn, target_date=date(2026,3,20))
  # zscore_normalize は kabusys.data.stats.zscore_normalize

ロギング / 環境モード
- settings.log_level でログレベルを検証できます。
- settings.env により挙動（paper_trading / live / development）を切り替えできます。
- 本番では settings.is_live を参照して発注階層を有効化してください。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py                 — パッケージ宣言、バージョン
- config.py                   — 環境変数/.env 読み込みと Settings
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメント算出（OpenAI 呼び出し、チャンク化、検証）
  - regime_detector.py        — マーケットレジーム判定（MA200 + LLM 合成）
- data/
  - __init__.py
  - jquants_client.py         — J-Quants API クライアント（認証・リトライ・保存関数）
  - pipeline.py               — ETL パイプライン（run_daily_etl 他）
  - etl.py                    — ETLResult のエクスポート
  - news_collector.py         — RSS 収集（SSRF 対策・正規化）
  - calendar_management.py    — 市場カレンダー管理（営業日判定等）
  - stats.py                  — zscore_normalize 等の統計ユーティリティ
  - quality.py                — データ品質チェック
  - audit.py                  — 監査ログ（テーブル定義・初期化）
- research/
  - __init__.py
  - factor_research.py        — モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py    — 将来リターン計算、IC、統計サマリー

設計上の注意点 & 運用メモ
------------------------
- Look-ahead バイアス防止: 多くの関数は内部で date.today() を参照せず、呼び出し側が target_date を渡すことを想定しています。ETL の場合は run_daily_etl が内部で today を使いますが、研究用途では明示的に日付を渡してください。
- 環境変数自動読み込み: プロジェクトルートの .git または pyproject.toml を探して .env/.env.local をロードします。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し: レスポンスは JSON mode を使って厳密にパースしています。API エラー・パース失敗時はフォールバック（スコア 0.0 など）し、処理継続性を重視しています。
- DuckDB 互換性: 一部の executemany 空リストの扱いに注意（実装中に明示的チェックあり）。
- セキュリティ: RSS フェッチは SSRF 対策、gzip サイズチェック、トラッキングパラメータ除去を実施。J-Quants クライアントは rate limiting を実装。

貢献 / テスト
--------------
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使い、必要な設定はテスト用に注入してください。
- OpenAI / J-Quants 呼び出し部分は差し替え可能（内部の _call_openai_api や _urlopen をモックしてテスト可能）。

最後に
------
この README はコードベースに基づく概要と利用ガイドです。実運用前に .env（または環境変数）と DuckDB スキーマ（必要な raw_* テーブルや ai_scores, market_regime など）が適切に準備されていることを確認してください。質問や改善提案があればお知らせください。