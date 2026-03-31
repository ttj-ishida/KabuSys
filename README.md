# KabuSys

日本株の自動売買・データ基盤ライブラリ（KabuSys）のリポジトリ用 README。

このパッケージは J-Quants / kabu/station API からのデータ ETL、ニュース収集・NLP スコアリング、ファクター計算、監査ログ管理、及び市場レジーム判定などを提供します。DuckDB をデータストアに用いることを前提としたライブラリ群です。

---

## 概要

KabuSys は以下の目的を持つコンポーネント群を含む Python ライブラリです。

- J-Quants API からの株価・財務・カレンダー等の差分取得（ETL）
- RSS ベースのニュース収集と OpenAI を用いたニュースセンチメント解析（ai/news_nlp）
- マクロニュースと ETF MA を組み合わせた市場レジーム判定（ai/regime_detector）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と研究用ユーティリティ（research）
- データ品質チェック、マーケットカレンダー管理（data）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ定義と初期化（data.audit）
- 設定管理（環境変数自動読込 / config）

設計上の特徴：
- Look-ahead バイアスを避けるため date/datetime の扱いに配慮
- DuckDB を中心に SQL と Python の実装で効率的に処理
- OpenAI 呼び出しはリトライ・フェイルセーフを備える
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧（主要）

- data.jquants_client
  - J-Quants から日次株価、財務、上場情報、マーケットカレンダーの取得
  - DuckDB への冪等保存（save_* 系）
  - rate limiting / retry / token refresh を内包
- data.pipeline
  - 日次 ETL（run_daily_etl）: カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 結果を保持する ETLResult
- data.quality
  - 欠損、スパイク、重複、日付不整合などの品質チェック
- data.news_collector
  - RSS フィード取得、記事ID生成、前処理、raw_news への格納補助
  - SSRF 対策、レスポンスサイズ制限、XML の安全パース等
- data.calendar_management
  - market_calendar を基に営業日判定、next/prev_trading_day、get_trading_days 等
- data.audit
  - signal_events / order_requests / executions 等の監査スキーマ定義と初期化
  - init_audit_db で専用 DuckDB を初期化
- ai.news_nlp
  - 指定ウィンドウのニュースを銘柄ごとにまとめて OpenAI（gpt-4o-mini）でスコアリングし ai_scores に書込
- ai.regime_detector
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）を合成し market_regime に日次判定を書込
- research.*
  - ファクター算出（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化（data.stats）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の union 型 `X | Y` を使用）
- Git リポジトリのルートに `.env` / `pyproject.toml` 等を置くと config の自動読み込みが働きます

1. リポジトリをクローン
   (例)
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール
   最低限必要な外部依存（コードから読み取れる）:
   - duckdb
   - openai
   - defusedxml

   例:
   ```
   pip install duckdb openai defusedxml
   ```

   パッケージ化されている場合は:
   ```
   pip install -e .
   ```

4. 環境変数／.env の準備
   プロジェクトルートに `.env` や `.env.local` を作成すると自動読み込みされます（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須の環境変数（少なくとも実行する機能に応じて設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（data.jquants_client.get_id_token で使用）
   - KABU_API_PASSWORD     : kabu ステーション API のパスワード（発注連携を行う場合）
   - SLACK_BOT_TOKEN       : Slack 通知を使う場合
   - SLACK_CHANNEL_ID      : Slack 通知先チャンネル ID

   OpenAI を使う機能を使う場合:
   - OPENAI_API_KEY        : OpenAI API キー（ai.news_nlp / ai.regime_detector は引数で注入可能）

   オプション:
   - DUCKDB_PATH           : デフォルト data/kabusys.duckdb
   - SQLITE_PATH           : 監視用 SQLite データベース path
   - KABUSYS_ENV           : development | paper_trading | live （デフォルト development）
   - LOG_LEVEL             : DEBUG|INFO|WARNING|ERROR|CRITICAL

   例 .env（最小）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本的な例）

