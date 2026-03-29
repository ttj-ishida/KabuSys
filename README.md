# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
DuckDB をデータプラットフォームとして使い、J-Quants からのデータ取得（株価・財務・カレンダー）、RSS ニュース収集、AI（OpenAI）を使ったニュースセンチメント／市場レジーム判定、研究用ファクター計算、ETL パイプライン、監査ログ（注文・約定のトレーサビリティ）などを提供します。

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易チュートリアル・例）
- ディレクトリ構成
- 環境変数一覧（必須/任意）
- 注意事項

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と自動売買を想定したライブラリ群です。主な設計方針は次のとおりです：

- DuckDB をデータストアとして利用し、ETL（差分更新）を行う
- J-Quants API を通じた株価・財務・カレンダー取得（レート制御・リトライ・トークン自動更新）
- RSS ベースのニュース収集（SSRF 対策・前処理・冪等保存）
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP と市場レジーム判定（フェイルセーフ・リトライ実装）
- 研究モジュール（ファクター算出、IC・将来リターン計算など）、統計ユーティリティ（Z-score）
- データ品質チェックと監査ログ（signal → order_request → execution の追跡）

---

## 機能一覧

- データ取得・保存
  - J-Quants からの株価日足（OHLCV）・財務データ・上場銘柄情報・市場カレンダー取得（ページネーション対応、リトライ）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE など）
- ETL パイプライン
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集
  - RSS フィード取得、テキスト前処理、raw_news / news_symbols への保存（冪等）
  - SSRF・gzip・XML攻撃対策あり
- AI（OpenAI）連携
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出（gpt-4o-mini、JSON mode、チャンク処理、リトライ）
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースセンチメントの合成による市場レジーム判定
- 研究（Research）
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量解析: calc_forward_returns / calc_ic / factor_summary / rank
  - zscore_normalize（統計ユーティリティ）
- 監査ログ
  - 監査スキーマの初期化（init_audit_schema / init_audit_db）
  - signal_events / order_requests / executions の管理
- ユーティリティ
  - カレンダー判定（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
  - 設定管理（環境変数自動ロード・Settings）

---

## セットアップ手順

前提:
- Python 3.10 以上（| 型注釈を利用）
- DuckDB、openai、defusedxml 等の依存パッケージが必要

1. リポジトリをクローン（またはパッケージを入手）
2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```
3. インストール（プロジェクトルートで）
   - 開発中: editable install
     ```bash
     pip install -e .
     ```
   - 必要なパッケージがある場合は requirements.txt を使ってください（本コードベースには同梱されていないため、最低限以下をインストールしてください）:
     ```bash
     pip install duckdb openai defusedxml
     ```
4. 環境変数を用意
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - `.env.example` を参照して設定してください（以下に詳細を記載）。
5. DuckDB データベースの初期化（監査DBなど）
   - 監査DBを作る例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - ETL/スキーマ初期化等は利用する用途に応じて行ってください。

---

## 環境変数一覧

※ `.env` に設定することを想定しています。KABUSYS は自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（CWD依存しない探索）

必須（動作に必須なもの）
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（注文系と連携する場合）
- SLACK_BOT_TOKEN
  - Slack 通知用 Bot トークン（通知を利用する場合）
- SLACK_CHANNEL_ID
  - Slack 通知先チャンネル ID

任意 / デフォルトあり
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live。デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO)
- OPENAI_API_KEY (news_nlp / regime_detector の呼び出し時に未指定なら環境変数から参照)

自動ロード制御
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込まなくなります（テスト時などに便利）。

---

## 使い方（主要関数・例）

以下は代表的な使用例です。すべて DuckDB の接続オブジェクト（kabuys が期待する DuckDBPyConnection）を渡して操作します。

- ETL（日次）を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを取得して ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数に設定するか、第3引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print("scored codes:", count)
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(momentum), "records")
  ```

- 監査DBを初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが作成されます
  ```

- カレンダー判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026, 1, 1)))
  print(next_trading_day(conn, date(2026, 1, 1)))
  ```

注意:
- AI系（news_nlp / regime_detector）は OpenAI API キーが必要です。関数引数として api_key を渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL 実行時は J-Quants のトークン（JQUANTS_REFRESH_TOKEN）を設定しておく必要があります。

---

## ディレクトリ構成（抜粋）

ソースは `src/kabusys` 以下に配置されています。主要なモジュールは以下のとおりです。

- src/kabusys/
  - __init__.py
  - config.py            — 環境変数・設定の管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント算出（OpenAI 連携）
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - etl.py                 — ETL 公開インターフェース
    - pipeline.py            — ETL パイプラインの実装（run_daily_etl など）
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログテーブル定義＆初期化
    - jquants_client.py      — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py      — RSS ニュース収集、前処理、保存
    - etl.py                 — ETL 公開 API（再エクスポート）
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — forward_returns / IC / factor_summary / rank
  - ai、data、research の中にさらに細かい関数群・ユーティリティあり

（README はプロジェクト全体の抜粋です。詳細は各モジュールの docstring を参照してください）

---

## 注意事項 / 運用上のポイント

- Look-ahead bias を避ける実装思想
  - 多くのモジュールは target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計になっています。バックテストや再現性の確保に注意してください。
- OpenAI 呼び出しはリトライ・パース失敗時のフェイルセーフ（デフォルト 0.0）実装あり
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装済みです
- ニュース RSS は SSRF・XML Bomb 対策、レスポンスサイズ制限（10 MB）等の防御を組み込んでいます
- DuckDB のバージョンによる挙動差（executemany の空リスト可否など）に配慮した実装があります
- 自動ロードされる `.env` はプロジェクトルート（.git または pyproject.toml の親ディレクトリ）を探索します。CI/テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを無効化できます。

---

ヘルプや追加ドキュメント（例えば API の細かな仕様や ETL の稼働スケジュール、Slack 通知設定など）が必要であれば、どの部分を詳しく書くか教えてください。