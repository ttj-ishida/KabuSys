# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース + LLM によるセンチメント評価、リサーチ用ファクター計算、監査ログスキーマなどを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのデータパイプラインとリサーチ・自動売買の基盤ライブラリです。主な目的は次のとおりです。

- J-Quants API から株価・財務・マーケットカレンダーを差分取得して DuckDB に保存する ETL。
- RSS ニュースの収集と前処理、銘柄別ニュース集合を OpenAI モデルで評価して ai_scores を生成。
- マクロニュース + ETF 200 日移動平均乖離を組み合わせた「市場レジーム判定」。
- ファクター計算（モメンタム・ボラティリティ・バリュー）と特徴量探索（将来リターン、IC 等）。
- 監査ログ（signal / order_request / execution）用のスキーマ初期化ユーティリティ。
- データ品質チェック（欠損・スパイク・重複・日付不整合）。

設計方針として「ルックアヘッドバイアス回避」「冪等性」「API レート制御」「フェイルセーフ（API失敗時はスキップ）」を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 各種）
  - カレンダー管理（is_trading_day 等）
  - ニュース収集（RSS → raw_news）
  - データ品質チェック（run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み・管理（自動で .env/.env.local を読み込み、settings オブジェクトを提供）

---

## 要件（推奨）

- Python 3.10+
- 必要な Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI）

（実際の requirements.txt はこのコードベース外の可能性があります。インストール時はプロジェクトのパッケージ定義を参照してください。）

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトが pip パッケージになっている場合は `pip install -e .` / requirements.txt を使用してください）

4. 環境変数の設定
   プロジェクトルートに `.env` / `.env.local` を作成すると、kabusys.config が自動で読み込みます（.git または pyproject.toml をルート検出基準に使用）。

   自動ロードを無効にする場合:
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（必須とされるもの）:
   - JQUANTS_REFRESH_TOKEN  (J-Quants refresh token)
   - KABU_API_PASSWORD      (kabuステーション API パスワード)
   - SLACK_BOT_TOKEN        (Slack 通知用)
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY         (OpenAI 呼び出し時、関数に直接渡しても可)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB, default: data/monitoring.db)
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベースの準備（監査DB など）
   - 監査ログ専用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

---

## 使い方（クイックスタート）

以下は基本的な用例です。全ての例は Python からインポートして実行します。

- DuckDB 接続例
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（データ取得・保存・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアリング（OpenAI API キーは env または引数で指定）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None -> OPENAI_API_KEY 環境変数を参照
  print(f"scored {count} codes")
  ```

  注意: OpenAI 呼び出し失敗時は設計上フォールバック（該当チャンクをスキップ）します。

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  rows = calc_momentum(conn, target_date=date(2026, 3, 20))
  # rows は [{ "date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
  ```

- 監査ログスキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db はテーブルとインデックスを作成して DuckDB 接続を返す
  ```

- カレンダー判定例
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

エラーハンドリング:
- OpenAI API キーが未設定の場合、score_news / score_regime は ValueError を送出します。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants 関連は get_id_token で JQUANTS_REFRESH_TOKEN を参照します。未設定の場合は ValueError。

テスト時の補助:
- 自動的な .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出しやネットワーク I/O をモックできるよう関数が分離されています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch などで差し替え可能）。

---

## ディレクトリ構成

主要ファイル / モジュールの概要を示します（src/kabusys 以下）。

- __init__.py
  - パッケージ公開 API。version 情報など。

- config.py
  - 環境変数の自動読み込み（.env / .env.local）、Settings クラス（settings インスタンス）。

- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・OpenAI での銘柄別センチメント付与（score_news）
  - regime_detector.py — ETF(1321) MA200 とマクロ記事から市場レジーム判定（score_regime）

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（fetch/save 各種、レート制御・リトライ）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py — ETLResult の再エクスポート
  - calendar_management.py — JPX カレンダー管理（is_trading_day, next_trading_day, run calendar_update_job）
  - news_collector.py — RSS 取得・前処理・raw_news への保存（SSRF/サイズ制限等の安全対策あり）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ（init_audit_schema / init_audit_db）

- research/
  - __init__.py
  - factor_research.py — calc_momentum, calc_value, calc_volatility
  - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

その他:
- news_collector と jquants_client はセキュリティ（SSRF、XML インジェクション、レスポンス上限）や冪等性（INSERT ... ON CONFLICT）に配慮して実装されています。
- AI関連は OpenAI の JSON Mode を想定したレスポンス処理・バリデーション・リトライを含みます。

---

## 注意事項 / 運用上のヒント

- 本ライブラリは「データ基盤 / 研究用」の機能が主であり、実際の注文実行フロー（ブローカーの発注 API との連携）は別モジュール／ラッパーが必要です。order_requests / executions テーブルは監査用スキーマを提供しますが、実際の送信ロジックは本リポジトリに含まれていない可能性があります。
- production（本番）環境では KABUSYS_ENV=live を設定し、ログレベルや Slack 通知などの運用設定を適切に行ってください。
- OpenAI の呼び出しはコストとレイテンシを伴います。batch サイズやトークン量、リトライ設定を運用に合わせて調整してください。
- J-Quants API はレート制限があります（実装は固定間隔スロットリング）。大量取得時はバックオフや分散スケジュールを検討してください。

---

必要であれば以下を作成／追記します:
- requirements.txt / pyproject.toml の依存定義例
- サンプル .env.example（フル）
- コマンドライン実行用のスクリプト例（ETL ジョブや監視ジョブ）

ご希望があればどれを優先して追加するか教えてください。