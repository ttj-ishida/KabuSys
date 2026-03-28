# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。  
ETL、ニュース収集、LLM を用いたニュースセンチメント、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ収集（J-Quants）、データ品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング（OpenAI を利用）、市場レジーム判定、監査ログ（発注→約定のトレーサビリティ）などを一貫して扱える内部ライブラリです。  
設計上、バックテストでのルックアヘッドバイアスを避けるため日付参照に注意した実装がなされています（多くのモジュールで `date` / `target_date` を明示的に受け取り、`date.today()` を直接参照しない等）。

主な用途:
- 日次 ETL（株価、財務、マーケットカレンダー）の差分取得と保存
- ニュース収集および銘柄ごとのセンチメント算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算・特徴量解析（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → execution の永続化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）

---

## 機能一覧

- 環境設定管理
  - 自動的にプロジェクトルートの `.env` / `.env.local` を読み込み（無効化可能）
  - 必須環境変数取得用ユーティリティ

- データ ETL（kabusys.data.pipeline）
  - J-Quants API 経由で株価日足 / 財務 / カレンダーを差分取得
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損、スパイク、重複、日付整合性）

- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証トークン自動リフレッシュ、レート制御、リトライ付き HTTP ラッパー
  - fetch / save 系の関数を提供

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存の想定

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄毎のセンチメントを JSON モードで取得
  - バッチ処理、トリミング、リトライ、レスポンスバリデーション

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を算出・保存

- 研究用（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、z-score 正規化

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のスキーマ初期化ユーティリティ
  - 監査用 DuckDB DB 初期化

- 汎用ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - カレンダー管理（営業日判定、next/prev_trading_day 等）

---

## セットアップ手順

前提:
- Python >= 3.10 を推奨（コードベースで Python 3.10 の構文を使用）
- DuckDB、OpenAI SDK、defusedxml 等を利用します

1. リポジトリをクローン / 開発環境に配置
   git clone <リポジトリ>
   cd <repo>

2. 仮想環境を作成・有効化（任意だが推奨）
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - 必要な最小パッケージ例:
     pip install duckdb openai defusedxml

   プロジェクトに requirements.txt / pyproject.toml があればその通りにインストールしてください。開発インストール:
     pip install -e .

4. 環境変数を設定
   プロジェクトルートに `.env` を作成すると自動読み込みされます（自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

   主な環境変数（最低限必要なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
   - SLACK_BOT_TOKEN: Slack 通知を使う場合
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI を使う場合（score_news / score_regime 呼び出し時に引数で渡すことも可能）
   - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス等（任意）
   - KABUSYS_ENV: development / paper_trading / live（デフォルトは development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   .env の例（テンプレート）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. データベース初期化（監査ログ用の例）
   以下は監査ログ用の DuckDB を初期化する例:
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   既定ではタイムゾーンを UTC に固定します。

---

## 使い方（主要な例）

以下は代表的なユースケースの最小サンプルです。各関数は DuckDB の接続オブジェクト（kabusys.data.* は DuckDB 接続）を受け取り操作します。

- 環境設定参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- 日次 ETL の実行:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI 必須）:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定:
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- RSS フィード取得（ニュース収集の単体ユーティリティ）:
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

- ファクター計算（研究用途）:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

注意:
- OpenAI 呼び出しを行う関数は `api_key` 引数でキーを注入できます。引数が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
- 多くの処理は外部 API（J-Quants / OpenAI）に依存するため、ネットワークアクセス・認証情報が必要です。

---

## 設計上の注意点 / 重要事項

- ルックアヘッドバイアス防止: 多くのモジュールが `target_date` を明示的に受け取り、データ取得クエリは target_date より前（排他）で集計する等の配慮が入っています。バックテストや研究で利用する際はこの契約を守ってください。
- 自動 .env 読み込み: パッケージはプロジェクトルート（.git または pyproject.toml を探索）から `.env` / `.env.local` を自動読み込みします。テスト時にこれを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI レスポンスは JSON モードで受け取り、レスポンスプラットフォームによる不整合に備えたパース・バリデーションを行います。API エラー時はフェイルセーフ（スコアを 0 にフォールバック）する実装が多くありますが、呼び出し側でログ・再試行ポリシーを検討してください。
- J-Quants API 呼び出しにはレート制限（120 req/min）やリトライロジックが実装されています。大量取得時は適切に ETL ジョブを分割してください。

---

## ディレクトリ構成

プロジェクトの主要ファイル / モジュール（src/kabusys を基準）:

- src/kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLP（OpenAI）
    - regime_detector.py     # 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py # マーケットカレンダー管理
    - etl.py                 # ETL公開インターフェース
    - pipeline.py            # 日次 ETL パイプライン
    - stats.py               # 統計ユーティリティ
    - quality.py             # データ品質チェック
    - audit.py               # 監査ログスキーマ初期化
    - jquants_client.py      # J-Quants API クライアント（fetch/save）
    - news_collector.py      # RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # 将来リターン、IC、統計サマリー
  - (その他)                  # strategy / execution / monitoring 等のエクスポート予定箇所

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取り DB に対して操作する設計です。ETL は id_token 等を注入可能にしてテストしやすくなっています。

---

## 開発・テストに関するヒント

- 自動 .env の読み込みを無効化する:
  KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストで環境を制御する際に有用）。
- OpenAI / J-Quants 呼び出しをテストする場合、各モジュールは内部の API 呼出しラッパーをモックできるように設計されています（例: unittest.mock.patch で _call_openai_api を差し替え）。
- DuckDB をインメモリで使うことでテストを軽量化できます（db_path=":memory:"）。
- ログレベルは環境変数 LOG_LEVEL で制御できます。

---

## ライセンス / 貢献

（この README にはライセンス情報が含まれていません。リポジトリルートに LICENSE ファイルを追加してください。）

貢献する際は、変更がデータ品質や安全性に影響する箇所（ETL、ニュース収集、API 呼び出し）については慎重なレビューをお願いします。

---

この README はコードベースの実装（主要モジュール、設定、使用例）に基づいて作成されています。必要であれば、具体的な実行コマンドや CI 設定、requirements/pyproject の追記サンプルを追加します。