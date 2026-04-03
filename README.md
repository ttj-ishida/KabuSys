# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング、研究用ファクター計算、監査ログスキーマ、マーケットカレンダー管理、レジーム判定などを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「DuckDB を用いた冪等な保存」「外部 API 呼び出しの堅牢化（リトライ／バックオフ）」です。

---

## 機能一覧

- data（kabusys.data）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 系関数、トークン自動リフレッシュ、レートリミット管理）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days、calendar_update_job）
  - ニュース収集（RSS 取得・前処理・SSRF 対策・raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付整合性検査）
  - 監査ログ初期化（監査用テーブル・インデックスの作成、init_audit_db）
  - 統計ユーティリティ（zscore 正規化等）

- ai（kabusys.ai）
  - ニュースセンチメント評価（score_news）
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントを ai_scores テーブルへ保存
    - バッチ処理・リトライ・レスポンス検証あり
  - 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次レジームを market_regime テーブルへ保存

- research（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
  - data.stats の zscore_normalize を利用

- 設定管理（kabusys.config）
  - .env 自動読み込み（プロジェクトルートを検出して .env/.env.local を読み込み）
  - 必須環境変数チェックと便利なプロパティ（settings オブジェクト）

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（他に標準ライブラリのみで実装している部分が多いですが、利用する機能に応じて追加パッケージが必要になる場合があります）

例: pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。
   - 下記の主要な環境変数を設定してください。

   推奨される環境変数（抜粋）

   - JQUANTS_REFRESH_TOKEN (必須)  
     J-Quants のリフレッシュトークン（ETL で使用）

   - OPENAI_API_KEY (必須 for AI 機能)  
     OpenAI API キー（score_news / score_regime に使用）。関数呼び出し時に api_key を引数で渡すことも可能。

   - KABU_API_PASSWORD  
     kabu ステーション等と連携する場合のパスワード

   - KABUSYS_ENV (optional)  
     実行環境: development / paper_trading / live（デフォルト: development）

   - LOG_LEVEL (optional)  
     ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

   - DUCKDB_PATH (optional)  
     デフォルト: data/kabusys.duckdb

   - SQLITE_PATH (optional)  
     デフォルト: data/monitoring.db

   - その他監視／LINE 関連の変数:
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID 等

   .env の自動読み込みはデフォルトで有効です。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易ガイド・コード例）

以下は代表的な利用例です。どの API も DuckDB の接続オブジェクト（duckdb.connect の戻り値）を受け取ります。

- ETL（日次 ETL）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントの実行（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に設定済み
  print("書き込んだ銘柄数:", written)
  ```

  - api_key を明示的に渡すことも可能:
    score_news(conn, target_date, api_key="sk-...")

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY 必須
  ```

- 監査用 DuckDB の初期化
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # あるいは既存接続へスキーマ追加:
  # conn = duckdb.connect("data/kabusys.duckdb")
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- market calendar の判定ユーティリティ（例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI への呼び出しはネットワーク／API エラーを想定してリトライ・フェイルセーフ設計になっています。API キーは環境変数 OPENAI_API_KEY または各関数の api_key 引数で提供してください。
- DuckDB のファイルパスは settings.duckdb_path により制御できます（既定は data/kabusys.duckdb）。

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは `src/kabusys` 下に配置されています。主なモジュール構成は以下の通り（抜粋）:

- kabusys/
  - __init__.py
  - config.py                   - 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                - ニュース NLP（score_news）
    - regime_detector.py         - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py          - J-Quants API クライアント（fetch/save）
    - pipeline.py                - ETL パイプライン（run_daily_etl 等）
    - etl.py                     - ETL 結果クラスの公開
    - calendar_management.py     - 市場カレンダー管理
    - news_collector.py          - RSS ニュース収集（SSRF 対策等）
    - quality.py                 - データ品質チェック
    - stats.py                   - 統計ユーティリティ（zscore_normalize）
    - audit.py                   - 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py         - ファクター計算（momentum/value/volatility）
    - feature_exploration.py     - 将来リターン / IC / summary 等

（README で抜粋しているため、実際のファイルはさらに細かく存在します）

---

## 環境変数と .env の取り扱い

- 自動ロード: package import 時にプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` → `.env.local` の順でロードします。
  - OS 環境変数は優先され、`.env.local` は `.env` より優先して上書きします。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

- 主要な変数（まとめ）
  - JQUANTS_REFRESH_TOKEN (必須)
  - OPENAI_API_KEY (AI 機能で必須)
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
  - KABUSYS_ENV (development / paper_trading / live)
  - LOG_LEVEL (DEBUG/INFO/...)

設定例（.env）
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 開発・拡張のポイント

- DuckDB の SQL を多用しており、SQL チューニングで性能改善が可能です。
- OpenAI 呼び出しはモジュール内で抽象化されているためテスト時はモックしやすく設計されています（_call_openai_api を patch）。
- ETL は冪等に設計されているため、スケジュールジョブで繰り返し実行できます。
- ニュース収集は SSRF / XML Bomb / 大容量レスポンス対策が実装されています。

---

必要に応じて README に含める具体的な .env.example、依存関係一覧（requirements.txt）、実行スクリプト（CLI/cron用のサンプル）、運用上の注意（API レート・コスト制御、OpenAI 使用量上限）を追加できます。詳細を追加したい箇所があれば教えてください。