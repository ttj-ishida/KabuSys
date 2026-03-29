# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント）、市場レジーム判定、研究用ファクター計算、監査（注文/約定トレース）などの機能を提供します。

## 目的（プロジェクト概要）
KabuSys は日本株のアルゴリズム売買基盤・研究基盤向けのユーティリティ群です。  
主に以下を目的とします。
- J-Quants API からの株価・財務・カレンダー等データの差分取得と DuckDB への冪等保存（ETL）
- RSS ニュースの収集と前処理、OpenAI を使った記事/銘柄ごとのセンチメント付与
- ETF 指標とマクロニュースを組み合わせた市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と研究用統計関数
- 発注から約定に至る監査ログ（監査テーブルの初期化・操作）およびデータ品質チェック

## 主な機能一覧
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証・レートリミット・リトライ実装）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、記事 ID 正規化）
  - カレンダー管理（営業日判定、next/prev trading day 等）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions のスキーマ定義と初期化）
  - 汎用統計ユーティリティ（zscore 正規化 等）
- ai/
  - news_nlp.score_news: ニュース記事をまとめて OpenAI に送り、銘柄ごとの ai_score を ai_scores テーブルに保存
  - regime_detector.score_regime: ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成し market_regime テーブルへ保存
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, 統計サマリー、rank 等）
- config.py
  - .env 自動読み込み（プロジェクトルート検出）と Settings オブジェクト（環境変数アクセスの便）

## セットアップ手順

前提:
- Python 3.10 以上（型ヒントで | 型が使われているため）
- DuckDB を使います（ローカルファイルに永続化）

1. リポジトリをチェックアウト
   - 例: git clone ... && cd your-repo

2. 依存ライブラリをインストール
   - 最低限必要なパッケージ:
     - duckdb
     - openai
     - defusedxml
   - pip 例:
     - pip install duckdb openai defusedxml
   - （開発用 / パッケージ化されている場合は）プロジェクトルートで:
     - pip install -e .

3. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 必須の環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabu API のパスワード（発注連携を行う場合）
     - SLACK_BOT_TOKEN: Slack 通知を使う場合
     - SLACK_CHANNEL_ID: Slack 通知のチャンネル ID
     - OPENAI_API_KEY: OpenAI を使う処理を実行する場合（score_news / score_regime）
   - 任意 / デフォルト値
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
     - KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
     - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"
     - SQLITE_PATH: デフォルト "data/monitoring.db"

   サンプル .env（README 用）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データベースの準備
   - デフォルトは `data/kabusys.duckdb`（Settings.duckdb_path）
   - 監査専用 DB を初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

## 使い方（典型例）

- Settings の利用（環境変数読み取り）
  ```
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

- 日次 ETL の実行（DuckDB 接続が必要）
  ```
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（score_news）
  ```
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, date(2026, 3, 20), api_key="your_openai_key")
  print("written:", n_written)
  ```

- 市場レジーム判定（score_regime）
  ```
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, date(2026, 3, 20), api_key="your_openai_key")
  ```

- 監査ログスキーマ初期化
  ```
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー操作（営業日判定など）
  ```
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  is_trade = is_trading_day(conn, date(2026,3,20))
  nxt = next_trading_day(conn, date(2026,3,20))
  ```

注意点:
- LLM（OpenAI）呼び出しを伴う処理は API キーが必要です。無い場合は ValueError を投げます。
- 全モジュールはルックアヘッドバイアスを避ける設計になっており、内部で date.today() を参照せず、明示的な target_date を受け取ることが多いです。

## ディレクトリ構成（要約）
リポジトリは src/kabusys 配下が主要モジュールです。主なファイル/ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                — 環境設定・.env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント（score_news）
    - regime_detector.py     — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - news_collector.py      — RSS ニュース収集
    - quality.py             — データ品質チェック
    - stats.py               — 汎用統計（zscore_normalize 等）
    - audit.py               — 監査テーブル定義・初期化
    - etl.py                 — ETL インターフェース再エクスポート
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算 (momentum, value, volatility)
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - research/*.py
  - その他（strategy, execution, monitoring などの名前空間は __all__ で公開予定）

（実際のリポジトリではさらに細かなモジュールやテストが配置される想定です）

## 環境変数・設定の補足
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。CWD に依存しません。
- .env のパースはシェル風の export KEY=val 形式やクォート、インラインコメントの扱いに対応しています。
- 自動読み込みを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

設定参照例:
```
from kabusys.config import settings
print(settings.duckdb_path)       # Path オブジェクト
print(settings.log_level)         # "INFO" 等
```

## 注意事項 / 運用上のポイント
- J-Quants の API レート制限（120 req/min）や OpenAI のコスト・レート制限に注意してください。jquants_client と ai モジュールはそれぞれリトライやレート制御を備えていますが、運用設計は必要です。
- DuckDB のバージョン依存（executemany の空リスト不可など）をコード中で考慮しています。運用時は互換性のある DuckDB を使用してください。
- 監査テーブルは削除しない前提で設計されています（履歴保存）。初期化は慎重に行ってください。
- OpenAI の応答パースに失敗した場合はフェイルセーフとしてスコアを 0 にする等の挙動になっています（例外で処理全体を止めません）。

---

その他、具体的な使い方や追加のヘルパーが必要であれば、実際に使いたいユースケース（ETL を日次バッチで回したい、ニュース収集のみ実行したい、監査 DB を立ち上げたい 等）を教えてください。設定テンプレートや実行スクリプト例を用意します。