# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュースNLP（OpenAI）・市場レジーム判定・監査ログ等、取引システム／リサーチ基盤で必要となる機能群を提供します。

バージョン: 0.1.0

---

## 主要な特徴（機能一覧）

- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存（DuckDB）
  - ページネーション対応、レート制御、401→トークン自動リフレッシュ、指数バックオフリトライ
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付不整合（未来日／非営業日データ）検出
- ニュース収集（RSS）
  - RSS フィード取得、安全対策（SSRF、XML脆弱性、応答サイズ制限）、URL 正規化、記事保存
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースを集約して LLM に投げ、センチメント（ai_score）を ai_scores テーブルに保存
  - バッチ処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF（1321）200日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成して日次で `market_regime` を更新
  - OpenAI によるマクロセンチメント評価（フェイルセーフ有）
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルを定義・初期化するユーティリティ
  - 発注フローの UUID ベースでの完全トレーサビリティを想定
- ヘルパー
  - カレンダー管理（営業日判定、next/prev trading day）
  - 統計ユーティリティ（Zスコア正規化）
  - リサーチ用ファクター計算（Momentum/Value/Volatility）、特徴量探索（forward returns, IC, summary）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントなどに合わせて）
- DuckDB が使えること
- OpenAI API キー、J-Quants リフレッシュトークン 等（必要に応じて）

1. リポジトリをクローン（任意）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

3. 依存パッケージをインストール
   - 本サンプルコードは標準ライブラリ + openai, duckdb, defusedxml 等を想定しています。requirements.txt がある場合はそれを使ってください。
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   - 必要な環境変数（詳細は下記「環境変数」参照）を設定するか、プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 必要な環境変数

主なキー（プロジェクト内で参照されるもの）:

- J-Quants / データ
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）

- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime に不要であれば api_key 引数で渡せます）

- kabuステーション（発注等）
  - KABU_API_PASSWORD: kabu API パスワード（必須: 発注機能利用時）

- Slack（通知）
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID

- システム
  - KABUSYS_ENV: development / paper_trading / live （デフォルト development）
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意:
- .env ファイルはプロジェクトルート（.git または pyproject.toml のある親ディレクトリ）から自動読み込みされます。`.env.local` は `.env` より優先して上書きされます。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## 使い方（簡単なコード例）

以下はモジュールの代表的な使い方例です。実行前に必要な環境変数をセットしてください。

- DuckDB 接続
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると today が使用されます
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別 ai_scores）算出
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されているか、
  # api_key 引数でキーを渡してください
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用の DuckDB を作成）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- カレンダー更新ジョブ（夜間バッチ相当）
  ```python
  from datetime import date
  from kabusys.data.calendar_management import calendar_update_job

  saved = calendar_update_job(conn, lookahead_days=90)
  print(f"saved: {saved}")
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。APIキーの設定とコストに注意してください。
- ETL 系は J-Quants API を呼び出します。`JQUANTS_REFRESH_TOKEN` の設定が必須です。
- DuckDB テーブルスキーマは想定されているテーブル名（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）に従って作成・使用してください。初期化用のDDLはプロジェクトに存在する想定です（schema 初期化ユーティリティがあればそちらを使用してください）。

---

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要モジュール:

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / .env ロードと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（銘柄別センチメント算出）
    - regime_detector.py    — 市場レジーム判定（MA + マクロセンチメント合成）
  - data/
    - __init__.py
    - etl.py                — ETL 公開インターフェース（ETLResult）
    - pipeline.py           — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py     — J-Quants API クライアント（fetch / save）
    - news_collector.py     — RSS ニュース収集
    - calendar_management.py— マーケットカレンダー管理（営業日判定等）
    - quality.py            — データ品質チェック
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログスキーマ初期化
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py    — ファクター計算（momentum/value/volatility）
    - feature_exploration.py— forward returns / IC / summary / rank
  - ai、data、research にまたがるユーティリティが実装されています。

（README 記載時点での主要ファイル一覧。実際のリポジトリではさらにサブモジュールやテスト等が存在する場合があります）

---

## 設計上の重要な注意点

- Look-ahead bias 回避
  - 日付・ウィンドウ計算は内部で date / datetime の取得を外部引数（target_date）経由にし、実行時の現在時刻参照を極力避けています。バックテスト等での使用時は必ず適切な target_date を設定してください。
- 冪等性
  - J-Quants からの保存処理は ON CONFLICT（INSERT … DO UPDATE）で冪等に実装されています。
  - ニュースの ID は URL 正規化→SHA256 を用いた一意化で重複保存を防ぎます。
- フェイルセーフ
  - LLM/API の失敗時は全体を停止させず、フォールバック値（例: macro_sentiment=0.0）で継続する設計が多く取り入れられています。
- セキュリティ
  - RSS 収集では SSRF 対策・受信サイズ制限・XML脆弱性対策（defusedxml）を実装しています。
  - J-Quants / OpenAI のキーは環境変数で安全に取り扱ってください。

---

## よくある作業例・コマンド

- DuckDB で手動クエリ（REPL）
  ```bash
  python -c "import duckdb; conn=duckdb.connect('data/kabusys.duckdb'); print(conn.execute('SELECT 1').fetchall())"
  ```

- ETL をスクリプトとして定期実行（例: daily_job.py を用意）
  - cron / systemd timer 等で実行。ETL は各ステップで例外を捕捉してログに残すので、運用時はログ監視を推奨。

---

必要であれば、README に以下の追加情報を追記できます:
- 実際のテーブルスキーマ（DDL）一覧
- 詳細な環境変数の .env.example
- デプロイ / 運用手順（systemd / cron / Docker）
- テストの実行方法とモックの取り扱い（OpenAI / J-Quants のモック化）

ご希望があれば、上記のいずれかを追記して README を拡張します。