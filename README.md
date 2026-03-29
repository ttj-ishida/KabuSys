# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）、研究用ファクター計算、監査ログ（発注・約定トレース）、および簡易な市場レジーム判定などを含むモジュール群を提供します。

---

## 主要な機能（抜粋）

- 環境設定管理
  - `.env` / 環境変数の自動読み込み（プロジェクトルート検出）
  - 必須設定の取得ユーティリティ
- データパイプライン（ETL）
  - J-Quants からの差分取得（株価・財務・カレンダー）
  - DuckDB へ冪等保存（ON CONFLICT による更新）
  - 品質チェック（欠損・重複・スパイク・日付整合性）
  - 日次 ETL の統合エントリポイント `run_daily_etl`
- データユーティリティ
  - マーケットカレンダー管理（営業日判定・next/prev 等）
  - ニュース収集（RSS）と前処理（SSRF対策・トラッキング除去）
  - 監査ログ（signal / order_request / execution テーブル）の初期化ユーティリティ
- 研究（research）
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリ
  - Zスコア正規化ユーティリティ
- AI（OpenAI）
  - ニュースのセンチメントスコアリング（gpt-4o-mini）: `kabusys.ai.news_nlp.score_news`
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）: `kabusys.ai.regime_detector.score_regime`
  - 両モジュールとも JSON Mode で LLM を呼び出し、堅牢なリトライやバリデーションを備えます

---

## 必要な環境変数

主に以下を使用します（README内の例は最小限）。実運用では `.env.example` を参照して設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知に使用（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で省略可能：api_key 引数でも指定可）
- DUCKDB_PATH: DuckDB ファイルパス（省略時: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（省略時: data/monitoring.db）
- KABUSYS_ENV: `development` / `paper_trading` / `live`（省略時: development）
- LOG_LEVEL: `DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`（省略時: INFO）

自動 `.env` 読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を探索し、`.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先されます。
- 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（開発用）

このリポジトリは src レイアウトを想定しています。仮想環境作成後、必要パッケージをインストールしてください。

1. Python 仮想環境（Python 3.10+ 推奨）を作成・有効化
   - 例: python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール
   - 最低限の依存例:
     pip install duckdb openai defusedxml
   - プロジェクト配布パッケージ（setup/pyproject がある場合）:
     pip install -e .

3. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成して上記の必須変数を設定
   - 例（簡易）:
     JQUANTS_REFRESH_TOKEN=あなたのトークン
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=Cxxxxx
     DUCKDB_PATH=data/kabusys.duckdb

4. DuckDB データベース用ディレクトリを作成
   - 例: mkdir -p data

備考:
- openai SDK のバージョンや挙動に依存する部分があるため、プロジェクトの requirements.txt / pyproject.toml を参照してください（存在する場合）。

---

## 使い方（主な API / 例）

下記はいくつかの主要な操作例です。conn は DuckDB 接続オブジェクト（duckdb.connect）です。

- DuckDB 接続と Settings
  ```python
  from kabusys.config import settings
  import duckdb

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL を実行（全 ETL + 品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- 個別 ETL（株価・財務・カレンダー）
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl

  fetched, saved = run_prices_etl(conn, target_date=date(2026,3,20))
  ```

- ニュースのセンチメントスコアリング（OpenAI キーは環境変数または引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 監査ログ用スキーマ初期化（既存 DB にテーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査ログ専用 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- RSS フィード取得（ニュース収集の低レベルユーティリティ）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

注意点:
- AI モジュールは OpenAI API に依存します。API キーや利用コストに注意してください。
- ETL / DB 書き込み操作は冪等性を念頭に設計されていますが、実運用前にテスト環境で確認してください。

---

## ディレクトリ構成（主要ファイル）

（src/layout 内の kabusys パッケージを抜粋）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings クラス（自動 .env ロード、必須キーチェック）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（OpenAI 呼び出し・バリデーション）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロ NLP 合成）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存関数・リトライ・レート制御）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py  — RSS 収集、前処理、SSRF 対策
    - quality.py         — データ品質チェック（欠損・重複・スパイク・日付整合）
    - stats.py           — 汎用統計ユーティリティ（Zスコア正規化等）
    - audit.py           — 監査ログ（DDL と初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター計算・探索用ユーティリティ）

各モジュールはドキュメント文字列とログ出力が充実しており、設計上の注意点（ルックアヘッドバイアス回避、冪等性、API リトライ、フェイルセーフの設計など）が記載されています。実運用時はソース内 docstring を参照してください。

---

## 開発・運用上の注意

- ルックアヘッドバイアス回避: 多くの処理は `date` 引数ベースで動作し、`datetime.today()` を直接参照しない設計です。バックテストでは必ず過去データのみを読み込むワークフローで使用してください。
- API キー/トークン管理: J-Quants / OpenAI などのキーは環境変数で安全に管理してください。`.env`はローカルのみで管理し、リポジトリにコミットしないでください。
- リトライ・レート制御: J-Quants クライアントは固定間隔のスロットリングとリトライを実装していますが、長時間バッチ運用時のレート制御設定は要確認です。
- テスト: AI 呼び出しや外部 API 呼び出しはモック可能なように設計されています（内部呼び出し関数を patch してテスト可能）。

---

必要であれば、導入手順の詳細化（pyproject.toml / requirements.txt からのインストール手順、CI/CD 用の例、運用用 systemd / cron ジョブ例）や、各 API の詳細な使い方サンプル（ETL の実行順序や scheduler 連携例）を追加で作成します。ご希望を教えてください。