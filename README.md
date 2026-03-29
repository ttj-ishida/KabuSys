# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株向けのデータプラットフォームとリサーチ / AI / ETL / 監査機能を備えた自動売買基盤のライブラリ群です。DuckDB ベースのローカルデータレイクから J-Quants API を通じたデータ取得、ニュース NLP によるセンチメント集計、ファクター計算、ETL パイプライン、監査ログテーブルの初期化などを提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない）
- DuckDB による効率的な集計・ウィンドウ処理
- API 呼び出しはリトライ・レート制御・フェイルセーフ設計
- 冪等性を意識した DB 書き込み（ON CONFLICT / DELETE→INSERT 等）

---

## 機能一覧

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須値チェック（例: JQUANTS_REFRESH_TOKEN 等）

- データ収集 / ETL（kabusys.data）
  - J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ、レート制御）
  - 日次 ETL パイプライン（prices / financials / calendar）
  - JPX マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal / order_request / executions テーブル、インデックス、初期化ユーティリティ）

- AI（kabusys.ai）
  - ニュースセンチメント集計（news_nlp.score_news）：OpenAI を用いて銘柄ごとにスコアを生成
  - 市場レジーム判定（regime_detector.score_regime）：ETF の MA とマクロニュースの LLM センチメントを合成

- リサーチ（kabusys.research）
  - ファクター算出（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - 汎用統計ユーティリティ（zscore_normalize）

- 監視・実行（execution / monitoring パッケージ名で公開想定）
  - （コードベースに含まれるモジュールと連携して発注・監視を行う想定）

---

## 前提 / 必要環境

- Python 3.10+
- DuckDB（Python パッケージ duckdb）
- OpenAI SDK（openai）
- defusedxml（XML パースの安全化）
- 標準ライブラリ外パッケージは pyproject.toml / requirements に従ってインストールしてください。

（実装上で利用される外部 API キーやローカル DB パスが必要になります）

---

## セットアップ手順

1. リポジトリをクローン・配置
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   - プロジェクトに pyproject.toml がある想定なら:
     ```
     pip install -e .
     ```
   - または requirements.txt があれば:
     ```
     pip install -r requirements.txt
     ```
   必要な主なパッケージ例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` として下記値を設定します（例: `.env.example` を参考に作成）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
     - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID: Slack チャネル ID（必須）
     - OPENAI_API_KEY: OpenAI API キー（AI モジュール利用時に必要）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: environment (development|paper_trading|live)（デフォルト: development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
   - 自動読み込み:
     - パッケージ import 時にプロジェクトルートを検出し `.env` と `.env.local` を自動で読み込みます。
     - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で使用）。

5. DB 初期化（監査用など）
   - 監査ログ用 DuckDB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - または既存接続にスキーマを追加:
     ```python
     import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表的な利用例）

以下はライブラリを直接利用する簡単な例です。スクリプトやジョブ（cron）として組み込んでください。

- DuckDB 接続準備（デフォルトパスを使用）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略時は今日）
  res = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(res.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API キー必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news(conn, target_date, api_key=None) -> 書き込み件数を返す
  count = score_news(conn, date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を .env で設定しておく
  ```

- 市場レジーム判定（OpenAI API キー必要）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, date(2026, 3, 20))
  ```

- ファクター計算 / リサーチユーティリティ
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

- 監査スキーマ初期化（既存 DB に追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- テスト時のヒント
  - OpenAI 呼び出しは内部で _call_openai_api を使っている箇所があるため、ユニットテストでは該当関数を patch してレスポンスを制御できます（例: unittest.mock.patch）。
  - 自動 .env ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## 主要モジュールとディレクトリ構成

リポジトリの主要なディレクトリ / ファイル構成（src/kabusys 以下）と概要：

- kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、.env 自動読み込み、settings オブジェクトを提供
  - ai/
    - __init__.py
    - news_nlp.py
      - RSS 等で収集した raw_news から銘柄ごとにニュースを集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込む
    - regime_detector.py
      - ETF (1321) の 200 日 MA 乖離とマクロニュースの LLM センチメントを重ね合わせて市場レジームを判定（market_regime テーブル書込）
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得 / 保存 用ヘルパー、レートリミット、トークン管理）
    - pipeline.py
      - 日次 ETL の本体（prices / financials / calendar の差分取得、品質チェック）
      - ETLResult 定義
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS フィード取得、前処理、raw_news への冪等保存（SSRF・gzip・XML 安全処理）
    - calendar_management.py
      - market_calendar（JPX カレンダー）管理、営業日判定・next/prev/get_trading_days、calendar_update_job（J-Quants 取得）
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログテーブル定義・初期化（signal_events, order_requests, executions 等）
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py
      - 将来リターン算出、IC 計算、rank、factor_summary

（その他、execution / monitoring 等の公開 API 名はパッケージ __all__ に含まれていますが、本リポジトリ内の該当実装に合わせて利用してください）

---

## 開発上の注意点

- 時刻・日付は基本的に naive な date / datetime を用い、UTC 管理や変換は各モジュールで明示的に行っています（例: fetched_at は UTC）。
- DuckDB に対する executemany の制約（空リスト不可）を考慮した実装になっています。
- OpenAI／外部 API 呼び出しはリトライとバックオフを備え、API 失敗時はフェイルセーフ挙動（スコア 0.0 など）で継続する設計です。
- ETL は部分失敗を許容し、品質チェックの結果は ETLResult に集約します。呼び出し元で停止判断を行ってください。

---

## よく使う環境変数（要設定）

- JQUANTS_REFRESH_TOKEN (必須)
- OPENAI_API_KEY（AI 機能利用時）
- KABU_API_PASSWORD (kabu station API)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（通知機能等）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- KABUSYS_ENV (development|paper_trading|live)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 （自動 .env ロードを無効化）

---

以上が README の概要です。README の補足や具体的な実行スクリプト（systemd / cron / Airflow での運用例）、テスト用 .env.example のテンプレート作成、CI 設定などをご希望であれば追記します。