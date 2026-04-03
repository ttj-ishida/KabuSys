# KabuSys

日本株のデータ取得・処理・研究・自動売買を支援するライブラリ群／ミニフレームワークです。  
DuckDB を用いたデータプラットフォーム、J-Quants API 経由の ETL、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算・解析、監査ログなどを備えます。

---

## 主な特徴

- データ取得 / ETL
  - J-Quants API から株価（日次OHLCV）、財務データ、JPXマーケットカレンダーを差分取得・保存（ページネーション・レート制御・リトライ対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付不整合検出）

- ニュース処理 / AI
  - RSS 収集（SSRF対策、トラッキングパラメータ除去、前処理）と raw_news 保存
  - OpenAI（gpt-4o-mini）を使ったニュースセンチメントスコアリング（銘柄単位、バッチ処理・リトライ）
  - マクロニュースを使った市場レジーム判定（ETF 1321 の MA 乖離と LLM センチメントを合成）

- リサーチ
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- 監視・監査
  - 注文〜約定に至る監査ログスキーマ（signal_events / order_requests / executions）
  - 監査DBの初期化ユーティリティ

- 設計方針（主な要点）
  - Look-ahead bias を避ける設計（関数は date 引数ベース、datetime.today() を使わない箇所が多い）
  - 冗長な例外投げを避けるフェイルセーフ（AI/API呼び出し失敗時はフォールバックやスキップ）
  - テスト可能性を考慮した設計（API呼び出しの差し替えがしやすい）

---

## 要件

- Python 3.10+
- 必須パッケージ（主なもの）
  - duckdb
  - openai
  - defusedxml
- （任意）J-Quants / OpenAI の API 利用に必要な環境変数

実際のプロジェクトでは requirements.txt や pyproject.toml を用意してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン／チェックアウト
   - git clone <repo-url>

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject/requirements があればそれを使用）

4. パッケージを編集可能インストール（任意）
   - pip install -e .

5. データ用ディレクトリ作成（デフォルトの DB パス等）
   - mkdir -p data

6. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロード無効化）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...         (必須：J-Quants リフレッシュトークン)
     - OPENAI_API_KEY=...                (必須：OpenAI API キーを使う機能で必要)
     - KABU_API_PASSWORD=...             (kabuステーション API 用パスワード)
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KILL_FLAG_CLEAR_ON_START=0
     - CPU_THRESHOLD_PCT=90.0
     - MEMORY_THRESHOLD_PCT=85.0
     - DISK_THRESHOLD_PCT=90.0
     - KABUSYS_ENV=development  (development|paper_trading|live)
     - LOG_LEVEL=INFO

---

## 簡単な使い方（コード例）

以下は主要ユーティリティの呼び出し例です。実行前に環境変数（OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN など）を設定してください。

- DuckDB 接続を用意して日次 ETL を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai_scores）を生成する

  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {num_written}")
  ```

- 市場レジーム判定（market_regime テーブルへ書き込む）

  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログDBを初期化する

  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # conn を使って order_requests / signal_events / executions テーブルが利用可能になります
  ```

- 研究用ファクター計算例

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))

  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

注意：
- OpenAI 呼び出しを行う関数は api_key 引数でキーを直接与えることができます（テスト時に差し替えしやすい）。
- 多くの関数は内部でトランザクション処理（BEGIN / COMMIT / ROLLBACK）を行います。DuckDB の挙動に注意してください（executemany に空リストを渡さないなどの実装上の配慮あり）。

---

## 自動環境変数ロードについて

パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探す）を基準に `.env` / `.env.local` の自動読み込みを行います。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

.env のパースは Bash ライクな形式（export KEY=VAL、クォート、コメント）にかなり忠実に対応しています。

---

## 主なモジュール（機能一覧・概要）

- kabusys.config
  - Settings: 環境変数ラッパー（J-Quants / Kabu / LINE / DBパス / 監視閾値 等）
  - 自動 .env 読み込み機能

- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch/save 系・認証・レート制御・リトライ）
  - pipeline: ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - quality: 品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 取得と前処理（SSRF 対策、ID生成、保存ロジック）
  - calendar_management: 市場カレンダー管理（is_trading_day, next_trading_day 等）
  - audit: 監査ログスキーマ定義と初期化ユーティリティ
  - stats: zscore_normalize 等統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースセンチメント取得→ai_scores 書き込み
  - regime_detector.score_regime: ETF 1321 MA 乖離と LLM マクロセンチメントを合成して market_regime に書き込み

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 注意点 / 運用上の補足

- OpenAI / J-Quants の API 呼び出しはそれぞれキーやトークン管理が必要です。local 環境では .env に設定してください。
- AI 呼び出しは外部API依存のため失敗を考慮したフェイルセーフ設計になっています（失敗時は 0 やスキップで継続）。
- ETL は差分取得 + backfill の設計です。run_daily_etl はカレンダー取得→株価ETL→財務ETL→品質チェックの順で実行します。
- DuckDB のバージョンや設定によっては executemany の空パラメータなど挙動差があるため、関数側でその対応が施されています。

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル／パッケージ構成例（src 配下）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - jquants_client.py
      - pipeline.py
      - etl.py
      - quality.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - stats.py
      - audit.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py

（上は本 README に含まれるモジュール一覧の抜粋です。実際のファイルは src/kabusys 内に多数存在します）

---

## ライセンス・貢献

- ライセンス情報やコントリビューションガイド（CONTRIBUTING.md）がある場合はリポジトリルートを参照してください。

---

README に記載の例は最小限の利用方法を示したものです。実運用ではログ設定、例外監視、定期ジョブ（cron / systemd timer / Airflow 等）によるスケジューリング、シークレット管理（Vault 等）を併用してください。必要であれば各モジュールの詳細ドキュメント（関数の使い方、DB スキーマ定義、ETL のパラメータなど）を追記できます。