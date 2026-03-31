# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などの機能を提供します。

目次
- プロジェクト概要
- 機能一覧
- 必要条件
- セットアップ手順
- 環境変数（.env）について
- 使い方（簡易サンプル）
- ディレクトリ構成
- 注意事項 / 設計上のポイント

---

## プロジェクト概要

KabuSys は、日本株の自動売買や研究（リサーチ）を支援するモジュール群です。  
主に以下をカバーします。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得と DuckDB へ保存（ETL）
- ニュース収集（RSS） → raw_news 保存および銘柄紐付け
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（ai_scores）と市場レジーム判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal/events / order_requests / executions）用スキーマ初期化ユーティリティ
- kabuステーション連携や注文実行ロジック（別モジュール想定）

設計方針として「ルックアヘッドバイアスを避ける」「ETL/保存は冪等」「外部API呼び出しはリトライ・レート制御」「DuckDB を中心とした軽量データ基盤」を重視しています。

---

## 機能一覧

主な機能と提供箇所（モジュール）

- 環境設定
  - kabusys.config: .env 自動読み込み、必須値チェック、設定オブジェクト提供
- データ取得 / ETL
  - kabusys.data.jquants_client: J-Quants API クライアント（認証・取得・保存）
  - kabusys.data.pipeline: 日次 ETL 実行（run_daily_etl 等）
  - kabusys.data.calendar_management: 市場カレンダー管理 / 営業日ユーティリティ
  - kabusys.data.news_collector: RSS 取得/前処理/保存（SSRF対策等）
  - kabusys.data.quality: データ品質チェック
  - kabusys.data.audit: 監査ログスキーマ初期化 / init_audit_db
- AI / ニュース NLP
  - kabusys.ai.news_nlp.score_news: ニュースを銘柄ごとに集約し LLM でスコア化
  - kabusys.ai.regime_detector.score_regime: ma200 とマクロニュースを合成して市場レジーム判定
- 研究用ユーティリティ
  - kabusys.research.factor_research: calc_momentum, calc_value, calc_volatility
  - kabusys.research.feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - kabusys.data.stats.zscore_normalize: Zスコア正規化

---

## 必要条件

- Python 3.10+
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ: urllib, datetime, json, logging 等

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

---

## セットアップ手順

1. リポジトリをクローン / ワークツリーへ
   - 例: git clone ...

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 例:
     - pip install -U pip
     - pip install duckdb openai defusedxml
   - （プロジェクトに pyproject.toml や requirements.txt があれば）pip install -e . または pip install -r requirements.txt

4. 環境変数（.env）を準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（最低限）
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
     - KABU_API_PASSWORD: kabu API パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack チャンネル ID
     - OPENAI_API_KEY: OpenAI を利用する場合に必要（score_news / score_regime）
   - 任意 / 既定値あり
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/...
     - DUCKDB_PATH: data/kabusys.duckdb（既定）
     - SQLITE_PATH: data/monitoring.db（既定）
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env のパースはシェル形式にかなり忠実で、クォートやエスケープ、コメントなどの取り扱いに対応します。

5. データベース初期化（監査ログなど）
   - 監査用 DB を作る例:
     - from kabusys.data.audit import init_audit_db
       conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡易サンプル）

以下は代表的な利用例です。実行はアプリケーションやスクリプト内で行ってください。

- DuckDB 接続を作る（デフォルトパスは settings.duckdb_path）
  - from kabusys.config import settings
    import duckdb
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントのスコア付け（OpenAI API キーが必要）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    count = score_news(conn, target_date=date(2026, 3, 20))
    print("scored:", count)

- 市場レジーム判定（ma200 + マクロニュース）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    score_regime(conn, target_date=date(2026, 3, 20))

- ファクター計算 / 研究ユーティリティ
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, date(2026, 3, 20))
  - from kabusys.data.stats import zscore_normalize
    normed = zscore_normalize(records, ["mom_1m", "mom_3m"])

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")

注意: 上記 API は例示で、実行には事前に環境変数や DB スキーマ等が整っている必要があります。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースの LLM スコアリング
  - regime_detector.py  — 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント（取得＋DuckDB保存）
  - pipeline.py         — ETL（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理・営業日ロジック
  - news_collector.py   — RSS 取得・前処理・保存（SSRF対策含む）
  - quality.py          — 品質チェック（欠損・スパイク・重複・日付整合性）
  - stats.py            — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py            — 監査ログテーブル定義・初期化
  - etl.py              — ETLResult 再エクスポート
- research/
  - __init__.py
  - factor_research.py  — ファクター算出（モメンタム・バリュー・ボラティリティ）
  - feature_exploration.py — 将来リターン、IC、統計サマリー
- research/* は Research 用の集約関数群

---

## 注意事項 / 設計上のポイント

- ルックアヘッドバイアス対策:
  - 多くの関数は date.today() に依存せず、引数で target_date を受け取ることで「その時点で利用可能なデータのみ」を参照するように設計されています。バックテストに利用する際はこの点を活用してください。
- 冪等性:
  - DB 保存は ON CONFLICT DO UPDATE などを用いて冪等化しています（jquants_client.save_* 等）。
- リトライ / レート制御:
  - J-Quants API には固定間隔のレートリミッタやリトライロジックが組み込まれています。OpenAI 呼び出しもリトライと失敗フォールバックを備えています。
- セキュリティ:
  - RSS 収集は SSRF 対策、受信サイズ制限、defusedxml を用いたパース等の対策が組み込まれています。
- テスト容易性:
  - OpenAI・HTTP 呼び出しなどは内部呼び出しを差し替えてモックできるように設計されています（テスト用に関数を patch する想定）。

---

この README はコードベースの主要点を簡潔にまとめたものです。より詳細な仕様（DataPlatform.md / StrategyModel.md 等）が別途ある想定ですので、実運用や拡張の際はそれらの設計ドキュメントを参照してください。必要であれば README に実行スクリプト例、CI / デプロイ手順、より詳細な環境変数一覧や DB スキーマの例を追加します。どの情報を優先して追加しましょうか？