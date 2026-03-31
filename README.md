# KabuSys

日本株向け自動売買・データプラットフォームライブラリ（バージョン 0.1.0）

KabuSys は J-Quants / kabuステーション 等のデータソースと連携して、
データの ETL、品質チェック、ニュース NLP、マーケットレジーム判定、
リサーチ用ファクター計算、監査ログ（注文→約定のトレーサビリティ）を
提供する Python モジュール群です。

## 特徴（機能一覧）

- 環境変数管理（.env 自動読み込み、上書き制御）
- J-Quants API クライアント
  - 日次株価（OHLCV）、財務データ、マーケットカレンダー取得（ページネーション対応）
  - レートリミッティング、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（run_daily_etl, 個別 ETL ジョブ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と NLP スコアリング（OpenAI）
  - ニュース→銘柄マッピング、記事前処理、SSRF対策、サイズ制限
  - gpt-4o-mini を用いた JSON モードでのセンチメント取得
- マーケットレジーム判定（ETF 1321 の MA とマクロニュースを合成）
- 研究用モジュール（ファクター計算、将来リターン、IC・統計サマリー）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）
- 複数 DB パス設定（DuckDB / SQLite）

---

## 必要要件

- Python 3.10+
- 主要依存パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml

プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してインストールしてください。
例:
```bash
pip install duckdb openai defusedxml
# またはローカルで editable install
pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 展開する。

2. 仮想環境を作る（推奨）:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール:
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定:
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主要環境変数（必須／推奨）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合は必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視等）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境（development / paper_trading / live、デフォルト development）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   ※ .env.example を参考に .env を作成してください（リポジトリにない場合は上記キーを参照）。

5. データディレクトリ作成（必要に応じて）:
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要な例）

以下は代表的な利用例です。関数は duckdb の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

- DuckDB 接続の例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL の日次実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定しない場合は今日の日付が使われます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア付与（OpenAI API キーは環境変数 OPENAI_API_KEY で取得されるか、api_key 引数で指定）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("scored", n_written, "codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例: モメンタム）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

注意:
- AI 関連関数は OpenAI API を呼び出します。料金・レートに注意してください。
- ETL / データ操作は DuckDB に対する INSERT/UPDATE を実行します。事前にスキーマ初期化が必要な場合があります（運用スクリプト等でスキーマ作成を行ってください）。

---

## 環境変数と設定（Settings API）

ライブラリ内部では `kabusys.config.settings` を通じて各種値にアクセスします。主なプロパティ:

- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token
- settings.slack_channel_id
- settings.duckdb_path (Path)
- settings.sqlite_path (Path)
- settings.env / settings.is_live / settings.is_paper / settings.is_dev
- settings.log_level

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われ、優先順位は OS 環境変数 > .env.local > .env です。テスト等で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成

主要なファイル / モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py                - パッケージメタ（__version__=0.1.0）
  - config.py                  - 環境変数/.env 管理と Settings
  - ai/
    - __init__.py
    - news_nlp.py              - ニュースの NLP スコアリング（score_news）
    - regime_detector.py       - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        - J-Quants API クライアント（fetch/save 系）
    - pipeline.py              - ETL パイプライン（run_daily_etl 等）
    - etl.py                   - ETL の公開型（ETLResult）
    - stats.py                 - 統計ユーティリティ（zscore_normalize）
    - quality.py               - データ品質チェック
    - calendar_management.py   - マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py        - RSS ニュース収集（fetch_rss 他）
    - audit.py                 - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py       - ファクター計算（momentum / volatility / value）
    - feature_exploration.py   - 将来リターン・IC・統計サマリー等

各モジュールには docstring と設計コメントが含まれており、DuckDB を使った SQL＋Python の処理や API 呼び出しのリトライ/フェイルセーフ設計がされています。

---

## 運用上の注意・セキュリティ

- API トークンやパスワードは決してリポジトリにコミットしないでください。`.env` は .gitignore に追加してください。
- OpenAI / J-Quants / 証券 API などの呼び出しは課金・レート制限対象です。ロギングや retry の挙動を理解してから運用してください。
- DuckDB への書き込みは冪等化されていますが、実運用ではバックアップ・監視を推奨します。
- news_collector は外部 URL をダウンロードするため SSRF 対策・受信サイズ制限等の安全策が組み込まれていますが、さらに sandbox 環境でテストすることを推奨します。

---

もし README の追加情報（例: pyproject.toml でのインストール手順、CI 設定、サンプルスキーマ SQL、.env.example のテンプレート等）が必要であれば、必要な項目を教えてください。