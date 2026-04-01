# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
ETL（データ収集）、データ品質チェック、特徴量計算、ニュースNLP（OpenAI）によるセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）等を含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は次の目的を持つ Python パッケージ群です。

- J-Quants API から株価・財務・市場カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- 保存データに対する品質チェック（欠損・スパイク・重複・日付整合性）
- ファクター / 特徴量の計算（モメンタム、ボラティリティ、バリュー等）
- ニュース記事の収集・前処理と OpenAI を使った銘柄別センチメント算出
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- 監査ログテーブル（signal → order_request → executions）を DuckDB に初期化・扱うユーティリティ
- 各種設定は環境変数 / .env から読み込み

設計上のポイント：
- ルックアヘッドバイアスの回避（内部で date.today()/datetime.today() を不用意に参照しない）
- API 呼び出しはリトライ／バックオフやフェイルセーフ処理を実装
- DuckDB における冪等保存（ON CONFLICT DO UPDATE / DO NOTHING）を重視

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー操作（is_trading_day / next_trading_day / get_trading_days など）
  - ニュース収集（RSS）と前処理（SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（missing_data, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを計算して ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF(1321)のMA乖離 + マクロニュースセンチメントで市場レジーム判定を保存
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - Settings: 環境変数 / .env 読み込みと各種設定値の取得（J-Quants / OpenAI / DB パス 等）

---

## セットアップ手順

前提
- Python 3.10 以上（| 型アノテーション等を使用）
- システムに duckdb 等のネイティブ依存がある場合は環境に応じてインストールしてください。

1. リポジトリをクローンしてパッケージをインストール（開発形態）
   - pip を利用する場合（プロジェクトルートに pyproject.toml が存在する想定）
     ```
     git clone <repo-url>
     cd <repo>
     pip install -e .
     ```
   - あるいは必要なパッケージを直接インストール
     ```
     pip install duckdb openai defusedxml
     ```

2. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` として必要な設定を置くと自動で読み込まれます。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必須の主な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime 時に必要）
     - KABU_API_PASSWORD: kabuステーション API パスワード（利用する場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（利用する場合）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用途の SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
   - .env の自動読み込みはプロジェクトルートの .env → .env.local の順で行われ、OS 環境変数が優先されます。

3. データベース初期化（監査ログなど）
   - 監査ログ用の DuckDB を初期化する例:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)
     ```
   - 既存接続に監査スキーマを追加する場合:
     ```python
     from kabusys.data.audit import init_audit_schema
     import duckdb
     conn = duckdb.connect(str(settings.duckdb_path))
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（主要なユースケース例）

1. 設定値取得
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)
   print(settings.is_paper)
   ```

2. DuckDB 接続を作って日次 ETL を実行
   ```python
   import duckdb
   from datetime import date
   from kabusys.config import settings
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュースセンチメントのスコア算出（OpenAI 必須）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None -> env OPENAI_API_KEY を使用
   print(f"書き込んだ銘柄数: {written}")
   ```

4. 市場レジーム判定
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

5. ファクター計算の呼び出し（研究用途）
   ```python
   import duckdb
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

   conn = duckdb.connect("data/kabusys.duckdb")
   mom = calc_momentum(conn, date(2026,3,20))
   vol = calc_volatility(conn, date(2026,3,20))
   val = calc_value(conn, date(2026,3,20))
   ```

6. データ品質チェック
   ```python
   from kabusys.data import quality
   issues = quality.run_all_checks(conn, target_date=date(2026,3,20))
   for i in issues:
       print(i)
   ```

注意点:
- OpenAI API の呼び出しはレスポンス検証・リトライ処理を含みますが、API キーが未設定の場合は ValueError が発生します。
- ETL / ニュース / レジーム判定はすべてルックアヘッドバイアス防止の設計が施されています（内部で現在時刻を参照しないなど）。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュールとその役割の概観です。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / .env 管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュースから銘柄別センチメント算出（score_news）
    - regime_detector.py               — ETF + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                      — ETL のエントリポイント（run_daily_etl 等）
    - etl.py                           — ETLResult の再エクスポート
    - jquants_client.py                — J-Quants API クライアント & 保存処理
    - calendar_management.py           — マーケットカレンダー管理、営業日ロジック
    - news_collector.py                — RSS 収集・前処理
    - quality.py                       — データ品質チェック
    - stats.py                         — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査ログスキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py               — Momentum/Value/Volatility の計算
    - feature_exploration.py           — 将来リターン計算、IC、統計サマリー 等

---

## 運用上の補足とベストプラクティス

- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml から探索します。CI / テスト等で自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI を利用する箇所は API レートや応答フォーマット変化に注意してください。レスポンスのバリデーションやフェイルセーフ動作（失敗時にスコア 0 を返す等）が組み込まれていますが、運用時の監視を推奨します。
- J-Quants API 呼び出しはレート制御・トークン自動リフレッシュ等を行います。ID トークンの取得に失敗する場合は JQUANTS_REFRESH_TOKEN を確認してください。
- DuckDB ファイルはデフォルトで data/kabusys.duckdb を使用します。バックアップや運用環境ではファイル配置・パーミッションに注意してください。
- 監査ログテーブルは削除しない前提で設計されています。必要に応じて init_audit_schema を実行してテーブルを作成してください。

---

この README はコードベースから把握できる設計・使用法をまとめたものです。実際の運用や開発にあたっては pyproject.toml / requirements.txt / .env.example（存在する場合）やテストコードを参照のうえ、環境に応じた設定・依存関係の確認を行ってください。必要な追加情報（例: サンプル .env.example、実行スクリプト、CI 設定など）があれば作成を支援します。