# KabuSys — 日本株自動売買基盤 (README)

このリポジトリは日本株向けのデータ基盤・研究・戦略実行を想定したライブラリ群です。  
主に J-Quants からのデータ取得、DuckDB を用いたデータ保存・品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ等の機能を提供します。

## プロジェクト概要
- 名称: KabuSys
- 目的: 日本株の自動売買システムに必要なデータ収集（ETL）・品質チェック・特徴量生成・ニュースNLP・レジーム判定・監査ログ等を提供するライブラリ群
- 設計方針（抜粋）:
  - DuckDB をデータストアとして利用（オンディスク/インメモリ両対応）
  - J-Quants API から株価 / 財務 / カレンダー等を差分取得し冪等で保存
  - ニュースは RSS から収集し、OpenAI（gpt-4o-mini）でセンチメント/スコアリングを行う
  - ルックアヘッドバイアスを避ける実装（関数は明示的な target_date を受ける）
  - ETL / 品質チェックは部分失敗を許容して処理継続（問題は収集して上位へ通知）

## 機能一覧
- 設定管理
  - 環境変数 / .env ファイルの自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - 必須環境変数の取得ユーティリティ
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（run_daily_etl）: 市場カレンダー・株価・財務の差分取得・保存・品質チェック
  - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants API クライアント（jquants_client）
    - fetch / save の一連処理（リトライ・レート制御・トークン自動リフレッシュ）
- データ品質（kabusys.data.quality）
  - 欠損、スパイク、重複、日付不整合などの検出
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理・ID生成・冪等保存（SSRF対策・gzip/サイズ制限含む）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
- 研究ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（情報係数）、統計サマリー、Zスコア正規化
- AI モジュール（kabusys.ai）
  - news_nlp.score_news: ニュースを銘柄別にまとめて OpenAI に投げ、ai_scores に書き込む
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュースセンチメントを合成して market_regime に書き込む
- 汎用統計（kabusys.data.stats）
  - zscore_normalize（クロスセクションZスコア正規化）

## セットアップ手順

1. Python 環境を作成（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 依存ライブラリをインストール  
   必須パッケージ（例）:
   - duckdb
   - openai
   - defusedxml

   例（pip）:
   ```
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してインストールしてください。

3. 環境変数の準備  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動的にロードされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   代表的な環境変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB ファイルのディレクトリを作成（必要に応じて）
   ```
   mkdir -p data
   ```

## 使い方（サンプル）

- Python スクリプトから直接呼び出す例

  基本的な ETL を実行する:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", written)
  ```

  市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  監査ログ用 DB 初期化:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- 設定の読み込みについて
  - パッケージ起動時にプロジェクトルートの `.env` および `.env.local` を自動で読み込みます（OS 環境変数が優先されます）。
  - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 必須の設定値は `kabusys.config.settings` 経由で取得できます（例: `settings.jquants_refresh_token`）。

## よく使う API の説明（短期リファレンス）
- kabusys.data.pipeline.run_daily_etl(conn, target_date, id_token=None, ...)
  - 日次 ETL のトップレベル。ETLResult を返す。
- kabusys.data.jquants_client.fetch_daily_quotes(...)
  - J-Quants から株価データを取得。
- kabusys.data.jquants_client.save_daily_quotes(conn, records)
  - raw_prices テーブルへ冪等保存。
- kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - ニュースを AI でスコア化し ai_scores テーブルへ書き込む。
- kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存。
- kabusys.research.calc_momentum / calc_value / calc_volatility
  - ファクター計算関数。DuckDB 接続と target_date を渡して利用。

## ディレクトリ構成
（主なファイル・モジュールのみを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                      — 環境変数 / 設定管理
    - ai/
      - __init__.py
      - news_nlp.py                  — ニュースNLP（score_news 等）
      - regime_detector.py           — 市場レジーム判定（score_regime 等）
    - data/
      - __init__.py
      - jquants_client.py            — J-Quants API クライアント（fetch/save）
      - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
      - etl.py                       — ETLResult の再エクスポート
      - news_collector.py            — RSS ニュース収集
      - calendar_management.py       — 市場カレンダー管理（is_trading_day 等）
      - audit.py                     — 監査ログテーブル定義・初期化
      - quality.py                   — データ品質チェック
      - stats.py                     — 統計ユーティリティ（zscore_normalize）
    - research/
      - __init__.py
      - factor_research.py           — Momentum/Value/Volatility 計算
      - feature_exploration.py       — 将来リターン/IC/統計サマリー
    - research/ (その他)
    - monitoring/ (存在する場合や将来的モジュール)
    - strategy/ (戦略関連モジュール／将来的拡張)
    - execution/ (注文送信 / ブローカー連携用の層)

## 注意事項 / 実運用上のヒント
- OpenAI 呼び出し回数はコスト・レート制限に注意してください。score_news はバッチで複数銘柄をまとめて送信しますが、モデル・バッチサイズ調整が可能です。
- J-Quants のレート制限に合わせて jquants_client は内部でスロットリングを実装しています。大量の連続リクエストは避けること。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるので、本実装では空チェックを行っています。
- すべての日時取り扱いではルックアヘッドバイアスを避けるため関数は target_date を受け取り、内部で date.today() 等を参照しない設計になっています（例外は ETL のトップレベルでの today の扱いのみ）。

---

README に記載がない細かい実装仕様や関数の引数・戻り値は、各モジュールの docstring を参照してください。追加の使い方（CLI、Docker、CI など）が必要であれば、その要件に合わせた README の補足を作成します。