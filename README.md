KabuSys — 日本株自動売買／データプラットフォーム
================================

概要
----
KabuSys は日本株のデータ取得（ETL）、品質チェック、ニュース収集、AIベースのニュースセンチメント判定、マーケットレジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを備えた研究 & 自動売買向けのライブラリ群です。DuckDB をストレージに使い、J-Quants API や RSS、OpenAI を用いた処理を想定しています。モジュールはバックテストや本番環境の両方で偏りのない（look-ahead バイアスを避ける）設計になっています。

主な機能
--------
- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーの差分取得（ページネーション対応）
  - 保存は冪等（ON CONFLICT DO UPDATE）
  - 日次 ETL の統合エントリーポイント（run_daily_etl）
- データ品質チェック
  - 欠損、重複、スパイク（急騰・急落）、日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS フィード取得、前処理、raw_news テーブルへの冪等保存
  - SSRF / Gzip Bomb 等の安全対策を組み込み
- AI 系処理（OpenAI）
  - ニュースの銘柄別センチメント計算（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を合わせた市場レジーム判定（ai.regime_detector.score_regime）
  - API 呼び出しはリトライ / バックオフ / フォールバック実装
- 研究用ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events, order_requests, executions 等の監査テーブル作成・初期化ユーティリティ
  - 監査用の専用 DuckDB 初期化関数（init_audit_db / init_audit_schema）
- 設定管理
  - .env（.env.local 優先）あるいは環境変数から設定を自動ロード（パッケージ位置に基づきプロジェクトルート検出）
  - 必須変数チェックを含む Settings オブジェクト（kabusys.config.settings）

動作要件（主要）
----------------
- Python 3.9+（型ヒントに union 型等を利用）
- 必要な Python パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS）
- 環境変数（下記参照）および DuckDB 書き込み可能なファイルシステム

セットアップ手順
----------------
1. リポジトリを取得し、Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実際のプロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r で管理してください）

3. 環境変数の設定
   - プロジェクトルート（pyproject.toml または .git のあるディレクトリ）に .env を置くと自動読み込みされます。
   - 自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定できます（テスト時など）。

必須の環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabu ステーション API のパスワード（発注などで使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時）
- オプション（デフォルトあり）:
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/...（デフォルト INFO）
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: デフォルト data/monitoring.db

簡単な使い方（例）
-----------------

- DuckDB に接続して日次 ETL を実行する（最も基本的な例）:
  - python -c "import duckdb, datetime; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect('data/kabusys.duckdb'); r=run_daily_etl(conn, target_date=datetime.date(2026,3,20)); print(r.to_dict())"

- ニュースセンチメント（OpenAI 必須）:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    count = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数に設定しておく
    print("scored:", count)

- 市場レジーム判定（OpenAI 必須）:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect('data/kabusys.duckdb')
    score_regime(conn, target_date=date(2026,3,20))

- 監査ログ DB の初期化（専用 DB）:
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db('data/audit.duckdb')
    # テーブルが作成され UTC タイムゾーンに設定されます

- 設定値取得:
  - from kabusys.config import settings
    print(settings.duckdb_path)  # Path オブジェクト

補足 / 実運用上の注意
--------------------
- AI 呼び出しは課金・レート制限対象です。OpenAI キーの管理とコール回数に注意してください。
- J-Quants API の利用はトークン管理・レート制限を守る必要があります。jquants_client は内部でレート制御と自動リフレッシュを行いますが、使用時は API 利用規約を遵守してください。
- ETL / AI モジュールは look-ahead バイアスを避ける設計になっていますが、バッチ呼び出しの日時・target_date の取り扱いは慎重に行ってください。
- DuckDB executemany の仕様（空リスト不可など）に依存する部分があるため、ライブラリバージョンに注意してください。

ディレクトリ構成
----------------
（主要ファイルを抜粋した構成）

- src/kabusys/
  - __init__.py
  - config.py                        # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     # ニュースセンチメント（銘柄別）
    - regime_detector.py              # 市場レジーム判定（ETF + マクロ）
  - data/
    - __init__.py
    - calendar_management.py          # 市場カレンダー管理（営業日判定等）
    - etl.py                          # ETL 再公開インターフェース
    - pipeline.py                     # 日次 ETL パイプライン（run_daily_etl 等）
    - stats.py                        # 統計ユーティリティ（z-score 正規化）
    - quality.py                      # データ品質チェック
    - audit.py                        # 監査ログ（テーブル定義／初期化）
    - jquants_client.py               # J-Quants API クライアント（取得＋保存）
    - news_collector.py               # RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py              # ファクター計算（momentum/value/volatility）
    - feature_exploration.py          # 将来リターン / IC / 統計サマリー 等
  - (その他)                           # strategy, execution, monitoring など（パッケージ API を想定）

開発者向けメモ
---------------
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に行われます。テスト時などで自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しのユーティリティ関数は各モジュールで独立実装されています（テストの差し替えがしやすい設計）。
- DuckDB 接続は呼び出し元で管理してください。init_audit_db のように DB を作成して接続を返すユーティリティも提供しています。

ライセンス／問い合わせ
---------------------
（このリポジトリに合わせてライセンスや連絡先を追記してください）

以上。README に追加してほしい具体的なコマンド例や、環境変数の .env.example を作成したい場合は教えてください。