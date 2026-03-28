# KabuSys

日本株向けのデータプラットフォーム兼自動売買基盤のライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ、マーケットレジーム判定などの主要処理を提供します。

---

## 概要

KabuSys は以下の目的で設計されたモジュール群です。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ニュース収集と記事の前処理（SSRF／サイズ制限対策付き）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_scores / マクロセンチメント）
- ファクター算出（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）
- データ品質チェック（欠損、重複、スパイク、日付不整合など）

設計方針として「ルックアヘッドバイアス回避」「冪等性」「フォールバック・フェイルセーフ」を重視しています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants API クライアント（fetch/save daily quotes / financials / market calendar / listed info）
  - ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース
  - RSS 収集（SSRF・サイズ制限・トラッキングパラメータ除去）
  - OpenAI を使った銘柄別ニューススコアリング（ai_scores への書き込み）
- AI
  - 銘柄別ニュースセンチメント: kabusys.ai.news_nlp.score_news
  - マクロセンチメント＋ETF MA を用いた市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 研究支援
  - ファクター計算（momentum, value, volatility）、Zスコア正規化、IC 計算等
- データ品質
  - 欠損、重複、スパイク、日付不整合チェック（QualityIssue レポート）
- 監査ログ
  - signal_events / order_requests / executions の DDL + 初期化ユーティリティ

---

## 前提 / 必要条件

- Python 3.10 以上（型ヒントに `|` を使用しているため）
- 必須パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ以外は pip でインストールしてください。

例:
pip install duckdb openai defusedxml

プロジェクト固有の依存関係は各自の requirements ファイルや pyproject.toml にまとめてください。

---

## インストール（ローカル開発向け）

1. リポジトリをクローン
2. 仮想環境を作成して有効化（推奨）
3. 必要パッケージをインストール
   - 例: pip install -e .（パッケージ化されている場合）
   - または: pip install duckdb openai defusedxml

---

## 環境変数 / 設定

KabuSys は .env / .env.local / OS 環境変数から設定を読み込みます（優先順: OS > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

主要な環境変数（必須と推奨）:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（jquants_client で使用）
- OPENAI_API_KEY (必須 for AI 呼び出し時)
  - OpenAI API キー。score_news / score_regime のデフォルト解決先
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード（注文実行系で使用）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須)
  - 通知先チャンネル ID
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH（任意）
  - DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）
  - 監視用 SQLite または別 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV（任意）
  - 利用モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL（任意）
  - ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

注意: Settings クラスは一部必須環境変数が未設定だと ValueError を投げます。

---

## セットアップ手順（例）

1. .env を作成（.env.example を参考に）
   - 必須キー（上記参照）を設定
2. DuckDB ファイル用ディレクトリを準備
   - デフォルトは data/ 配下を想定
3. 監査ログ DB を初期化（任意）
   - 例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
4. ETL 実行用に DuckDB 接続を作成
   - 例:
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))

---

## 使い方（代表的な呼び出し例）

- 日次 ETL の実行
  - Python から:
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメント評価（銘柄別 ai_scores への書き込み）
  - score_news を利用:
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("書き込んだ銘柄数:", n_written)

  - OPENAI_API_KEY は環境変数または score_news の api_key 引数で渡せます。

- 市場レジーム判定
  - score_regime を利用:
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログの初期化（テーブル作成）
  - init_audit_schema / init_audit_db:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # または既存接続へスキーマ追加
    from kabusys.data.audit import init_audit_schema
    init_audit_schema(conn, transactional=True)

- カレンダー更新ジョブ（JPX カレンダーの差分取得）
  - calendar_update_job:
    from kabusys.data.calendar_management import calendar_update_job
    calendar_update_job(conn)

たいていの関数は DuckDB 接続（duckdb.DuckDBPyConnection）と target_date を引数に受け取り、内部で look-ahead を防ぐ実装になっています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py           # 銘柄別ニューススコアリング
  - regime_detector.py    # 市場レジーム判定
- data/
  - __init__.py
  - calendar_management.py
  - pipeline.py           # ETL パイプライン・run_daily_etl 等
  - etl.py                # ETLResult の再エクスポート
  - jquants_client.py     # J-Quants API クライアント & save_* 実装
  - news_collector.py     # RSS 取得・前処理
  - quality.py            # データ品質チェック
  - stats.py              # 共通統計ユーティリティ
  - audit.py              # 監査ログ定義・初期化
- research/
  - __init__.py
  - factor_research.py    # momentum / value / volatility ファクター
  - feature_exploration.py# forward returns / IC / summary / rank

---

## 開発上の注意（重要な設計方針）

- ルックアヘッドバイアス回避:
  - 多くの関数は datetime.today() / date.today() を直接参照せず、target_date を明示的に受け取ります。
- 冪等性:
  - ETL の保存処理は ON CONFLICT を利用して冪等に保存します。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）での失敗は、可能な限り部分失敗で終わらせ、例外は必要な範囲で伝播します（例: score_news は API 失敗時に個別チャンクをスキップする）。
- テスト容易性:
  - OpenAI 呼び出しは内部で分離されており、ユニットテスト時はパッチが可能です（モジュール内の _call_openai_api をモック）。

---

## よくある操作・トラブルシューティング

- .env が自動読み込みされない場合
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認してください。テストで自動ロードを無効化しているケースがあります。
- OpenAI 呼び出しが失敗する場合
  - OPENAI_API_KEY が正しく設定されているか、モデル名（デフォルト gpt-4o-mini）や API 利用制限を確認してください。API エラーは内部的にリトライを試みます。
- J-Quants API への接続
  - JQUANTS_REFRESH_TOKEN は必須です。get_id_token での自動リフレッシュやページネーション用のトークンキャッシュが実装されています。

---

必要であれば、README に使用例（コマンドラインツール化、サンプル .env.example、CI 設定、より詳細な API リファレンス）を追加できます。どの範囲が必要か教えてください。