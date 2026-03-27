# KabuSys

KabuSys は日本株向けの自動売買／データパイプライン基盤です。J-Quants からのデータ取得・ETL、ニュースの収集と LLM によるセンチメント評価、市場レジーム判定、研究用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを統合的に提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API失敗時は安全側で継続）」で、DuckDB を中核にデータを保持します。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定の自動ロード（`.env`, `.env.local`, 環境変数）
- J-Quants API クライアント（株価日足、財務データ、JPX マーケットカレンダー）
  - レートリミット制御、リトライ、トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（日次 ETL：カレンダー → 株価 → 財務 → 品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）とニュース前処理（SSRF 対策・トラッキング除去）
- OpenAI を使ったニュース NLP（銘柄ごとのセンチメントを ai_scores に書き込み）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用モジュール（ファクター計算、将来リターン、IC 計算、Zスコア正規化）
- 監査ログ／トレーサビリティ用テーブル定義と初期化ユーティリティ（監査 DB 用 DuckDB）
- Kabu ステーション等への発注に必要な設定プレースホルダ（API パスワード等）

---

## 必要な依存関係（主なもの）

- Python 3.10+
- duckdb
- openai
- defusedxml

（その他、標準ライブラリのみで多くが実装されています。実際の導入時は requirements.txt / pyproject.toml を確認してください。）

---

## セットアップ手順

1. リポジトリをクローン／配置
   - 例: git clone ... / あるいはパッケージをプロジェクトに追加

2. 仮想環境を作成して依存パッケージをインストール
   - 例:
     ```
     python -m venv .venv
     source .venv/bin/activate
     pip install -U pip
     pip install duckdb openai defusedxml
     # またはプロジェクトの pyproject.toml / requirements.txt があればそれを使う
     ```

3. 環境変数設定
   - プロジェクトルート（.git または pyproject.toml がある階層）に `.env` と `.env.local` を置くことで自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   代表的な `.env` の例:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # OpenAI
   OPENAI_API_KEY=sk-...

   # kabuステーション（注文用）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # Slack 通知
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境 / ログ
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB データファイル準備
   - デフォルトは `data/kabusys.duckdb`（`settings.duckdb_path`）に保存されます。必要に応じて `.env` の `DUCKDB_PATH` を変更してください。
   - 監査ログ専用 DB を別途作る場合は `kabusys.data.audit.init_audit_db(path)` を使用します。

---

## 使い方（基本例）

以下は Python スクリプト／対話での利用例です。

- 設定を参照する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 環境変数 JQUANTS_REFRESH_TOKEN を参照
  ```

- DuckDB 接続を開く
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（銘柄ごとの ai_scores を生成）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"written: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査テーブルの初期化（既存接続に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 監査データベースの作成（専用ファイル）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

注意:
- OpenAI API を使う関数は `api_key` を引数で渡すか、環境変数 `OPENAI_API_KEY` を設定してください。未設定時は ValueError が発生します。
- 各処理はルックアヘッドバイアスを避けるために `target_date` を明示的に受け取る設計です。内部で `date.today()` を安易に参照しないようにしています（ただし ETL のデフォルトは today を使用します）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で必要）
- KABU_API_PASSWORD: kabu ステーション API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID: Slack チャネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

---

## 開発者向けメモ / テスト容易性

- 環境変数の自動ロードはモジュール import 時に行われます。テストで自動ロードを抑止する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部で `_call_openai_api` を使っています。ユニットテストでは `unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")` のように差し替えてテストできます。
- RSS フェッチのネットワーク呼び出しは `kabusys.data.news_collector._urlopen` をモックして差し替える設計になっています。

---

## ディレクトリ構成

（抜粋。実際のリポジトリでは他ファイル・テスト等が存在する可能性があります）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント解析（OpenAI）
    - regime_detector.py    — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - pipeline.py           — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                — ETLResult の再エクスポート
    - calendar_management.py— 市場カレンダー管理（営業日判定等）
    - stats.py              — 統計ユーティリティ（zscore_normalize 等）
    - quality.py            — データ品質チェック
    - news_collector.py     — RSS 収集、前処理、保存
    - audit.py              — 監査ログ用スキーマ定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（Momentum/Value/Volatility 等）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー 等

---

## 運用上の注意

- 実際の注文（ライブ発注）を行う場合は `KABUSYS_ENV` を適切に設定し、リスク管理・ダブルチェックを必ず行ってください。
- OpenAI の呼び出しにはコストとレイテンシがあります。バッチサイズ・リトライ設定等は運用に合わせて調整してください。
- J-Quants の API レート制限を守るため、クライアント側でもレート制御を行っていますが、大量データを短時間で取得する際は注意してください。
- DuckDB に対する executemany の空パラメータ等の互換性に注意している箇所があります（DuckDB バージョンによる違いに注意）。

---

必要であれば、導入用の簡易 CLI スクリプト例や .env.example ファイル、より詳細な運用ガイド（ETL スケジューリング、監視/アラート、バックテストでのデータ取り扱い等）も作成できます。どの情報を追加したいか教えてください。