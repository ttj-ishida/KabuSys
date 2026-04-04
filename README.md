# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants / OpenAI / kabuステーション 等と連携して、データ収集（ETL）、データ品質チェック、ニュースのAIセンチメント集計、市場レジーム判定、監査（トレーサビリティ）を提供します。

## 概要
KabuSys は以下を目的とした Python パッケージ群です。
- J-Quants API からの差分 ETL（株価・財務・マーケットカレンダー）
- RSS ニュース収集と OpenAI による銘柄別センチメント算出（ai.news_nlp）
- マクロニュース＋ETF（1321）200日移動平均乖離からの市場レジーム判定（ai.regime_detector）
- 研究用ファクター計算・特徴量解析（research）
- データ品質チェック、カレンダー管理、監査ログ（data.audit）
- 環境変数管理（config）

設計方針として、バックテストにおけるルックアヘッドバイアス回避、冪等性（DB 保存時の ON CONFLICT）、API リトライ／レート制御、フェイルセーフ（API 失敗時にゼロフォールバック）などを重視しています。

---

## 主な機能一覧
- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・保存・品質チェック）
  - J-Quants クライアント（認証自動更新、ページネーション、レート制御、リトライ）
- データ品質
  - 欠損検出 / スパイク検出 / 重複チェック / 日付整合性チェック（data.quality）
- ニュース処理（news_collector）
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去、前処理）と raw_news への保存支援
- ニュース NLP（ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを取得し ai_scores テーブルへ保存
- 市場レジーム判定（ai.regime_detector）
  - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で bull/neutral/bear を判定
- 監査ログ（data.audit）
  - signal_events / order_requests / executions といった監査テーブルの初期化・管理（冪等・UTC 時刻）
- 研究ユーティリティ（research）
  - モメンタム・ボラティリティ・バリュー等のファクター計算、将来リターン計算、IC 計算、Z スコア正規化

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に `|` を使用）
- ネットワーク接続（J-Quants / OpenAI 等）

1. リポジトリをクローン・作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell: .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   代表的な依存（プロジェクトの setup/requirements を参照してください）:
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外のパッケージを pip でインストール）
   例:
   ```bash
   pip install duckdb openai defusedxml
   # またはパッケージにセットアップがあれば:
   # pip install -e .
   ```

4. 環境変数の設定
   プロジェクトは .env / .env.local を自動でプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   必須／推奨の環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - KABU_API_PASSWORD: kabu API パスワード（必要なら）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG/INFO/...

   簡易の .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本例）

Python から直接機能を呼び出す例を示します。ここでは duckdb を使った簡易的な実行例。

1. DuckDB 接続（ETL / データ操作共通）
   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL の実行
   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニューススコアリング（OpenAI API キーが必要）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # conn は DuckDB 接続
   count = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {count} codes")
   ```

   api_key を直接渡すことも可能:
   ```python
   score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
   ```

4. 市場レジーム判定
   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026,3,20))
   ```

5. 監査ログ DB を初期化
   ```python
   from kabusys.data.audit import init_audit_db
   audit_conn = init_audit_db("data/audit.duckdb")
   ```

6. ai スコアや market_regime テーブルに書き込まれるため、事前にスキーマ（該当テーブル群）が作成されていることを前提にしています。ETL / schema 初期化処理が別モジュールにある場合はそちらを呼び出してください（data.schema など）。

---

## 設定（環境変数読み込みの挙動）
- パッケージ import 時（kabusys.config）はプロジェクトルート（.git または pyproject.toml を基準）を自動探索し、`.env` → `.env.local` の順で読み込みます。OS 環境変数が優先されます。
- 自動読み込みを無効化するには環境変数を設定:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- 設定値は kabusys.config.settings オブジェクト経由で参照できます（例: settings.jquants_refresh_token）。

---

## ディレクトリ構成（主要ファイルと簡単説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動読み込み、settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - 銘柄別ニュースセンチメント算出（OpenAI 呼び出し、バッチ、リトライ、検証、ai_scores に書込）
    - regime_detector.py
      - ETF（1321）MA200 乖離 + マクロニュース LLM を合成して market_regime に書き込む
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証、fetch/save、リトライ、レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - news_collector.py
      - RSS 収集・正規化・前処理（SSRF 対策）
    - quality.py
      - データ品質チェック
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブルの DDL と初期化（init_audit_schema / init_audit_db）
    - etl.py
      - ETLResult の公開再エクスポート
  - research/
    - __init__.py
    - factor_research.py
      - momentum / value / volatility 等のファクター計算
    - feature_exploration.py
      - forward returns / IC / rank / factor_summary 等
  - (その他) strategy / execution / monitoring のプレースホルダや将来的なモジュール

---

## 注意点・運用上のポイント
- OpenAI を利用する処理（score_news, score_regime）は API キーを必要とし、呼び出し回数やレスポンスの検証に注意してください。失敗時は多くの箇所でゼロフォールバックやスキップを行い安全側に倒しています。
- J-Quants API はレート制限や token の有効期限に注意（自動リフレッシュ実装あり）。
- DuckDB を永続化に使用する場合はバックアップや排他アクセスに注意してください（複数プロセスでの同時書き込み等）。
- ETL 実行は監視（pid / kill flag / CPU・メモリの閾値）やログレベルの設定を行って運用してください。
- テスト時は環境変数自動読み込みを無効化（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）して、必要な環境設定をテスト側で注入できます。

---

## サポート / 開発メモ
- 単体テストやモック化（OpenAI / ネットワーク呼び出し）を想定した設計が随所にあります。たとえば ai モジュール内の HTTP 呼び出しや _call_openai_api 関数はユニットテストでモック可能です。
- 追加機能（kabu ステーション発注、Line 通知等）は strategy / execution / monitoring に統合される想定です。

---

この README は概要と主要な使い方を示したものです。より詳細な API リファレンスや運用手順（運用スケジュール、監視ダッシュボード、セキュリティ要件等）は別途ドキュメント（Design doc / Ops runbook）で管理してください。