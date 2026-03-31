KabuSys — 日本株自動売買プラットフォーム
====================================

概要
----
KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI支援・監査ログ・ETL を備えた自動売買基盤のライブラリ群です。主に以下を提供します。

- J-Quants からのデータ取得（株価・財務・市場カレンダー）と DuckDB への冪等保存
- ニュース収集・前処理・LLM によるニュースセンチメント評価（銘柄単位）
- 市場レジーム判定（ETF MA とマクロニュースの LLM スコア合成）
- ファクター計算・将来リターン・IC 計算などのリサーチユーティリティ
- データ品質チェック、マーケットカレンダー管理、ETL パイプライン
- 監査ログ（signal → order_request → executions）のスキーマ初期化ユーティリティ

主な機能一覧
-------------
- 環境設定管理（kabusys.config）
  - .env 自動ロード（プロジェクトルートを探索して .env / .env.local を読み込み）
  - 必須環境変数取得のラッパー（例: JQUANTS_REFRESH_TOKEN 等）
- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API から日足・財務・マーケットカレンダーを取得（ページネーション・レート制御・リトライ・トークン自動リフレッシュ）
  - DuckDB への冪等保存（ON CONFLICT 処理）
- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl: カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - 個別 ETL ヘルパー（run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合 の検出と QualityIssue レポート
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得（SSRF 防止・サイズ制限・URL 正規化）と raw_news への保存ロジックを想定
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions スキーマ作成と初期化ユーティリティ
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄ごとに集約して LLM（gpt-4o-mini）でスコア化し ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA とマクロニュース LLM スコアを合成して market_regime に保存
- リサーチ（kabusys.research）
  - factor_research: momentum / value / volatility / liquidity 等のファクター計算
  - feature_exploration: forward returns, IC（Spearman ρ）、統計サマリー、ランク関数
- 汎用統計ユーティリティ（kabusys.data.stats）
  - zscore_normalize（クロスセクション Z スコア正規化）

セットアップ手順
----------------

依存ライブラリ（代表例）
- Python 3.10+
- duckdb
- openai
- defusedxml

インストール（ローカル開発）
- ソースルートで pip install -e .（パッケージ化されていれば）
  例:
  - pip install -e .

環境変数
- プロジェクトは .env / .env.local を自動で読み込みます（プロジェクトルートの検出は .git または pyproject.toml に基づく）。
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主に必要な環境変数（README 用抜粋）
- JQUANTS_REFRESH_TOKEN    （必須）J-Quants のリフレッシュトークン
- KABU_API_PASSWORD        （必須）kabu ステーション API パスワード（発注系）
- KABU_API_BASE_URL        （任意）kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN          （必須）Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID         （必須）Slack チャンネル ID
- OPENAI_API_KEY           （LLM 呼び出しで使用：score_news / score_regime にも渡せる）
- DUCKDB_PATH              （任意）DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH              （任意）監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL                （任意）ログレベル（DEBUG/INFO/...）
- KABUSYS_ENV              （任意）environment（development/paper_trading/live）

例: .env（最低限）
- JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

使い方（簡単な例）
-----------------

準備: DuckDB 接続と設定読み込み
- Python スクリプトから利用する例:
  - from datetime import date
    import duckdb
    from kabusys.config import settings
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    from kabusys.data.audit import init_audit_db

  - conn = duckdb.connect(str(settings.duckdb_path))

ETL 実行（データ取得）
- result = run_daily_etl(conn, target_date=date(2026, 3, 20))
- result は ETLResult オブジェクト（取得数・保存数・quality_issues・errors を含む）

ニューススコアリング（LLM）
- n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  - api_key を省略すると環境変数 OPENAI_API_KEY を使用します
  - 戻り値は書き込んだ銘柄数

市場レジーム判定（LLM + MA）
- ok = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  - 戻り値 1 が成功

監査ログ DB 初期化
- audit_conn = init_audit_db(settings.duckdb_path)  # または別ファイルパス
  - テーブル作成・インデックス作成を行い、UTC タイムゾーンを設定します

ログ設定・デバッグ
- 環境変数 LOG_LEVEL=DEBUG 等で詳細ログを有効化できます
- KABUSYS_ENV にて動作モードを指定（development / paper_trading / live）

注意事項・トラブルシューティング
---------------------------------
- OpenAI / J-Quants の API キーは必須。未設定の場合は明確な ValueError が発生します。
- J-Quants API はレート制限があるため jquants_client で内部制御しています。大量取得時は注意。
- news_collector は SSRF 対策・応答サイズ制限・XML パースの安全化を実装していますが、実際のネットワーク環境での検証を推奨します。
- DuckDB の executemany に空リストはエラーとなる場合があるため、モジュール実装では空チェックを行っています。API 使用時は返却レコードを確認してください。

ディレクトリ構成（主要ファイルと概要）
-------------------------------------

src/kabusys/
- __init__.py
  - パッケージのバージョンと公開サブパッケージ定義
- config.py
  - 環境変数の自動ロード、Settings クラス（アプリ設定）を提供

kabusys/ai/
- __init__.py
  - score_news をエクスポート
- news_nlp.py
  - ニュースの集約・LLM による銘柄別スコア算出、ai_scores への書き込み
- regime_detector.py
  - ETF(1321) の MA とマクロニュース LLM を合成して market_regime を算出

kabusys/data/
- __init__.py
- calendar_management.py
  - market_calendar の管理、営業日判定、next/prev/get_trading_days、calendar_update_job
- etl.py
  - ETLResult の再エクスポート
- pipeline.py
  - 日次 ETL パイプライン（run_daily_etl 等）、ETL の個別ジョブ
- stats.py
  - zscore_normalize 等の統計ユーティリティ
- quality.py
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- audit.py
  - 監査ログテーブルの DDL と初期化ユーティリティ
- jquants_client.py
  - J-Quants API クライアント（取得・リトライ・レート制御・保存処理）
- news_collector.py
  - RSS 取得・前処理・ID 生成・SSRF 対策

kabusys/research/
- __init__.py
  - 研究向け関数群のエクスポート
- factor_research.py
  - momentum, value, volatility 等のファクター計算
- feature_exploration.py
  - forward returns, IC (Spearman) 計算、統計サマリー、rank

その他
- 各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り、SQL と Python を組み合わせて処理を行います。
- LLM 呼び出しは openai.OpenAI クライアントを使います（gpt-4o-mini を想定）。テスト容易性のため内部の API 呼び出し関数をモック可能に設計しています。

貢献と拡張
-----------
- 新たな ETL 対応やニュースソース追加は data/news_collector.py / jquants_client.py を拡張してください。
- LLM モデルやプロンプトの変更は kabusys/ai/news_nlp.py および regime_detector.py 内の定数・プロンプトを修正してください。
- 監査スキーマの変更は kabusys/data/audit.py に追記してください（冪等に実行されます）。

ライセンス
----------
- 本 README ではライセンスの記載省略。実際の配布時は LICENSE を必ず含めてください。

以上です。必要であれば、README に入れるサンプルスクリプトや .env.example、よくある作業フロー（ETL → ニューススコア → レジーム判定 → 戦略評価）を追加で作成します。どの内容を例示しますか？