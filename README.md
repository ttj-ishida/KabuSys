# KabuSys

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買基盤を支える Python ライブラリ群です。J-Quants / kabuステーション / RSS / OpenAI など外部データソースと連携し、ETL・データ品質チェック・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ周りの機能を提供します。

主な想定用途:
- 日次 ETL による株価・財務・マーケットカレンダー取得と DuckDB への保存
- ニュースの収集と LLM を用いた銘柄単位センチメント評価
- ファクター計算（モメンタム / ボラティリティ / バリュー等）と研究ツール
- 市場レジーム判定（ETF + マクロニュース）
- 取引監査ログ（監査テーブル）の初期化と管理

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動ロード（パッケージルート検出、無効化オプションあり）
  - 必須環境変数の取得とバリデーション

- データ ETL（kabusys.data.pipeline）
  - J-Quants から株価・財務・マーケットカレンダーを差分取得
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集、URL 正規化、SSRF/サイズ対策、raw_news への冪等保存

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメント評価（ai_scores テーブルへ書き込み）

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュースの LLM スコアを合成して daily の市場レジームを判定

- リサーチ（kabusys.research）
  - ファクター計算（momentum/value/volatility）・将来リターン計算・IC/統計サマリ等
  - z-score 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査 DB を DuckDB で初期化する helper

- J-Quants クライアント（kabusys.data.jquants_client）
  - API 呼び出し、ページネーション、トークン自動リフレッシュ、レートリミット/リトライ管理
  - DuckDB へ保存する save_* 関数群

---

## セットアップ手順

前提:
- Python 3.10 以上（Union 型記法などを利用）
- DuckDB を使用するための環境

1. リポジトリをクローン / コピー
   (パッケージ配布がある場合は pip install でも可)

   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（推奨）

   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 本リポジトリに requirements.txt がなければ最低限以下をインストールしてください。

   ```
   pip install duckdb openai defusedxml
   ```

   追加でネットワーク/HTTP 層を使う場合は標準ライブラリで対応していますが、必要に応じて他ライブラリを追加してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 例（.env）:

     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD（使用機能に応じて）
   - OpenAI 呼び出しを行う場合は OPENAI_API_KEY を設定するか、各関数に api_key 引数を渡してください。

5. インストール（開発モード）
   ```
   pip install -e .
   ```

---

## 使い方（主要ユーティリティの例）

以下はライブラリ API を直接使う簡単な例です。多くの関数は duckdb.DuckDBPyConnection を受け取ります。

- DuckDB 接続を作る（ファイル / メモリ）:

  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # ファイル
  # conn = duckdb.connect(":memory:")  # インメモリ
  ```

- 日次 ETL を実行する（J-Quants トークンは settings か id_token 引数経由）:

  ```python
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)  # target_date を省略すると今日（ただしカレンダー調整あり）
  print(result.to_dict())
  ```

- ニュース NLP（ai_scores を更新）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # target_date はスコア生成日（前日 15:00 JST ～ 当日 08:30 JST を対象）
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  # api_key を直接渡すことも可能: score_news(conn, date(2026,3,20), api_key="sk-...")
  ```

- 市場レジーム判定を行う:

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用の DuckDB を初期化する（order / execution テーブルを作る）:

  ```python
  from kabusys.data.audit import init_audit_db
  db_conn = init_audit_db("data/audit.duckdb")
  # transaction=True オプションは関数内で処理（デフォルト transactional=True が使われています）
  ```

- 設定参照 (環境変数は Settings 経由で取得):

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)       # Path オブジェクト
  print(settings.is_live)          # bool
  ```

注意点:
- AI 呼び出し（OpenAI）は API のエラーやレート制限に対するリトライを実装していますが、API キーとコスト管理は利用者の責任です。
- J-Quants クライアントはレート制限（120 req/min）やトークン自動更新を行います。ID トークンは settings.jquants_refresh_token から取得されます。

---

## ディレクトリ構成

以下はパッケージ内の主要なファイル / モジュール構成（src/kabusys 以下）です。実装の概要も併記します。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数ロード・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約して OpenAI でスコアリング、ai_scores へ保存
    - regime_detector.py
      - ETF MA とマクロニュース LLM を合成して market_regime を更新
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API 呼び出し・ページネーション・保存ロジック
    - pipeline.py
      - 日次 ETL 実装（run_daily_etl, run_prices_etl, ...）
    - etl.py
      - ETLResult の公開リダイレクト
    - news_collector.py
      - RSS 収集、前処理、SSRF / サイズ対策
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py
      - JPX カレンダー管理、営業日判定
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブル定義と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value などのファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリ、ランク関数

---

## 補足・運用上の注意

- .env の自動ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml の存在）を検出して `.env` / `.env.local` を読み込みます。
  - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

- Look-ahead bias 対策
  - 多くの処理は datetime.today() を直接参照せず、明示的な target_date を受け取るか、DB 内の最終更新日に基づいて処理します。バックテスト時は ETL の取得時点を適切に管理してください。

- トークンと秘密情報の管理
  - OpenAI / J-Quants / Slack / kabu API のトークンは秘匿し、安全に管理してください（CI シークレットや Vault の利用を推奨）。

- DuckDB の executemany の挙動について
  - DuckDB のバージョン差異により executemany に空リストを渡せないケースがあるため、実装では空チェックを行っています。

---

この README はコードベース（src/kabusys）をもとに作成しています。さらに詳細な利用例や運用手順（CI/定期ジョブ、モニタリング、Slack 通知の組み込み等）は運用環境や要件に合わせて追記してください。質問やサンプルスクリプトが必要であれば教えてください。