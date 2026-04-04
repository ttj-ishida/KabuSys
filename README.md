# KabuSys — 日本株自動売買基盤ライブラリ

KabuSys は日本株向けのデータプラットフォーム・リサーチ・AI スコアリング・監査ログ・ETL を備えたライブラリ群です。
DuckDB を用いたローカルデータ基盤と、J-Quants / OpenAI / RSS 等の外部データを組み合わせて、
ファクター計算、ニュース由来のセンチメントスコアリング、市場レジーム判定、ETL バッチ等を安全に実行できることを目的としています。

主な設計方針：
- ルックアヘッドバイアス防止（内部処理で datetime.today() を直接参照しない等）
- DuckDB を中心とした冪等的なデータ保存（ON CONFLICT / INSERT … DO UPDATE）
- 外部 API 呼び出しに対するリトライ・レート制御・フォールバックを実装
- セキュリティ考慮（RSS の SSRF 対策、defusedxml 利用等）

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API 経由の株価（日足）、財務、上場銘柄情報、マーケットカレンダーの差分取得・保存（jquants_client）
  - ETL パイプライン：日次 ETL（run_daily_etl）・個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP
  - RSS 取得と前処理（news_collector）
  - OpenAI（gpt-4o-mini）を使った銘柄単位ニュースセンチメント解析（news_nlp.score_news）
  - マクロニュースを組み合わせた市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ（ファクター計算）
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

- 環境設定管理
  - .env 自動読み込み、環境変数経由の設定（config.Settings）

---

## 必要条件（概略）

- Python 3.9+
- DuckDB
- openai（OpenAI Python SDK v1系に合わせて実装）
- defusedxml
- その他標準ライブラリ

推奨インストール例（最低限）:
pip install duckdb openai defusedxml

プロジェクト配布に requirements.txt があればそちらを利用してください。

---

## セットアップ手順

1. リポジトリをクローンする
   git clone <repository-url>
   cd <repository-root>

2. 仮想環境を作成して有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）

4. 環境変数の設定
   プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   README 用の主要な環境変数（例）:

   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行に必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実注文本体がある場合）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
   - KABUSYS_ENV: environment（development / paper_trading / live）
   - PID_FILE_PATH / KILL_FLAG_PATH 等（監視・実行管理用）

   例（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development

5. データディレクトリの作成
   mkdir -p data

---

## 使い方（主要 API とサンプル）

以下は Python スクリプトや対話セッション内での利用例です。

- 共通: settings の参照
  from kabusys.config import settings
  print(settings.duckdb_path, settings.jquants_refresh_token)

- DuckDB 接続の作成（ローカル DB を指定）
  import duckdb
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

  run_daily_etl は市場カレンダー → 株価 → 財務 → 品質チェックを順に実行し ETLResult を返します。

- ニューススコア（銘柄単位）を生成する
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None → 環境変数 OPENAI_API_KEY を使用
  print(f"書き込んだ銘柄数: {written}")

- 市場レジームを判定する
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect(str(settings.duckdb_path))
  status = score_regime(conn, target_date=date(2026, 3, 20))
  print("score_regime 完了:", status)

- 監査 DB の初期化（監査ログ専用）
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")

- RSS を直接フェッチする（news_collector ユーティリティ）
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["title"], a["datetime"])

注意点：
- OpenAI 呼び出しは外部 API を使用するため API キーとコストに注意してください。API の失敗時はモジュール内でフェイルセーフ（多くはスコア=0 等）を取る設計です。
- J-Quants の ID トークンは自動リフレッシュを実装していますが、リフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必須です。
- DuckDB の一部操作（executemany に空リストを渡す等）はバージョン依存の扱いになっているため、エラー回避がコード内で考慮されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                      — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                  — ニュースセンチメント（銘柄別）スコアリング
  - regime_detector.py           — 市場レジーム判定（ETF + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py            — J-Quants API クライアント（取得・保存）
  - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
  - etl.py                       — ETL 型再エクスポート（ETLResult）
  - news_collector.py            — RSS 収集・前処理
  - calendar_management.py       — マーケットカレンダー管理
  - quality.py                   — データ品質チェック
  - audit.py                     — 監査ログ（テーブル定義・初期化）
  - stats.py                     — 統計ユーティリティ（zscore 正規化等）
- research/
  - __init__.py
  - factor_research.py           — Momentum / Volatility / Value 等の計算
  - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等
- research/*, data/* 内に DuckDB 接続を受け取り SQL と Python で完結する実装

（上記は主要ファイルの抜粋です。詳細はソースを参照してください）

---

## 運用上の注意事項 / ベストプラクティス

- 環境分離: 本番（live）と開発（development / paper_trading）は settings.env で切り替え可能です。実売買を行う場合は設定ミスと API キー管理に注意してください。
- 秘密情報管理: .env をリポジトリにコミットしないでください。機密情報は環境変数管理ツールに保管することを推奨します。
- OpenAI 使用時の費用管理: ニュースのバッチスコアリングやレジーム判定は API 呼び出し量が増えます。バッチサイズ・頻度を調整してコストを管理してください。
- DuckDB バージョン依存: executemany 等の挙動に依存する箇所があるため、DuckDB を最新安定版にしておくことを推奨します。
- テスト / CI: 外部 API を叩く実装はモック可能な設計になっています（内部呼び出しを差し替えられるよう関数化されているため、単体テストで外部依存をモックしてください）。

---

## 貢献 / 追加情報

- バグ報告・機能提案は Issue を作成してください。
- 外部 API の呼び出し・レート管理・リトライ設定は本リポジトリ固有の要件に合わせて調整しています。別環境へ移植する場合は設定値（RATE・タイムアウト等）を見直してください。

---

README はここまでです。必要であれば次のような追加を作成できます：
- .env.example の自動生成
- requirements.txt / pyproject.toml の推奨依存一覧
- 実行用の CLI スクリプト（cron 用 wrapper）のテンプレート
- 具体的なテーブルスキーマ（DDL）の抜粋（DuckDB 用）