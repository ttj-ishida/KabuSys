# KabuSys

日本株自動売買プラットフォーム用のユーティリティ群（ETL・データ品質・NLP・リサーチ・監査ログ 等）

このリポジトリは、日本株向けデータプラットフォームと研究／戦略実装のための共通ライブラリ群を提供します。J-Quants API や RSS、OpenAI 等と連携してデータ収集・品質管理・AI スコアリング・ファクター計算・監査ログの初期化までをカバーします。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() に依存しない）
- DuckDB を利用したローカルデータストア中心の設計
- API 呼び出しはリトライ／レート制御を備えフェイルセーフに動作
- ETL／チェックは部分失敗を許容して他処理へ影響を与えない設計

---

## 機能一覧

- config
  - 環境変数の自動読み込み（`.env` / `.env.local`）と取得ユーティリティ
  - 必須環境変数チェック、アプリ設定アクセス（settings オブジェクト）
- data
  - J-Quants API クライアント（認証・ページネーション・レートリミット・保存）
  - ETL パイプライン（日次 ETL：株価・財務・カレンダー）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - マーケットカレンダー管理（営業日判定 / next/prev / カレンダー更新ジョブ）
  - ニュース収集（RSS -> raw_news、SSRF 対策、前処理）
  - 監査ログ（signal / order_request / executions テーブルのスキーマ初期化）
  - 統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP（銘柄毎にニュースを集約して OpenAI でスコアリング、ai_scores へ保存）
  - 市場レジーム判定（ETF 1321 の MA200 と LLM によるマクロセンチメントを合成）
- research
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 特徴量探索（forward returns, IC, summary 等）

（strategy / execution / monitoring パッケージはトップレベル公開対象に含まれますが、本リポジトリ内の具体実装は用途に応じて拡張します。）

---

## 必要条件（概略）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
  - そのほか標準ライブラリのみで動作する実装が多いですが、環境に応じて追加が必要です。

本リポジトリに requirements.txt がある場合はそれを使用してください。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - ない場合は最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

5. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
   - KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - SLACK_BOT_TOKEN (必須)
   - SLACK_CHANNEL_ID (必須)
   - DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (任意, デフォルト: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
   - KABUSYS_ENV (development | paper_trading | live, デフォルト development)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - OPENAI_API_KEY（AI モジュールを使う場合に必要。score_news / score_regime の api_key 引数からも指定可）

   参考: settings オブジェクトを通じてこれらへアクセスできます。

---

## 使い方（主なユースケース例）

以下は代表的な呼び出し例です。実行前に環境変数や DuckDB のスキーマ（テーブル定義）が必要です。

- settings の利用（環境変数読み込み）
  ```py
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作成して日次 ETL を実行
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP（OpenAI を使って銘柄別スコアを生成）
  ```py
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境変数に設定
  print(f"scored {n} codes")
  ```

- 市場レジーム判定
  ```py
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要
  ```

- 監査ログ用 DB 初期化
  ```py
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```py
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026,3,20))
  ```

各関数は docstring に詳細な引数・戻り値・副作用・エラーハンドリング方針が記載されています。API キーやトークンは関数引数で注入可能なケースが多く、テスト時の差し替えがしやすい設計になっています。

---

## .env の仕様（自動読み込み）

- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動で読み込みます。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - `.env.local` は .env を上書きする想定
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースは POSIX シェル形式をある程度サポート（export KEY=val、クォート・エスケープ・インラインコメント対応）

---

## よく使うモジュール一覧（ディレクトリ構成）

src/kabusys/
- __init__.py — パッケージ公開設定（version 等）
- config.py — 環境変数 / 設定管理（settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリングと ai_scores 書き込み
  - regime_detector.py — ETF MA + マクロセンチメントによる市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch / save）
  - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
  - quality.py — データ品質チェック群
  - calendar_management.py — マーケットカレンダー管理
  - news_collector.py — RSS 収集（SSRF 対策・正規化）
  - audit.py — 監査ログテーブル定義・初期化
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー等
  - feature_exploration.py — forward returns / IC / summary / rank
- ai, research, data 以外に strategy/, execution/, monitoring/ 等の公開先が想定されています（必要に応じて追加）。

---

## 注意点 / 運用上のヒント

- DuckDB スキーマ（テーブル定義）は運用で一度用意してから ETL を回してください。save_* 関数は ON CONFLICT による冪等保存を行いますが、適切なスキーマが必要です。
- OpenAI 利用部分は外部 API 呼び出しを伴うため、API レート・料金に注意してください。関数の多くは api_key を引数で受け取れるためテスト時はスタブ／モックに差し替えてください。
- jquants_client は ID トークンの自動リフレッシュ、リトライ、レート制御（120 req/min）を備えています。大量データ取得時はページネーション処理に注意してください。
- ニュース収集は外部 URL にアクセスするため SSRF 対策（ホスト検査・リダイレクト検査）や最大受信サイズ制限が実装されています。RSS ソースは信頼できるものを指定してください。
- ETL と品質チェックは同一プロセスで実行しても一部失敗時に他の処理を継続するよう設計されています。問題は logging と ETLResult に収集されます。

---

## サポート / 貢献

- バグ報告、機能要望、PR はリポジトリの Issue / Pull Request を利用してください。
- 大きな設計変更や外部 API 仕様変更がある場合は関連ドキュメント（DataPlatform.md / StrategyModel.md 等）と合わせて更新してください。

---

README は実装や開発フローに応じて随時更新してください。必要であれば各モジュールの詳細な使い方（引数説明、実行例、スキーマ定義等）を別途ドキュメント化することを推奨します。