# KabuSys

KabuSys は日本株向けの自動売買・データパイプライン基盤です。  
J-Quants や RSS、OpenAI（LLM）などの外部ソースからデータを収集・品質チェックし、ファクター計算・ニュース NLP・市場レジーム判定・監査ログを提供します。バックテスト／発注レイヤーと接続することで自動売買フローを実装できます。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- データ取得／ETL
  - J-Quants API から株価（OHLCV）、財務データ、上場銘柄情報、JPX カレンダーを差分取得（ページネーション対応）
  - ETL 実行結果を集約する ETLResult
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュース収集／NLP
  - RSS フィードからニュースを収集して raw_news に保存（SSRF 対策・トラッキング除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）算出
- 市場レジーム判定
  - ETF（1321）200 日移動平均乖離とマクロニュース（LLM）のセンチメントを合成して market_regime を生成
- 研究／ファクター
  - モメンタム・バリュー・ボラティリティ等のファクター計算
  - 将来リターン計算、IC（情報係数）、ファクター統計サマリー
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルでシグナル〜約定の完全トレーサビリティを提供（冪等性・タイムスタンプ）
- 設定管理
  - .env / 環境変数から設定を自動読み込み（プロジェクトルート検出）
  - セキュアなキー管理と保護（既存 OS 環境変数保護）

---

## 要求環境 / 依存（参考）

- Python 3.10 以上（コード内で | 型注釈等を使用）
- 主要依存パッケージ（例）
  - duckdb
  - openai（OpenAI API クライアント、OpenAI(api_key=...) を使用）
  - defusedxml
- その他: 標準ライブラリの urllib, json, logging 等を多用

（プロジェクトの pyproject.toml / requirements.txt を参照してください。ここではコードベースから推測した主要依存を記載しています）

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements ファイルがある場合は pip install -r requirements.txt）

3. 環境変数（.env）を用意
   - プロジェクトルートに `.env`（および開発専用に `.env.local`）を配置すると自動で読み込まれます。
   - 自動読み込みを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY（news_nlp / regime_detector を使う場合は必須）
   - （任意）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...）
   - 例（.env）:
     ```
     JQUANTS_REFRESH_TOKEN=あなたの_refresh_token
     KABU_API_PASSWORD=証券APIのパスワード
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     ```

5. データディレクトリ作成（必要時）
   - mkdir -p data

---

## 使い方（簡単なコード例）

以下は主要な機能を Python REPL やスクリプトから使う最小例です。各関数は DuckDB 接続（duckdb.connect(...)）を受け取ります。

- ETL（日次パイプライン）を実行する例
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（銘柄別ニュースセンチメント）を計算して書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OpenAI API キーは環境変数 OPENAI_API_KEY で指定するか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {count}")
  ```

- 市場レジーム判定を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化する（独立 DB を使う例）
  ```python
  from pathlib import Path
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db(Path("data/audit.duckdb"))
  # 以後 conn_audit を監査ログ操作に使用
  ```

- 設定（Settings）から値を取得する
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  ```

---

## 注意点 / 設計方針（運用上のポイント）

- Look-ahead bias を避ける設計（内部で datetime.today() を直接参照せず、target_date を明示的に渡すことでバックテストでの未来情報漏洩を防止）
- OpenAI 呼び出しはリトライ／バックオフを行い、失敗時はフェイルセーフ（0.0 スコア等）で継続する設計
- J-Quants API 呼び出しはレートリミット制御（120 req/min）とトークン自動リフレッシュを行う
- ニュース収集は SSRF 対策・受信サイズ制限・トラッキング除去等を実施
- DuckDB への書き込みは冪等（ON CONFLICT DO UPDATE / DO NOTHING）で扱う
- audit（監査）テーブルは削除しない前提で設計（トレーサビリティ保持）

---

## ディレクトリ構成（主要ファイルと概要）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み・Settings クラス（アプリ設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約 → OpenAI による銘柄別センチメント算出 → ai_scores へ書き込み
    - regime_detector.py
      - ETF（1321）200 日 MA 偏差とマクロニュース（LLM）を合成して market_regime を決定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント、fetch/save 関数（raw_prices, raw_financials, market_calendar など）
    - pipeline.py
      - ETL パイプライン（run_daily_etl 等）と ETLResult
    - etl.py
      - ETLResult の再エクスポート（インターフェース）
    - calendar_management.py
      - market_calendar の扱い、営業日判定ユーティリティ（is_trading_day, next_trading_day, ...）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（欠損、重複、スパイク、日付不整合）
    - audit.py
      - 監査ログ（signal_events, order_requests, executions）の DDL と初期化関数
    - news_collector.py
      - RSS フィード取得・前処理・raw_news への保存（SSRF 対策等）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、ランク関数

---

## よくある質問（FAQ）

- Q: 環境変数の自動ロードを無効化したい
  - A: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。読み込みのタイミングでプロジェクトルートが自動検出され `.env` / `.env.local` が読み込まれますが、これを抑制できます。

- Q: OpenAI の API キーはどう指定する？
  - A: 環境変数 OPENAI_API_KEY を使用するか、各関数の api_key 引数に直接渡します。

- Q: DuckDB のファイルパスは？
  - A: デフォルトは data/kabusys.duckdb（Settings.duckdb_path）。必要に応じて DUCKDB_PATH 環境変数で変更可能です。

---

もし README に追記したい実行例や運用手順（cron ジョブ、コンテナ化手順、CI/CD 設定など）があれば、用途に合わせてセクションを追加できます。どの項目を詳しくしたいか教えてください。