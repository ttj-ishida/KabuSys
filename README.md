# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants）→ データ品質チェック → ニュース NLP → 市場レジーム判定 → リサーチ / ファクター計算 → 監査ログ（発注/約定トレーサビリティ）までを想定したモジュール群を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・加工・解析・監査ログを一貫して行うための内部ライブラリです。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- RSS ニュース収集と OpenAI を用いた記事/銘柄単位のセンチメントスコア付与
- ETF を用いた市場レジーム判定（MA + マクロニュースの LLM スコア合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- 発注から約定までの監査ログ（監査テーブルの初期化、監査DBユーティリティ）
- 設定は .env または環境変数で管理（自動ロード機構あり）

設計方針の特徴:
- DuckDB を中心としたローカル DB ベース（Look-ahead バイアスを避ける設計）
- API 呼び出しに対する堅牢なリトライ・レート制御
- LLM 呼び出しは JSON Mode を想定し、レスポンスのバリデーションやフォールバックを実装
- 冪等（idempotent）設計：DB への保存は ON CONFLICT / DELETE→INSERT 等で二重書き込みを回避

---

## 機能一覧

- 設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の取得ユーティリティ

- データ収集（J-Quants クライアント）
  - fetch_daily_quotes / save_daily_quotes（株価日足）
  - fetch_financial_statements / save_financial_statements（財務）
  - fetch_market_calendar / save_market_calendar（取引カレンダー）
  - rate limiting / リトライ / トークン自動リフレッシュ

- ETL パイプライン
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - run_daily_etl（まとめて実行・品質チェック含む）
  - ETLResult（実行結果のデータクラス）

- データ品質チェック
  - 欠損データ、重複、スパイク、日付不整合の検出
  - run_all_checks でまとめて実行して QualityIssue リストを返す

- ニュース収集・NLP
  - RSS フィード取得（SSRF / gzip / サイズ制限 / トラッキングパラメータ除去）
  - news_nlp.score_news: OpenAI を使った銘柄別ニュースセンチメント付与（ai_scores へ保存）
  - 安全なリトライ・レスポンス検証・チャンク処理

- 市場レジーム判定
  - regime_detector.score_regime: ETF 1321 の 200 日 MA 乖離 + マクロニュースの LLM スコアの合成で 'bull'/'neutral'/'bear' を判定し market_regime に書き込み

- 研究用ユーティリティ
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

- 監査ログ（Audit）
  - 監査用テーブル群（signal_events, order_requests, executions）とインデックスの初期化
  - init_audit_schema / init_audit_db（DuckDB で監査 DB を初期化）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の型表記（A | B）を使用しているため）
- Git リポジトリルートに .env / .env.local を置く想定

推奨手順（ローカル開発向け）:

1. リポジトリをクローンしてワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   - venv 例:
     ```
     python -m venv .venv
     source .venv/bin/activate   # macOS / Linux
     .\.venv\Scripts\activate    # Windows (PowerShell の場合)
     ```

3. 依存パッケージをインストール
   - setup.py / pyproject.toml がある前提で editable install:
     ```
     pip install -e .
     ```
   - 主要依存（手動で入れる場合）:
     ```
     pip install duckdb openai defusedxml
     ```
   - その他、実行環境に応じて sqlite3 は標準ライブラリで利用可能です。

