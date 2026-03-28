# KabuSys

日本株のデータプラットフォームおよび自動売買補助ライブラリ（KabuSys）の軽量リポジトリです。J-Quants / kabu ステーション / OpenAI を組み合わせ、データ ETL、ニュース NLP、ファクター研究、監査ログなどの機能を提供します。

> 本 README はソースコード（src/kabusys 以下）に基づいて作成しています。各機能の詳細は該当モジュールの docstring を参照してください。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ記録などを行うユーティリティ群です。主要な役割は次のとおりです。

- J-Quants API を使った日次株価・財務・カレンダーの差分 ETL（duckdb へ保存）
- RSS ベースのニュース収集とニュースの前処理（SSRF や XML 攻撃対策あり）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（銘柄別）評価（ai_score）
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム / バリュー / ボラティリティなど）と研究ユーティリティ
- 監査ログスキーマ（signal_events / order_requests / executions）を DuckDB に保存する初期化機能
- データ品質チェック（欠損・スパイク・重複・日付不整合）

---

## 主な機能一覧

- data.jquants_client
  - J-Quants API からのデータ取得（株価、財務、上場銘柄、カレンダー）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - レート制御とリトライ（401 の自動リフレッシュ含む）

- data.pipeline
  - run_daily_etl: 市場カレンダー → 株価 → 財務 → 品質チェックまでの一括 ETL
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult（実行結果のデータクラス）

- data.news_collector
  - RSS 取得、前処理、raw_news への冪等保存、銘柄紐付け（news_symbols）

- ai.news_nlp
  - calc_news_window / score_news: 指定ウィンドウのニュースを集約し OpenAI で銘柄ごとのセンチメントを算出・保存

- ai.regime_detector
  - score_regime: ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して市場レジームを判定・保存

- research.*
  - calc_momentum / calc_value / calc_volatility: ファクター算出
  - calc_forward_returns / calc_ic / factor_summary / rank: 研究支援ユーティリティ
  - data.stats.zscore_normalize: Z スコア正規化

- data.audit
  - 監査ログの DDL / インデックス定義
  - init_audit_schema / init_audit_db による監査 DB 初期化

- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks

---

## セットアップ手順

1. Python 環境を準備（推奨: Python 3.10+）
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate

2. 必須パッケージをインストール
   - 最低限必要な外部依存:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   - （プロジェクトに packaging があれば）editable インストール:
     - pip install -e .

3. 環境変数設定
   - .env または OS 環境変数で設定します。パッケージ起動時に自動で .env をロードします（ただしプロジェクトルートは .git または pyproject.toml で検出）。
   - 自動ロードを抑止したい場合:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知に使用する場合
     - SLACK_CHANNEL_ID — Slack 通知チャンネル
     - KABU_API_PASSWORD — kabuステーション API のパスワード

   - OpenAI API:
     - OPENAI_API_KEY を設定するか、score_news / score_regime に api_key を直接渡します。

   - 任意（デフォルト値あり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

   - 例 .env
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABU_API_PASSWORD=secret
     DUCKDB_PATH=data/kabusys.duckdb
     ```

4. DuckDB スキーマの準備
   - ETL や保存関数は対応するテーブル（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / prices_daily / ...）が存在することを前提とする箇所があります。プロジェクトにスキーマ初期化モジュール（data.schema 等）があればそれを実行してください。
   - 監査ログは data.audit.init_audit_db / init_audit_schema で初期化できます。

---

## 使い方（主要な呼び出し例）

下記は最低限の使用例です。実運用ではログ設定や例外ハンドリングを追加してください。

- 共通: settings の使用例
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)  # Path オブジェクト
  ```

- DuckDB 接続を作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 27))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を計算して ai_scores に保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY 環境変数が設定されていれば api_key を省略可
  written = score_news(conn, target_date=date(2026, 3, 27), api_key=None)
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームスコア計算（market_regime テーブルへ保存）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 27), api_key=None)
  ```

- 監査 DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, date(2026, 3, 27))
  val = calc_value(conn, date(2026, 3, 27))
  vol = calc_volatility(conn, date(2026, 3, 27))
  ```

注意:
- score_news / score_regime は OpenAI API を呼び出します。API 利用量・レート制限・コストに注意してください。
- ETL 周りは J-Quants API の認証トークンを必要とします（JQUANTS_REFRESH_TOKEN）。

---

## .env 読み込みの挙動

- 自動読み込み順序:
  1. OS 環境変数（既に設定されているものは保護）
  2. プロジェクトルート/.env （override=False：未設定のみセット）
  3. プロジェクトルート/.env.local （override=True：.env を上書き。ただし OS 環境変数は保護）

- プロジェクトルートの検出:
  - このパッケージは __file__ を基点に親ディレクトリを探索し、.git または pyproject.toml が見つかったディレクトリをプロジェクトルートと見なします。見つからない場合は自動ロードをスキップします。

- 自動ロードを無効化:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを抑制します（テスト時に便利）。

- .env のパース:
  - export PREFIX=... 形式に対応
  - クォート取り扱い、インラインコメント、エスケープ等に配慮したパーサを使用

---

## ディレクトリ構成（src/kabusys ベース）

主なファイル/モジュール（抜粋）:

- kabusys/
  - __init__.py
  - config.py  — 環境変数および設定管理
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント算出（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py        — ETL パイプライン / run_daily_etl / ETLResult
    - calendar_management.py — 市場カレンダー管理ロジック
    - news_collector.py  — RSS 取得・前処理
    - audit.py           — 監査ログスキーマ初期化
    - etl.py             — ETLResult のエクスポート
    - quality.py         — データ品質チェック
    - stats.py           — 統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py

（各モジュールは docstring に機能・設計方針・使い方が記載されています。詳細は該当ファイルを参照してください。）

---

## 運用上の注意点 / トラブルシューティング

- テーブルスキーマ
  - 保存関数（save_daily_quotes など）は対象テーブルが存在することを前提とします。スキーマ初期化用の関数/DDL が別にある場合は先に実行してください。
  - 監査用スキーマは data.audit.init_audit_db / init_audit_schema で初期化できます。

- OpenAI の呼び出し
  - レスポンスパース失敗や API エラーはフェイルセーフとしてスコアを 0.0 にフォールバックする実装箇所が多くあります（ログは出ます）。
  - API キーが無い場合、score_news / score_regime は ValueError を送出します。

- J-Quants API
  - レート制限（120 req/min）に合わせたレート制御と再試行ロジックを組み込んでいます。認証はリフレッシュトークン経由です。

- ニュース収集の安全対策
  - RSS のリダイレクトやホスト名に対して SSRF 対策を実施しています。XML パーサには defusedxml を使用しています。

---

## ライセンス / 貢献

- この README はコードベースに対する説明であり、実際のライセンス表記はプロジェクトルートの LICENSE ファイル等を参照してください。
- 貢献や修正はプルリクエストでお願いします。ユニットテストと型チェック（mypy など）の追加を推奨します。

---

もし README に追加してほしい項目（例: 具体的なスキーマ DDL、CI 設定、拡張方法のガイド）があれば教えてください。必要に応じてサンプル .env.example も作成します。