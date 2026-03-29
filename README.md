# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB を用いたデータパイプライン、J-Quants 連携、ニュースの NLP スコアリング、ファクター計算、監査ログスキーマなどを提供します。

## 概要

KabuSys は以下を目的とした内部ライブラリです。

- J-Quants API からの株価・財務・カレンダー等の差分 ETL
- ニュース収集と OpenAI を用いた銘柄別・マクロセンチメントのスコアリング
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究ユーティリティ
- 市場カレンダー管理（営業日判定・次/前営業日取得）
- 監査ログ（signal → order_request → executions のトレーサビリティ）用スキーマ
- データ品質チェック（欠損・重複・スパイク・日付不整合）

設計上、ルックアヘッドバイアスを避けるために内部で `date.today()` 等を盲目的に参照せず、ETL/スコアリングの入力に明示的な日付を渡すことを推奨します。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（取得・保存・認証・レート制御・リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS 取得・正規化・SSRF 対策・raw_news 保存）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news：OpenAI を使って銘柄別センチメントを ai_scores テーブルへ書き込み）
  - 市場レジーム判定（score_regime：ETF の MA とマクロニュースのセンチメントを合成して market_regime へ書き込み）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（calc_forward_returns / calc_ic / factor_summary / rank）
- monitoring（監視・Slack 通知等は monitoring モジュールで提供（実装ファイルは本リポジトリ構成に依存））

---

## セットアップ手順

前提
- Python 3.10 以上（コード内での型記法・ union 型演算子 `|` を使用）
- DuckDB を利用可能な環境

1. リポジトリをクローン
   - 例: git clone <リポジトリURL>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - requirements.txt が無ければ最低限以下をインストールしてください：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは pyproject.toml / requirements.txt に必要パッケージを明示してください。

4. パッケージを開発モードでインストール（任意）
   - プロジェクトルートに pyproject.toml 又は setup.py がある場合:
     - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（ただしテスト時など自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必要な環境変数（主要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI 呼び出し時に使用（score_news/score_regime に渡す引数でも指定可）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — development / paper_trading / live （デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   - .env（例）
     ```
     JQUANTS_REFRESH_TOKEN=xxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

---

## 使い方（主な例）

以下は Python スクリプト/対話環境での使用例です。DuckDB 接続には `duckdb.connect()` を使用してください。

1. ETL（デイリー ETL）を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュース NLP スコアを取得して ai_scores に書き込む
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # OPENAI_API_KEY が環境変数にあるか、api_key に直接渡す
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
   print("written:", written)
   ```

3. 市場レジーム判定を実行する
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
   ```

4. 監査ログ DB の初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は DuckDB 接続（UTC タイムゾーン設定済み）
   ```

5. 市場カレンダーの判定ユーティリティ
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
- OpenAI を使う部分（score_news, score_regime）は API キーが必要です。api_key を直接渡すか環境変数 `OPENAI_API_KEY` を設定してください。
- ETL / API 呼び出しはリトライ・レート制御を備えていますが、実行環境のネットワークや API レート制限にはご注意ください。
- DuckDB のスキーマ（テーブル定義）は別スクリプトで初期化しておくか、ETL 実行前にスキーマ初期化の仕組みを用意してください（本コードは保存関数を提供しますが、テーブル作成ロジックはリポジトリにより提供されている想定です）。

---

## 環境変数と設定の自動読み込み

- パッケージは実行時にプロジェクトルート（.git または pyproject.toml の存在）を探索し、`.env` と `.env.local` を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な設定は `kabusys.config.settings` から参照できます（例: `settings.jquants_refresh_token`）。

---

## ディレクトリ構成

以下は主なファイル/モジュールの構成（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP スコアリング（score_news）
    - regime_detector.py           — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETLResult の再エクスポート
    - news_collector.py            — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py       — 市場カレンダー管理
    - quality.py                   — データ品質チェック
    - stats.py                     — 共通統計ユーティリティ（zscore_normalize）
    - audit.py                     — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum/value/volatility）
    - feature_exploration.py       — 将来リターン・IC・統計サマリー
  - monitoring/                    — 監視・通知関連（モジュール参照は __all__ に含む）
  - ai, research, data パッケージ群に多数の補助関数と堅牢なエラーハンドリングが含まれます。

---

## 運用上の注意 / ベストプラクティス

- OpenAI 呼び出し・外部 API 呼び出しはレートやエラーの影響を受けます。実行環境では適切なレート制御・監視を設定してください。
- ETL はリトライと品質チェックを備えますが、初期化・スキーマ作成は事前に行ってください（raw_prices / raw_financials / market_calendar / ai_scores / market_regime 等のテーブル）。
- 本ライブラリはバックテスト用のデータアクセスと本番発注を分離する方針です（研究モジュールは発注 API にアクセスしません）。
- 重要環境変数（トークン・パスワード）は安全に管理してください（シークレット管理サービスや環境変数により）。

---

## ライセンス・貢献

- ライセンス情報や開発に関するルールはリポジトリのトップレベルの LICENSE / CONTRIBUTING を参照してください（本 README に明示がない場合は管理者へ問い合わせてください）。

---

README に不足があれば、特に知りたい機能（例: スキーマ定義、実行 cron の例、詳細な依存関係リスト、.env.example 生成）を教えてください。追加で記載します。