# KabuSys

日本株向けのデータプラットフォーム兼自動売買支援ライブラリ（KabuSys）。  
DuckDB をデータ層に使い、J‑Quants / RSS / OpenAI など外部データを取り込み、研究用ファクター計算・ニュースNLP・市場レジーム判定・ETL・データ品質チェック・監査ログを提供します。

---

## 主な特徴（概要）
- ETL: J‑Quants API から株価/財務/カレンダーを差分取得して DuckDB に保存（冪等）
- データ品質チェック: 欠損・スパイク・重複・日付不整合を検出するチェック群
- ニュース収集: RSS を安全に取得・前処理して raw_news に格納（SSRF 対策、トラッキング除去）
- AI スコアリング:
  - news_nlp: 銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント化し ai_scores に書込
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して市場レジームを判定
- リサーチユーティリティ:
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
- 監査ログ（audit）: シグナル→発注→約定までトレースできる監査テーブル定義と初期化ユーティリティ
- 設定管理: .env / .env.local と OS 環境変数から設定を読み込む自動ローダー（無効化可能）

---

## 機能一覧（要約）
- data/
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J‑Quants クライアント（認証／ページネーション／保存関数）
  - カレンダー管理（営業日ロジック、calendar_update_job）
  - ニュース収集（RSS 安全取得、記事正規化、news_symbols との紐付け）
  - 品質チェック（missing/spike/duplicates/date_consistency）
  - 統計ユーティリティ（zscore_normalize）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- research/
  - calc_momentum / calc_volatility / calc_value
  - calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings（環境変数アクセス・.env 自動ロード・検証）

---

## セットアップ手順

前提:
- Python 3.8+（typing の一部アノテーションに合わせてください）
- システムにネットワークアクセスが可能（J‑Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境の作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（requirements.txt がある場合はそれを使ってください）
   最低限必要なライブラリ（例）:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに依存定義ファイルがある場合はそちらを利用）

4. 環境変数の設定
   - リポジトリルートに `.env`（と任意で `.env.local`）を置くか、OS 環境変数で設定します。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須：J‑Quants リフレッシュトークン）
     - OPENAI_API_KEY（LLM を使う場合は必須）
     - KABU_API_PASSWORD（kabu API が必要な場合）
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（通知に使用する場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB 等: data/monitoring.db）
     - PID_FILE_PATH（実行監視）
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）
   - .env 自動ロード:
     - OS 環境 > .env.local > .env の順で設定が反映されます
     - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

5. 初期 DB（監査ログ等）の作成
   例: 監査ログ専用 DB を作る
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   ```
   一般的には settings.duckdb_path を使い DuckDB 接続を取得してスキーマ初期化します。

---

## 使い方（基本的なコード例）

※ すべての関数は DuckDB の接続オブジェクト（duckdb.connect() の返り値）を受け取ります。

- DuckDB 接続の作成
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl

  # target_date を None にすると今日が対象（内部で営業日調整あり）
  result = run_daily_etl(conn, target_date=None)
  print(result.to_dict())
  ```

- ニュース NLP スコア付け（ai_scores に書き込む）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # 明示的に OPENAI_API_KEY を渡すことも可能
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"written {written} codes")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- ファクター計算（研究用途）
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
  from datetime import date

  date0 = date(2026, 3, 20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

- ETL の個別実行
  ```python
  from kabusys.data.pipeline import run_prices_etl, run_financials_etl, run_calendar_etl
  from datetime import date

  target = date(2026, 3, 20)
  run_prices_etl(conn, target)
  run_financials_etl(conn, target)
  run_calendar_etl(conn, target)
  ```

- 監査スキーマの初期化
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

注意点:
- LLM 呼び出し（news_nlp / regime_detector）は OPENAI_API_KEY が必要です。api_key 引数で明示的に渡すことも可能。
- ETL / data モジュールはデータベース状態に依存します。初回は J‑Quants から大量データを取得するため時間がかかります（API レート制限あり）。
- DuckDB の executemany に対するバージョン依存（空リストの扱い等）に注意しています（コード内コメント参照）。

---

## 設定（.env の取り扱い）
- プロジェクトルート（.git または pyproject.toml がある階層）から .env/.env.local を自動ロードします。
- 環境変数の優先順位:
  - OS 環境変数 > .env.local > .env
- 自動ロードを無効化:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env を読み込みません（テスト用）。
- .env 内のパースはシェル風の export KEY=VAL やクォート、コメント処理をサポートしています。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数/設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュースセンチメントの LLM スコアリング
    - regime_detector.py                — MA200 とマクロセンチメント合成によるレジーム判定
  - data/
    - __init__.py
    - pipeline.py                       — ETL パイプライン / run_daily_etl 等
    - etl.py                            — ETL 結果クラス再エクスポート
    - jquants_client.py                 — J‑Quants API クライアント（認証・取得・保存）
    - news_collector.py                 — RSS 取得・前処理・保存ロジック（SSRF 対策等）
    - calendar_management.py            — 市場カレンダー管理・営業日ロジック
    - quality.py                        — データ品質チェック
    - stats.py                          — zscore_normalize 等の統計ユーティリティ
    - audit.py                          — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py                — momentum/value/volatility の計算
    - feature_exploration.py            — forward returns / IC / factor_summary / rank

---

## 注意事項 / ベストプラクティス
- Look-ahead bias を避けるため、内部ロジックは target_date を明示的に受け取り、date.today() を無用に使わない設計です。バックテスト用途では ETL 時点のデータのみを利用すること。
- OpenAI 呼び出しは失敗時にフェイルセーフ（スコア 0 等で継続）する挙動を持ちますが、API キーは正しく設定してください。
- J‑Quants API との通信はレートリミットを守る実装になっています。複数プロセスで同時アクセスする場合は注意してください。
- DuckDB スキーマやテーブル作成はアプリケーション起動時に行うか、audit.init_audit_db 等のユーティリティを利用して初期化してください。

---

## 貢献 / 変更履歴
この README はコードベースから主要ポイントを抜粋してまとめたものです。機能追加や API の変更があった場合は README を更新してください。

---

質問や特定の利用例（例: バックテスト用データ準備手順、OpenAI の呼び出しテスト方法、J‑Quants 認証の扱い等）があれば教えてください。必要に応じてサンプルスクリプトを追加で用意します。