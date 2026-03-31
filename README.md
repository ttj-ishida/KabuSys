# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリ（KabuSys）。  
DuckDB をバックエンドに、J-Quants からのデータ取得・ETL、ニュースの収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレース）などの機能を提供します。

---

## 主な特徴（機能一覧）

- 環境管理
  - .env / .env.local の自動読み込み（プロジェクトルートを自動検出）
  - 必須環境変数のラップ（settings オブジェクト）
- データETL（J-Quants API 経由）
  - 株価日足（OHLCV）取得・保存（差分取得、ページネーション、冪等保存）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL の統合エントリ run_daily_etl
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックと QualityIssue レポート
- ニュース収集・NLP
  - RSS 取得（SSRF 対策・gzip/サイズ制限・トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント解析（news_nlp.score_news）
  - LLM 呼び出しでの堅牢なリトライ・レスポンス検証
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離 + マクロニュースセンチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）
  - ルックアヘッドバイアス対策を考慮した実装
- リサーチ用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research）
  - 将来リターン集計・IC（Information Coefficient）計算・ファクター統計
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルによるトレーサビリティ
  - init_audit_db で監査用 DuckDB を初期化可能

設計上のポイント:
- Look-ahead バイアスを避ける実装（date を明示して処理）
- DuckDB を中心としたローカル永続化と SQL 主導の処理
- 外部 API 呼び出しに対する堅牢なリトライ・フォールバック

---

## セットアップ手順

前提:
- Python 3.10+（typing の一部表記が使用されています）
- ネットワーク接続（J-Quants / OpenAI / RSS 取得）

1. リポジトリを取得（例）
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 必要パッケージのインストール（最小）
   ```
   python -m pip install duckdb openai defusedxml
   ```
   追加で logging や sqlite 利用、テスト用モック等が必要なら適宜インストールしてください。

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

3. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local があれば優先して上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

   主要な環境変数（例）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=...
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development   # development / paper_trading / live
   LOG_LEVEL=INFO
   ```
   注意: Settings のプロパティのいくつか（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は必須で、未設定だと Settings が ValueError を出します。

4. データディレクトリ作成（例）
   ```
   mkdir -p data
   ```

---

## 使い方（基本例）

以下は簡単な Python スニペット例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しないと本日（ただし内部で営業日に調整する）
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア（銘柄別）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  print(records[:5])
  ```

注意点:
- OpenAI を使う関数（score_news / score_regime）は環境変数 `OPENAI_API_KEY` を参照します。直接引数で api_key を渡すこともできます。
- モデル呼び出しは gpt-4o-mini（コード内定義）を利用する設計です。API 呼び出しでのリトライやエラーハンドリングは組み込まれていますが、APIキーやレート制限には注意してください。
- run_daily_etl などは DB スキーマ（raw_prices 等）が前提です。初期スキーマの作成はプロジェクト側のスクリプト / マイグレーションを用意してください（サンプルでは init_audit_schema など一部は提供）。

---

## 環境変数と自動ロードの挙動

- 自動ロード: kabusys.config はパッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、`.env` を読みます。さらに `.env.local` があれば上書きします。
- 無効化: テストや特殊用途で自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 値取得: `from kabusys.config import settings` で各種プロパティ（settings.jquants_refresh_token, settings.duckdb_path, settings.env など）にアクセスできます。未設定の必須変数は _require() により ValueError を送出します。

有効な KABUSYS_ENV 値: `development`, `paper_trading`, `live`  
有効な LOG_LEVEL: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

---

## ディレクトリ構成（主要ファイル）

（ソースは src/kabusys 以下）

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 -- ニュース NLP（銘柄別センチメント）
    - regime_detector.py          -- 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py           -- J-Quants API クライアント + 保存
    - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
    - etl.py                      -- ETL 結果クラス再エクスポート
    - calendar_management.py      -- 市場カレンダー管理（営業日判定 等）
    - news_collector.py           -- RSS 取得と前処理
    - quality.py                  -- データ品質チェック
    - stats.py                    -- 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                    -- 監査ログ初期化 / テーブル定義
  - research/
    - __init__.py
    - factor_research.py          -- モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py      -- 将来リターン / IC / 統計サマリー 等
  - (その他)
    - 監視や実行、戦略・発注に関するモジュールは別ディレクトリ（strategy, execution, monitoring）が想定されていますが、主要ロジックは上記に含まれます。

---

## 開発・テストのヒント

- テスト時は OpenAI / J-Quants の外部呼び出しをモックしてください。コード内には unittest.mock.patch を使いやすい箇所（_call_openai_api 等）があります。
- 自動 .env ロードを無効化すると環境のコントロールが容易になります（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
- DuckDB を使用しているため、スキーマ初期化スクリプトをプロジェクトに用意するとテストが容易です（raw_prices / raw_financials / market_calendar / ai_scores / prices_daily / ... 等）。
- ETL 実行ログは logging 設定で出力レベルを変更できます（LOG_LEVEL 環境変数）。

---

## よくある問題と対処

- ValueError: 環境変数が見つからない
  - 必須の環境変数（例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, SLACK_*）を .env に設定するか、環境でエクスポートしてください。
- OpenAI リクエスト失敗
  - API キー・レート・ネットワークを確認。モジュールはリトライ・フォールバック（スコア 0.0）を実装していますが、長時間の失敗が続くと結果が欠損します。
- RSS 取得で SSRF/接続エラー
  - news_collector はプライベートアドレスや不正スキームを弾く設計です。内部ネットワークの RSS を取得する場合はホワイトリストなどを検討してください。

---

必要であれば README にサンプルの DB スキーマ（DDL）や、より詳細な運用手順（cron/ジョブスケジューラ、監視、Slack 通知フロー）を追加できます。どの情報を優先して追記しますか？