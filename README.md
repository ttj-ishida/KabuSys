# KabuSys

日本株向け自動売買・データ基盤ライブラリ「KabuSys」のリポジトリ用 README。

この README ではプロジェクトの概要、主要機能、セットアップ方法、基本的な使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株のデータ取得、品質チェック、ニュース NLP、ファクター計算、マーケットレジーム判定、監査ログ管理などを包含する汎用ライブラリです。主に以下用途を想定しています。

- J-Quants API を用いた株価・財務・カレンダーの ETL
- RSS ニュース収集と LLM によるニュースセンチメント解析（OpenAI）
- ファクター計算・研究（モメンタム、バリュー、ボラティリティ等）
- 市場レジーム判定（ETF MA とマクロニュースの合成）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用 DuckDB スキーマ
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴：
- DuckDB を主要なオンディスク DB として利用
- Look-ahead バイアス回避のため日付参照を慎重に扱う（内部で date.today() を不用意に参照しない設計）
- J-Quants / OpenAI 呼び出しはリトライ・レート制御、フェイルセーフを持つ
- 冪等的な DB 保存（ON CONFLICT を利用）を前提にした設計

---

## 機能一覧

主なモジュールと機能（抜粋）：

- kabusys.config
  - .env 自動ロード（.env, .env.local）／環境変数管理
- kabusys.data
  - jquants_client: J-Quants API client（データ取得・DuckDB保存）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 収集、前処理、raw_news への保存ロジック
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定、next/prev_trading_day、calendar 更新ジョブ
  - audit: 監査ログスキーマ作成・初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュースを合成して market_regime を生成
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## 必要条件・依存関係

- Python 3.10 以上（コードで「|」型や typing 機能を利用しています）
- 必要な主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順 (ローカル開発向け)

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（例: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - pyproject.toml や requirements.txt がある場合はそちらを使ってください。無ければ最低限:
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージを編集可能モードでインストール（任意）
   ```
   pip install -e src
   ```

5. 環境変数 (.env) の準備
   - プロジェクトルートに `.env` または `.env.local` を配置すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時）
     - KABU_API_PASSWORD: kabu API パスワード
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=XXXXXXXXXXXXXXXXXXXX
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=yourpassword
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な API と例）

以下は基本的な利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（ai_scores へ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written_count = score_news(conn, target_date=date(2026, 3, 20))
  print("wrote", written_count)
  ```

- 市場レジーム判定（market_regime へ書き込む）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（既存 conn に対して）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 監査専用 DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードの取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

注意:
- score_news / score_regime は OpenAI API にアクセスします。API キーは api_key 引数で上書き可能（省略時は環境変数 OPENAI_API_KEY を参照）。
- J-Quants 呼び出しは rate limit（120 req/min）や認証リフレッシュ処理を内部で行います。

---

## ディレクトリ構成（抜粋）

src/kabusys の主要ファイルと役割：

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数の自動読み込み・設定取得（settings）
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py           : ニュースの LLM スコアリング（score_news）
  - regime_detector.py    : マクロセンチメント + ETF MA によるレジーム判定（score_regime）
- src/kabusys/data/
  - __init__.py
  - jquants_client.py     : J-Quants API クライアント（fetch_*/save_*）
  - pipeline.py           : ETL パイプライン（run_daily_etl 等）
  - etl.py                : ETL 公開インターフェース（ETLResult の再エクスポート）
  - news_collector.py     : RSS 収集・前処理・保存
  - calendar_management.py: マーケットカレンダー管理（営業日判定・カレンダー更新）
  - quality.py            : データ品質チェック
  - stats.py              : zscore_normalize 等の統計ユーティリティ
  - audit.py              : 監査ログスキーマ・初期化機能
- src/kabusys/research/
  - __init__.py
  - factor_research.py    : モメンタム・バリュー・ボラティリティ等のファクター計算
  - feature_exploration.py: 将来リターン、IC、統計サマリー等

（各ファイル内に多数の関数や補助ユーティリティが実装されています。詳しくは該当ソースを参照してください。）

---

## 運用・開発上の注意事項

- セキュリティ:
  - RSS 収集は SSRF 対策、受信サイズ上限、defusedxml による XML 攻撃対策を組み込んでいます。
  - API キーやパスワードは .env に置くか Secrets マネージャを使用してください。絶対に公開リポジトリに含めないでください。
- レート制御:
  - J-Quants は 120 req/min のレート制限があります（jquants_client に固定間隔レートリミッタ実装あり）。
  - OpenAI もレート制御・リトライが必要です。大量バッチ処理の際は適切に待機時間を確保してください。
- Look-ahead バイアス:
  - モジュールはバックテストや研究でのルックアヘッドバイアスを避ける設計がなされています。date 引数などを明示的に渡して時刻依存の副作用を避けてください。
- 自動環境変数ロード:
  - kabusys.config はプロジェクトルート（.git または pyproject.toml）を起点に .env/.env.local を自動ロードします。テスト時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます。

---

## よくある質問（FAQ）

- Q: OpenAI の呼び出しをテストで差し替えたい
  - A: 各モジュールは _call_openai_api のような内部関数を経由しているため、unittest.mock.patch で差し替え可能です（ソース内にその旨の記述あり）。

- Q: DuckDB のスキーマはどこで定義されている？
  - A: audit スキーマは data.audit に定義済み。その他のテーブルは ETL や初期化スクリプトで作成される想定です（プロジェクト別に schema 初期化ロジックを別途用意してください）。

---

以上が README の概要です。追加で以下が必要であれば作成します：
- 完全な requirements.txt / pyproject.toml の例
- 実行用 CLI スクリプトの使い方（cron / Airflow 用）
- データベーススキーマ定義の詳細（raw_prices, raw_financials, raw_news, ai_scores, market_regime 等）