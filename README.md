# KabuSys

日本株向け自動売買／データ基盤ライブラリセット（KabuSys）。  
DuckDB をデータストアに用い、J-Quants / kabuステーション / OpenAI を組み合わせてデータ取得・品質管理・ニュースNLP・市場レジーム判定・ファクター計算・監査ログを提供します。

概要
- パッケージ名: kabusys
- 目的: 日本株のデータパイプライン（ETL）・品質チェック・ニュースセンチメント解析・市場レジーム判定・ファクター計算・監査ログの基盤機能を提供し、戦略層や執行層と組み合わせて自動売買システムを構成するためのユーティリティ群を実装。
- 設計方針の一部:
  - ルックアヘッドバイアスを避けるために内部で date.today() / datetime.today() を不用意に参照しない。
  - DuckDB をコアデータベースとして SQL と Python を組み合わせ、外部 API 呼び出しは明示的に扱う。
  - API 呼び出しはレート制御・リトライ・フェイルセーフ（失敗時はゼロやスキップ）を備える。
  - 監査ログ（信号→発注→約定まで）を冪等・追跡可能に保持。

主な機能一覧
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 必須環境変数チェック、環境（development/paper_trading/live）判定、ログレベルなど
- データ取得 / ETL (kabusys.data.pipeline, jquants_client, news_collector 等)
  - J-Quants から株価日足・財務・上場情報・市場カレンダーの差分取得・保存
  - ETL パイプライン（run_daily_etl）と個別 ETL ジョブ
  - RSS からニュース収集（SSRF 対策・トラッキング除去・サイズ制限・前処理）
  - DuckDB への冪等保存ユーティリティ
- データ品質チェック (kabusys.data.quality)
  - 欠損、重複、スパイク（前日比急変）、日付不整合（未来日・非営業日）検出
  - QualityIssue オブジェクト群として結果を返却
- カレンダー管理 (kabusys.data.calendar_management)
  - 営業日判定、前後営業日取得、営業日リスト取得、JPX カレンダー更新ジョブ
- 監査ログ（Audit） (kabusys.data.audit)
  - signal_events / order_requests / executions などのテーブル定義と初期化（冪等）
  - init_audit_db, init_audit_schema による DB 初期化
- AI ニュース NLP (kabusys.ai.news_nlp)
  - OpenAI (gpt-4o-mini 等) を用いた銘柄毎ニュースセンチメント（ai_scores への書き込み）
  - バッチ処理・トリム・リトライ・レスポンスバリデーションを実装
- 市場レジーム判定 (kabusys.ai.regime_detector)
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して daily レジーム判定（bull/neutral/bear）
- 研究用ユーティリティ (kabusys.research)
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC 計算、Zスコア正規化 等
- 汎用統計ユーティリティ (kabusys.data.stats)
  - zscore_normalize 等

セットアップ手順（開発環境向け、概要）
1. Python の準備
   - 推奨: Python 3.10+（typing の型注釈等を使用）
   - 仮想環境作成:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS/Linux
     .venv\Scripts\activate     # Windows (PowerShell/CMD)
     ```

2. 必要パッケージのインストール（代表的な依存）
   - 必要なライブラリ（少なくとも以下）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実際のプロジェクトでは requirements.txt / poetry などでバージョンを固定してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある場所）に .env/.env.local を置くことで自動読み込みされます（os 環境変数が優先、.env.local は .env を上書きします）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主な必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
     - SLACK_BOT_TOKEN — Slack 通知用 Bot Token
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
   - オプション:
     - KABUSYS_ENV — development / paper_trading / live（既定: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（既定: INFO）
     - DUCKDB_PATH — デフォルト data/kabusys.duckdb
     - SQLITE_PATH — 監視用 SQLite（data/monitoring.db）
   - サンプル .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C12345678
     KABUSYS_ENV=development
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB データベースの準備（例）
   - Python REPL / スクリプトで:
     ```python
     import duckdb
     from kabusys.data import audit
     conn = duckdb.connect("data/kabusys.duckdb")
     # 必要に応じてスキーマ初期化（監査テーブル等）
     audit.init_audit_schema(conn)
     conn.close()
     ```

使い方（代表的な利用例）
- 日次 ETL 実行（株価 / 財務 / カレンダー の差分取得）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメントのスコアリング（OpenAI 必須）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数に設定するか api_key 引数を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", written)
  conn.close()
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- 監査用 DuckDB 初期化（専用DB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn を利用して監査ログを書き込む
  ```

- ファクター計算・研究用ユーティリティの使用例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  normed = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

注意点 / 運用上のポイント
- OpenAI 呼び出しはコストとレイテンシが発生するため、バッチ設計やキャッシュを検討してください。
- J-Quants API はレート制限があり、モジュール内で固定インターバル・リトライを設けています。認証トークンの自動更新機能も備えています。
- ETL / 品質チェックは失敗時にも他処理を継続する設計です（問題は結果オブジェクトに集約されます）。運用側で問題に応じたアラートや停止判断を実装してください。
- DuckDB の executemany に関する挙動（空リスト不可）に注意して部分書き換えを行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースセンチメント（ai_scores への書き込み）
    - regime_detector.py              — 市場レジーム判定（1321 MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL インターフェース/再エクスポート
    - news_collector.py               — RSS 取得・前処理・raw_news 保存
    - quality.py                      — データ品質チェック
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - calendar_management.py          — 市場カレンダー管理
    - audit.py                         — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py              — Momentum / Value / Volatility 等
    - feature_exploration.py          — 将来リターン / IC / summary / rank
  - monitoring/ (パッケージ宣言のみ含まれる想定)
  - strategy/ (戦略層は外部で実装、インターフェース想定)
  - execution/ (執行層は外部で実装、監査ログとの連携を想定)

開発・コントリビューション
- 静的型注釈を多用しているため mypy 等の型チェックが効果的です。
- テストは外部 API コールをモックすること（OpenAI / J-Quants / ネットワーク）で安定化します。
- .env 読み込みはデフォルトで自動実行されます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にしてください。

ライセンス / 著作権
- 本 README はコードベースの説明です。実際のライセンス表記はプロジェクトの LICENSE ファイルを参照してください。

以上。README に追加したい例や使い方（CI や Docker 化、運用手順など）があれば教えてください。具体例を追記します。