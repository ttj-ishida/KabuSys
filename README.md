# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。  
ETL（J-Quants からの日次データ取得）、ニュース収集・NLP（OpenAI）、因子計算・リサーチ、監査ログ・発注監視などを組み合わせて、研究環境から実運用まで想定した機能群を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡単なコード例）
- 環境変数（.env 例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は日本株を対象にしたデータプラットフォームとリサーチ／自動売買のための共通ユーティリティ群をまとめた Python パッケージです。主に下記の領域をカバーします。

- J-Quants API からのデータ取得（株価・財務・市場カレンダー）
- DuckDB を用いたローカルデータベースのETL保存（冪等性あり）
- ニュース収集（RSS）および OpenAI を使ったニュースセンチメント計算
- 市場レジーム判定（ETF + マクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定をトレースするテーブル群）
- 設定管理（.env 自動ロード・検証）

設計の共通方針として、バックテストや研究での「ルックアヘッドバイアス」防止を強く念頭に置いています（date を明示して処理する、datetime.today() を直接参照しない等）。

---

## 機能一覧（抜粋）
- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 系）
  - market_calendar 管理（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック（SSRF/サイズ上限対策済）
  - quality: データ品質チェック（missing, spike, duplicates, date consistency）
  - audit: 監査ログスキーマ初期化（signal_events / order_requests / executions）
  - jquants_client の堅牢な HTTP / リトライ / レート制御
- ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して daywise market_regime を記録
- research
  - factor_research: calc_momentum / calc_volatility / calc_value
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- utils
  - data.stats.zscore_normalize
- config
  - 環境変数の自動ロード（プロジェクトルートの .env / .env.local）と必須変数検証

---

## セットアップ手順

前提:
- Python 3.9+（型ヒントで Union 型等を使用）
- pip 環境

1. リポジトリをクローンまたはパッケージソースを配置
2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```
   - 他に urllib / datetime 等は標準ライブラリで賄われています。
   - 実行環境によっては追加で HTTP クライアント等をインストールしてください。

3. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動的にロードされます（.env.local は上書き）。
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 必須の環境変数（例）は後述のセクションを参照してください。

4. DuckDB データベースファイルの用意（例）
   - データファイルを格納するディレクトリを作成:
     ```
     mkdir -p data
     ```
   - 監査ログ用 DB を初期化する例（Python REPL / スクリプトで実行）:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn は duckdb connection オブジェクト
     ```

---

## 使い方（簡単なコード例）

以下は基本的な利用例です。詳細なパラメータや戻り値については各モジュールの docstring を参照してください。

- 設定の参照
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

- DuckDB に接続して日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを取得して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"scored {count} symbols")
  ```

- 市場レジーム判定を実行する
  ```python
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査スキーマの初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（研究）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  date = date(2026, 3, 20)
  mom = calc_momentum(conn, date)
  vol = calc_volatility(conn, date)
  val = calc_value(conn, date)
  ```

注意:
- OpenAI を呼ぶ関数は `api_key` 引数で明示的に渡すか、環境変数 `OPENAI_API_KEY` を設定してください。未設定時は ValueError を送出します。
- J-Quants 用の API キーは `JQUANTS_REFRESH_TOKEN` を .env に設定しておくと自動で get_id_token に利用されます。

---

## 環境変数（.env 例）
次の環境変数のいくつかは必須です（初期化処理や一部機能で参照されます）。

例（.env または .env.local）:
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu ステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXXX

# OpenAI（AI スコアリング）
OPENAI_API_KEY=sk-...

# DB パス（オプション）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

動作の注意:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` / `.env.local` を自動ロードします。
- 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル・モジュール）
パッケージの主要構成は以下の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                         — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                      — ニュース NLP スコアリング（OpenAI 呼び出し、バッチ処理）
    - regime_detector.py               — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py                — J-Quants API クライアント（fetch/save）
    - pipeline.py                      — ETL パイプライン（run_daily_etl 等）
    - etl.py                           — ETLResult 再エクスポート
    - news_collector.py                — RSS 収集・前処理・保存（SSRF 対策等）
    - calendar_management.py           — マーケットカレンダー判定・更新ロジック
    - quality.py                       — データ品質チェック
    - stats.py                         — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                         — 監査ログスキーマ定義 / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py               — モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py           — 将来リターン / IC / 統計サマリ等

各モジュールは docstring で設計方針や入力／出力を詳細に記述しています。実運用時は各関数の docstring を参照してください。

---

## 補足・運用上の注意
- ルックアヘッドバイアスに注意して設計されていますが、バックテスト実装側でもデータ利用時の厳密さ（取得日時や fetched_at の取り扱い）を守ってください。
- OpenAI / J-Quants など外部 API を使う箇所はリトライやフォールバック（失敗時に 0.0 を返す等）を組み込んでいますが、運用時はレート制限・コストに注意してください。
- DuckDB のバージョン差異による挙動（executemany の空リスト挙動や配列バインド等）に注意してテストしてください。

---

この README はコードベースの docstring に基づいて作成しています。各機能の詳細や拡張については該当モジュールの docstring を参照してください。必要であれば、具体的なワークフロー（ETL スケジューリング、監査ログと発注フローの連携、Slack 通知例など）についての追加ドキュメントを作成できます。