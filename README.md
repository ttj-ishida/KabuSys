# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。  
ETL、データ品質チェック、ファクター・リサーチ、ニュースNLP（OpenAI）および市場レジーム判定、監査ログ（発注→約定トレーサビリティ）などのユーティリティ群を含みます。

注意: 本リポジトリはライブラリ/バッチ処理向けの内部実装群です。実際の発注や本番連携には各種 API キー・設定と運用上の注意が必要です。

## 主な特徴
- J-Quants API からの差分ETL（株価、財務、JPXカレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集（RSS）＋前処理、ニュース→銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント（銘柄別 ai_score）とマクロセンチメントによる市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）、将来リターン / IC 計算、Zスコア正規化
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化と専用 DuckDB 初期化ユーティリティ
- 環境変数管理と自動 .env ロード（プロジェクトルート検出）

## 依存関係（主要）
- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリ以外は pyproject / requirements に合わせてインストールしてください）

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabuステーション API パスワード（実行モジュール用）
- SLACK_BOT_TOKEN — Slack 通知用トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID
- OPENAI_API_KEY — OpenAI 呼び出しで使用（news_nlp / regime_detector）

任意 / デフォルトあり:
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視データベースパス（デフォルト data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

自動 .env ロード:
- パッケージはパッケージルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動読み込みします。自動ロード無効化は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

## セットアップ手順（例）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
3. 依存ライブラリをインストール（pyproject.toml / requirements.txt に従う）
   - 例: pip install -e .[all]（該当する extras がある場合）
4. 環境変数を設定（.env をプロジェクトルートに作成）
   - 例 .env:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development
     ```
5. DuckDB ファイルなどの初期ディレクトリを作成（デフォルトは data/ 配下を想定）
   - 例: mkdir -p data

## 基本的な使い方（コード例）

- DuckDB 接続を作って日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコア取得（ai_scores への書き込み）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written} codes")
  ```
  注意: OpenAI API キーは環境変数 OPENAI_API_KEY から取得されます（引数で上書き可）。

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DuckDB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit に対して発行ログテーブルが作成される
  ```

- ファクター計算 / リサーチ:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

## 主要コマンド / エントリポイント
（本リポジトリに CLI がない場合は上記のように Python API を直接呼び出す想定です。運用用のスクリプトや cron / systemd ユニットから呼ぶ想定。）

- ETL バッチ: kabusys.data.pipeline.run_daily_etl
- カレンダー差分更新: kabusys.data.calendar_management.calendar_update_job
- ニュース収集: kabusys.data.news_collector.fetch_rss / 保存処理は専用スクリプトで raw_news へ保存する想定
- AI 処理: kabusys.ai.news_nlp.score_news、kabusys.ai.regime_detector.score_regime
- 監査スキーマ初期化: kabusys.data.audit.init_audit_db / init_audit_schema

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ初期化、version
  - config.py — 環境変数 / .env 自動ロード / Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースをバッチで OpenAI に投げ銘柄ごとのスコアを ai_scores に書き込む
    - regime_detector.py — ETF(1321) の MA200 とマクロニュースを組み合わせて日次市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理・営業日ユーティリティ
    - etl.py — ETL 用の公開型（ETLResult）
    - pipeline.py — 日次 ETL パイプライン（差分取得 / 品質チェック）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログ（テーブルDDL・初期化）ユーティリティ
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 取得・前処理・SSRF 対策・記事ID正規化
  - research/
    - __init__.py — 研究用ユーティリティ再エクスポート
    - factor_research.py — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — 将来リターン計算、IC/ランク/統計サマリー
  - ai/、research/、data/ 以下に多数の関数・ユーティリティあり（詳細はソース参照）

## 運用上の注意
- OpenAI / J-Quants 等の API キーは厳重に管理してください。テスト・CI ではキーのモック化を推奨します（モジュール内で _call_openai_api を差し替えられる設計）。
- 自動 .env ロードは便利ですが、CI やテストで外部環境に依存したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB executemany の空パラメータに対する互換性に注意（実装内で保護されています）。
- ニュース収集モジュールは外部 RSS に対して SSRF 対策やレスポンスサイズ制限を実装していますが、運用に合わせた追加の堅牢化を検討してください。
- 本コードはルックアヘッドバイアスを避ける設計方針が多々組み込まれています。バックテストなどで使用する際は target_date を明示的に与えることで安全に再現できます。

## 既知の前提 / 制約
- DuckDB をデータストアとして利用する前提（ファイルパスは設定可能）。
- OpenAI は JSON mode（response_format）を用いたやり取りを想定しているため、出力のバリデーションを厳密に行います。
- J-Quants API のレート制限を守るため固定間隔スロットリングと指数バックオフを実装しています。

---

さらに具体的な利用方法や運用スクリプト、テーブルスキーマ、外部サービス連携のサンプルが必要であれば、どのワークフロー（ETL、ニュース収集、AIスコアリング、監査DB初期化、研究解析 等）について詳しい手順やサンプルを提示するか教えてください。