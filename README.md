# KabuSys

日本株向けの自動売買 / データプラットフォーム ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集と NLP スコアリング・市場レジーム判定・リサーチ用ファクター計算・注文監査ログ等を含みます。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() 等を安易に参照しない）
- DuckDB を中心としたローカルデータレイヤ
- J-Quants API / OpenAI API 等の外部サービス呼び出しはリトライやレート制御を実装
- ETL / データ保存は冪等性を重視（ON CONFLICT 等）
- セキュリティ考慮（RSS 収集時の SSRF 対策、XML パースの安全化等）

---

## 機能一覧

- 環境設定
  - .env / .env.local の自動読み込み（必要に応じて無効化可）
  - 設定アクセスは `kabusys.config.settings` 経由

- データプラットフォーム（kabusys.data）
  - J-Quants API クライアント（fetch / save / token refresh / rate limiter）
  - ETL パイプライン（prices / financials / market calendar）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - ニュース収集（RSS → raw_news、SSRF・サイズ検査・ID 正規化）
  - 監査ログ（signal_events / order_requests / executions のスキーマ定義・初期化）

- AI（kabusys.ai）
  - ニュース NLP スコアリング（gpt-4o-mini を用いた銘柄ごとのセンチメント）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー等）
  - 特徴量解析ユーティリティ（将来リターン計算、IC、統計サマリー、ランク付け）
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- その他
  - DuckDB / SQLite パス設定（settings）
  - Slack トークン等の通知連携設定を環境変数で管理
  - 高度な例外 / ログ出力・フェイルセーフ（API 失敗時はフォールバック）  

---

## 必要条件

- Python 3.10 以上（PEP 604 の型記法などを使用しています）
- OS ネットワークアクセス（J-Quants / OpenAI / RSS 取得のため）
- 推奨パッケージ例（実際の requirements.txt / pyproject.toml を参照してください）:
  - duckdb
  - openai
  - defusedxml

（プロジェクトには pyproject.toml が含まれている想定です。パッケージ依存はそこからインストールしてください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .\.venv\Scripts\activate    # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml / requirements.txt がある場合はそれに従ってください。例:
     ```
     pip install -r requirements.txt
     ```
   - または開発インストール:
     ```
     pip install -e .
     ```

4. 環境変数を設定
   - .env をプロジェクトルート（.git または pyproject.toml があるトップレベル）に置くと自動で読み込まれます（.env.local は上書き優先で読み込み）。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

   必須（少なくとも以下を設定しておく必要がある箇所があります）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
   - OPENAI_API_KEY — OpenAI 呼び出しに使用（`score_news` / `score_regime`）
   - KABU_API_PASSWORD — kabuステーション API パスワード（注文周りで使用）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知に使用

   任意:
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live）
   - LOG_LEVEL（DEBUG / INFO / ...）

   サンプル .env（例）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主なユースケース）

以下はライブラリを直接使う簡単なサンプルコード例です。実運用ではログ設定やエラーハンドリングを追加してください。

- DuckDB 接続の準備
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次パイプライン）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（前日 15:00 JST ～ 当日 08:30 JST ウィンドウ）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news は OPENAI_API_KEY を環境変数から参照します（api_key 引数で上書き可）
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions テーブルが初期化されます
  ```

- マーケットカレンダー関係
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- リサーチ機能（例: モメンタム計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  recs = calc_momentum(conn, date(2026, 3, 20))
  # recs は各銘柄のファクター辞書のリスト
  ```

---

## 注意点 / 実運用上の考慮

- OpenAI 呼び出し
  - モデル: gpt-4o-mini（コード内参照）
  - API エラーやレート制限へのフォールバックを実装していますが、API キーの利用状況に応じたレート調整は運用側で管理してください。

- J-Quants
  - API レート制限（120 req/min）に合わせた内部 RateLimiter を使用
  - 401 の場合は自動でリフレッシュトークンから ID トークンを更新してリトライします

- ニュース収集
  - RSS のダウンロード時に SSRF 対策や最大受信サイズチェック、gzip 解凍後のサイズチェック等を行っています
  - XML の安全なパーシングには defusedxml を使用

- DuckDB の executemany に関する互換性（コード内コメント参照）
  - 空リストで executemany を呼ばないよう保護している箇所があります

- 環境変数の自動読み込み
  - .env / .env.local をプロジェクトルート (".git" または "pyproject.toml" があるディレクトリ) から読み込みます
  - 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                         # 環境設定管理 (.env 自動読み込み、Settings)
  - ai/
    - __init__.py
    - news_nlp.py                      # ニュースセンチメント（銘柄別）スコアリング
    - regime_detector.py               # 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py                # J-Quants API クライアント（fetch/save）
    - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
    - etl.py                           # ETL 結果型の公開（ETLResult）
    - news_collector.py                # RSS 収集・前処理
    - calendar_management.py           # マーケットカレンダー管理
    - quality.py                       # データ品質チェック
    - stats.py                         # 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                         # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py               # ファクター計算（momentum/value/volatility）
    - feature_exploration.py           # 将来リターン / IC / 統計サマリー 等

（上記以外に strategy / execution / monitoring 等のパッケージが存在する想定で __all__ に露出されています）

---

## 開発 / テスト

- 環境変数の自動ロードを無効化してユニットテスト実行する場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  pytest
  ```

- OpenAI 呼び出し等外部 API をテストでモックすることを想定した設計です（内部の _call_openai_api 等を patch 可能）。

---

## 貢献 / ライセンス

- この README はコードベースの概要・使い方を示すもので、実際の導入や運用にあたっては pyproject.toml / requirements.txt / CI 設定等を参照し、さらに環境ごとのセキュリティ・運用手順（鍵管理、ネットワーク制限、監視）を整備してください。

- ライセンス情報はリポジトリのトップレベルにある LICENSE を参照してください（ここには含まれていません）。

---

必要であれば、README にサンプル .env.example やよくあるトラブルシュート（OpenAI の rate limit、J-Quants の 401 対策、DuckDB のパーミッションなど）を追記します。どの項目を詳しく書きたいか教えてください。