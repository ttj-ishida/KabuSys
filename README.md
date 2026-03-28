# KabuSys

日本株向けの自動売買・データ基盤ライブラリ KabuSys の README。  
このリポジトリはデータ収集（ETL）、データ品質チェック、特徴量 / 研究モジュール、ニュース NLP、OpenAI を使った市場レジーム判定、監査ログ（発注/約定トレーサビリティ）等を含む内部ツール群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買／リサーチ基盤を構成するためのライブラリ群です。主な目的は以下です。

- J-Quants API を利用した株価・財務・市場カレンダーなどの差分 ETL
- DuckDB を用いたローカルデータストアと品質チェック
- ニュース収集（RSS）と OpenAI を用いたニュースセンチメント（銘柄別 ai_score）算出
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）
- ファクター計算・特徴量探索（モメンタム／バリュー／ボラティリティ等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 環境変数管理・設定ユーティリティ

設計上の特徴として、ルックアヘッドバイアス回避、冪等性（ON CONFLICT、IDempotency）、堅牢なエラーハンドリングとリトライ、外部 API 呼び出しの失敗をフェイルセーフにする方針を採っています。

---

## 機能一覧

- config: .env / 環境変数の読み込み、Settings オブジェクト
- data:
  - jquants_client: J-Quants API の取得 / 保存（ページネーション・リトライ・レート制限）
  - pipeline: 日次 ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - news_collector: RSS 収集・前処理・raw_news への保存ロジック（SSRF 対策等）
  - news_nlp: OpenAI を使った銘柄別ニュースセンチメント集計（score_news）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定（score_regime）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - calendar_management: 市場カレンダー管理（営業日判定 / next/prev_trading_day 等）
  - audit: 監査ログテーブル定義と初期化（init_audit_db / init_audit_schema）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- research:
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC、サマリー統計
- ai:
  - news_nlp.score_news: ニュースを LLM で評価して ai_scores テーブルへ書き込み
  - regime_detector.score_regime: 市場レジーム判定（ma200 + macro sentiment）

---

## セットアップ手順

1. Python バージョン
   - Python 3.10 以上を推奨（型ヒントに | を使っているため 3.10+）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 依存はプロジェクトに合わせて調整してください。最低限必要なパッケージ例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください。）

4. 環境変数（必須）
   - 以下はこのコードベースで参照される主な環境変数です。`.env` または `.env.local` に定義できます。
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY         : OpenAI API キー（score_news / score_regime で利用）
     - KABU_API_PASSWORD      : kabuステーションの API パスワード（必須）
     - KABU_API_BASE_URL      : kabu API のベース URL（省略時は http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN        : Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID       : Slack チャンネル ID（必須）
     - DUCKDB_PATH            : DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH            : SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV            : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
   - 自動ロード:
     - パッケージ import 時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索して `.env` と `.env.local` を自動で読み込みます。
     - `.env.local` が `.env` を上書きします。
     - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. DuckDB データベース初期化（監査ログ用例）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 他のテーブルスキーマはプロジェクト側で用意する想定（スキーマ初期化関数を追加して呼ぶ等）。

---

## 使い方（例）

以下は Python REPL / スクリプトからの基本的な呼び出し例です。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（pipeline.run_daily_etl）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコアを計算して ai_scores に保存（score_news）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定しておく
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（research）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  ```

- 設定を参照する（config）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- 多くの関数は OpenAI API キーや J-Quants トークンを環境変数から取得します。テスト時は引数で明示的に渡すこともできます。
- 関数群はルックアヘッドバイアスに配慮して設計されています（内部で date.today() を直接参照しない等）。

---

## ディレクトリ構成

主要なファイル/モジュールを抜粋したツリー表示:

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - audit (functions: init_audit_db, init_audit_schema)
    - etl.py (ETLResult re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/ (上記)
  - research/ (上記)
  - data/ (上記)

（リポジトリルートには pyproject.toml / .git / .env.example がある想定です。プロジェクトルートの探索は config._find_project_root により行われます。）

---

## 環境変数サンプル (.env の例)

例: .env（プロジェクトルートに配置）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

- `.env.local` はローカル専用上書き（機密情報やローカル設定）に使います。
- 自動読み込みを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ロギング / 環境モード

- 設定は Settings.log_level / Settings.env で制御できます。
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG / INFO / ...
- Settings.is_live / is_paper / is_dev を使用して実行時の分岐ができます。

---

## 開発・テストについて

- 外部 API 呼び出し（OpenAI / J-Quants / RSS）を行う関数は、ユニットテストではモック可能な構造になっています（内部の API 呼び出し関数を patch して差し替えられます）。
- DuckDB はインメモリ ":memory:" でも使用可能なのでテスト用 DB を簡単に作成できます。

---

## ライセンス・貢献

この README ではライセンスについての記述は省略しています。実際のリポジトリでは LICENSE を追加してください。貢献する場合は PR と issue を通じてお願いします。

---

以上がこのコードベースの README.md の要約です。必要に応じて、実行例（スクリプト化）、DB スキーマの初期化手順、CI 用のセットアップ手順などを補足できます。どの部分を詳しく書いてほしいか教えてください。