4. 環境変数設定（.env を作成）
   - プロジェクトルートの .env/.env.local で下記を設定してください（例: .env.example を参考に作成）。
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - KABU_API_BASE_URL (省略可、デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN=<slack bot token>
     - SLACK_CHANNEL_ID=<slack channel id>
     - OPENAI_API_KEY=<openai api key>  # news/regime に必要
     - DUCKDB_PATH=data/kabusys.duckdb  # デフォルト
     - SQLITE_PATH=data/monitoring.db    # デフォルト
     - KABUSYS_ENV=development|paper_trading|live  # デフォルト: development
     - LOG_LEVEL=INFO|DEBUG|...

   - 自動ロードについて:
     - 設定管理モジュールはプロジェクトルートにある .env を自動で読み込みます（.env.local は上書き）。
     - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。

---

## 使い方（簡易ガイド）

以下は代表的な使用例です。すべて Python コードからモジュールを直接呼び出す想定です。

- DuckDB 接続の取得（例）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次 ETL）の実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定（省略すると today を使います）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコア付け（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  t = date(2026, 3, 20)
  mom = calc_momentum(conn, t)
  val = calc_value(conn, t)
  vol = calc_volatility(conn, t)
  ```

- Z スコア正規化ユーティリティ
  ```python
  from kabusys.data.stats import zscore_normalize

  normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "per"])
  ```

- 監査ログテーブル（監査 DB）の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions が作成されます
  ```

- 設定値の参照
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

注意点:
- LLM を使う処理（news_nlp, regime_detector）は OPENAI_API_KEY に依存します。キーが未設定だと ValueError を送出します。
- run_daily_etl の一部ステップが失敗しても他のステップは継続します（結果は ETLResult に格納されます）。
- DuckDB executemany に空リストを渡すと問題になる箇所があるため、内部で空チェックを行っています（利用側での注意は通常不要）。

---

## よくある環境変数（テンプレート）

（プロジェクトルートに .env を作成する例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabu API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# OpenAI
OPENAI_API_KEY=sk-...

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 環境 / ログ
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## ディレクトリ構成（主なファイル・モジュール）

以下は src/kabusys 配下の主なモジュールと機能の概観です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                   — 環境変数 / .env 管理、Settings クラス
  - ai/
    - __init__.py                — score_news をエクスポート
    - news_nlp.py                — ニュースの LLM ベースセンチメント（score_news）
    - regime_detector.py         — ETF MA + マクロニュースで市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py     — 市場カレンダー管理・営業日ユーティリティ
    - etl.py / pipeline.py       — ETL パイプライン（run_daily_etl 他）
    - stats.py                   — zscore_normalize 等の統計ユーティリティ
    - quality.py                 — データ品質チェック（QualityIssue 等）
    - audit.py                   — 監査ログテーブルの DDL / 初期化（init_audit_schema / init_audit_db）
    - jquants_client.py          — J-Quants API クライアント（fetch/save 系）
    - news_collector.py          — RSS 収集と前処理
    - etl.py                     — ETL の公開インターフェース（ETLResult）
  - research/
    - __init__.py
    - factor_research.py         — calc_momentum/calc_value/calc_volatility
    - feature_exploration.py     — calc_forward_returns/calc_ic/factor_summary 等

---

## 開発・運用上の注意

- Python バージョン: 3.10 以上
- OpenAI の呼び出し部分は API レート・失敗時のフォールバックを備えていますが、実際の運用では API 利用料金やレートに注意してください。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。CI／テスト環境で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- ETL / ニュース収集等はネットワークアクセスを行います。テスト時は各種外部呼び出し（OpenAI, J-Quants, HTTP）をモックしてください（コード内で差し替え可能なポイントが用意されています）。
- DuckDB スキーマや監査テーブルは初期化関数で自動作成できますが、運用時のバックアップや権限設定は別途管理してください。

---

## 参考（簡単なワークフロー例）

1. .env に認証情報を用意する
2. DuckDB を接続して ETL を実行（run_daily_etl）
3. ニュース収集 & score_news を実行して ai_scores を更新
4. score_regime を実行して market_regime を更新
5. research モジュールでファクターを計算・正規化して戦略に供給
6. 監査ログ（signal/orders/executions）は audit.init_audit_db で初期化して利用

---

その他、各モジュールの詳細な仕様・トランザクション挙動・SQL スキーマはソースコードの docstring に詳述されています。運用にあたっては各関数の docstring を参照してください。質問や追加のドキュメント化が必要であればお知らせください。