# KabuSys

日本株向け自動売買 / データ基盤ライブラリ (KabuSys)

簡単な説明:
KabuSys は日本株のデータ収集（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）によるセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ用スキーマ、及び kabu ステーション等と連携するためのユーティリティ群を提供する Python パッケージです。内部的には DuckDB を DB 層に使い、OpenAI（gpt-4o-mini）で記事やマクロセンチメントを評価します。

---

## 機能一覧

- データ ETL（株価日足、財務、マーケットカレンダー）と差分取得ロジック
- J-Quants API クライアント（取得、レート制御、リトライ、トークン自動リフレッシュ）
- DuckDB への冪等保存（ON CONFLICT ... DO UPDATE）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- RSS ベースのニュース収集（SSRF 対策、gzip 制限、URL 正規化）
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア生成、JSON Mode 利用）
- マクロセンチメント + ETF MA200 を組み合わせた市場レジーム判定
- 研究用モジュール（モメンタム、バリュー、ボラティリティ、将来リターン、IC、統計サマリー）
- 監査ログ（signal / order_request / executions テーブル群）作成ユーティリティ
- 市場カレンダー管理（営業日判定、next/prev trading day、カレンダー更新ジョブ）
- 環境変数管理（.env 自動読込 / 上書きロジック）

---

## 前提 / 必要環境

- Python 3.10+
- 推奨パッケージ（少なくとも、以下をインストールしてください）
  - duckdb
  - openai
  - defusedxml

（requirements.txt があればそれを使ってください。なければ下のコマンド例を参照）

---

## セットアップ手順

1. リポジトリをクローン（既にプロジェクトが手元にある想定）:
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成・有効化（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate    # macOS / Linux
   .venv\Scripts\activate       # Windows
   ```

3. 必要パッケージをインストール:
   例（最低限）:
   ```
   pip install duckdb openai defusedxml
   ```
   プロジェクトを開発モードでインストールする場合:
   ```
   pip install -e .
   ```

4. 環境変数の設定:
   プロジェクトルートに `.env` / `.env.local` を置くと、自動的に読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須（代表例、実際のプロジェクトでは .env.example を参照してください）:
   - JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
   - SLACK_BOT_TOKEN=（Slack ボットトークン）
   - SLACK_CHANNEL_ID=（通知先 Slack チャンネル ID）
   - KABU_API_PASSWORD=（kabu API のパスワード）
   - OPENAI_API_KEY=（OpenAI API キー） — score_news / score_regime 実行時に環境変数でも指定可能

   任意・デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを抑止

   例 `.env`:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. データベース初期化（監査ログ用など）:
   Python REPL またはスクリプトから:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます
   ```

---

## 使い方（主要な API の例）

- DuckDB 接続作成例:
  ```python
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)   # デフォルトは today
  print(result.to_dict())
  ```

- ニュース NLP で銘柄別 ai_score を作成:
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  target_date = datetime.date(2026, 3, 20)
  n_written = score_news(conn, target_date, api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print(f"書き込み銘柄数: {n_written}")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb, datetime
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, datetime.date(2026, 3, 20))
  ```

- 研究用関数（モメンタム等）:
  ```python
  from kabusys.research.factor_research import calc_momentum
  import datetime
  result = calc_momentum(conn, datetime.date(2026, 3, 20))
  ```

- 監査スキーマ初期化（既存 DB に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- J-Quants から株価を直接取得（テスト／ユーティリティ）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes
  rows = fetch_daily_quotes(date_from=datetime.date(2026,1,1), date_to=datetime.date(2026,3,20))
  ```

注意点:
- OpenAI API 呼び出しを行う関数（score_news / score_regime）は api_key 引数を受け付けます。None の場合は環境変数 OPENAI_API_KEY を使います。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、関数内部でチェックされています（開発者目線の重要情報）。

---

## ディレクトリ構成（主なファイルと役割）

リポジトリ内での主要モジュール（src/kabusys）:

- kabusys/
  - __init__.py — パッケージメタ情報（version, __all__）
  - config.py — 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース記事の OpenAI による銘柄別センチメント評価（score_news）
    - regime_detector.py — ETF MA200 とマクロセンチメントを合成して市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存 / トークン管理 / レート制御）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py — ETL の公開インターフェース（ETLResult 再エクスポート）
    - stats.py — 共通統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - news_collector.py — RSS 収集、SSRF 対策、前処理
    - calendar_management.py — 市場カレンダー管理・営業日判定・calendar_update_job
    - audit.py — 監査ログスキーマの DDL / 初期化（signal/order_requests/executions）
  - research/
    - __init__.py
    - factor_research.py — モメンタム / バリュー / ボラティリティ等のファクター計算
    - feature_exploration.py — 将来リターン計算、IC、rank、factor_summary
  - monitoring/ (※コードベース上に監視関連のコードがある想定。ここでは sqlite 関連設定が config に含まれる)

各モジュールは設計上、ルックアヘッドバイアスを避ける（現在時刻の参照抑制）等の注意が払われており、テスト用に外部呼び出しを差し替えやすく作られています（例: API 呼び出し関数をモック可能）。

---

## 運用上の注意

- 本ライブラリは実取引（live）用途でも環境変数でモードを切り替えられます（KABUSYS_ENV）。paper_trading / live モードは安全/リスク挙動に影響を与え得るため、運用前に設定を確認してください。
- OpenAI / J-Quants / kabu API のキーは機密情報です。必ず安全に管理し、公開リポジトリにコミットしないでください。
- ETL / API 呼び出しはレート制限やリトライを含みますが、長時間の取得や大量データの処理はリソース管理を慎重に行ってください。
- ニュース収集では外部 URL を取得するため SSRF 対策・サイズ上限を実装していますが、自ホスト環境のファイアウォール等で更に保護を検討してください。

---

もし README に追加したい具体的な使用例（スクリプト、CI の設定、.env.example の雛形、テストコマンド等）があれば教えてください。必要に応じてサンプル .env.example やスニペットを作成します。