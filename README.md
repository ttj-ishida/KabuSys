# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL、ニュースNLP（LLM ベース）、市場レジーム判定、ファクター計算、カレンダー管理、J-Quants クライアント、監査ログなどの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI によるニュース評価・市場レジーム判定・監査ログなどを含む、運用・研究向けの基盤ライブラリです。  
主要コンポーネントは DuckDB を用いたデータ管理、J-Quants API 経由のデータ取得、OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価およびそれを利用したレジーム判定です。

設計上の特徴：
- ルックアヘッドバイアス防止（内部で date.today() を不用意に参照しない設計）
- 冪等性（ETL・保存処理は idempotent）
- フェイルセーフ（外部 API 失敗時は安全側のデフォルトで継続）
- 単体モジュール化（AI 呼び出し等は抽象化・差し替え可能）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（トークン管理、レートリミット、リトライ、保存関数）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に保存）
  - レジーム判定（score_regime: MA200 + マクロニュースセンチメントから market_regime を算出）
- research
  - ファクター計算（momentum / volatility / value 等）
  - 特徴量探索（将来リターン計算、IC 計算、統計サマリー、ランク化）
- config
  - 環境変数管理（.env 自動読み込み、必須チェック、設定オブジェクト：settings）

---

## セットアップ手順

以下はローカル開発・実行環境構築の例です。

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 依存パッケージをインストール  
   （プロジェクトに requirements.txt が無い場合は主要依存を個別に入れてください）
   ```
   pip install duckdb openai defusedxml
   ```
   - 必要に応じて他のパッケージ（例: requests 等）を追加してください。

4. 環境変数設定  
   プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（config モジュールで自動ロード）。  
   自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須環境変数（例）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL / jquants_client）
   - SLACK_BOT_TOKEN — Slack 通知用ボットトークン（監視系）
   - SLACK_CHANNEL_ID — Slack チャネル ID
   - KABU_API_PASSWORD — kabu ステーション API パスワード（約定連携がある場合）
   - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能を使う場合）

   省略時のデフォルトパス（settings 参照）:
   - DUCKDB_PATH: data/kabusys.duckdb
   - SQLITE_PATH: data/monitoring.db
   - PID_FILE_PATH: data/execution.pid
   - KABUSYS_ENV: development（有効値: development, paper_trading, live）
   - LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   KABU_API_PASSWORD=your_password
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. DuckDB の初期化（監査DB など）
   Python REPL / スクリプトで:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # ファイルがなければ作成されます
   # 追加スキーマ初期化が必要な場合は他の schema 初期化関数を呼ぶ
   ```

---

## 使い方（簡易例）

以下は代表的な呼び出し例です。実行は Python スクリプト / コンソールから行います。

- ETL（日次パイプライン）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しなければ今日（内部で調整あり）
  print(result.to_dict())
  ```

- ニューススコアリング（LLM を用いる）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```
  ※ OPENAI_API_KEY が環境変数に設定されている必要があります（または api_key 引数で渡す）。

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- J-Quants からデータを手動取得
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,19))
  ```

- カレンダー操作
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- 監査スキーマの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- AI 関連機能を使う場合は OpenAI の API キーと通信環境が必要です。
- J-Quants API を使う ETL を行うには J-Quants の認証情報（リフレッシュトークン）が必要です。

---

## 設定（settings）

kabusys.config.settings からアクセスできます（プロパティ形式）。例:
- settings.jquants_refresh_token
- settings.kabu_api_password
- settings.kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- settings.slack_bot_token / settings.slack_channel_id
- settings.duckdb_path, settings.sqlite_path
- settings.env (development / paper_trading / live)
- settings.log_level

.env 自動読み込み:
- プロジェクトルート（.git または pyproject.toml のあるディレクトリ）にある `.env` / `.env.local` が自動で読み込まれます。読み込み順は OS 環境変数 > .env.local > .env。
- テスト時などに自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル/モジュールは以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLU / ai_scores 書込み
    - regime_detector.py              — MA200 + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント & 保存ロジック
    - pipeline.py                     — ETL パイプライン run_daily_etl 等
    - etl.py                          — ETLResult 再エクスポート
    - quality.py                      — データ品質チェック
    - stats.py                        — zscore_normalize 等統計ユーティリティ
    - calendar_management.py          — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py               — RSS 収集・前処理
    - audit.py                        — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py              — momentum / value / volatility
    - feature_exploration.py           — 将来リターン / IC / summary / rank

（上記はコードベースに含まれる主要モジュールの抜粋です）

---

## 開発 / テストに関する補足

- モジュール内部の外部 API 呼び出しはユニットテスト時に patch しやすい設計（_call_openai_api 等をモック）になっています。
- DuckDB を使っているためローカルで簡単にインメモリやファイル DB を使えます（":memory:" も利用可能）。
- LLM 呼び出しは JSON Mode を使う設計（厳密な JSON を期待）。レスポンスのパース失敗はログを出して安全にフォールバックします。
- ETL は失敗に強い（各ステップは個別に try/except され、ログに集約されます）。

---

## 参考・問い合わせ

- OpenAI API のレート・利用ポリシー、J-Quants の API 利用規約など外部サービスの規約を遵守してください。  
- 実運用（live）環境では必ず十分な検証と安全対策（取引時の二重発注防止、監査ログの確認、監視）を行ってください。

---

以上。README に含めてほしい補足や、サンプルスクリプト（ETL の定期実行例や監視ジョブの実装例）が必要であれば教えてください。必要に応じて README を拡張します。