# KabuSys — 日本株自動売買システム (README)

KabuSys は日本株を対象としたデータ取得・ETL・特徴量生成・シグナル生成・監査ロギングを目的としたライブラリ群です。J-Quants API 等から市場データ・財務データ・ニュースを収集し、DuckDB を中心にデータレイヤを構築、戦略用の特徴量を作成してシグナルを生成します。実際の発注（証券会社）との接続は execution 層で扱う設計です。

主な対象ユーザー：データエンジニア、クオンツ・リサーチャー、戦略エンジニア

---

## 目次
- プロジェクト概要
- 機能一覧
- 要件
- 環境変数（設定）
- セットアップ手順
- 使い方（クイックスタート）
- 主要 API（抜粋）
- ディレクトリ構成 / 主要ファイル
- 注意事項

---

## プロジェクト概要
KabuSys は以下の責務を持つモジュール群で構成されています。

- データ収集（J-Quants API）と DuckDB への冪等保存
- 市場カレンダー管理（JPX）
- ニュースのRSS収集・前処理・銘柄紐付け
- ファクター（モメンタム/ボラティリティ/バリュー等）計算
- 特徴量の正規化・保存（features テーブル）
- シグナル生成（BUY / SELL）と signals テーブルへの保存
- ETL パイプライン（差分更新・品質チェック）
- スキーマ定義（DuckDB）と監査ログ類

設計方針としては「ルックアヘッドバイアスの排除」「冪等性」「外部 API のレート制御とリトライ」「DBトランザクションによる原子性保証」を重視しています。

---

## 機能一覧
- DuckDB スキーマの初期化（init_schema）
- J-Quants クライアント（認証、自動リフレッシュ、ページネーション、リトライ、レート制御）
- 日次 ETL（run_daily_etl）: 市場カレンダー / 株価 / 財務 の差分取得・保存
- ニュース収集（RSS）と raw_news / news_symbols への保存
- ファクター計算: calc_momentum / calc_volatility / calc_value
- 特徴量作成: build_features（Zスコア正規化・ユニバースフィルタ等）
- シグナル生成: generate_signals（最終スコア計算、BUY/SELL 判定、冪等保存）
- マーケットカレンダー管理（is_trading_day / next_trading_day 等）
- 統計ユーティリティ（zscore_normalize, IC 計算等）
- 監査ログスキーマ（signal_events / order_requests / executions など）

---

## 要件
- Python 3.10 以上（typing の `X | None` などの構文を使用）
- 必要な Python パッケージ（最低限）
  - duckdb
  - defusedxml
- 標準ライブラリで実装されている部分が多く、pandas 等には依存しません。

インストール例:
```
python -m pip install "duckdb" "defusedxml"
```

（プロジェクトに requirements.txt がある場合はそちらを参照してください）

---

## 環境変数（設定）
KabuSys は .env / .env.local または OS 環境変数から設定を読み込みます。自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を検出して行います。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（execution 層で使用）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知を利用する場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（通知を利用する場合）

オプション（デフォルトあり）:
- KABUSYS_ENV — `development` / `paper_trading` / `live`（既定: development）
- LOG_LEVEL — `DEBUG`/`INFO`/`WARNING`/...（既定: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite のパス（既定: data/monitoring.db）

簡易的な .env 例（.env.example として保存）:
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順
1. Python 環境を用意（3.10+ 推奨）。
2. 依存パッケージをインストール:
   ```
   python -m pip install duckdb defusedxml
   ```
3. リポジトリをクローン／配置し、プロジェクトルートに `.env`（または .env.local）を作成して必要な環境変数を設定する。
4. DuckDB スキーマを初期化:
   - Python REPL やスクリプトで以下を実行:
     ```python
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")
     ```
   - これにより `data/` ディレクトリが作成され、必要なテーブルが作られます。

---

## 使い方（クイックスタート）
以下は基本的なワークフローの例です。

