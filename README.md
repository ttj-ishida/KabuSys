# KabuSys

日本株向けのデータ基盤・研究・自動売買（監査・ETL・NLP・リサーチ）ライブラリです。  
このリポジトリはデータ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログ等のユーティリティを集めたモジュール群を提供します。

バージョン: `kabusys.__version__ = 0.1.0`

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構築するための基盤ライブラリです。主な目的は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分取得（ETL）
- ニュース収集（RSS）と OpenAI によるニュースセンチメント（銘柄別 ai_score / マクロセンチメント）
- ファクター（モメンタム・バリュー・ボラティリティ等）の計算と研究用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → executions）のスキーマ初期化・管理
- 環境設定管理と自動 .env ロード

設計方針として、ルックアヘッドバイアスの排除、冪等性、API リトライ・レート制御、DuckDB による高速なローカル処理を重視しています。

---

## 主な機能一覧

- Data / ETL
  - J-Quants からの差分取得（prices, financials, market calendar）
  - ETL パイプライン（run_daily_etl）と ETL 結果クラス（ETLResult）
  - データ品質チェック（check_missing_data, check_spike, check_duplicates, check_date_consistency）
  - ニュース収集（RSS → raw_news）と記事前処理（SSRF 対策, gzip 上限など）
  - 市場カレンダー管理（営業日判定、next/prev/get_trading_days）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - DuckDB への保存ユーティリティ（冪等保存）

- AI / NLP
  - ニュースの銘柄別センチメントスコアリング（news_nlp.score_news）
  - マクロニュース＋ETF（1321）MA による市場レジーム判定（ai.regime_detector.score_regime）
  - OpenAI の JSON Mode を使った厳密なレスポンス処理とリトライ戦略

- Research
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリ
  - Zスコア正規化ユーティリティ

- 設定管理
  - 環境変数 / .env の自動読み込み（プロジェクトルート検出）
  - 必須変数の取得ラッパー（settings）

---

## セットアップ手順

1. リポジトリをクローン（例）

   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（例）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があれば）
   pip install -e .

4. 環境変数を設定（.env をプロジェクトルートに配置することを推奨）

   必須（実行する機能によって変わります）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - OPENAI_API_KEY         : OpenAI API キー（news_nlp / regime_detector 用）
   - KABU_API_PASSWORD      : kabu ステーション API パスワード（発注連携等）
   - SLACK_BOT_TOKEN        : Slack 通知用 Bot Token
   - SLACK_CHANNEL_ID       : Slack チャンネル ID

   任意（デフォルト値あり）:
   - DUCKDB_PATH            : DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH            : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV            : development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL              : DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

   自動 .env ロード:
   - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用等）。

---

## 使い方（代表的な例）

以下は簡単な利用例です。適宜 Python スクリプトや cron / Airflow ジョブに組み込んでください。

- DuckDB 接続の作成（デフォルトファイルを使用）

  from datetime import date
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（市場カレンダー取得 → prices, financials → 品質チェック）

  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026,3,20))
  print(result.to_dict())

- ニュースセンチメント（OpenAI を使って銘柄別 ai_scores を生成）

  from kabusys.ai.news_nlp import score_news
  from datetime import date
  n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"written {n_written} codes")

- マクロ & MA による市場レジーム判定（market_regime テーブルへ書き込み）

  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- 監査ログ DB 初期化（監査専用 DuckDB を作る）

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って signal/order/execution のインサートや検索が可能

- ファクター計算（例：モメンタム）

  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  records = calc_momentum(conn, date(2026,3,20))
  print(records[:5])

注意:
- OpenAI を呼ぶ関数は api_key 引数でキー注入可能（テストでの差替えが容易）。
- run_daily_etl などは内部で date.today() を直接参照しない設計（ルックアヘッドバイアス防止）です。target_date を明示的に与えることを推奨します。

---

## 主要ディレクトリ / ファイル構成

（src/kabusys 配下の主要モジュール）

- kabusys/
  - __init__.py  — パッケージ初期化（__version__ 等）
  - config.py    — 環境変数 / .env の自動読み込み、設定アクセス（settings）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースの銘柄別センチメント取得（OpenAI 呼び出し・検証）
    - regime_detector.py — ETF MA + マクロニュースから市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存・認証・レート制御）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）、ETLResult
    - etl.py             — ETLResult の公開再エクスポート
    - news_collector.py  — RSS から raw_news へ収集するロジック（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理（is_trading_day など）
    - stats.py           — zscore_normalize 等の統計ユーティリティ
    - quality.py         — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py           — 監査ログ（DDL・インデックス・初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — forward_returns, calc_ic, factor_summary 等

---

## 環境変数（主なもの）

- 必須:
  - JQUANTS_REFRESH_TOKEN
  - OPENAI_API_KEY (news_nlp / regime_detector を使う場合)
  - SLACK_BOT_TOKEN (Slack 通知を行う場合)
  - SLACK_CHANNEL_ID

- 任意・デフォルトあり:
  - KABUSYS_ENV = development | paper_trading | live (default: development)
  - LOG_LEVEL = INFO (default)
  - KABUSYS_DISABLE_AUTO_ENV_LOAD = 1 で .env 自動読み込みを無効化
  - DUCKDB_PATH = data/kabusys.duckdb
  - SQLITE_PATH = data/monitoring.db
  - KABU_API_BASE_URL (kabu API 用、デフォルト http://localhost:18080/kabusapi)
  - KABU_API_PASSWORD (kabu ステーションに接続する場合)

---

## 注意事項 / トラブルシューティング

- OpenAI / J-Quants / kabu ステーションなど外部 API のキー・エンドポイントは適切に管理してください。公開リポジトリにキーを置かないでください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行います。CI やテストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空リストを与えるとエラーになる箇所があるため、ライブラリ内部は空チェックを行っています。直接 SQL を実行する場合は注意してください。
- run_daily_etl 等は部分失敗しても他の処理を継続する設計です。戻り値の ETLResult 内の errors / quality_issues を確認して運用判断してください。
- news_collector は SSRF 対策や受信サイズ制限を行っています。RSS フィードにより取得失敗する場合はログを確認してください。
- DuckDB ファイルの保存ディレクトリが存在しない場合、audit.init_audit_db は親ディレクトリを自動作成しますが、他の箇所では同様の自動作成がないことに留意してください。

---

## 開発・テストについて

- モジュール内の外部 API 呼び出し（OpenAI / J-Quants / urllib）や時間関数はテスト容易性を考慮して抽象化してあるため、unittest.mock などで差し替えて単体テストを実行できます。
- settings は Settings クラスを通じて取得します。テスト中は環境変数を直接差し替えるか、KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して .env 自動読み込みを無効化してください。

---

もし README に追加したいサンプルスクリプト、CI 設定、あるいは実際の発注モジュール（execution）やモニタリング周りの説明が必要であれば、用途に合わせて追記します。