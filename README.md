# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）・データ品質チェック・ニュースの NLP スコアリング・市場レジーム判定・監査ログ（トレーサビリティ）など、売買アルゴリズムと研究で必要となる共通機能群を提供します。

---

## 主な特長（機能一覧）

- データ取得・保存（J-Quants API）
  - 日次株価（OHLCV）、財務データ、JPX マーケットカレンダーの差分取得（ページネーション対応）
  - DuckDB へ冪等（ON CONFLICT DO UPDATE）で保存
  - レートリミット・リトライ・トークン自動リフレッシュ対応

- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - バックフィル（直近数日再取得）やルックアヘッドバイアス対策を考慮

- データ品質チェック
  - 欠損、重複、前日比スパイク、将来日付や非営業日のデータ検出
  - QualityIssue オブジェクトで問題を集約

- ニュース収集・前処理
  - RSS 取得（SSRF 対策、リダイレクト検証、トラッキングパラメータ除去）
  - 記事の正規化・ID 生成・raw_news への保存を想定したユーティリティ

- ニュース NLP / LLM スコアリング
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのセンチメントスコア生成（score_news）
  - マクロニュースと移動平均乖離を組み合わせた市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（モメンタム・バリュー・ボラティリティ）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Zスコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブルを DuckDB に初期化（init_audit_schema / init_audit_db）
  - 発注フローの UUID ベーストレーサビリティを提供

---

## 要求環境（推奨）

- Python 3.10+
- 主要依存パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

プロジェクトに requirements.txt がある場合はそちらを利用してください。無ければ最低限次をインストールしてください:

pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／取得
   ```
   git clone <repository_url>
   cd <repository_dir>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```
   pip install -r requirements.txt   # あれば
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env`（必要に応じて `.env.local`）を配置すると、自動で読み込まれます。
   - 自動ロードはデフォルトで有効。無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 功能を使う場合）
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時のモック約定挙動）
   - PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）

   .env の取り扱い:
   - 読み込み順: OS 環境変数 > .env.local > .env
   - protected によって OS 既存の環境変数は上書きされません

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下はライブラリを直接利用する簡単な例です。実行は Python スクリプトや REPL から行います。

- 設定の読み取り
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を使った ETL 実行（1日分）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使う
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
  conn = init_audit_db("data/monitoring.duckdb")
  # conn は初期化済みの DuckDB 接続
  ```

- RSS フィード取得（保存ロジックは呼び出し側で実装）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- AI 関連機能（score_news, score_regime）は OpenAI API を利用します。`OPENAI_API_KEY` を設定してください。
- J-Quants API 利用には `JQUANTS_REFRESH_TOKEN` が必須です。
- run_daily_etl は内部で calendar ETL を先に実行し、営業日調整を行います。

---

## 重要な設定・挙動メモ

- .env 自動ロード
  - パッケージインポート時に、プロジェクトルート（.git または pyproject.toml のあるディレクトリ）から `.env` / `.env.local` を自動読み込みします。
  - 自動読み込みを止めるには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテスト等で有用）。

- KABUSYS_ENV の有効値
  - development / paper_trading / live
  - live かどうかは settings.is_live で判定できます。

- PAPER_FILL_MODE の有効値
  - instant / partial / never / reject（paper trading モード時のモック約定動作を制御）

- OpenAI の呼び出しは、リトライや 5xx 処理を含む堅牢な実装になっていますが、API 呼び出し回数やコストに注意してください。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュールと簡単な説明:

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄ごとに集約し OpenAI でスコアリング（score_news）
    - regime_detector.py
      - ETF 1321 の MA200 乖離とマクロ記事の LLM センチメントを統合して市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - quality.py
      - データ品質チェック（欠損・重複・スパイク・日付不整合）
    - news_collector.py
      - RSS 取得・前処理・安全対策（SSRF 対応、トラッキング削除）
    - calendar_management.py
      - JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
    - audit.py
      - 監査ログ用スキーマ初期化（signal_events, order_requests, executions）
    - etl.py
      - ETLResult の公開（エントリポイント用型）
    - stats.py
      - 共通統計ユーティリティ（zscore_normalize 等）
  - research/
    - __init__.py
    - factor_research.py
      - ファクター計算（momentum, value, volatility）
    - feature_exploration.py
      - 将来リターン計算、IC、統計サマリー、rank 等

（上記は抜粋です。プロジェクトルートに README や pyproject.toml がある想定です。）

---

## よくある質問 / トラブルシューティング

- .env が読み込まれない
  - プロジェクトルートが検出できないと自動ロードはスキップされます（.git または pyproject.toml を基準に探索）。手動で環境変数を export してください、または `KABUSYS_DISABLE_AUTO_ENV_LOAD` を確認してください。

- OpenAI のレスポンスパースに失敗する
  - モジュールはパース失敗時にフェイルセーフ（スコア 0.0 など）で継続します。ログを確認して再試行してください。

- J-Quants 呼び出しで 401 が返る
  - リフレッシュトークンが正しくない／期限切れの可能性があります。`JQUANTS_REFRESH_TOKEN` を確認してください。クライアントは 401 を検出したらトークンを自動リフレッシュし再試行します（1回）。

---

README に書かれている以外にも内部ユーティリティや調整用のパラメータが多く用意されています。実運用前に各設定値（特に API キー・DB パス・ENV）を正しく準備し、ローカルでの dry-run（paper_trading）やユニットテストを行ってください。必要であれば各モジュールのドキュメント生成や追加のサンプルスクリプト作成をお手伝いします。