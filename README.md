KabuSys — 日本株自動売買プラットフォーム
=================================

概要
----
KabuSys は日本株データの取得・品質管理・特徴量生成・AI ベースのニュースセンチメント解析・市場レジーム判定・監査ログ管理などを備えた、バックテスト／リサーチ／運用向けのソフトウェアコンポーネント群です。主に以下を目的とします。

- J-Quants API からのデータ取得（株価、財務、取引カレンダー）
- DuckDB を用いたデータ格納・クエリ
- ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュースを LLM でスコアリング（銘柄別センチメント）
- マーケットレジーム判定（MA + マクロニュース）
- 監査ログ（シグナル → 発注 → 約定のトレース）
- 研究用ファクター計算・解析ユーティリティ

主な機能
--------
- データ収集（jquants_client）
  - 日次株価（OHLCV）、四半期財務、JPX カレンダー等の取得と DuckDB への冪等保存
  - レート制限・再試行・トークン自動リフレッシュ対応
- ETL パイプライン（data.pipeline）
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL 実行エントリ run_daily_etl
- ニュース収集（data.news_collector）
  - RSS 取得・正規化・SSRF 対策・前処理・raw_news 保存
- ニュース NLP（ai.news_nlp）
  - 銘柄ごとのニュース集合を LLM（gpt-4o-mini 等）で評価し ai_scores に保存
  - バッチ処理・リトライ・レスポンス検証・スコアクリップ
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成し daily レジームを判定
  - OpenAI 呼び出しは安全なリトライとフェイルセーフを搭載
- 研究用ユーティリティ（research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、Z スコア正規化等
- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブルの初期化・管理
  - 監査用 DuckDB データベース作成ユーティリティ

セットアップ手順
----------------

前提
- Python 3.10 以上（型注釈の | を使用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（LLM 呼び出しを行う場合）
- defusedxml（RSS パーシングの安全化）
- （任意）その他 HTTP/SSL が使える環境

推奨インストール（プロジェクトルートで）
1. 仮想環境作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例: pip）
   - pip install duckdb openai defusedxml

   ※ プロジェクトが配布パッケージであれば pip install -e . 等を検討してください。

3. 環境変数の用意
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env または .env.local を置くと自動読み込みされます。
   - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須／重要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client で使用）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知を行う場合
- DUCKDB_PATH: デフォルトの DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 .env（最小）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-...
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C01234567
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

使い方（簡易ガイド）
-------------------

1) DuckDB 接続を作る
    import duckdb
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

   - ETL はカレンダー → 株価 → 財務 → 品質チェックの順で実行します。
   - ETLResult で fetched/saved/quality issues を確認できます。

3) ニュースのスコアリング（銘柄別）
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"written scores: {written}")

   - OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡します。
   - 処理はウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に基づきます。

4) 市場レジーム判定
    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    score_regime(conn, target_date=date(2026, 3, 20))

   - ETF 1321 の ma200 とマクロニュース（LLM）を使って regime を決定し market_regime テーブルへ保存します。

5) 監査ログ DB 初期化
    from kabusys.data.audit import init_audit_db

    audit_conn = init_audit_db("data/audit.duckdb")
    # または :memory:

注意事項
- OpenAI / J-Quants など外部 API 呼び出しはコスト・レート制限が発生します。API キー管理と使用量に注意してください。
- LLM 呼び出しは失敗時にフォールバック動作をする（例: macro_sentiment=0.0）ようになっていますが、運用ではエラーハンドリングと監視を強化してください。
- DuckDB の executemany に空リストを渡すと問題となるバージョンがあるため、モジュール内でガードしています。

主要モジュール / ディレクトリ構成
-------------------------------

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定読み込みロジック（.env 自動読込）
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュースセンチメントスコアリング（銘柄別）
    - regime_detector.py            - マーケットレジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             - J-Quants API クライアント（取得 & DuckDB 保存）
    - pipeline.py                   - ETL パイプライン（run_daily_etl 等）
    - etl.py                        - ETLResult の公開エイリアス
    - news_collector.py             - RSS ニュース収集（SSRF対策、正規化）
    - calendar_management.py        - 市場カレンダー（営業日判定・更新ジョブ）
    - quality.py                    - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                      - zscore_normalize 等の統計ユーティリティ
    - audit.py                      - 監査ログ（テーブル定義 / 初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py            - Momentum/Value/Volatility 等の計算
    - feature_exploration.py        - 将来リターン・IC・統計サマリー等

推奨ワークフロー（運用例）
------------------------
1. .env に J-Quants と OpenAI のキーを配置
2. 日次バッチで run_daily_etl を実行してデータを更新
3. 毎朝 news_nlp.score_news を実行して ai_scores を更新
4. market_regime を判定し、ストラテジー層のパラメータ（リスク許容など）に反映
5. 戦略で生成したシグナルは audit テーブルへ記録し、発注は order_requests を経由して監査

その他
-----
- コード内にはルックアヘッドバイアス防止（target_date より未来のデータを参照しない）や、DuckDB 上での冪等操作、外部 API の堅牢なリトライ設計など、バックテスト・運用で重要な考慮が多数組み込まれています。
- 実運用では監視・アラート（Slack 通知等）や権限・シークレット管理の整備を強く推奨します。

貢献・開発
----------
- コーディング規約、テスト（ユニット・統合）を追加していくことで信頼性を向上できます。
- AI モジュールはレスポンス形式とレートに依存するため、OpenAI SDK のバージョン変更時は挙動確認が必要です。

ライセンス
----------
- 本リポジトリに付与されたライセンス情報を参照してください（ここではライセンスファイルは含まれていません）。

以上。README をプロジェクトの実情に合わせて適宜編集してください。必要であれば、README に含めるサンプル .env.example、requirements.txt、起動スクリプト例なども作成します。どれを追加しますか？