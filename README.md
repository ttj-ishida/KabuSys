# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買（研究 & 実行）支援ライブラリです。J-Quants API を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI を利用）、ファクター計算、マーケットカレンダー管理、監査ログ（発注〜約定のトレース）などのユーティリティを提供します。

主な用途
- 日次 ETL（株価・財務・カレンダー）の差分取得と保存
- ニュースを用いた銘柄センチメント解析（LLM）
- 市場レジーム判定（MA とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- DuckDB を用いた監査ログスキーマ初期化・管理
- データ品質チェック

---

## 機能一覧

- 環境設定管理（.env 自動ロード、必須設定の検証）
- J-Quants API クライアント（差分取得・ページネーション・トークン自動リフレッシュ・レートリミット、保存関数）
- ETL パイプライン（run_daily_etl、個別 ETL ヘルパー）
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集（RSS -> raw_news、SSRF 対策、正規化）
- ニュース NLP（gpt-4o-mini を用いたバッチセンチメント、ai_scores への書き込み）
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- 研究用ユーティリティ（ファクタ計算、forward returns、IC、統計サマリ、zscore 正規化）
- マーケットカレンダー管理（営業日判定 / next/prev / バッチ更新）
- 監査ログ（signal_events / order_requests / executions テーブル、監査DB初期化）

---

## セットアップ手順

1. Python 環境
   - 推奨: Python 3.10+（型注釈に union 型などを使用）
   - 仮想環境を作成して有効化してください。
     ```
     python -m venv .venv
     source .venv/bin/activate  # Unix/macOS
     .venv\Scripts\activate     # Windows
     ```

2. 依存パッケージをインストール
   - 想定依存例（プロジェクトの requirements.txt があればそれを使用してください）:
     ```
     pip install duckdb openai defusedxml
     ```
   - その他必要に応じて logging, urllib 等の標準ライブラリを使用します。

3. 環境変数 / .env
   - プロジェクトルートに `.env`（および `.env.local`）を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 主要な環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系利用時）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: monitoring 用 sqlite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等の監視設定
     - KABUSYS_ENV: development / paper_trading / live
     - LOG_LEVEL: DEBUG/INFO/...

   - .env のサンプル（README 用例）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
     DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
     KABU_API_PASSWORD=your_kabu_password
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化（監査ログ用）
   - 監査ログ用 DuckDB を作成する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他のテーブルは ETL 実行や schema 初期化用ユーティリティを別途用意してください（本リポジトリに schema 初期化一式がある場合はそちらを使用）。

---

## 基本的な使い方

以下は代表的なユースケースと呼び出し例です。いずれも Python スクリプト内から呼び出します。

- 設定参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- DuckDB に接続して日次 ETL を実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（銘柄ごと）を計算して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # api_key を引数に渡すか、環境変数 OPENAI_API_KEY を設定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", written)
  ```

- 市場レジームを判定して market_regime に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（上）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用関数の利用例（モメンタム等）
  ```python
  from kabusys.research.factor_research import calc_momentum
  import duckdb
  from datetime import date

  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # 結果は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ... }, ...]
  ```

注意点
- LLM（OpenAI）を呼ぶ処理は外部 API 呼び出しを行います。API キーや課金に注意してください。
- 日付処理はルックアヘッドバイアスを避ける設計になっています（関数は target_date を受け取り内部で date.today() を参照しない等）。
- ETL / API 呼び出しはネットワークエラーや API レート制限に対するリトライを備えていますが、運用時はログと監視を設定してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要なモジュール構成（src/kabusys 以下）:

- kabusys/__init__.py
  - __version__ = "0.1.0"

- kabusys/config.py
  - 環境変数の自動ロード（.env, .env.local）
  - Settings クラス（アプリ設定のプロパティ）

- kabusys/ai/
  - news_nlp.py         — ニュースセンチメント解析（OpenAI）
  - regime_detector.py  — 市場レジーム判定（MA + マクロニュース）

- kabusys/data/
  - jquants_client.py       — J-Quants API クライアント（取得・保存）
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETLResult 再エクスポート
  - calendar_management.py  — マーケットカレンダー管理（is_trading_day 等）
  - news_collector.py       — RSS 収集（SSRF 対策・正規化）
  - audit.py                — 監査ログスキーマ初期化（signal/order/executions）
  - quality.py              — データ品質チェック
  - stats.py                — 統計ユーティリティ（zscore_normalize）

- kabusys/research/
  - factor_research.py      — ファクター（モメンタム/バリュー/ボラティリティ）
  - feature_exploration.py  — 将来リターン/IC/統計サマリ
  - __init__.py             — 研究向け関数のエクスポート

- kabusys/ai/__init__.py     — score_news の公開

各モジュールの詳細は該当ファイルの docstring を参照してください。多くの関数は DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り、DB 上の所定テーブル（raw_prices, raw_news, ai_scores, prices_daily, raw_financials, market_calendar, market_calendar など）を参照または更新します。

---

## 運用上のヒント

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化できます。
- DuckDB を永続化する場合はバックアップや VACUUM ポリシーを検討してください。
- OpenAI 呼び出しはバッチ単位で行われ、429 / タイムアウト / 5xx に対して指数バックオフでリトライしますが、運用時は API レート・コストを常に監視してください。
- ETL 実行後は quality.run_all_checks で品質問題を検出し、重大なエラーがあればアラートをあげると良いです。
- 監査ログは削除しない設計です。長期運用での DB サイズ管理（アーカイブ）を検討してください。

---

必要であれば、README にサンプル .env.example、requirements.txt、起動スクリプト（run_etl.py 等）のテンプレートを追加できます。何を優先して追記しましょうか？