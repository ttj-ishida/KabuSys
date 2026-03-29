# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants）、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを含んだモジュール群です。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買システムおよびデータプラットフォームのためのユーティリティ群です。主な目的は次の通りです。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS ニュース収集と記事の前処理 / 銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）およびマクロセンチメント合成による市場レジーム判定
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック
- 監査ログ（signal_events / order_requests / executions）用スキーマ生成・初期化

設計上の留意点として、バックテスト等でのルックアヘッドバイアスを防ぐ工夫（API 呼び出しタイミングの扱い、日付フィルタなど）や、外部 API 呼び出しのリトライ／フォールバック処理、DB への冪等保存が組み込まれています。

---

## 機能一覧

- Data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（差分取得・保存・ページネーション対応・トークン自動更新）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS）・前処理（SSRF対策、gzip制御、トラッキングパラメータ削除など）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- AI
  - ニュース NLP スコアリング: score_news (銘柄単位のセンチメント → ai_scores)
  - 市場レジーム判定: score_regime (ETF 1321 の MA200 乖離 + マクロニュースセンチメント合成)
- Research
  - ファクター計算: calc_momentum, calc_value, calc_volatility
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank

---

## 必要条件

- Python 3.10 以上（PEP 604 型記法などを使用）
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

実行環境や使用機能によりさらに必要なパッケージ・外部サービス（kabuステーション接続など）が増えます。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml に依存関係を定義してください。

4. 環境変数 (.env) を用意  
   リポジトリルート（.git や pyproject.toml がある場所）に `.env` / `.env.local` を置くと、自動で読み込まれます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   推奨される環境変数（例）:

   - JQUANTS_REFRESH_TOKEN=...         （必須: J-Quants リフレッシュトークン）
   - OPENAI_API_KEY=...                （必須: OpenAI API キー、score_news/score_regimeで使用）
   - KABU_API_PASSWORD=...             （必須: kabuステーション API パスワード）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （任意: デフォルトは上記）
   - SLACK_BOT_TOKEN=...               （必須: Slack 通知を使う場合）
   - SLACK_CHANNEL_ID=...              （必須: Slack 通知を使う場合）
   - DUCKDB_PATH=data/kabusys.duckdb    （任意: デフォルト）
   - SQLITE_PATH=data/monitoring.db     （任意: デフォルト）
   - KABUSYS_ENV=development|paper_trading|live  （任意, デフォルト: development）
   - LOG_LEVEL=INFO|DEBUG|...          （任意）

   .env の書式は shell の KEY=VALUE に準じます。`config.py` の自動読み込みでは `.env` → `.env.local` の順に上書きされます（OS 環境変数が優先されます）。

---

## 使い方（主要な例）

下記は最小限の Python スニペット例です。実運用ではロギング設定やエラーハンドリング、スケジューラ等を用意してください。

- DuckDB 接続の取得（デフォルトパスを使用）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する（市場カレンダー / 株価 / 財務 / 品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの ai_scores 書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境か引数で必要
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written codes:", n_written)
  ```

- 市場レジーム判定（ma200 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

  ※ api_key が None の場合、環境変数 OPENAI_API_KEY を使用します。未設定だと ValueError が発生します。

- 監査ログ DB の初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- J-Quants の id_token を取得する（内部で settings.jquants_refresh_token を使う）
  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
  ```

注意点:
- score_news / score_regime は OpenAI 呼び出しを含むため、APIキーと対象テーブル（raw_news, news_symbols, prices_daily 等）が事前に整っている必要があります。
- ETL は J-Quants API を叩きます。J-Quants 用のトークン（JQUANTS_REFRESH_TOKEN）を設定してください。
- 自動で .env を読み込ませたくないテスト時等は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なファイルと説明です：

- src/kabusys/
  - __init__.py                 (パッケージメタ情報: __version__)
  - config.py                   (環境変数 / 設定管理・.env 自動読み込み)
  - ai/
    - __init__.py
    - news_nlp.py               (ニュースセンチメント → ai_scores)
    - regime_detector.py        (市場レジーム判定)
  - data/
    - __init__.py
    - pipeline.py               (ETL パイプライン / ETLResult)
    - jquants_client.py         (J-Quants API クライアント + 保存関数)
    - news_collector.py         (RSS 収集・前処理)
    - calendar_management.py    (市場カレンダー管理)
    - quality.py                (データ品質チェック)
    - stats.py                  (zscore_normalize 等)
    - etl.py                    (ETLResult 再エクスポート)
    - audit.py                  (監査ログスキーマ・初期化)
  - research/
    - __init__.py
    - factor_research.py        (モメンタム / バリュー / ボラティリティ計算)
    - feature_exploration.py    (将来リターン / IC / 統計サマリー)
  - research/*                   (研究用ユーティリティ)
  - その他（将来的に strategy / execution / monitoring モジュールが追加される想定）

---

## 実運用での注意事項

- セキュリティ:
  - RSS 収集では SSRF 対策、gzip サイズ上限、XML の安全パーサ（defusedxml）を使用していますが、運用環境ではプロキシやネットワーク ACL など追加の対策を検討してください。
  - API キー / トークンは適切に管理してください（Vault 等の利用を推奨）。
- 可用性:
  - 外部 API（J-Quants、OpenAI）のレート制限やエラーに対してリトライ・フォールバックが組み込まれていますが、監視とアラート設定を行ってください。
- テスト:
  - AI 呼び出し・ネットワークリクエストはユニットテストでモック可能なように設計されています（内部関数の差し替えを想定）。
- DuckDB:
  - 一部の実装は DuckDB のバージョンによる挙動差（executemany の空リスト扱い等）を考慮しています。運用で使用する DuckDB のバージョンを固定してください。

---

## 参考 / 開発者向けメモ

- パッケージ version は `kabusys.__version__`（現行 0.1.0）。
- config.Settings による環境変数取得は ValueError を投げるため、呼び出し側でキャッチして適切に扱ってください。
- OpenAI SDK のレスポンスやステータスコード取り扱いは将来の SDK 変更を考慮して安全側で記述されています。
- 各モジュールは「ルックアヘッドバイアス防止」を設計方針に明示しており、内部で date.today() を参照しない関数設計がなされています（引数で date を明示する）。

---

必要であれば、README に下記を追加できます：
- 詳細な .env.example（雛形）
- systemd / cron / Airflow などの運用例（ETL スケジューリング）
- Dockerfile / Compose 設定例
- API 仕様（jquants_client の各エンドポイントマッピング）