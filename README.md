# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu ステーション連携などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の責務を持つモジュール群をまとめたパッケージです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得し DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI を用いたニュースセンチメント（銘柄別）とマクロセンチメントから市場レジーム判定
- 研究用ファクター計算（モメンタム、ボラティリティ、バリューなど）と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ初期化ユーティリティ
- 環境変数管理（.env の自動ロード等）

設計方針の特徴：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- 冪等性（DB への保存は ON CONFLICT / DELETE→INSERT 等で安全に）
- フェイルセーフ（外部 API 失敗時に例外で止めずスキップして継続する箇所がある）
- DuckDB を主要なストレージとして利用

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント：fetch_* / save_*（kabusys.data.jquants_client）
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks（kabusys.data.quality）
- ニュース
  - RSS 取得・前処理（kabusys.data.news_collector）
  - 銘柄毎ニュースセンチメント計算（score_news、OpenAI 使用）(kabusys.ai.news_nlp)
- 市場レジーム
  - ETF（1321）MA200 乖離とマクロセンチメントを合成して regime 判定（score_regime、kabusys.ai.regime_detector）
- 研究用
  - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
  - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）
- 設定管理
  - Settings（kabusys.config）: .env 自動ロード、必須環境変数の取得

---

## 必要条件 / 依存 (例)

- Python >= 3.10（型注釈の union 演算子 (X | Y) を使用）
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ: urllib, json, datetime, logging など

（実際の packaging / requirements.txt はプロジェクトに合わせて用意してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 必要パッケージをインストール（例）

   ```bash
   pip install duckdb openai defusedxml
   # あるいはプロジェクトの requirements.txt を使用
   # pip install -r requirements.txt
   ```

3. パッケージをローカルインストール（オプション）

   プロジェクトが setuptools/pyproject を備えていれば:

   ```bash
   pip install -e .
   ```

4. 環境変数 / .env の用意

   プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（設定は kabusys.config を参照）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   最低限設定すべき環境変数（用途）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 用）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注を使う場合）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - その他（任意）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）

   例 (.env):

   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（サンプル）

以下は代表的な利用例です。Python スクリプトやジョブから呼び出して利用します。

- DuckDB 接続の用意（デフォルトパスは settings.duckdb_path）:

  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）:

  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントをスコア化して ai_scores に保存（score_news）:

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API キーは環境変数 OPENAI_API_KEY を設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジームを評価して market_regime に保存（score_regime）:

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算例:

  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（監査専用 DB を使う場合）:

  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 以後 audit_conn を用いて監査テーブルにアクセス可能
  ```

- ニュース RSS を取得（news_collector）:

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

注意点:
- OpenAI を使う関数は API 呼び出しに制限や課金が発生します。テスト時は該当モジュール内の _call_openai_api をモックすると安全です。
- J-Quants API は認証とレート制限があります。jquants_client はトークンリフレッシュ・レート制御を含んでいます。

---

## 設定（kabusys.config）について

- .env 自動ロードの優先順位:
  - OS 環境変数 > .env.local > .env
- 自動ロード無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動読み込みを行わなくなります（テストで利用）。
- 主な Settings プロパティ（参照例）:
  - settings.jquants_refresh_token（必須）
  - settings.kabu_api_password
  - settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
  - settings.line_channel_access_token, settings.line_user_id
  - settings.duckdb_path (デフォルト: data/kabusys.duckdb)
  - settings.sqlite_path (デフォルト: data/monitoring.db)
  - settings.env / is_live / is_paper / is_dev
  - settings.log_level

必須の環境変数が未定義の場合、Settings のアクセス時に ValueError を投げます（プログラム開始時に早期検出させることが可能）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

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
    - (その他: e.g. migration/schema 初期化ロジック等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ 以下は研究用ユーティリティ（ファクター計算、IC、統計サマリー）
  - その他サブパッケージ: execution, monitoring, strategy（パッケージ公開用 __all__ に含む可能性あり）

---

## 開発・運用上の注意

- DuckDB スキーマ
  - ETL / save_* 関数は所定のテーブル（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, prices_daily 等）を前提に動作します。事前にスキーマを用意してください（スキーマ初期化スクリプトを用意することを推奨）。
- テスト
  - OpenAI 呼び出し、HTTP 呼び出し、J-Quants とのやり取りはモックが推奨されます。ライブラリ内ではテスト時に差し替え可能な内部関数を用意しています（例: _call_openai_api の patch）。
- セキュリティ
  - news_collector は SSRF 対策や XML インジェクション対策（defusedxml）を実装していますが、運用時はネットワークポリシーや実行環境の制限も検討してください。
- レート制御・リトライ
  - jquants_client は内部で固定間隔スロットリングと指数バックオフを実装しています。J-Quants の利用規約に従って運用してください。
- ログレベル
  - settings.log_level でログレベルを制御可能。デフォルトは INFO。

---

## ライセンス・貢献

（ここにプロジェクトのライセンス情報や貢献ルールを記載してください）

---

README のサンプルは以上です。必要であれば以下について追記できます：

- さらに具体的なインストール手順（pyproject.toml / setup.cfg を含めたパッケージ化）
- DuckDB のスキーマ定義（CREATE TABLE 文のテンプレート）
- CI / テストの実行方法
- サービス運用時のコンフィグ例（systemd、コンテナ化、ジョブスケジューリング例）