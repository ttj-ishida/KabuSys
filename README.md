# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
DuckDB をデータストアに、J-Quants / JPEX カレンダー / RSS / OpenAI を組み合わせてデータ ETL、品質チェック、ニュース NLP、リサーチ用ファクター計算、監査ログ（トレーサビリティ）を提供します。

---

## 主要な特徴（機能一覧）

- データ収集（ETL）
  - J-Quants API から株価（日足）、財務データ、上場情報、JPX カレンダーを差分取得・保存
  - 差分取得・バックフィル・ページネーション対応・トークン自動リフレッシュ
- データ品質チェック
  - 欠損、スパイク（急騰/急落）、重複、日付不整合チェック
- ニュース収集・前処理
  - RSS 取得、URL 正規化、トラッキング除去、SSRF 対策、gzip 制限、XML の安全パース
- ニュース NLP（OpenAI）
  - 銘柄別ニュースをまとめて LLM（gpt-4o-mini）でセンチメント評価し ai_scores に保存
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM を合成）
  - JSON Mode を利用した堅牢なパース・リトライ設計
- 研究（Research）
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）やファクター統計量
  - z-score 正規化ユーティリティ
- 監査ログ（Audit / トレーサビリティ）
  - signal_events / order_requests / executions テーブルを提供
  - 注文フローの UUID 連鎖でトレーサビリティを確保
- 設定管理
  - .env / .env.local の自動読込（プロジェクトルートを .git や pyproject.toml で検出）
  - 環境変数の必須検査や KABUSYS_ENV / LOG_LEVEL のバリデーション

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | を使用）
- Git（.env 自動ロードを使う場合はプロジェクトルート判定に利用）

1. リポジトリをクローン（開発用）
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   必要な主なライブラリ:
   - duckdb
   - openai
   - defusedxml
   ```
   pip install duckdb openai defusedxml
   ```

   （開発用に extras やテストライブラリがあれば適宜追加）

4. パッケージとしてインストール（編集可能モード）
   ```
   pip install -e .
   ```

5. 環境変数（.env）を用意
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local`（任意）を置くと自動で読み込まれます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN=...      （J-Quants リフレッシュトークン、必須）
   - OPENAI_API_KEY=...             （OpenAI API キー、score_news / regime に必要）
   - KABU_API_PASSWORD=...          （kabu ステーション API パスワード）
   - SLACK_BOT_TOKEN=...            （Slack 通知を使う場合）
   - SLACK_CHANNEL_ID=...           （Slack 通知先）
   - DUCKDB_PATH=data/kabusys.duckdb（デフォルト、変更可）
   - SQLITE_PATH=data/monitoring.db （監視用 SQLite、変更可）
   - KABUSYS_ENV=development|paper_trading|live（運用モード）
   - LOG_LEVEL=INFO|DEBUG|...       （ログレベル）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

---

## 使い方（基本例）

以下は Python スクリプトや REPL から各機能を呼び出す例です。

- DuckDB 接続と settings 利用
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー / 株価 / 財務 を差分取得）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn)  # target_date を指定しなければ今日（システム日）を使用
  print(result.to_dict())
  ```

- ニュース NLP（前日に相当するウィンドウの記事を銘柄別にスコアリングして ai_scores に保存）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込み銘柄数を返す
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースで判定）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  ```

- 設定アクセス例
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)
  print(settings.is_live)
  ```

注意点
- LLM を使う関数（score_news / score_regime）は OpenAI API キーが必要です。引数で明示的に渡すことも可能です（api_key）。
- ETL / API 呼び出しはネットワーク・外部 API に依存します。ローカル環境やテストではモック化して実行してください。
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml で検出します。パッケージ配布後に挙動が異なる場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に制御できます。

---

## 主要 API / テーブル（概要）

- ETL / データ取得
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client.fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - jquants_client.save_daily_quotes / save_financial_statements / save_market_calendar

- ニュース
  - news_collector.fetch_rss
  - ai.news_nlp.score_news -> writes to ai_scores
  - ai.regime_detector.score_regime -> writes to market_regime

- データ品質
  - data.quality.run_all_checks (returns list of QualityIssue)

- 監査ログ
  - data.audit.init_audit_db / init_audit_schema
  - Tables: signal_events, order_requests, executions

テーブル名（主なもの）
- raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, signal_events, order_requests, executions

---

## ディレクトリ構成

（ライブラリの主要パッケージ構成）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP / OpenAI 呼出し
    - regime_detector.py            — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント & 保存関数
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の再エクスポート
    - news_collector.py             — RSS ベースのニュース収集
    - calendar_management.py        — マーケットカレンダー管理・営業日判定
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore など）
    - audit.py                      — 監査ログ（トレーサビリティ）初期化/ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            — Momentum/Volatility/Value 等
    - feature_exploration.py        — forward returns / IC / summary / rank
  - ai/, data/, research/ 等のサブモジュールが公開 API を持ちます

---

## 注意事項・設計上のポイント

- Look-ahead bias 対策:
  - 各モジュールは内部で datetime.today() を直接参照しない方針（関数に target_date を明示的に渡すことでバックテスト時のリークを防止）。
  - J-Quants のデータは fetched_at を記録し「いつ知り得たか」を追跡可能にしています。

- 冪等性:
  - J-Quants 保存関数は ON CONFLICT DO UPDATE を利用し冪等です。
  - ETL は最終取得日ベースの差分更新とバックフィルを組み合わせます。

- API リトライ・レート制御:
  - J-Quants クライアントはレート制限（120 req/min）に合わせたレートリミッタと指数バックオフを備えています。
  - OpenAI 呼出しもリトライや 5xx 判断を段階的に行います。

- セキュリティ:
  - news_collector は SSRF 対策（ホストがプライベートかの判定、リダイレクト検査）や defusedxml による XML パース安全対策を実装。
  - .env の読み込みはプロジェクトルートを検出して行い、既存 OS 環境変数を優先します。

---

必要であれば、README に含める具体的な .env.example、テーブル DDL の抜粋、ユースケース別の実行手順（CI 実行、スケジューラ設定、Slack 通知連携例）なども追加で作成します。どの情報がさらに必要か教えてください。