以下はライブラリをインポートして処理を実行する一例です。DuckDB のファイルパスは settings.duckdb_path で既定値を取得できます。

- 日次 ETL を実行する（データ取得 → 保存 → 品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 30))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成（ai.news_nlp）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 30))
  print("scored:", n_written)
  ```

  note: score_news は api_key 引数を受け取り、None の場合は環境変数 OPENAI_API_KEY を参照します。

- 市場レジーム判定を実行（ai.regime_detector）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 30))
  ```

- 監査ログ用 DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター算出（research）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,30))
  print(len(records), "records")
  ```

エラー処理・ログ:
- 各モジュールは logging を利用しています。LOG_LEVEL を環境変数で設定してください。
- OpenAI / J-Quants API 呼び出しはリトライとフェイルセーフ（多くの場合 0 値でフォールバック）を備えています。API キー未設定時は ValueError を送出します。

---

## 設定管理の挙動（自動 .env ロード）

- モジュール kabusys.config はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env`（優先度低） と `.env.local`（優先度高）を自動で読み込みます。
- OS 環境変数が優先され、`.env` で上書きしない既定動作です（`.env.local` は override=True で既存の値を上書き）。
- 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須となる getter（settings オブジェクト）:
- settings.jquants_refresh_token (JQUANTS_REFRESH_TOKEN)
- settings.kabu_api_password (KABU_API_PASSWORD)
- settings.slack_bot_token (SLACK_BOT_TOKEN)
- settings.slack_channel_id (SLACK_CHANNEL_ID)

その他:
- settings.duckdb_path / sqlite_path はデフォルト値を持ちます
- settings.env は `development | paper_trading | live` のいずれかでなければ例外

---

## ディレクトリ構成（概要）

以下はパッケージ内部の主要ファイル・モジュール（src/kabusys 以下）の一覧と簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py             -- 環境変数 / .env 自動ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py         -- ニュースの LLM センチメントスコアリング
    - regime_detector.py  -- マクロ + ETF MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py    -- J-Quants API クライアント、保存関数
    - pipeline.py         -- ETL パイプライン（run_daily_etl 等）
    - etl.py              -- ETLResult の再エクスポート
    - news_collector.py   -- RSS 取得・前処理
    - calendar_management.py -- market_calendar 管理 / 営業日判定
    - quality.py          -- データ品質チェック
    - stats.py            -- zscore_normalize 等の統計ユーティリティ
    - audit.py            -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  -- モメンタム/バリュー/ボラティリティなど
    - feature_exploration.py -- 将来リターン / IC / summary / rank
  - monitoring/ (present in __all__ but not shown in抜粋? 若干の監視系モジュール想定)
  - execution/, strategy/, monitoring/ などはパッケージ化や拡張ポイント

（上記はリポジトリ抜粋に基づく要約です。細かなファイルは実際の tree を参照してください）

---

## 開発・貢献

- コードスタイル：PEP8 に準拠
- テスト：ユニットテストはモジュール単位で OpenAI / ネットワーク呼び出しをモックする設計になっています（_call_openai_api の差し替え等）。
- Pull Request を歓迎します。重要な変更はドキュメントとタイプ注釈を付けてください。

---

## 注意事項 / セキュリティ

- RSS 取得は SSRF 対策や受信サイズ制限、XML の安全パース（defusedxml）を取り入れていますが、運用時は受信元リストの管理を徹底してください。
- 実取引（live モード）での使用は慎重に。KABUSYS_ENV の設定により live/paper_trading/development を切替え運用してください。
- API キー・認証情報は `.env` のままリポジトリにコミットしないでください。

---

この README はコードベース（src/kabusys/*.py）の抜粋に基づいて作成しています。追加の機能や CLI、サンプルスクリプト等はリポジトリ内に別途用意してください。必要であれば利用例や運用ガイドを追記します。