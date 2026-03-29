# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、研究用ファクター計算、データ品質チェック、監査ログ（オーディット）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ基盤と研究・自動売買パイプラインを構築するためのモジュール群です。主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント付与（AI スコア）
- マーケットレジーム判定（ETF + マクロニュースの LLM 判定）
- 研究（ファクター計算、将来リターン、IC、統計サマリー）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注フローの監査ログスキーマと初期化ユーティリティ（DuckDB）

設計方針として、ルックアヘッドバイアス回避、冪等性、堅牢なエラーハンドリング（リトライ・フォールバック）、および外部 API 呼び出しの安全化（SSRF 対策等）を重視しています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants クライアント（fetch/save 系）
  - market calendar 管理（is_trading_day / next_trading_day / get_trading_days）
  - news_collector（RSS 取得・前処理・保存ロジック）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログ（init_audit_schema / init_audit_db）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI でスコア化して ai_scores に書き込む
  - regime_detector.score_regime: ETF（1321）の MA とマクロ記事センチメントを合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- 設定管理
  - kabusys.config.settings: 環境変数経由の設定取得（自動 .env ロード機能あり）

---

## 必要要件（概略）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API, 各 RSS フィード, OpenAI API（利用時）

（パッケージ化 / 依存ファイルが無い場合はプロジェクトに合わせて requirements.txt を用意してください）

---

## セットアップ手順

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数の設定
   - プロジェクトルート（.git や pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（kabusys.config が起動時にロード）。
   - 自動ロードを無効化したい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注等を行う場合）
   - SLACK_BOT_TOKEN: Slack 通知用（任意だが設定されている箇所あり）
   - SLACK_CHANNEL_ID: Slack チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合）
   - その他（オプション）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視DB等、デフォルト: data/monitoring.db）

5. 例: .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=passwd
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C0123456
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

---

## 使い方（基本例）

以下は代表的なユースケースの Python スニペットです。DuckDB 接続には `duckdb` を使用します。

- ETL（日次パイプラインを実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースをスコアリングして ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None で環境変数 OPENAI_API_KEY を参照
  print(f"written {written} codes")
  ```

- 市場レジーム判定を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ファイルを作成してスキーマを初期化
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

---

## よく使う設定 / ヒント

- 自動 .env 読み込み
  - プロジェクトルートに `.env` / `.env.local` を置くと、kabusys.config が起動時に自動でロードします。
  - OS 環境変数は .env の上書きを防ぎます。.env.local は .env を上書きします。
- テスト時: 自動読み込みを無効化
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを停止できます（テストで明示的に環境を制御したい場合に便利）。
- OpenAI 呼び出しのフォールバック
  - ネットワークエラーや API の一時障害時、news_nlp / regime_detector はフェイルセーフ（スコア = 0.0、あるいは該当処理をスキップ）で継続します。
- DuckDB のバージョン差異
  - 一部 executemany の挙動やリストバインドに差異があるため、コード中に互換性対策（individual DELETE executemany 等）を入れています。DuckDB の推奨バージョンをプロジェクトに合わせて固定してください。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py
    - pipeline.py
    - stats.py
    - quality.py
    - audit.py
    - jquants_client.py
    - news_collector.py
    - etl.py (ETLResult re-export)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research の他モジュール（factor/feature）
- pyproject.toml / setup.cfg / README.md（本ファイル）

（各モジュールは README の「主な機能一覧」で触れた API を公開しています）

---

## トラブルシューティング

- 環境変数が足りない / KeyError や ValueError が出る場合:
  - 必須キー（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY など）が設定されているか確認してください。
  - kabusys.config.Settings のプロパティは未設定時に ValueError を投げます。
- DuckDB 接続周り
  - ファイルパスの親ディレクトリが存在しないとエラーになる箇所があります（init_audit_db は親ディレクトリを自動作成しますが、他は要確認）。
- OpenAI / J-Quants の API エラー
  - レート制限・ネットワーク障害は自動的にリトライされますが、継続的に失敗する場合は API キー／ネットワークを確認してください。
- RSS 取得で SSRF / ローカル IP 拒否
  - news_collector はリダイレクト先やホストのプライベートアドレスを拒否します。内部ネットワークの RSS を使う場合は設定を調整する必要があります（ただしセキュリティリスクに注意）。

---

## 開発・貢献

- コードの設計方針は各モジュール冒頭の docstring に記載されています（エラーハンドリング、冪等性、ルックアヘッドバイアスへの配慮など）。
- ユニットテストや CI の導入を推奨します。OpenAI / J-Quants 呼び出し部分はモック可能な設計（_call_openai_api の差し替え、jquants_client の get_id_token キャッシュなど）になっています。

---

必要に応じて README に含めるサンプル .env.example や requirements.txt、起動用 CLI スクリプト（例: run_etl.py, score_news.py）を追加できます。希望があればテンプレートや具体的な実行スクリプトの雛形も作成します。