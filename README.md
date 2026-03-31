# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants などからのデータ取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなど、取引システムやリサーチ環境で必要となる共通処理を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（日付は明示的に渡す／DB の過去データのみ参照）
- DuckDB を中心としたローカル DB ベースの ETL / 保存（冪等性を重視）
- OpenAI（gpt-4o-mini 等）を用いたニュース解析（JSON モード）
- API 呼び出しはリトライ・レート制御・フェイルセーフを実装

## 機能一覧
- 環境設定読み込み（.env 自動ロード、保護キー管理） — kabusys.config
- データ取得 / ETL（J-Quants クライアント、差分更新、品質チェック） — kabusys.data.pipeline, jquants_client, quality, calendar_management
- ニュース収集（RSS）と前処理 — kabusys.data.news_collector
- ニュース NLP スコアリング（OpenAI） — kabusys.ai.news_nlp
- 市場レジーム判定（MA + マクロニュースの LLM センチメント合成） — kabusys.ai.regime_detector
- 監査ログ／トレーサビリティ用スキーマの初期化・管理 — kabusys.data.audit
- ファクター計算・特徴量探索・統計ユーティリティ — kabusys.research, kabusys.data.stats
- データ保存ユーティリティ（DuckDB への冪等保存関数） — kabusys.data.jquants_client

## 必要要件
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

（実際のプロジェクトでは requirements.txt / pyproject.toml を用意して依存管理してください）

## セットアップ手順（例）
1. 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（プロジェクトに合わせて requirements を用意してください）
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数を設定
   - 必須（少なくともこれらを .env に用意するか環境変数でセット）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN : （通知がある場合）Slack Bot Token
     - SLACK_CHANNEL_ID : （通知がある場合）Slack チャンネル ID
     - KABU_API_PASSWORD : kabuステーション API パスワード（使用する場合）
   - オプション / デフォルト値あり
     - KABUSYS_ENV : development / paper_trading / live （default: development）
     - LOG_LEVEL : DEBUG / INFO / WARNING / ERROR / CRITICAL （default: INFO）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロードを無効化する場合に "1" を設定
     - KABU_API_BASE_URL : kabu API の base URL（default: http://localhost:18080/kabusapi）
     - DUCKDB_PATH : DuckDB ファイルパス（default: data/kabusys.duckdb）
     - SQLITE_PATH : モニタリング用 sqlite パス（default: data/monitoring.db）

   自動ロード機能:
   - パッケージ内の設定モジュールはプロジェクトルート（.git または pyproject.toml のある親）を探索し、
     .env を読み込み、さらに .env.local を上書き読み込みします。
   - OS 環境変数は上書きされません（.env の override は OS 環境変数を保護）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. DuckDB の初期化（監査ログ用 DB など）
   - 監査ログ用 DB を作成する簡単な例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - 既存の DuckDB 接続に監査スキーマを追加する場合は init_audit_schema を使用できます。

## 使い方（代表的な例）

- ETL（日次パイプライン実行）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キーは env OPENAI_API_KEY か api_key 引数で渡す）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すことも可能
  count = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print("scored", count)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続（UTC タイムゾーン設定済）
  ```

- RSS 取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点
- OpenAI 呼び出しはレート限界・コストに注意してください。API キーは環境変数 OPENAI_API_KEY で設定できます。
- ETL / データ取得関数はページネーション・リトライ・トークンリフレッシュ等の対策を組み込んでいますが、実運用ではログとエラーハンドリングを十分に行ってください。
- DuckDB の executemany は空リストを受け付けないバージョンがあるため、内部で空チェックを行っています。

## ディレクトリ構成（主要ファイル）
（提供されたコードベースからの抜粋）

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
    - pipeline.py
    - etl.py
    - jquants_client.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research に含まれるユーティリティ: zscore_normalize, calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank

（プロジェクト全体のトップレベルには pyproject.toml / .git / .env などが想定されます）

## テスト・開発のヒント
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して、テストで環境を手動で制御してください。
- OpenAI 呼び出しや外部 HTTP 呼び出しはユニットテストでモック可能な設計になっています（内部呼び出し関数に注入や patch が可能）。
- DuckDB でのテーブル存在チェックや executemany の取り扱いには実際のバージョン差異があるため、ローカル開発環境の DuckDB バージョンと合わせてテストしてください。

---

必要であれば、README に以下を追加できます：
- 具体的な requirements.txt / pyproject.toml の例
- テーブルスキーマ（raw_prices, ai_scores, market_calendar など）のドキュメント
- CI / デプロイ手順（監視・運用に関するガイド）
ご希望があれば追記します。