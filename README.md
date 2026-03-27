# KabuSys

日本株向け自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター計算、研究用ユーティリティ、監査ログ（トレーサビリティ）、市場レジーム判定などを提供します。

---

## 主な特徴（機能一覧）

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - レート制限管理・リトライ・トークン自動リフレッシュを備えた堅牢なクライアント
- ETL パイプライン
  - 差分取得（バックフィル対応）→ 保存（冪等）→ 品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次 ETL のエントリポイント（run_daily_etl）
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF 対策、トラッキングパラメータ除去、前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント解析（score_news）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）（score_regime）
- 研究用モジュール（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ、Zスコア正規化
- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定までのトレーサビリティ用テーブルの初期化ユーティリティ
  - DuckDB に監査専用 DB を作成する関数（init_audit_db / init_audit_schema）
- 設定管理
  - .env / .env.local / OS 環境変数から自動ロード（プロジェクトルートを検出）
  - 必須環境変数を明示的に要求する Settings API

---

## 必要条件

- Python 3.10+
- 主要依存（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他：requests 等の補助依存は実装に応じて必要）

requirements.txt はこのリポジトリに含まれていないため、上記ライブラリを環境に合わせてインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト

2. 仮想環境作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際の運用では追加の依存が必要になる場合があります。プロジェクトの pyproject.toml / requirements を参照してください。

4. 環境変数 (.env) を準備する  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として以下を設定します（例）:

   ```
   # .env の例
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_station_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 自動ロード機構:
     - OS 環境変数 > `.env.local` > `.env` の順で読み込み（`.env.local` は `.env` を上書き）
     - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定
     - プロジェクトルートは `.git` または `pyproject.toml` を基準に検出されます

5. DuckDB データベースディレクトリ等が必要なら作成してください（settings.duckdb_path の親ディレクトリなど）。

---

## 使い方（基本的な例）

以下はライブラリの主要機能を呼び出す最小例です。事前に必要な環境変数（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）を設定してください。

- 日次 ETL を実行する（データ取得・保存・品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())
  ```

- ニュース NLP のスコアリングを実行する（ai.news_nlp.score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY は env から自動取得されますが、引数で明示的に渡すことも可能
  written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"written scores: {written}")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査用 DuckDB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # settings.sqlite_path は監視DBパスのデフォルトを返します（例: data/monitoring.db）
  conn = init_audit_db(settings.duckdb_path)  # 任意パスを指定可能
  ```

- 設定アクセス例
  ```python
  from kabusys.config import settings
  print(settings.kabu_api_base_url)
  print(settings.is_live)
  ```

注意点:
- AI 関連の関数は OpenAI API キーが必要です（環境変数 OPENAI_API_KEY または関数引数で指定）。
- ETL や API 呼び出しはネットワーク・トークンに依存します。実運用ではトークン管理・ログ監視を行ってください。
- 多くの処理は DuckDB 接続を直接受け取ります。ローカル環境では settings.duckdb_path を使用して接続を作成してください。

---

## 主要モジュールとディレクトリ構成

リポジトリの主要なファイル／パッケージ（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込みと Settings クラス（J-Quants, kabu API, Slack, DB パスなど）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント解析（OpenAI）
    - regime_detector.py — マクロ + ETF MA200 から市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / rate limit）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - news_collector.py — RSS 収集と前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定・更新ジョブ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
    - stats.py — 汎用統計ユーティリティ（zscore 正規化等）
    - audit.py — 監査ログ（監査テーブル DDL / 初期化）
    - etl.py — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — forward returns / IC / 統計サマリ / rank 等
  - monitoring / strategy / execution / のためのプレースホルダパッケージ（パブリッシュ対象に含める意図）

（上記は実装済みの主要ファイルの概要です。詳細は個々のモジュールの docstring を参照してください。）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (オプション, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能を使う場合は必須)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

注意: settings は必須キーが未設定の場合に ValueError を投げます。

---

## 実装上の設計方針（簡潔）

- Look-ahead bias を避けるため、内部では date.today() / datetime.today() を不必要に参照しない（外部から target_date を渡すことを想定）。
- DuckDB をメインのローカルデータストアとして使用。INSERT は冪等（ON CONFLICT DO UPDATE）で保存。
- 外部 API 呼び出しはリトライ・バックオフ・レート制限をもち堅牢に実装。
- ニュース収集は SSRF / XML Bomb 等の攻撃に対する防御ロジックを実装。
- 品質チェックは Fail-Fast ではなく全件収集し、呼び出し側に判断を委ねる。

---

## 開発・寄稿について

- 型注釈とモジュール docstring を重視しています。機能追加や修正を行う際は既存の設計方針（Look-ahead 回避、冪等性、リトライ方針等）に従ってください。
- 自動ロードされる .env はプロジェクトルートを基準に検索します。テスト時等に自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

これで README の概要を終わります。  
個別の使い方（例: ETL パラメータの調整、OpenAI レスポンスモック、テスト戦略など）や実運用向けのデプロイ手順が必要であれば、用途に応じた追加ドキュメントを作成します。