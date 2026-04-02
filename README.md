# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README（日本語）

概要
----
KabuSys は日本株のデータ収集・品質管理・特徴量計算・ニュース NLP（LLM を利用したセンチメント）・市場レジーム判定・監査ログ等を備えたミニマルな自動売買／データプラットフォーム用ライブラリ群です。  
主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（外部 API エラー時は安全にフォールバック）」「DuckDB を中心とした軽量データストア」です。

主な機能
--------
- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場／カレンダー情報の差分取得（ページネーション、レート制限、トークンリフレッシュ対応）
- ETL パイプライン
  - 日次 ETL（市場カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得 / バックフィル / 品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集
  - RSS フィードの取得と前処理（SSRF 対策、URL 正規化、トラッキングパラメータ除去、記事ID生成）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを一括送信してセンチメント（ai_scores）を算出・保存（バッチ・リトライ・レスポンス検証）
  - マクロニュースを使った市場レジーム判定（ma200 と LLM センチメントの重み合成）
- リサーチ / ファクター処理
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリ、Z スコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定 をトレース可能にする監査テーブル群（DuckDB、冪等で初期化）
- 設定管理
  - .env 自動ロード（プロジェクトルート検出）、必須環境変数の明示化
- ユーティリティ
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - 汎用統計ユーティリティ（zscore_normalize）

セットアップ
----------
前提:
- Python 3.9+（型アノテーション等に依存）
- DuckDB と OpenAI SDK、defusedxml など（以下は推奨パッケージの例）

1. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストール（プロジェクトに requirements.txt がない場合は最低以下を用意）
   ```bash
   pip install duckdb openai defusedxml
   ```
   （ネットワーク RSS 取得で urllib が標準で使われます。追加でロギング等のパッケージが必要なら適宜追加してください）

3. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます（ただしテスト等で KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます）。
   - 主要な環境変数（必須）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（注文実行等）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - 任意 / デフォルト:
     - KABUSYS_ENV — development / paper_trading / live（default: development）
     - LOG_LEVEL — DEBUG/INFO/…（default: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（default: data/monitoring.db）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - OpenAI 利用時は `OPENAI_API_KEY` を環境変数に設定するか、各関数の api_key 引数に渡してください。

使い方（代表的な例）
-----------------

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（LLM）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxx")
  ```

- 監査ログ DB 初期化（監査専用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブルが作成される
  ```

- ファクター計算（研究用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は各銘柄の dict のリスト
  ```

開発・運用上の注意
-----------------
- 外部 API（J-Quants / OpenAI / RSS ソース）を使用します。実行にはそれぞれの API キーやネットワーク接続が必要です。
- OpenAI 呼び出しはエラー時にフォールバック（0.0 スコア）するよう設計されていますが、API キーは必須です。
- ETL は差分更新を行い、DuckDB への保存は冪等（ON CONFLICT）で行います。バックフィルのパラメータで過去取り込みの再取得が可能です。
- DuckDB 側のスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, audit テーブル等）が必要です。アプリ起動前にスキーマ準備スクリプトを用意するか、モジュールの初期化関数を呼んでください（audit モジュールには init_audit_schema/init_audit_db が用意されています）。
- ニュース収集は SSRF/大容量レスポンス対策・XML パースの安全化（defusedxml）等を実装していますが、運用時には RSS ソースの信頼性管理を行ってください。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / .env 自動ロードと設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（OpenAI）による ai_scores 書き込み
    - regime_detector.py      — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL の公開型（ETLResult など）
    - jquants_client.py       — J-Quants API クライアント（取得・保存）
    - news_collector.py       — RSS 収集・前処理
    - calendar_management.py  — 市場カレンダー管理（営業日判定）
    - quality.py              — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - audit.py                — 監査テーブル定義 & 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Volatility / Value 等
    - feature_exploration.py  — forward returns / IC / rank / summary
  - ai/ (上記)
  - research/ (上記)
  - （strategy, execution, monitoring 等の高位レイヤは今後追加想定）

環境変数の一覧（主要）
---------------------
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API パスワード（発注等）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）
- SLACK_BOT_TOKEN (必須) — Slack 通知用
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（default: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（default: development）
- LOG_LEVEL — ログレベル（default: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動ロードを無効化

推奨ワークフロー例
------------------
- 開発環境:
  - KABUSYS_ENV=development、OPENAI_API_KEY をモックに差し替えてユニットテストを実行
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を使って環境制御を明示的に行う
- ステージング / paper trading:
  - KABUSYS_ENV=paper_trading、SQLite 等で監視（監査ログは本番 DB とは分離）
- 本番:
  - KABUSYS_ENV=live、十分な監視（cpu/memory/disk thresholds）・監査ログの永続化

ライセンス・貢献
----------------
- 本リポジトリのライセンス情報（LICENSE）はプロジェクトルートに置いてください。外部 API キーや秘密情報は絶対にコミットしないでください。
- 新機能追加時はコードスタイル・テスト・ドキュメントの整備をお願いします。

補足（実装上の重要点）
--------------------
- ルックアヘッドバイアス対策:
  - 多数のモジュールが date 引数を明示的に受け取り、内部で datetime.today()/date.today() を直接参照しないよう設計されています（バックテストでの公平性を維持）。
- 冪等性:
  - J-Quants からの保存や監査テーブルの初期化は冪等に実装されています（ON CONFLICT / INSERT ... DO UPDATE 等）。
- フェイルセーフ:
  - LLM 呼び出しや外部 API はエラー時にフォールバック（0.0 スコア・スキップ）し、プロセス全体を停止させない設計です。

最後に
------
ここに記載した README はコードベースの主要機能と利用方法の概観を提供することを目的としています。実際の運用にあたっては、環境固有の設定、適切なシークレット管理、テスト・モニタリングを必ず行ってください。必要であれば、個別のモジュール（ETL、news_nlp、regime_detector、jquants_client 等）ごとの詳細ドキュメントや使用例を追加で作成します。