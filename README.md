KabuSys — 日本株自動売買／データプラットフォーム
======================================

概要
----
KabuSys は日本株向けのデータプラットフォームおよび自動売買補助ライブラリです。  
J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）、RSS ベースのニュース収集、ニュースの LLM によるセンチメント評価、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを備えています。  
本 README はリポジトリの主要コンポーネント、セットアップ方法、代表的な使い方、ディレクトリ構成を示します。

主な機能一覧
-------------
- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務（四半期）データ、JPX カレンダーを差分取得・保存（duckdb）
  - 差分更新・バックフィル、リトライ・レート制御、ID トークン自動更新
- ニュース収集
  - RSS 取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存
- ニュース NLP
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（score_news）
  - マクロニュースの LLM 評価を使った市場レジーム判定（score_regime）
  - JSON Mode を使った厳密なレスポンスバリデーション、429/ネットワーク/5xx に対する指数バックオフ
- 研究向けユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリ、Zスコア正規化
- データ品質チェック
  - 欠損、スパイク（急騰・急落）、重複、日付不整合の検出（QualityIssue）
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までをトレースする監査テーブル作成ユーティリティ（duckdb）
- 設定管理
  - .env / .env.local / 環境変数読み込み（自動ロード可、無効化フラグあり）
  - 必須設定の検証（settings）

動作環境 / 依存関係
-------------------
- Python >= 3.10（typing のユニオン表記等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- (任意) requests 等を別途使う場合は追加してください。

セットアップ手順
----------------

1. リポジトリをクローン / ソースを取得
   - 例: git clone <repo>

2. 仮想環境を作成して有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - 例（最低限）:
     - pip install duckdb openai defusedxml

   - 開発用に setuptools インストールしている場合:
     - pip install -e .

   （本リポジトリに requirements.txt があればそれを利用してください）

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に .env と .env.local を自動ロードします。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注機能を使う場合）
     - SLACK_BOT_TOKEN       : Slack 通知を使う場合
     - SLACK_CHANNEL_ID      : Slack 通知先チャンネル
     - OPENAI_API_KEY        : OpenAI を使う処理（score_news / score_regime 等）で必要

   - 追加設定:
     - KABUSYS_ENV = development | paper_trading | live  (デフォルト development)
     - LOG_LEVEL = DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH / SQLITE_PATH （デフォルト: data/kabusys.duckdb, data/monitoring.db）

   例 .env:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     LOG_LEVEL=INFO

使い方（代表的な API）
---------------------

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
  - Python 例:
    from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニューススコアリング（LLM を用いた銘柄別センチメント）
  - score_news は OpenAI API キーを環境変数 OPENAI_API_KEY で参照します（または api_key 引数で指定可）。
  - 例:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込み銘柄数: {written}")

- 市場レジーム判定（MA200 と マクロニュースの合成）
  - 例:
    from kabusys.ai.regime_detector import score_regime
    written = score_regime(conn, target_date=date(2026,3,20))
    print(written)

- 監査ログ DB 初期化（監査用テーブルを作る）
  - 例:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # conn を使って order_requests / executions 等を操作できます

- 研究用ファクター計算
  - calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic などは
    DuckDB 接続と target_date を渡して呼び出します。

設定と挙動に関する注意
---------------------
- .env 自動読み込み
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索し、.env → .env.local の順で読み込みます。
  - テスト等で自動ロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し
  - gpt-4o-mini を使用し JSON Mode（response_format）を要求します。API レートエラーや一時的失敗に対するリトライが組み込まれています。
  - API キーは api_key 引数で渡すか、環境変数 OPENAI_API_KEY を使用します。
- J-Quants API
  - get_id_token() が内部でリフレッシュを行い、ページネーション間は ID トークンをキャッシュします。
  - レート制限（120 req/min）用の簡易 RateLimiter が実装されています。
- ファイルパス
  - デフォルトの DuckDB パスは settings.duckdb_path（data/kabusys.duckdb）。必要に応じて DUCKDB_PATH 環境変数で上書きしてください。
- ルックアヘッドバイアス対策
  - 多くのモジュールは datetime.today() / date.today() を内部で直接参照しない設計です（外部から target_date を渡すことを前提）。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py                 — パッケージ初期化（version 等）
- config.py                   — 環境変数/設定管理（.env 自動ロード・Settings）
- ai/
  - __init__.py
  - news_nlp.py               — ニュースセンチメントスコアリング（score_news）
  - regime_detector.py        — マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py    — 市場カレンダー管理 / 営業日判定
  - pipeline.py               — ETL パイプライン（run_daily_etl 等） / ETLResult
  - jquants_client.py         — J-Quants API クライアント（fetch/save 関連）
  - news_collector.py         — RSS ニュース収集
  - quality.py                — データ品質チェック
  - stats.py                  — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py                  — 監査ログテーブル作成・初期化
  - etl.py                    — ETLResult エクスポート
- research/
  - __init__.py
  - factor_research.py        — ファクター計算（mom/vol/value）
  - feature_exploration.py    — 将来リターン/IC/summary/rank 等
- ai、data、research の下にさらに補助関数やユーティリティが含まれます

開発 / 追加情報
----------------
- ロギング: settings.log_level で制御（環境変数 LOG_LEVEL）
- 環境: settings.env（development / paper_trading / live）により is_live 等の挙動フラグが変わります
- テスト: 各外部 API 呼び出しはモック可能な設計（内部 _call_openai_api / _urlopen 等に注入ポイントあり）
- DB スキーマ: ETL 保存先テーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）は ETL / save 関数が期待するスキーマであることを前提とします。初回セットアップ時はスキーマを作成するユーティリティやマイグレーションを用意してください（本リポジトリ内に schema 初期化ユーティリティがあればそちらを利用）。

よくある操作例（まとめ）
-----------------------
- 日次 ETL を Cron で回す:
  - python -c "import duckdb; from kabusys.config import settings; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect(str(settings.duckdb_path)); run_daily_etl(conn)"
- ニュース自動収集 + スコアリング:
  - RSS をフェッチ（news_collector.fetch_rss を利用）、raw_news に保存後 score_news を実行
- 監査 DB 作成:
  - from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')

ライセンス / 貢献
-----------------
（ここにライセンス情報や貢献方法を追記してください）

フィードバック / 問い合わせ
-------------------------
不具合報告や改善提案はリポジトリの Issue でお願いします。README の補足や実運用での注意点（証券会社 API の制約、実際の発注の安全性など）は別途ドキュメント化してください。

---

この README はリポジトリ内のソースコード（src/kabusys 以下）を基に作成しています。使用時は実運用上の安全確認（テスト環境での検証、二重発注防止、リスク管理ルールの導入）を必ず行ってください。