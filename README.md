# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
J-Quants からのデータ取得（ETL）、ニュースの NLP 分析（OpenAI）、因子計算・調査、監査ログと監視機能などを含む、バックテスト／運用に対応したツール群を提供します。

主な目的
- データ取得（株価、財務、マーケットカレンダー）の差分 ETL と DuckDB への保存
- ニュースのセンチメント解析（OpenAI）による銘柄ごとの AI スコア生成
- 市場レジーム判定（ETF MA とマクロニュース合成）
- 因子（モメンタム、バリュー、ボラティリティ等）の計算と探索的解析
- データ品質チェック、監査ログ（トレース可能な発注／約定ログスキーマ）
- ニュース収集（RSS）と SSRF・DoS を考慮した堅牢な実装

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants API クライアント（認証、取得、保存、ページネーション、レート制御、リトライ）
  - マーケットカレンダー管理（営業日判定、next/prev trading day など）
  - ニュース収集（RSS 取得、前処理、SSRF 回避）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp: ニュースをまとめて LLM に投げ、銘柄単位のスコアを ai_scores に書き込む（score_news）
  - regime_detector: ETF（1321）200日 MA とマクロニュースセンチメントを合成して日次の市場レジームを判定（score_regime）
  - OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証を組み込み
- research/
  - 因子計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config.py
  - .env 自動ロード（プロジェクトルート検出）、環境変数のラッピング（settings オブジェクト）
  - 自動ロード無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
- その他: logging / 環境モード（development / paper_trading / live）管理

---

## 前提・依存

- Python 3.10+
- 必要な主要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）
- J-Quants のリフレッシュトークン、OpenAI API キー等の環境変数

依存は pyproject.toml / requirements.txt にまとめられている想定です。開発環境に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローンしてパッケージをインストール（開発モード例）
   - git clone … 
   - cd <repo>
   - python -m pip install -e ".[dev]"  # optional extras に依存が定義されている想定

2. 必要な環境変数を設定
   - .env または環境変数で設定します。自動でプロジェクトルート（.git または pyproject.toml）を探し `.env` → `.env.local` の順に読み込みます（`.env.local` は上書き）。
   - 自動ロードを無効化するには:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 必要な環境変数（Settings で参照される主なキー）
   - 必須
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系を使う場合）
   - オプション / デフォルトあり
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データベース初期化（監査ログ用など）
   - 監査ログ専用 DB を初期化する例:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL 用の DuckDB に接続:
     ```
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（例）

以下は主要なユースケースの例です。実行は Python スクリプト / ジョブとして呼び出してください。

1. 日次 ETL を実行する
   ```
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニューススコアを生成（ai -> ai_scores へ書き込む）
   ```
   from datetime import date
   import duckdb
   from kabusys.config import settings
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 例: 明示的 api_key 指定 or env OPENAI_API_KEY を利用
   print("wrote", written)
   ```
   - 実際には api_key 引数に OpenAI API キーを渡すか、環境変数 OPENAI_API_KEY を設定してください。

3. 市場レジーム判定を行う
   ```
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026,3,20), api_key=settings.jquants_refresh_token)  # api_key は OpenAI のキー
   ```

4. 因子計算 / リサーチユーティリティ
   ```
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum

   conn = duckdb.connect("data/kabusys.duckdb")
   factors = calc_momentum(conn, target_date=date(2026,3,20))
   ```

5. RSS フィードを取得する（ニュース収集）
   ```
   from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
   articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
   for a in articles:
       print(a["id"], a["datetime"], a["title"])
   ```
   - fetch_rss は SSRF・レスポンスサイズ制限・gzip に対応しており、失敗時は例外または空リストを返します。取得後は DB へ保存するロジック（raw_news への挿入）と連携してください。

6. 監査ログスキーマの初期化（既存接続にテーブルを追加）
   ```
   from kabusys.data.audit import init_audit_schema
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

注意点
- 多くの API 呼び出しはネットワーク・レート制御あり。ログや retry を確認してください。
- OpenAI 呼び出しはレスポンスの JSON 検証を行い、不正レスポンスや API エラー時はフォールバック（0.0）やスキップして継続する設計です。
- DuckDB の executemany に空リストを渡すとエラーになる互換性を考慮して実装されています。

---

## ディレクトリ構成（主要ファイル）

（パッケージルート: src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py
  - calendar_management.py
  - news_collector.py
  - quality.py
  - audit.py
  - stats.py
  - pipeline.py (ETLResult 再エクスポート)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記以外に strategy / execution / monitoring などのサブパッケージが存在することを想定するトップレベル API がありますが、実装は各プロジェクト段階に依存します。）

---

## 開発・テストに関する補足

- config の .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI／テストで自動ロードを避ける場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモックして差し替える設計（モジュール内の _call_openai_api を patch する等）。
- DuckDB を使うため、インメモリ(":memory:") を使ったテストも可能です（init_audit_db は ":memory:" をサポート）。

---

## トラブルシューティング（よくあるエラー）

- ValueError: 環境変数未設定
  - settings のプロパティは必須環境変数がなければ ValueError を送出します（例: JQUANTS_REFRESH_TOKEN）。
- ネットワーク / API の接続エラー
  - jquants_client と OpenAI 呼び出しはリトライとバックオフを組み込んでいますが、接続不可や認証エラーはログを参照してください。
- DuckDB の executemany に空パラメータを与えるとエラーになるケースに対応済みですが、カスタム処理を書く場合は注意してください。

---

この README はコードベースに含まれるモジュール構成・設計方針を簡潔にまとめたものです。より詳細な仕様（StrategyModel.md、DataPlatform.md 等）がプロジェクトに同梱されている場合はそちらを参照してください。必要なら、使用例やデプロイ手順（systemd / supervisor ジョブ、監視設定）のテンプレートも作成できます。どの部分を補足したいか教えてください。