1. DuckDB スキーマ初期化
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")
   ```

2. 日次 ETL 実行（J-Quants からデータを取得して保存）
   ```python
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date

   res = run_daily_etl(conn, target_date=date.today())
   print(res.to_dict())
   ```

3. ニュース収集（RSS）と記事の銘柄紐付け
   ```python
   from kabusys.data.news_collector import run_news_collection
   # known_codes は既知の銘柄コード集合（例: {"7203","6758",...}）
   out = run_news_collection(conn, known_codes={"7203","6758"})
   print(out)
   ```

4. 特徴量作成（features テーブルへの登録）
   ```python
   from kabusys.strategy import build_features
   from datetime import date
   cnt = build_features(conn, target_date=date.today())
   print(f"features upserted: {cnt}")
   ```

5. シグナル生成（signals テーブルへの登録）
   ```python
   from kabusys.strategy import generate_signals
   from datetime import date
   total_signals = generate_signals(conn, target_date=date.today(), threshold=0.6)
   print(f"signals written: {total_signals}")
   ```

6. マーケットカレンダーの更新ジョブ
   ```python
   from kabusys.data.calendar_management import calendar_update_job
   saved = calendar_update_job(conn)
   print(f"calendar saved: {saved}")
   ```

注意: 上記はライブラリを直接使う例です。運用や cron / Airflow 等に組み込んで定期実行する想定です。

---

## 主要 API（抜粋）
- kabusys.data.schema
  - init_schema(db_path) → DuckDB 接続（スキーマを作成）
  - get_connection(db_path)
- kabusys.data.jquants_client
  - get_id_token(refresh_token=None)
  - fetch_daily_quotes(...)
  - fetch_financial_statements(...)
  - fetch_market_calendar(...)
  - save_daily_quotes(conn, records)
  - save_financial_statements(conn, records)
  - save_market_calendar(conn, records)
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date=None, ...)
  - run_prices_etl(...)
  - run_financials_etl(...)
  - run_calendar_etl(...)
- kabusys.data.news_collector
  - fetch_rss(url, source, timeout=30)
  - save_raw_news(conn, articles)
  - run_news_collection(conn, sources=None, known_codes=None)
- kabusys.research
  - calc_momentum(conn, date)
  - calc_volatility(conn, date)
  - calc_value(conn, date)
  - calc_forward_returns(...)
  - calc_ic(...)
- kabusys.strategy
  - build_features(conn, target_date)
  - generate_signals(conn, target_date, threshold=..., weights=None)
- kabusys.data.calendar_management
  - is_trading_day(conn, d)
  - next_trading_day(conn, d)
  - prev_trading_day(conn, d)
  - get_trading_days(conn, start, end)
  - calendar_update_job(conn, lookahead_days=90)

各関数は docstring に使用方法と引数・戻り値・副作用が記載されています。実運用時はログレベルや例外処理、リトライポリシーの設計を行ってください。

---

## ディレクトリ構成（抜粋）
以下は主要なファイル・モジュールの一覧（src/kabusys 内）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理（.env 自動読み込み含む）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（認証・取得・保存）
    - news_collector.py       — RSS 収集・前処理・DB保存
    - schema.py               — DuckDB スキーマ定義・初期化
    - pipeline.py             — ETL パイプライン（差分取得・保存・品質チェック）
    - stats.py                — 統計ユーティリティ（Zスコア等）
    - features.py             — features の再エクスポート
    - calendar_management.py  — マーケットカレンダー関連ユーティリティ
    - audit.py                — 監査ログスキーマ（signal/events/orders/executions）
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum/volatility/value）
    - feature_exploration.py  — IC / 統計サマリー 等
  - strategy/
    - __init__.py
    - feature_engineering.py  — 特徴量構築（正規化・ユニバースフィルタ等）
    - signal_generator.py     — シグナル生成ロジック（final_score 計算等）
  - execution/                — 発注・ブローカー連携用（空パッケージ）
  - monitoring/               — 監視/メトリクス（場所確保）

（実際のリポジトリではその他ファイル・ドキュメント、DataPlatform.md 等仕様ドキュメントが存在します）

---

## 注意事項 / 運用上のヒント
- Python バージョンは 3.10 以上を推奨します（構文的要件）。
- J-Quants の API レート制限（120 req/min）を考慮して実行してください。jquants_client は内部で固定間隔のレート制御とリトライを実装しています。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb に作成されます。運用時は適切な永続ストレージを確保してください。
- .env.local は .env を上書きする（優先）ため、ローカル機密情報を .env.local に置く運用が可能です。OS 環境変数は .env/.env.local より優先されます。
- ニュース RSS の取得では SSRF 対策や受信サイズ制限、XML パースの安全化（defusedxml）を行っていますが、運用では RSS ソースの管理を行ってください。
- シグナル→発注→約定のフローを完全にトレースするための監査テーブルを用意しています。実際のブローカー連携を行う際は order_request_id を冪等キーとして活用してください。
- テストや CI で自動ロードを抑止したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

フィードバックや改善点、追加したい機能があれば教えてください。README のサンプル .env.example や運用手順（cron/airflow のサンプル）など、さらに具体的なドキュメントも作成できます。