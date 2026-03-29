# KabuSys

日本株向けの自動売買 / データ基盤 / 研究ライブラリ群。  
ETL・データ品質チェック・ニュース収集・LLM を利用したニュースセンチメントや市場レジーム判定、ファクター計算・探索などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能
- 前提・依存
- セットアップ手順
- 環境変数（.env）説明
- 使い方（よく使う API 例）
- ディレクトリ構成
- 設計上の注意点

---

## プロジェクト概要
KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。  
主な目的は以下のとおりです。

- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- ニュース収集（RSS）と NLP（OpenAI）による銘柄別センチメント算出
- 市場レジーム判定（ETF の MA とマクロニュースの合成）
- 監査ログ（signal → order_request → execution）のための DuckDB スキーマ
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェックモジュール

設計上、ルックアヘッドバイアスを避ける実装やフェイルセーフ（API 失敗時のフォールバック）を意識しています。

---

## 主な機能
- ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- J-Quants クライアント（取得／保存：daily_quotes / financial_statements / market_calendar）
- ニュース収集（RSS → raw_news / news_symbols 保存）
- ニュース NLP（score_news: OpenAI による銘柄別センチメント）
- 市場レジーム判定（score_regime: ETF MA とマクロニュースの合成）
- 研究モジュール（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマの初期化（init_audit_schema / init_audit_db）

---

## 前提・依存
主な依存パッケージ（プロジェクトルートの requirements.txt を参照してくださいが、最低限）:
- Python 3.10+（型ヒントに Union 演算子等を想定）
- duckdb
- openai (OpenAI の新 SDK を使用するコードに対応)
- defusedxml

外部サービス:
- J-Quants API（リフレッシュトークン）
- OpenAI API（gpt-4o-mini を利用するための API キー）
- kabuステーション API（売買実行がある場合）
- Slack（通知がある場合）

---

## セットアップ手順

1. リポジトリをクローンし仮想環境を作成
   - 例:
     ```
     git clone <repo>
     cd <repo>
     python -m venv .venv
     source .venv/bin/activate
     ```

2. 依存パッケージをインストール
   - 例:
     ```
     pip install -r requirements.txt
     ```
   - 開発中にローカルで利用する場合:
     ```
     pip install -e .
     ```

3. 環境変数を設定
   - プロジェクトルートに `.env` として必要なキーを保存（次節参照）。
   - 設定は OS 環境変数 > .env.local > .env の優先順位で読み込まれます。
   - 自動で .env の自動読み込みを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. データベースの準備
   - DuckDB を用いる例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 監査用 DB を別ファイルで初期化すると、監査スキーマを含む DuckDB 接続が返ります。

---

## 環境変数（例と説明）
プロジェクトは .env（または環境変数）から設定を読み取ります。主要なキー:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector に必要。関数引数でも渡せます）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注を行う場合）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 "http://localhost:18080/kabusapi"）
- SLACK_BOT_TOKEN: Slack ボットトークン（通知用）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知先）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB 等のパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

注意: Settings クラスで必須キーは未設定のままだと ValueError を投げます。

---

## 使い方（代表的な例）

以下は単純な Python スクリプト例です。DuckDB 接続は duckdb.connect(...) で生成します。

- 日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成（OpenAI API キーを引数で渡すことも可能）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} codes")
  ```

- 市場レジーム判定を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査 DB 初期化（新規ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究モジュールの利用例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.research.feature_exploration import calc_forward_returns

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  momentum = calc_momentum(conn, target)
  fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
  ```

---

## ディレクトリ構成（主要ファイル）
（src 以下を想定）

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
    - etl.py (ETL の公開インターフェース)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (ディレクトリがある想定: 監視用コード)
  - strategy/ (戦略実装用モジュールの想定)
  - execution/ (発注/ブローカー連携モジュールの想定)

（上記は主要モジュールの一覧です。プロジェクトルートには pyproject.toml や .env.example を置く想定です。）

---

## 設計上・運用上の注意
- ルックアヘッドバイアスの回避: 多くのモジュールは date 引数による明示的な基準日を受け取り、内部で date.today()/datetime.now() に依存しない設計です。バックテスト時は必ず適切な基準日を与えてください。
- フェイルセーフ: 外部 API（OpenAI / J-Quants 等）の一部失敗はフォールバック（スコア=0 等）で継続する実装が多くあります。重要処理では戻り値/ログを確認してください。
- 本番発注: KABUSYS_ENV が "live" の場合にのみ実際の発注ロジックを有効化する等のガードを設けることを推奨します（コードベースでも環境チェックが利用されています）。
- .env の自動読み込み: package の config モジュールはプロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動で読み込みます。自動読み込みを無効化したいテストなどでは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DB 操作: DuckDB のバージョン差異により executemany の挙動等に差が出る可能性があります。運用環境の DuckDB バージョンを合わせてください。

---

もし README に追加したい内容（例: デプロイ手順、CI/CD、より詳しい API リファレンス、サンプル .env.example）や、特定モジュールの詳しい使い方があれば教えてください。README をその内容に合わせて拡張します。