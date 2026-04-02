# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。  
ETL、ニュース収集・NLU、研究用ファクター計算、監査ログ、JPXカレンダー管理、J-Quants API クライアントなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株投資システム向けの内部ライブラリ群です。主な目的は以下です。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ格納・ETL パイプライン（差分取得・冪等保存・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策やトラッキング除去）
- OpenAI（gpt-4o-mini 等）を使ったニュースセンチメント解析（銘柄毎）とマクロレジーム判定
- 研究用途（ファクター計算、将来リターン、IC 計算、Zスコア正規化等）
- 監査ログ（signal → order_request → execution のトレーサビリティ）
- 各所で「ルックアヘッドバイアス防止」「冪等性」「リトライ・レート制御」「安全対策（SSRFなど）」を設計方針に反映

---

## 機能一覧

- data/
  - jquants_client: J-Quants API クライアント（取得・保存・認証・レート制御・リトライ）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 他）
  - news_collector: RSS 収集・前処理・raw_news への保存（SSRF 対策あり）
  - calendar_management: JPX カレンダーの管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログテーブルの初期化（信号から約定までのトレースを保持）
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA200乖離 + マクロニュースで市場レジーム（bull/neutral/bear）を判定して market_regime に保存
- research/
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）、統計サマリ等
- config:
  - 自動 .env ロード・環境変数ラッパ（settings オブジェクト）。必須値の検査を含む。

---

## セットアップ手順（開発/実行）

下記は典型的なローカルセットアップ手順です。環境に合わせて読み替えてください。

1. Python 環境を用意（推奨: Python 3.10+）

2. リポジトリをクローンし、パッケージをインストール（開発モード）
   ```
   git clone <repo-url>
   cd <repo-dir>
   python -m pip install -e .
   ```
   ※ requirements.txt が別途ある場合は `pip install -r requirements.txt` を使用。  
   主な依存例: duckdb, openai, defusedxml

3. 環境変数 / .env を用意  
   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` と `.env.local` を置けます。
   config モジュールは自動で .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能）。

   主要な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabu API パスワード（必須）
   - KABU_API_BASE_URL: kabu API ベース URL（省略時: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI モジュール実行時に必要）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite パス（監視用、デフォルト data/monitoring.db）
   - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
   - KABUSYS_ENV: execution 環境 (development / paper_trading / live)
   - LOG_LEVEL: ログレベル (DEBUG/INFO/WARNING/ERROR/CRITICAL)

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=pass
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. データベースの準備（必要に応じて）
   - 監査ログ専用 DB 初期化例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メイン DuckDB は settings.duckdb_path を参照して接続してください:
     ```python
     import duckdb
     from kabusys.config import settings
     conn = duckdb.connect(str(settings.duckdb_path))
     ```

---

## 使い方（主要な呼び出し例）

以下は典型的な Python スクリプトからの呼び出し例です。

- 日次 ETL 実行（株価・財務・カレンダーの差分取得＋品質チェック）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアリング（ai_scores へ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 実運用は OPENAI_API_KEY を
  print(f"scored {count} codes")
  ```

- 市場レジーム判定（market_regime へ書き込み）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=settings.jquants_refresh_token)  # 実運用は OPENAI_API_KEY を
  ```

- 研究用関数（ファクター計算）
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- 統計ユーティリティ（Zスコア正規化）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, columns=["mom_1m", "ma200_dev"])
  ```

- 監査スキーマ初期化（既存 DuckDB 接続に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意:
- AI関連関数は OpenAI API キー（OPENAI_API_KEY）を必要とします。引数で api_key を渡すことも可能です。
- J-Quants 呼び出しには settings.jquants_refresh_token（環境変数 JQUANTS_REFRESH_TOKEN）が必要です。

---

## ディレクトリ構成

主要モジュールの一覧（src/kabusys/ 以下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの LLM スコアリング（銘柄別）
  - regime_detector.py — マクロセンチメント + ETF MA200 で市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py       — J-Quants API クライアント & DuckDB 保存ロジック
  - pipeline.py             — ETL パイプライン（run_daily_etl 等）
  - etl.py                  — ETLResult 再エクスポート
  - news_collector.py       — RSS 収集 & 前処理（SSRF 対策等）
  - calendar_management.py  — JPX カレンダー管理・営業日判定
  - quality.py              — 品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py                — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py      — Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py  — 将来リターン、IC、統計サマリ、rank
- research/__init__.py
- その他（将来的に strategy, execution, monitoring 等も想定）

---

## 設計上の注意・ポリシー

- ルックアヘッドバイアス防止: 多くの関数は date / target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計です。
- 冪等性: ETL の保存処理は ON CONFLICT を使い、再実行で上書きされるようにしています。
- リトライ & レート制御: J-Quants クライアントは固定間隔スロットリング（120 req/min）と指数バックオフのリトライを実装しています。OpenAI 呼び出しもリトライロジックを持ちます。
- セキュリティ: news_collector は SSRF 対策、受信サイズ制限、XML パース保護（defusedxml）などを実施しています。
- テスト容易性: 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD、内部 API 呼び出しを差し替えるためのモックポイントなどを提供。

---

## 開発・テストに関するメモ

- settings は Settings クラス経由で環境変数を取得します。必須値未設定時は ValueError を投げます（例: JQUANTS_REFRESH_TOKEN）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。テスト中に環境操作をしたい場合は自動ロードを無効化してください。
- OpenAI 呼び出しはテスト時に unittest.mock.patch で _call_openai_api を差し替えられるようになっています。
- DuckDB に関する実装は executemany の空リスト制約等、実行環境の DuckDB バージョンに依存する振る舞いに対処済みです。

---

## ライセンス・貢献

（ここにはプロジェクトのライセンスや貢献ガイドラインを記載してください。プロジェクトに合わせて追記をお願いします。）

---

必要であれば、README に「実行可能なサンプルスクリプト」「FAQ」「トラブルシューティング」などを追加します。どの項目を拡充するか指示をください。