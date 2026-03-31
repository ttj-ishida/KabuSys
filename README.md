# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。  
ETL（J-Quants）、ニュース収集、LLM を使ったニュースセンチメント、ファクター計算、監査ログなどを含むモジュール群を提供します。

主な設計方針:
- ルックアヘッドバイアスに注意した日付取り扱い
- DuckDB を中心としたローカルデータストア
- J-Quants API 呼び出しはレート制限・リトライ・トークン自動更新対応
- OpenAI（gpt-4o-mini）を使ったニュース NLP / レジーム判定の仕組み
- 冪等性（ON CONFLICT / order_request_idによる二重発注防止）・監査ログ

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価（日足）、財務データ、JPX カレンダーを差分取得して DuckDB に保存（jquants_client / pipeline）
  - ETL 結果を ETLResult として返却・ログ出力（run_daily_etl）

- ニュース収集 / 前処理
  - RSS フィードの取得、URL 正規化、トラッキングパラメータ除去、raw_news テーブルへの冪等登録（news_collector）

- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に投げ、センチメントを ai_scores テーブルへ書き込み（news_nlp.score_news）
  - マクロ記事の集合を LLM で評価し、ETF 200 日 MA と合成して市場レジームを判定（regime_detector.score_regime）

- 研究用 / ファクター計算
  - モメンタム / ボラティリティ / バリューなどのファクター計算（research.*）
  - 将来リターン計算、IC（スピアマン）や統計サマリー（feature_exploration）

- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出（data.quality.run_all_checks）

- カレンダー管理
  - market_calendar の取得・判定ユーティリティ（is_trading_day, next_trading_day 等）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions のテーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（config.settings）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+

主な Python パッケージ（最低限）
- duckdb
- openai
- defusedxml

（実行環境に応じて追加ライブラリが必要になる場合があります。requirements.txt や pyproject.toml を用意している場合はそれに従ってください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン、作業ディレクトリへ移動
   - git clone ...
   - cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements/pyproject があればそちらを利用してください）

4. 環境変数設定
   - プロジェクトルート（.git か pyproject.toml のあるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例 (.env):
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション（約定用）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # システム
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. DB 初期化（監査ログ用 DuckDB の例）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # または既存の conn を使って init_audit_schema(conn)
   ```

---

## 使い方（主要なサンプル）

共通: 設定は kabusys.config.settings から取得できます。自動で .env を読み込むため、環境変数を用意しておくこと。

- ETL（日次）を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアを付ける（OpenAI API キーが必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を直接渡すことも可能（None の場合は環境変数 OPENAI_API_KEY を参照）
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)
  print(f"scored {n_written} codes")
  ```

- 市場レジームを判定して保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- 監査ログスキーマを既存 DuckDB に追加
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算 / 研究用ユーティリティ
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  ```

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector などで使用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（注文周り）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると自動 .env ロードを無効化

設定値が必須で未設定の場合、kabusys.config.Settings の該当プロパティは ValueError を投げます。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py  -- 環境変数 / .env 読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py        -- ニュースセンチメント（OpenAI）
    - regime_detector.py -- マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  -- J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py        -- ETL のエントリポイント（run_daily_etl 他）
    - etl.py             -- ETLResult の再エクスポート
    - news_collector.py  -- RSS 取得・前処理・保存
    - calendar_management.py -- 市場カレンダー管理・判定ユーティリティ
    - quality.py         -- データ品質チェック
    - stats.py           -- 汎用統計（zscore_normalize）
    - audit.py           -- 監査ログスキーマ / init
  - research/
    - __init__.py
    - factor_research.py -- ファクター計算（momentum, value, volatility）
    - feature_exploration.py -- 将来リターン / IC / 統計サマリー
  - ai/, data/, research/ の各モジュールは、DuckDB 接続を受け取る設計で、
    バックテストやバッチ処理から安全に呼べるようになっています。

---

## 注意点 / 設計上の重要事項

- 日付の扱い
  - ほとんどの関数は内部で datetime.today() や date.today() を直接参照しない（引数で target_date を受け取る設計）。バックテストでのルックアヘッドバイアスを防止しています。

- 冪等性
  - ETL / 保存処理は基本的に ON CONFLICT DO UPDATE を用いた冪等設計です。

- 外部 API の扱い
  - J-Quants および OpenAI 呼び出しにはリトライ/バックオフ/レート制御が実装されています。APIキーは環境変数または関数引数で渡してください。

- セキュリティ
  - news_collector は SSRF 対策、XML パースに defusedxml を使用、レスポンス上限を設けるなど安全策が組み込まれています。

---

## 追加 / 開発メモ

- テストを書く際は、API 呼び出しをモック（unittest.mock.patch）して外部へのアクセスを防いでください。モジュール内の _call_openai_api, _urlopen 等はテストで差し替えやすく設計されています。
- production（live）用途では KABUSYS_ENV を `live` に設定し、十分な監視と注文リスク管理を実装してください。
- 監査ログ（audit）テーブルは削除しない前提です。order_request_id は冪等キーとして重要です。

---

必要であれば、README の英語版や具体的な例（docker-compose、systemd ジョブ、CI 設定、requirements.txt / pyproject.toml のテンプレート）も作成できます。どの部分を優先しますか？