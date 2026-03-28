# KabuSys — 日本株自動売買プラットフォーム（README 日本語）

概要
- KabuSys は日本株のデータ取得・ETL、ニュースNLP（LLM）によるセンチメント評価、ファクター計算、監査ログ管理などを備えた自動売買／リサーチ用のコードベースです。
- DuckDB をデータプラットフォームとして用い、J-Quants API や RSS ニュース、OpenAI（gpt-4o-mini 等）を組み合わせて市場レジーム判定や銘柄毎の AI スコアを生成します。
- 設計方針として「ルックアヘッドバイアス排除」「冪等処理」「堅牢なリトライ・フェイルセーフ」を重視しています。

主な機能
- データ取得・ETL
  - J-Quants から株価日足（OHLCV）、財務情報、マーケットカレンダーを差分取得し DuckDB に保存（冪等）。
  - ETL 実行の結果を ETLResult として返却・ログ化。
- データ品質チェック
  - 欠損データ、スパイク（大幅変動）、重複、日付不整合（未来日付・非営業日のデータ）を検出。
- ニュース収集・前処理
  - RSS フィードの安全な取得（SSRF 防止、gzip 上限、XML 安全パーサ）と正規化、raw_news 保存、銘柄紐付け。
- ニュース NLP（LLM）
  - 銘柄ごとのニュースをまとめて OpenAI に問い合わせ、-1.0〜1.0 のセンチメント（ai_score）を ai_scores テーブルへ保存（バッチ・リトライ・レスポンス検証）。
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
- ファクター計算 & リサーチ
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC（スピアマン）や統計サマリー、Z スコア正規化。
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを提供し、シグナル→発注→約定まで UUID を使って完全トレース可能に保存。
- 設定管理
  - .env/.env.local または環境変数から設定を読み込み（自動ロードを無効化するフラグあり）。

セットアップ手順（開発環境向け）
1. Python バージョン
   - Python 3.9+（できれば 3.10 / 3.11）を推奨。

2. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージのインストール
   - 代表的な依存例:
     - duckdb
     - openai
     - defusedxml
   - インストール例:
     - pip install duckdb openai defusedxml

   ※ 実プロジェクトでは requirements.txt / pyproject.toml を用意して pip install -r あるいは pip install . を使用してください。

4. 環境変数 / .env
   - プロジェクトルート（pyproject.toml や .git があるディレクトリ）に `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数（少なくともこれらを設定してください）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（利用する場合）
     - SLACK_BOT_TOKEN       : Slack 通知に使用する Bot トークン（利用する場合）
     - SLACK_CHANNEL_ID      : Slack のチャンネル ID（利用する場合）
     - OPENAI_API_KEY        : OpenAI API キー（LLM 呼び出しに必須）
   - 任意:
     - DUCKDB_PATH           : データベースパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト data/monitoring.db）
     - KABUSYS_ENV           : development / paper_trading / live（デフォルト development）
     - LOG_LEVEL             : ログレベル（DEBUG/INFO/...）

   - .env 例（簡易）
     JQUANTS_REFRESH_TOKEN=xxxxxxxx
     OPENAI_API_KEY=sk-xxxxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

使い方（簡単な例）
- DuckDB 接続を作って ETL・NLP・レジーム判定を呼ぶサンプルコード:

  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.ai.news_nlp import score_news
  from kabusys.ai.regime_detector import score_regime
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  # DuckDB 接続（ファイルは settings.duckdb_path）
  conn = duckdb.connect(str(settings.duckdb_path))

  # 日次 ETL を実行（target_date を省略すると今日）
  result = run_daily_etl(conn)
  print(result.to_dict())

  # ニュース NLP（例: 2026-03-20 の ai_scores を作る）
  n = score_news(conn, date(2026, 3, 20))
  print(f"ai scores written: {n}")

  # 市場レジーム判定（同日）
  r = score_regime(conn, date(2026, 3, 20))
  print("regime scoring done")

  # 監査用 DuckDB を初期化（別 DB 文件にして運用）
  audit_conn = init_audit_db("data/audit_duckdb.duckdb")
  # その後、order_requests 等に発注ログを記録していく

注意点 / 運用のヒント
- OpenAI 呼び出しや J-Quants API 呼び出しは料金・レート制限があるため、本番運用ではキー管理と呼び出し頻度に注意してください。
- LLM 呼び出し失敗時はいずれのモジュールもフェイルセーフ（ゼロスコアやスキップ）で継続する設計ですが、ログを監視して問題を検出してください。
- ETL は差分更新・バックフィル（デフォルト 3 日）を行います。初回は大量取得が発生します。
- テストや CI で自動読み込みの .env を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの LLM スコアリング（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - etl.py                — ETL インターフェース再エクスポート
    - pipeline.py           — ETL 実装（run_daily_etl, run_prices_etl, ...）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - quality.py            — データ品質チェック（check_missing_data 等）
    - audit.py              — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
    - jquants_client.py     — J-Quants API クライアント（fetch/save 系）
    - news_collector.py     — RSS 取得と raw_news への保存
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum, volatility, value）
    - feature_exploration.py— 将来リターン / IC / 統計サマリー
  - その他（strategy / execution / monitoring）に相当するパッケージ名が __all__ に列挙されていますが、今回の提供コードには一部モジュール群が中心です。

ロギングと実行環境
- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- KABUSYS_ENV により開発 / ペーパー / 本番（live）を区別できます。is_live / is_paper / is_dev が利用可能です。

ライセンス・貢献
- 本リポジトリのライセンス表記がない場合は、利用・配布前にライセンスを明示してください。
- バグ報告や改善提案は Issue を通じて行ってください。内部 API 変更時は後方互換性を考慮することを推奨します。

付録：よくある操作コマンド（例）
- パッケージを開発モードでインストール（プロジェクトに setup/pyproject がある場合）
  - pip install -e .
- リポジトリルートで .env を作成してから Python スクリプトを実行
  - python scripts/run_daily.py（任意のランナーを用意）
- DuckDB ファイルを指定して監査 DB を初期化（Python REPL）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")

以上。README の補足やサンプルスクリプト（CLI / systemd / Airflow ジョブ例など）を追加したい場合は、どのユースケース（ETL バッチ、リアルタイム発注ワーカー、バックテスト環境など）向けの例が必要か教えてください。