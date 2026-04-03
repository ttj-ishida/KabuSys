# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants からのデータ取得（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

---

## 概要

KabuSys は日本株のデータパイプラインとリサーチ／AI 支援のためのユーティリティ群を収集した Python モジュール群です。主な目的は以下です。

- J-Quants API を利用した差分 ETL（株価・財務・市場カレンダー）の実行
- RSS ニュース収集 → OpenAI による銘柄別ニュースセンチメント付与
- ETF（1321）ベースとマクロニュースの合成による市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定に至る監査ログスキーマと初期化ユーティリティ
- 研究用ファクター計算・特徴量解析のユーティリティ

設計上の特徴として、ルックアヘッドバイアスを防ぐ実装（内部で date.today() を不用意に参照しない等）、DuckDB を用いたオンプレミス／軽量 DB 前提、OpenAI の JSON Mode を用いた堅牢な API 呼び出しとリトライ、SSRF 対策を含む RSS パーシング等があります。

---

## 機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（株価、財務、カレンダー、上場情報）
  - ニュース収集: RSS 取得・前処理・raw_news への保存ロジック
  - データ品質チェック: 欠損・スパイク・重複・日付不整合検出
  - カレンダー管理: 営業日判定・前後営業日検索・カレンダー更新ジョブ
  - 監査ログ初期化: init_audit_schema / init_audit_db（監査テーブル、インデックス）
  - 統計ユーティリティ: zscore_normalize
- ai
  - score_news(conn, target_date, api_key=None): 銘柄別ニュースセンチメントを ai_scores テーブルへ書き込み
  - score_regime(conn, target_date, api_key=None): ETF 1321 の MA200 乖離とマクロニュースを合成して market_regime を更新
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数経由での設定管理（自動でプロジェクトルートの .env / .env.local を読み込み）

---

## 前提 (推奨)

- Python >= 3.10（型ヒントに `X | Y` を使用しているため）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（v1 系）
- defusedxml（RSS パースの安全性のため）
- ネットワーク到達可能な J-Quants API / OpenAI API キー（利用する機能による）

最低限のパッケージ例:
- duckdb
- openai
- defusedxml

---

## セットアップ手順

1. リポジトリをクローン / プロジェクトフォルダへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境の作成（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール

   代表的な依存をインストールする例:

   ```bash
   pip install duckdb openai defusedxml
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。）

4. 環境変数の設定

   プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（デフォルト）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数例（.env）:

   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

   Settings クラスに対する主なキー:
   - JQUANTS_REFRESH_TOKEN (必須 for jquants)
   - OPENAI_API_KEY (score_news / score_regime の呼び出し時に必要)
   - KABU_API_PASSWORD（kabu API を使う場合）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視 DB 用）
   - KABUSYS_ENV（development|paper_trading|live）

---

## 使い方（いくつかの例）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続に既定のファイルパスを使う例を示します。

- ETL（日次パイプライン）を実行する

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必要）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", written)
  ```

- 市場レジーム判定（OpenAI 必要）

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ DB 初期化

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  # テーブルが作成され、UTC タイムゾーンに設定されます
  ```

- 研究用: ファクター計算や forward returns

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  recs = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(recs))
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。API キーが未設定の場合は ValueError が発生します（api_key 引数または環境変数 OPENAI_API_KEY）。
- ETL は J-Quants にアクセスします。JQUANTS_REFRESH_TOKEN が必須です。
- デフォルトで .env / .env.local を自動読み込みします。テスト時等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## 設定（Settings）について

- 自動読み込み優先度: OS 環境変数 > .env.local > .env
- .env の記法は一般的な形式をサポート（export プレフィックス、シングル/ダブルクォート、コメント等）
- 必須のキーにアクセスすると未設定時にエラーを投げます（例: settings.jquants_refresh_token）

---

## ディレクトリ構成

以下は主要なファイルとモジュールのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - data/
      - __init__.py
      - pipeline.py
      - etl.py (再エクスポート等)
      - jquants_client.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - (その他: e.g., chron jobs / clients)
    - (strategy/, execution/, monitoring/ は __all__ に含まれている想定)

説明:
- kabusys/config.py: 環境変数と .env 自動読み込み、Settings を提供
- kabusys/data: データ取得・保存・品質・カレンダー・監査関連
- kabusys/ai: OpenAI を使ったニュース NLP とレジーム判定
- kabusys/research: ファクターと特徴量解析用のユーティリティ

---

## 開発・運用上の注意

- API 呼び出しは外部サービス依存のためリトライ/フェイルセーフ実装がされていますが、キー設定やネットワークは必須です。
- DuckDB のバージョンによっては executemany の振る舞い等に差があるため、運用時は推奨バージョンでの検証を推奨します。
- ニュース収集では SSRF 対策や XML パースの安全性（defusedxml）を実装しています。RSS ソースの追加時に URL 検証ロジックに注意してください。
- 監査テーブルは削除しない前提の設計です。スキーマ変更時は互換性に注意してください。
- KABUSYS_ENV による動作モード（development / paper_trading / live）を実装しており、本番接続時のフラグ管理に利用します。

---

## ライセンス・貢献

（リポジトリに合わせてライセンスやコントリビュート方法を記載してください）

---

README に記載漏れや、実際に実行したいユースケース（例: 「毎朝 ETL を cron で回したい」「バックテスト用にニューススコアを過去日で付与したい」等）があれば教えてください。具体的なスクリプト例や cron/systemd ユニット、Docker 化手順などのテンプレートを追加できます。