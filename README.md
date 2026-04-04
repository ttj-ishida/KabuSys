# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けのデータプラットフォーム兼自動売買支援ライブラリです。J-Quants API からデータを取得して DuckDB に保存する ETL、ニュースの NLP による銘柄センチメント評価、マーケットレジーム判定、ファクター計算・特徴量探索、データ品質チェック、監査ログ（トレーサビリティ）生成など、研究・運用の両フェーズで利用できる機能群を提供します。

主な設計方針：
- ルックアヘッドバイアスを生まない（target_date を明示して計算）
- DuckDB を DB 層として利用（オンプレ/ローカルでの高速処理）
- 外部 API 呼び出しはリトライやレート制御を備えた堅牢な実装
- OpenAI（gpt-4o-mini）を使ったニュース評価はフェイルセーフ設計

---

## 機能一覧

- ETL / データ取得
  - J-Quants から株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得・保存（jquants_client）
  - 差分取得 / バックフィル / ページネーション対応
  - ETL の集約エントリ（run_daily_etl）

- データ管理・品質
  - market_calendar（営業日判定、next/prev_trading_day 等）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP
  - RSS 収集器（news_collector）: トラッキング除去、SSRF 対策、XML サニタイズ
  - ニュースセンチメント評価（news_nlp）: OpenAI による銘柄別スコアリング、バッチ・リトライ・レスポンス検証

- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュース（LLM）を合成して市場レジームを日次判定（regime_detector）

- リサーチ（ファクター算出・解析）
  - Momentum / Volatility / Value 等のファクター計算（factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等（feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等のテーブル定義・初期化（audit）
  - order_request_id による冪等制御、UTC タイムスタンプ運用

- 実行監視用設定
  - PID ファイル / kill flag / CPU/Memory/Disk 閾値など（config.Settings）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型注釈（X | Y）を使用）
- ネットワーク経由で外部 API を利用するため適切なネットワーク環境

1. リポジトリをクローン
   - git clone ...（本手順はソース配布形態に合わせて調整してください）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 最低限の依存例：
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

4. 環境変数設定（.env）
   - プロジェクトルートに `.env` または `.env.local` を置くと自動ロードされます（OS 環境変数が優先）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須（運用に応じて）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携する場合）
   - オプション:
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に未指定の場合参照）
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知）
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
     - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   .env 例：
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development

5. データディレクトリ作成
   - settings.duckdb_path の親ディレクトリなどを作成
     - mkdir -p data

---

## 使い方（簡易サンプル）

Python スクリプトから主要な機能を呼ぶ例を示します。各関数は DuckDB 接続（duckdb.connect()）を受け取ります。

- DuckDB 接続を開く例
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date を指定して過去日の ETL も可
  print(result.to_dict())

- ニューススコア生成（OpenAI 必須）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))  # date を適宜指定
  print("書き込んだ銘柄数:", n_written)

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査 DB 初期化（監査専用 DB を使う場合）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions テーブルが作成される

注:
- score_news / score_regime は OpenAI API を直接呼ぶため、API キーを env または引数で渡す必要があります。
- run_daily_etl は内部で calendar ETL → price ETL → financial ETL → 品質チェック を実行します。各ステップは例外を個別に捕捉します。

---

## 主要モジュール・ディレクトリ構成

src/kabusys/
- __init__.py (パッケージエクスポート、バージョン)
- config.py
  - .env 自動ロード、Settings（J-Quants / kabu / LINE / DB / 監視 / システム設定）
- ai/
  - __init__.py (score_news をエクスポート)
  - news_nlp.py
    - ニュース記事を銘柄別にまとめ、OpenAI（gpt-4o-mini）でセンチメント評価、ai_scores に書き込み
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュース（LLM）を合成して market_regime に書き込み
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API 呼び出し、レート制御、認証トークン管理、DuckDB への保存関数
  - pipeline.py
    - ETLResult、run_daily_etl、個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - etl.py
    - ETLResult の再エクスポート
  - calendar_management.py
    - market_calendar 管理、営業日判定、calendar_update_job
  - news_collector.py
    - RSS 取得、前処理、raw_news への保存（SSRF/受信サイズ制限/XML サニタイズ）
  - quality.py
    - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py
    - zscore_normalize 等の統計ユーティリティ
  - audit.py
    - 監査ログテーブル定義・初期化
- research/
  - __init__.py (研究用関数をエクスポート)
  - factor_research.py
    - Momentum / Volatility / Value / Liquidity 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、rank、統計サマリー

---

## 注意事項 / 運用メモ

- OpenAI 使用時
  - レスポンスは JSON モード（response_format={"type":"json_object"}）を期待しているため、応答が不正な JSON だとフェールセーフで 0.0 またはスキップします。
  - API の失敗（ネットワーク/429/5xx 等）は再試行の後フェイルセーフで継続する設計です（例: macro_sentiment = 0.0）。

- J-Quants API
  - レート制限（120 req/min）を守るため内部でスロットリングを行います。
  - 401 でトークン期限切れが返った場合は自動でリフレッシュを試みます（1 回のみ）。

- データの時刻取り扱い
  - すべての TIMESTAMP は UTC で保存する設計（監査ログ等）。
  - ニュースのウィンドウや ETL は target_date を明示して動作し、datetime.today()/date.today() を直接参照しない実装が多く、バックテスト/再現性を重視しています。

- テスト
  - 自動 .env ロードの影響を避けたいテストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - OpenAI 等の外部呼び出し部はモック可能なように設計されています（モジュール内の _call_openai_api をパッチする等）。

---

もし README に追加したい内容（例: CI/Coverage、運用手順書、具体的な SQL スキーマ、サンプル .env.example）や、README を英語版でも作成してほしい等の要望があれば教えてください。