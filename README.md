# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
DuckDB をデータ層に用い、J-Quants API からのデータ取得、ニュース収集・LLMによるニュース分析、ファクター算出、ETL パイプライン、監査ログ（トレーサビリティ）などを提供します。

---

## 主な特徴（機能一覧）

- データ収集・ETL
  - J-Quants API からの株価（日足）・財務情報・マーケットカレンダー取得（差分更新・ページネーション対応）
  - ETL の結果を DuckDB に冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース関連 / AI
  - RSS からのニュース収集（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）
  - マクロニュース + ETF（1321）200日移動平均乖離から市場レジーム（bull/neutral/bear）判定

- リサーチ / ファクター
  - Momentum / Value / Volatility 等のファクター計算（prices_daily / raw_financials に基づく）
  - 将来リターン計算、IC（Information Coefficient）の算出、統計サマリー、Zスコア正規化

- 監査（Audit）
  - シグナル → 発注 → 約定のトレース可能な監査テーブル定義・初期化ユーティリティ

- 運用補助
  - マーケットカレンダー管理（営業日判定、next/prev trading day 等）
  - 実行監視用の設定（PID / killflag / CPU/メモリ閾値等）

---

## 必要要件（依存パッケージ・環境）

- Python 3.10+
- 主要 Python ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime 等）を多用

（プロジェクトに requirements.txt がある場合はそちらを利用してください。無ければ上記を pip でインストールします。）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存関係をインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt`）

4. 環境変数（.env）を作成
   - プロジェクトルート（.git または pyproject.toml のある場所）に `.env` / `.env.local` を置くと自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必須の環境変数を設定（例）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時）
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（データ取得）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（発注系を使う場合）
   - ほか任意設定（下記参照）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants リフレッシュトークン
- OPENAI_API_KEY（必須 for AI 実行時）: OpenAI API キー
- KABU_API_PASSWORD（必須 if 発注機能を使う場合）: kabuステーション API パスワード
- KABU_API_BASE_URL: kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知関連（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 実行環境 (development / paper_trading / live)。デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

※ .env のフォーマットはシェル形式（export 可、コメント可、クォート対応）です。config モジュールがプロジェクトルートの `.env` と `.env.local` を自動読み込みします（OS 環境変数が優先）。

---

## 使い方（主要なユースケース）

以下は簡単な Python REPL / スクリプトでの利用例です。実行前に環境変数を設定してください。

- DuckDB 接続の作成例
  - import duckdb, from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn)  # target_date を指定可能
  - print(result.to_dict())

- ニュースセンチメント（銘柄別）スコア生成（前日15:00JST～当日08:30JST のウィンドウ）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - n = score_news(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY を環境に設定

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20))  # OPENAI_API_KEY が必要

- 監査テーブルの初期化（監査専用 DB を使う）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # 必要なら監査用 conn をアプリへ渡す

- マーケットカレンダー更新ジョブ（夜間バッチ）
  - from kabusys.data.calendar_management import calendar_update_job
  - calendar_update_job(conn)  # lookahead_days 引数で先読み日数調整

注意:
- AI 呼び出し（OpenAI）には API 制約やレート制限があります。失敗時はフェイルセーフでスコアが 0.0 にフォールバックする実装が多く、例外を上位に投げないケースもあります。ログを確認してください。
- 時間・日付の扱いは「ルックアヘッドバイアス防止」を重視しており、内部実装は target_date ベースで過去データのみを参照します。

---

## ディレクトリ構成（主なファイル）

（src/kabusys 以下）

- __init__.py
- config.py
  - .env 自動読み込み、settings オブジェクト（環境変数ラッパー）
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの集約・OpenAI による銘柄別センチメント
  - regime_detector.py — マクロセンチメント + ETF MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py  — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py        — ETL パイプライン（run_daily_etl など）
  - etl.py             — ETLResult の再エクスポート
  - news_collector.py  — RSS 取得・前処理・raw_news 保存
  - quality.py         — データ品質チェック群
  - stats.py           — zscore_normalize 等の統計ユーティリティ
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py           — 監査ログスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py     — モメンタム／バリュー／ボラティリティ等
  - feature_exploration.py — 将来リターン、IC、統計サマリー、rank
- monitoring / execution / strategy / (その他): パッケージ公開用プレースホルダ（__all__ で参照）

簡易ツリー（抜粋）:
- src/kabusys/
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/
    - jquants_client.py
    - pipeline.py
    - news_collector.py
    - quality.py
    - calendar_management.py
    - audit.py
    - stats.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - config.py
  - __init__.py

---

## 運用上の注意

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を指定して自動読み込みを抑制できます。
- OpenAI 呼び出しはリトライ（指数バックオフ）とパース失敗時のフォールバックを備えていますが、APIキーの管理や使用量には注意してください。
- J-Quants API のレート制限（120 req/min）に合わせた内部レートリミッター・再試行ロジックがあります。大量取得は注意して行ってください。
- DuckDB バージョン依存の挙動（executemany の空配列扱いなど）に配慮された実装です。運用時は利用する DuckDB バージョンとの互換性を確認してください。

---

必要があれば以下の情報も追加で作成します：
- requirements.txt / poetry/pyproject.toml のサンプル
- 具体的な ETL 運用スクリプト（cron / systemd timer 用）
- テスト・CI のセットアップ例

ご希望があれば追加の README セクションや実行例を追記します。