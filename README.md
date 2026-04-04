# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL、ニュース収集・NLP（OpenAI 経由）、ファクター計算、監査ログ、マーケットカレンダー管理などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するためのライブラリ群です。主に以下を目的としています。

- J-Quants API からのデータ取得（株価・財務・カレンダー）
- DuckDB を用いたデータ永続化と ETL パイプライン
- RSS ニュースの収集と前処理（SSRF・XML攻撃対策を実装）
- OpenAI を用いたニュースセンチメント解析（銘柄ごと・マクロ）
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック・監査ログ（トレーサビリティ）

設計方針として「ルックアヘッドバイアス防止」「冪等性（idempotent）」「フェイルセーフ（API失敗時に部分的に継続）」を重視しています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価（daily_quotes）、財務データ、マーケットカレンダー取得
  - 差分更新・バックフィル・品質チェックを備えた日次 ETL（kabusys.data.pipeline.run_daily_etl）
- ニュース処理
  - RSS 取得、テキスト前処理、raw_news への冪等保存（kabusys.data.news_collector）
  - OpenAI を使った銘柄別ニュースセンチメント（kabusys.ai.news_nlp.score_news）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントの合成（kabusys.ai.regime_detector.score_regime）
- 研究用モジュール
  - ファクター計算（モメンタム / ボラティリティ / バリュー）（kabusys.research.*）
  - 将来リターン、IC 計算、統計サマリー
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（kabusys.data.quality）
- 監査ログ（トレーサビリティ）
  - signal → order_request → executions を追跡するテーブル定義・初期化（kabusys.data.audit）

---

## セットアップ手順

前提:
- Python 3.10 以上（型アノテーションに `X | Y` を使用）
- DuckDB を利用するためネイティブに問題ない環境

1. リポジトリをチェックアウトし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （実プロジェクトでは requirements.txt / pyproject.toml を利用してください）

3. パッケージをインストール（開発モード）
   - pip install -e .   （プロジェクトルートに setup.cfg/pyproject.toml がある想定）

4. 環境変数の設定
   - ルートに `.env` / `.env.local` を置くと自動的にロードされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能）。
   - 必要な主な環境変数（例）:

     ```
     # J-Quants 認証
     JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

     # OpenAI（ニュース NLP / レジーム判定）
     OPENAI_API_KEY=sk-...

     # kabu ステーション（発注等、未実装モジュール向け）
     KABU_API_PASSWORD=...
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # DB / ファイルパス
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PID_FILE_PATH=data/execution.pid
     KILL_FLAG_PATH=data/kill.flag

     # 環境
     KABUSYS_ENV=development   # development | paper_trading | live
     LOG_LEVEL=INFO
     ```

   - 必須: JQUANTS_REFRESH_TOKEN （ETL の場合）。OpenAI を使う場合は OPENAI_API_KEY が必要です。
   - 設定は Settings クラス（kabusys.config.settings）から参照できます。

---

## 使い方（主要な例）

以下は Python から呼び出す基本例です。DuckDB 接続には `duckdb` パッケージを使用します。

- DuckDB に接続して日次 ETL を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores テーブルに書き込む

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境に設定していれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {written} ai_scores rows")
  ```

- 市場レジームを判定して market_regime テーブルに保存する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境に設定
  ```

- 監査ログ用 DuckDB を初期化する（監査スキーマ作成）

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以降 conn に対して order_requests / signal_events / executions が利用可能
  ```

- ファクター計算（研究用）

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  ```

ログレベルや環境は `kabusys.config.settings` で参照・検証されます（KABUSYS_ENV は development/paper_trading/live のいずれかにする必要があります）。

---

## 注意事項（実運用向け）

- OpenAI 呼び出しは API エラー（429・タイムアウト・5xx）を考慮したリトライ実装がありますが、API キーや料金管理は運用側で行ってください。
- J-Quants API のレート制限（120 req/min）に合わせるために内部でレート制御とリトライを実装しています。認証トークンのリフレッシュも自動化されています（JQUANTS_REFRESH_TOKEN 必須）。
- DuckDB の executemany に関する互換性（空リスト不可）を考慮した実装がなされています。
- news_collector は SSRF 対策（リダイレクト先の検査、プライベートIPブロック）と XML の脆弱性対策（defusedxml）を行っています。
- ルックアヘッドバイアス回避: バックテストで使用する場合、ETL で取り込んだ時刻（fetched_at）や取得対象日付の扱いに注意してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                     - 環境変数 / 設定読み込み（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py                  - ニュースセンチメント（銘柄別）処理
  - regime_detector.py           - ETF MA + マクロニュースで市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py            - J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py                  - ETL パイプライン（run_daily_etl など）
  - etl.py                       - ETLResult の公開 re-export
  - news_collector.py            - RSS 取得・前処理・raw_news への保存
  - calendar_management.py       - マーケットカレンダー（営業日判定等）
  - quality.py                   - データ品質チェック
  - stats.py                     - 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py                     - 監査ログのスキーマ定義・初期化
- research/
  - __init__.py
  - factor_research.py           - モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py       - 将来リターン計算、IC、統計サマリー
- research/*                      - 研究補助ツール群
- (strategy/, execution/, monitoring/ が __all__ に含まれる想定だが、各モジュールは別途実装される想定)

---

## よく使う設定項目（環境変数）

- JQUANTS_REFRESH_TOKEN（必須）: J-Quants リフレッシュトークン
- OPENAI_API_KEY（News / Regime 用）
- KABU_API_PASSWORD, KABU_API_BASE_URL（kabu ステーション発注連携）
- DUCKDB_PATH（デフォルト data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB）
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（.env 自動ロードを無効化）

---

## テスト・開発時のヒント

- 自動環境変数ロードが邪魔なテストを行う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し部分はモジュール内で分離されているため、ユニットテストでは該当関数（例: kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api）をモックすることを想定しています。
- DuckDB はインメモリ（":memory:"）で初期化可能です。テスト時は一時 DB を使うと便利です。

---

## ライセンス / 貢献

この README はコードベースの説明を目的としています。ライセンスや貢献規約はリポジトリのルートにある LICENSE / CONTRIBUTING を参照してください。

---

必要であれば、README に含めるサンプル .env.example、より詳細なテーブルスキーマ、ETL パラメータのチューニング例やデバッグ方法（ログ設定方法や DuckDB の簡易クエリ例）を追記できます。どの情報を優先して追加しますか？