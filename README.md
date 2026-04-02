# KabuSys — 日本株自動売買プラットフォーム（ライブラリ）

KabuSys は日本株向けのデータプラットフォームと自動売買（研究 → シグナル → 発注）を想定した内部ライブラリ群です。  
DuckDB を用いたデータ基盤、J-Quants API 経由の ETL、ニュースの NLP（OpenAI）によるセンチメント評価、リサーチ用ファクター計算、監査ログスキーマなどのユーティリティを含みます。

主な用途例:
- 日次ETL（株価・財務・市場カレンダー）の差分更新
- ニュース記事の収集・NLP による銘柄センチメント付与
- 市場レジーム判定（MA200 + マクロニュース）
- ファクター計算・IC解析などのリサーチ処理
- 監査ログ（signal → order_request → execution）の初期化・管理

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須値チェック（settings オブジェクト）

- データ ETL（kabusys.data.pipeline）
  - J-Quants API から差分取得（株価・財務・カレンダー）
  - 差分保存（DuckDB、冪等保存）
  - 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集 / NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 収集（SSRF対策・トラッキング除去・前処理）
  - OpenAI を用いた銘柄別センチメントスコア（JSON Mode）
  - チャンク・リトライ・バリデーション

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成
  - LLM 呼び出し失敗時のフォールバック

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
  - zscore_normalize（クロスセクション標準化）

- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions の冪等的なDDL定義と初期化ユーティリティ
  - init_audit_db / init_audit_schema を提供

- J-Quants クライアント（kabusys.data.jquants_client）
  - トークン管理、レートリミット、リトライ、DuckDB 保存メソッド

## 前提・要件

- Python 3.10+（型注釈に union 型等を使用）
- 主な依存（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ多数：urllib, json, datetime など）

※ 実行には J-Quants のリフレッシュトークンや OpenAI API キーなど外部サービスの認証情報が必要です。

## セットアップ手順

1. リポジトリをクローン / コピー
   - 例: git clone <repo>

2. 仮想環境の作成と依存インストール
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -e . もしくは requirements.txt に基づくインストール
   - 必要なパッケージ例:
     - pip install duckdb openai defusedxml

3. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git が存在するディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   - 主要な必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN = <J-Quants リフレッシュトークン>
     - OPENAI_API_KEY = <OpenAI API キー>  （news_nlp / regime_detector が参照）
     - KABU_API_PASSWORD = <kabuステーション API パスワード>
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知用途）
   - 任意 / デフォルト付き:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live, デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）

4. DB 初期化（監査ログ等）
   - 監査用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")
   - もしくは既存 DuckDB 接続に対して init_audit_schema(conn)

## 使い方（主な例）

- settings を参照する
  - from kabusys.config import settings
  - settings.jquants_refresh_token / settings.duckdb_path / settings.is_live などを使えます。

- 日次 ETL を実行する（概略）
  - import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト

- ニュースのスコア付け（AI）
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026,3,20))  # 書き込んだ銘柄数

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

- 監査スキーマ初期化（既存接続に追加）
  - from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- J-Quants の手動データ取得
  - from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
    token = get_id_token()
    records = fetch_daily_quotes(date_from=..., date_to=...)

注意:
- すべての関数はバックテストでのルックアヘッドバイアスに配慮して実装されています（内部で date.today() を直接参照しない設計の箇所が多い）。
- OpenAI 呼び出しは外部 API のためレート制限・エラーに対するリトライ/フォールバックロジックを備えます。テスト時は内部の _call_openai_api をモックできます。

## ディレクトリ構成（概要）

- src/kabusys/
  - __init__.py (パッケージ初期化)
  - config.py (環境変数 / Settings)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント scorers)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント + DuckDB 保存)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー / trading day helpers)
    - stats.py (zscore_normalize 等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログスキーマ / init_audit_db)
  - research/
    - __init__.py
    - factor_research.py (モメンタム / バリュー / ボラティリティ)
    - feature_exploration.py (forward returns / IC / summary)
  - monitoring, strategy, execution など（パッケージ公開のための __all__ に含まれる想定。コードベースにより追加機能あり）

（実際のリポジトリではサブモジュールごとに細かいファイルが存在します。上は主要モジュールの抜粋です）

## テスト・開発メモ

- OpenAI 呼び出しや外部 HTTP はユニットテスト時にモックする設計（モジュール内の _call_openai_api、_urlopen などを patch 可能）。
- .env の自動パースは複雑なクォート・コメント・export 表記に対応しています。テストで自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

## 貢献 / ライセンス

- 開発ポリシー: モジュール分離、冪等性、フェイルセーフ（API失敗時は継続）を重視しています。変更の際は既存の API（特に DB スキーマ・ETL の挙動）との互換性に注意してください。
- ライセンス情報はリポジトリのトップレベルファイル（LICENSE 等）をご確認ください。

---

質問や特定機能の API 例が必要であれば、どのユースケース（ETL、ニューススコア、レジーム判定、監査初期化 など）を示したいか教えてください。具体的なコード例を追加します。