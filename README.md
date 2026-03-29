# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリ。J-Quants / kabuステーション / 各種RSS・LLM を組み合わせてデータ収集（ETL）、品質チェック、ニュースNLP、マーケットレジーム判定、リサーチ用ファクター計算、監査ログなどを提供します。

主にバックテスト用データ基盤や自動売買のオーケストレーションで利用する想定のモジュール群です。

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）・財務データ・JPXカレンダーを差分取得・保存（DuckDB）
  - 差分更新・バックフィル、ページネーション、トークン自動リフレッシュ、レート制御、リトライ付き

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付不整合チェック（future / 非営業日データ）

- ニュース収集・前処理
  - RSS フィードの収集、URL 正規化、SSRF 防止、トラッキングパラメータ除去、記事ID生成、raw_news への冪等保存向けユーティリティ

- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント算出（ai_scores テーブルへ）
  - バッチ・チャンク、JSON Mode、入出力バリデーション、リトライ制御あり

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次レジーム（bull / neutral / bear）を判定・保存

- 研究（Research）
  - momentum/value/volatility 等のファクター計算
  - 将来リターン計算、IC（Spearman）・統計サマリー、Zスコア正規化など

- 監査ログ（Audit）
  - signal → order_request → executions のトレーサビリティを保証する監査スキーマの初期化と DB 操作ユーティリティ

---

## 要件（概略）

- Python 3.10 以上（PEP 604 の Union 型 `X | Y` を使用）
- 必須パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース 等）
- 各種 API キー / トークン（下記参照）

プロジェクトに requirements.txt / pyproject がある想定で、そちらに従ってください。

---

## 環境変数（主なもの）

必須（Settings から参照されるキー）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（発注等）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意 / 推奨
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

自動読み込み
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動的に読み込みます。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env ファイルの書式は shell 形式（`KEY=VALUE`）に対応し、引用やコメントの扱いを配慮した実装です。

---

## セットアップ手順（例）

1. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate    # Unix/macOS
   .venv\Scripts\activate       # Windows
   ```

2. 依存パッケージをインストール（プロジェクトに requirements.txt または pyproject がある前提）
   ```bash
   pip install -r requirements.txt
   # または
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01ABCDEF
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動読み込み（.env/.env.local）はデフォルトで有効です。

4. データベース初期化（監査用など）
   - 監査DBを作る場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要な例）

以下はライブラリを直接インポートして使う典型的な例です。各関数は duckdb 接続（DuckDBPyConnection）を引数に取るものが多い点に注意してください。

- 日次 ETL を実行（prices / financials / calendar の差分取得と品質チェック）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=None)  # target_date=None -> 今日
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI を利用）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み済み銘柄数を返す
  ```

- 市場レジームのスコアリング
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- ファクター計算（Research）
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

  mom_z = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- RSS 収集ユーティリティ（単体取得）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

---

## 主要 API（モジュール / 関数一覧）

- kabusys.config
  - settings: 環境設定ラッパー（必須キー取得は _require により ValueError を投げる）

- kabusys.data
  - pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client: fetch_* / save_* / get_id_token 等
  - news_collector: fetch_rss, preprocess_text 等
  - quality: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - audit: init_audit_schema, init_audit_db
  - stats: zscore_normalize

- kabusys.ai
  - news_nlp.score_news
  - regime_detector.score_regime

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成（主要ファイル）

プロジェクトは以下のようなパッケージ構成を想定しています（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - pipeline.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - quality.py
      - stats.py
      - calendar_management.py
      - audit.py
      - etl.py (公開エイリアス)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/ (存在する場合のモジュール群)
    - strategy/ (存在する場合の戦略関連)
    - execution/ (存在する場合の発注関連)

README（およびプロジェクトルート）には .env.example を置いて、必須環境変数の雛形を記載することを推奨します。

---

## ベストプラクティス・注意点

- Look-ahead バイアス対策
  - 多くのモジュール（news_nlp, regime_detector, pipeline 等）は内部で datetime.today() を直接参照せず、target_date を明示する設計になっています。バックテストでは target_date を明示的に渡してください。

- OpenAI 呼び出し
  - news_nlp / regime_detector は JSON モードを利用し、レスポンスのバリデーションやリトライを実装していますが、API キーは環境変数（OPENAI_API_KEY）または関数引数で確実に渡してください。

- データベース（DuckDB）互換性
  - DuckDB バージョン差異（executemany の空リスト扱い等）がコード中で考慮されています。DuckDB のメジャーバージョンアップ時はテストを行ってください。

- セキュリティ / ネットワーク
  - news_collector は SSRF・Gzip Bomb・XML Injection（defusedxml）対策を実装していますが、RSS ソースや HTTP クライアントの動作確認は運用環境で行ってください。

---

## トラブルシューティング（よくある問題）

- 環境変数が見つからない
  - settings のプロパティは未設定時に ValueError を投げます。.env を作成して必要なキーをセットしてください。
  - 自動読み込みを無効にしている場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を未設定に戻すか手動で環境変数を設定してください。

- OpenAI で JSON パースエラーが出る
  - LLM レスポンスに余計なテキストが混ざることがあるため、news_nlp / regime_detector はパースフォールバックを備えています。頻発する場合はリトライやモデル設定を見直してください。

- J-Quants の認証・レート制限
  - get_id_token と _request は 401 時の自動リフレッシュや 120 req/min のレート制御を行います。大量取得時は間隔管理や page 単位のスリープを検討してください。

---

## ライセンス・貢献

本 README はコードベースから自動生成された概要です。実プロジェクトに組み込む場合はライセンスやコントリビューションルール（CONTRIBUTING.md）を追加してください。

---

必要があれば、README に追加する実行例（cron job や GitHub Actions での ETL スケジュール例）、.env.example のテンプレート、あるいはパッケージ公開向けの pyproject / setup 手順なども作成します。どれを追加しますか？