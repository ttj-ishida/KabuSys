# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLU（OpenAI を利用したセンチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の運用システム構築に必要なデータプラットフォームと研究・運用ユーティリティをまとめた Python パッケージです。主な設計方針は以下です。

- Look-ahead bias を避ける（内部で date.today()/datetime.today() を直接参照しない等）
- DuckDB をデータストアとして利用し、ETL と分析を高速に実行
- J-Quants API（株価・財務・カレンダー）との差分 ETL をサポート
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（銘柄別スコア、マクロセンチメント）
- データ品質チェック・監査ログ（signal → order → execution のトレース）
- 自動的に .env/.env.local を読み込む（環境変数優先、無効化可能）

---

## 機能一覧

- データ取得・ETL
  - J-Quants API から株価（daily_quotes）、財務（statements）、JPX カレンダーを差分取得し DuckDB に保存
  - run_daily_etl による日次パイプライン（カレンダー取得 → 株価 → 財務 → 品質チェック）
- ニュース収集
  - RSS フィードを安全に取得し raw_news / news_symbols に保存（SSRF 対策、URL 正規化、重複回避）
- ニュース NLP / AI
  - 銘柄別ニュースセンチメントを OpenAI に投げて ai_scores テーブルへ保存（score_news）
  - マクロニュースと ETF(1321) の MA200 乖離を組み合わせて市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算（calc_forward_returns）、IC 計算（calc_ic）、ランク付け・統計サマリ
  - Z スコア正規化ユーティリティ（zscore_normalize）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合を検出し QualityIssue を返却（run_all_checks）
- 監査ログ（Audit）
  - signal_events / order_requests / executions のテーブル定義と初期化（init_audit_db / init_audit_schema）
- 設定管理
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（無効化可能）
  - settings オブジェクトから各種設定値を取得

---

## セットアップ手順

前提:
- Python 3.10 以上を推奨（型注釈に `|` を使用）
- DuckDB を利用します
- OpenAI SDK を利用（gpt-4o-mini 等）
- defusedxml（RSS パースの安全化）

1. リポジトリをクローン／配置
   - パッケージレイアウトは src/ 配下に配置されています（例: src/kabusys）

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - 例（pip）:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用に editable install:
     ```
     pip install -e .
     ```
     （プロジェクトに setup.cfg/pyproject.toml がある前提）

4. 環境変数設定
   - プロジェクトルートに `.env` と `.env.local` を置くと、自動で読み込まれます。
   - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な必須/推奨環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI の API キー（score_news / regime で必要、関数に api_key を渡すことも可能）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（約定周りで使用）
   - KABUSYS_ENV: 環境 ('development' | 'paper_trading' | 'live')（デフォルト 'development'）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
   - DUCKDB_PATH / SQLITE_PATH 等（デフォルト値あり）

---

## 使い方（簡単な例）

以下の例では DuckDB に接続し、日次 ETL・ニューススコアリング・レジーム判定を呼び出す流れを示します。

1. DuckDB 接続の用意（デフォルトファイル: data/kabusys.duckdb）
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニューススコアリング（OpenAI API キーを環境変数に設定している想定）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込み銘柄数: {written}")
   ```

   - api_key を直接渡すことも可能: score_news(conn, date, api_key="sk-...")

4. 市場レジーム判定
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 研究用ファクター計算例
   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value

   mom = calc_momentum(conn, target_date=date(2026,3,20))
   val = calc_value(conn, target_date=date(2026,3,20))
   ```

6. 監査ログ DB 初期化（監査専用 DB を作る場合）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/monitoring_audit.duckdb")
   # テーブル作成済みの接続が返る
   ```

注意点:
- OpenAI 呼び出しはコストがかかるため、テスト時は api_key をモックするか呼び出しを回避してください。
- J-Quants API 呼び出しはレート制限があるため、ETL は差分取得ロジックを利用して効率的に実行します。
- run_daily_etl などは内部で例外を捕捉して処理をできるだけ継続する設計です。戻り値で品質問題やエラーを確認してください。

---

## 設定（settings）について

- settings オブジェクトは `kabusys.config.settings` で利用可能です。例:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```
- 自動的にプロジェクトルートの `.env` → `.env.local` を読み込みます（OS 環境変数が優先）。
- 自動読み込みを無効化する場合: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- KABUSYS_ENV の有効値: `development`, `paper_trading`, `live`
- LOG_LEVEL は標準的なログレベル（DEBUG/INFO/…）を設定可能

---

## ディレクトリ構成

プロジェクト内の主要ファイル（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数 / settings 管理
  - ai/
    - __init__.py
    - news_nlp.py                   # 銘柄別ニューススコアリング（OpenAI）
    - regime_detector.py            # 市場レジーム判定（MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント & DuckDB 保存
    - pipeline.py                   # ETL パイプライン（run_daily_etl 等）
    - etl.py                        # ETLResult エクスポート
    - calendar_management.py        # 市場カレンダー管理・営業日判定
    - news_collector.py             # RSS ニュース収集
    - quality.py                    # データ品質チェック
    - stats.py                      # 汎用統計ユーティリティ（zscore 等）
    - audit.py                      # 監査ログ（signal/order/execution）初期化
  - research/
    - __init__.py
    - factor_research.py            # Momentum/Value/Volatility ファクター計算
    - feature_exploration.py        # forward returns / IC / summary / rank
  - ai/, data/, research/ に他モジュールあり（上記は主要機能）

---

## 注意事項 / ベストプラクティス

- OpenAI の呼び出しはレート制御・リトライ実装を行っていますが、コストとレイテンシに注意してください。テストやローカル実行時はモックを推奨します。
- J-Quants のリフレッシュトークンは機密情報です。`.env` を含めてバージョン管理しないようにしてください。
- DuckDB ファイルは破損防止のためバックアップを考慮してください。監査ログなどは削除しない前提で設計されています。
- 本ライブラリはデータ取得・研究・監視用ユーティリティを提供しますが、実際の約定ロジック・リスク管理ルールは運用側で実装してください（order_requests テーブルは冪等キー等を用意しており二重発注防止の補助をします）。

---

## さらに進めるために

- CI / テストの追加（OpenAI / HTTP 呼び出しはモック化）
- 実運用では監視（プロセス監視、kill flag、PID ファイル）を組み合わせる
- backtesting 用に historical snapshot を DuckDB に保存して検証する
- 実際の注文送信ロジック（execution モジュール）を統合する

---

この README はコードベースの主要機能と使い方をまとめたものです。必要であれば、各モジュール（ETL、AI、research、audit 等）の API サンプルや .env.example のテンプレートも作成しますのでお知らせください。