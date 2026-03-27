# KabuSys

日本株向けの自動売買 / データパイプライン基盤ライブラリです。J-Quants や RSS、OpenAI を活用してデータ収集・品質チェック・NLP スコアリング・市場レジーム判定・監査ログなどを行うモジュール群を含みます。

主な設計方針:
- ルックアヘッドバイアスを避ける設計（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を用いたローカルデータストア（ON CONFLICT による冪等保存）
- 外部 API 呼び出しはリトライ・レートリミット・フェイルセーフを組み込み
- テスト容易性のため API 呼び出しや内部待機関数を差し替え可能

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを自動検出）
  - 必須環境変数アクセス用ラッパー（settings オブジェクト）

- データ ETL（J-Quants）
  - 株価日足（raw_prices）の差分取得・保存（ページネーション対応）
  - 財務データ（raw_financials）の差分取得・保存
  - JPX マーケットカレンダーの取得・保存
  - ETL の品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集 / NLP
  - RSS フィードの安全な取得（SSRF対策、サイズ検査、トラッキング除去）
  - raw_news への冪等保存
  - ニュースを銘柄で集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に保存（score_news）
  - マクロニュース + ETF 1321 の MA200乖離を合成して市場レジームを判定（score_regime）

- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（情報係数）計算、ファクター統計サマリー
  - Z スコア正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions など監査用テーブルの初期化
  - 監査 DB の初期化ユーティリティ（init_audit_db）

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型アノテーションで PEP 604 (|) を使用）
- 必要主要パッケージ:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, OpenAI, RSS ソース）

（実際のインストールではプロジェクトの requirements.txt などを参照してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト

2. 仮想環境を作成してアクティベート（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - 必要に応じてその他ライブラリを追加

4. パッケージをインストール（開発モードなど）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能）。
   - 必須例（.env）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意:
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABU_API_BASE_URL (kabuステーション用のベースURL)

6. データベースファイルの確認 / 作成
   - DuckDB ファイル (settings.duckdb_path) は自動作成されますが、各テーブルは ETL / 初期化関数で作成してください。
   - 監査用 DB を分けて初期化する場合:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な例）

以下はライブラリ関数の簡単な利用例です。実行前に必須環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続の作成:

  from pathlib import Path
  import duckdb
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path
  conn = duckdb.connect(str(db_path))

- 日次 ETL の実行:

  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（銘柄ごと）スコアリング:

  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {n}")

- 市場レジーム判定:

  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログスキーマの初期化（監査用 DB を独立させる場合）:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn に対して監査ログ操作を行えます

- 研究用ファクター計算の呼び出し例:

  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records は各銘柄ごとの dict のリスト

注意点:
- OpenAI 呼び出しは外部 API で課金対象です。テスト時は関数内で呼ばれる _call_openai_api をモックすると安全です（モジュール毎に独立した差し替えポイントがあります）。
- 自動 .env ロードはプロジェクトルート（.git や pyproject.toml を基準）から行われます。テスト・CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

---

## ディレクトリ構成

プロジェクトは src/kabusys 以下に主要モジュールを配置しています（抜粋）:

- src/kabusys/
  - __init__.py               (パッケージエントリ, __version__ 等)
  - config.py                 (環境変数 / Settings オブジェクト、自動 .env ロード)
  - ai/
    - __init__.py
    - news_nlp.py             (ニュース NLP スコアリング: score_news)
    - regime_detector.py      (市場レジーム判定: score_regime)
  - data/
    - __init__.py
    - jquants_client.py       (J-Quants API クライアント, save_* / fetch_* 実装)
    - pipeline.py             (ETL パイプライン実装, run_daily_etl 等)
    - etl.py                  (ETLResult の再エクスポート)
    - news_collector.py       (RSS 収集, 前処理, 保存)
    - calendar_management.py  (market_calendar 管理, is_trading_day 等)
    - quality.py              (品質チェック: 欠損・スパイク・重複・日付整合性)
    - stats.py                (zscore_normalize 等)
    - audit.py                (監査ログスキーマ定義・初期化)
  - research/
    - __init__.py
    - factor_research.py      (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py  (calc_forward_returns / calc_ic / rank / summary)
  - monitoring/ (監視系・Slack 通知などが想定されるディレクトリ — 実装は別途)
  - strategy/  (戦略関連モジュール — 実装は別途)
  - execution/ (約定/ブローカー連携モジュール — 実装は別途)

各モジュールはドキュメント文字列に設計方針・処理フロー・フェイルセーフの説明が含まれているため、実装を参照してください。

---

## 開発 / テストのヒント

- OpenAI や J-Quants の外部呼び出し周りはリトライ・レート制御実装があるため、テストではネットワーク依存部分をモックしてください（_call_openai_api / kabusys.data.jquants_client._request 等）。
- settings には自動 .env ロードがあるため、ユニットテストで環境を固定したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、必要な環境変数をテストコードから注入してください。
- DuckDB はインメモリ(':memory:') モードもサポートしているため、テストで永続ファイルを作らずに済ますことができます（init_audit_db(":memory:") 等）。

---

この README はコードベース内の主要モジュールと利用方法の概要を説明するものです。各関数・クラスの詳細な振る舞いは該当モジュールのドキュメント文字列を参照してください。必要であれば、インストール用の requirements.txt、.env.example、使い方の具体的なスクリプト例などを追加で作成できます。