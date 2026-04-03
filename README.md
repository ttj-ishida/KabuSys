# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM を用いたニュースセンチメント、リサーチ用ファクター群、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「DuckDB を中心としたローカル DB 利用」「API 呼び出しの堅牢化（リトライ・レート制御）」です。

バージョン: 0.1.0

---

## 機能一覧

- 設定管理
  - .env / 環境変数から自動読み込み（プロジェクトルート判定、`.env.local` 上書き対応）
  - settings オブジェクトで強制必須変数取得

- データ ETL（kabusys.data.pipeline）
  - J-Quants からの株価（日次 OHLCV）・財務・JPX カレンダーの差分取得と DuckDB への冪等保存
  - ETL 実行結果を ETLResult に集約
  - 品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集（kabusys.data.news_collector）
  - RSS 取得・前処理（URL 正規化・トラッキング除去）・raw_news への保存
  - SSRF 対策・XML の安全パース・レスポンスサイズ制限

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント付与
  - チャンク処理・リトライ・レスポンス検証・スコアクリップ

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で 'bull' / 'neutral' / 'bear' 判定

- リサーチ（kabusys.research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC 計算、ファクター統計サマリー
  - クロスセクション Z-score 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - init_audit_db で専用 DuckDB を初期化

- J-Quants クライアント（kabusys.data.jquants_client）
  - レート制御、リトライ、トークン自動更新対応の API 呼び出し
  - DuckDB への冪等保存関数（save_daily_quotes 等）

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union 型や型注釈を多用）
- DuckDB, OpenAI Python SDK, defusedxml などが必要

例: pipenv / venv を使用したインストール例

1. リポジトリをクローン、パッケージのインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-root>
   pip install -e ".[dev]"   # setup.py/pyproject.toml がある場合
   ```
   必要パッケージ（参考）:
   - duckdb
   - openai
   - defusedxml

2. 環境変数 / .env の準備  
   プロジェクトルート（.git または pyproject.toml がある場所）で `.env` と `.env.local` を配置できます。自動読み込み順は:
   OS 環境 > .env.local > .env

   主な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PID_FILE_PATH=data/execution.pid
   KILL_FLAG_PATH=data/kill.flag
   KILL_FLAG_CLEAR_ON_START=0
   CPU_THRESHOLD_PCT=90.0
   MEMORY_THRESHOLD_PCT=85.0
   DISK_THRESHOLD_PCT=90.0
   KABUSYS_ENV=development   # development | paper_trading | live
   LOG_LEVEL=INFO
   ```

   テストや CI で自動的に .env ロードを抑止したい場合:
   ```
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

3. DuckDB ファイル準備  
   デフォルトは `data/kabusys.duckdb`。settings.duckdb_path を参照して接続します。監査専用 DB を作る場合は init_audit_db を利用します（下記参照）。

---

## 使い方（主要な API と使用例）

- 共通: 設定オブジェクト
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- ETL 実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア付与（LLM を利用）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数を渡す
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants クライアントの直接利用例
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  import duckdb

  records = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
  conn = duckdb.connect(str(settings.duckdb_path))
  saved = save_daily_quotes(conn, records)
  ```

- リサーチ API 例（ファクター計算）
  ```python
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect(str(settings.duckdb_path))
  res = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意:
- OpenAI API は大きなコストが発生する可能性があるため、`OPENAI_API_KEY` の管理とバッチサイズの調整に注意してください。
- 環境が `KABUSYS_ENV=live` の場合は本番注文などの処理に注意して運用してください。

---

## 設計上の重要な注意点

- ルックアヘッドバイアス対策:
  - 各モジュールは内部で現在時刻を直接参照せず、呼び出し側が `target_date` を与える方式を採用している箇所が多いです（backtest に適切）。
  - DB クエリは date < target_date や date = target_date 等で厳密にスライスします。

- 自動 .env ロード:
  - パッケージ読み込み時にプロジェクトルートから `.env` と `.env.local` を自動で読み込みます。無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- エラー/フォールバック:
  - OpenAI・J-Quants 呼び出しはリトライ・フェイルセーフ（失敗時はスコア 0.0 やスキップ）を採用しています。呼び出しが失敗してもプロセス全体をクラッシュさせない設計です（ただし一部の致命的な DB 書き込み失敗は例外を伝播します）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なディレクトリとファイルの概要です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（OpenAI 連携）
    - regime_detector.py     — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存関数
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS ニュース収集
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns / IC / summary / rank

---

## テスト / 開発時のヒント

- 自動 .env 読み込みを止めたい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しはユニットテストでモックしやすいように内部の _call_openai_api を分離してあります。news_nlp/regime_detector 内の該当関数を patch してレスポンスを模擬してください。
- DuckDB はインメモリ ":memory:" でも初期化可能なので短時間のテストには便利です（例: init_audit_db(":memory:")）。

---

以上が README の概要です。必要であればサンプル .env.example、起動スクリプト例、CI 設定や詳細な API リファレンス（関数引数の詳細・戻り値の構造）も追記できます。どの部分を優先して追加しますか？