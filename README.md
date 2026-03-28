# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants クライアント、マーケットカレンダー管理など、バックテスト・運用で必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームとリサーチ／自動売買の基盤を提供する Python パッケージです。主な目的は次の通りです。

- J-Quants API からの市場データ ETL（株価・財務・カレンダー）
- RSS ベースのニュース収集と LLM（OpenAI）を使ったセンチメントスコアリング
- ファクター計算（モメンタム / バリュー / ボラティリティ 等）と特徴量解析ユーティリティ
- 市場レジーム判定（ETF の MA とマクロニュースを組合せ）
- DuckDB を用いた永続化・監査ログ（order/signal/execution のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の特徴として、ルックアヘッドバイアスを避けるため日付の扱いに注意しており、ETL や LLM 呼び出しにはフェイルセーフやリトライを備えています。

---

## 主な機能一覧

- データ取得 / ETL
  - J-Quants からの株価（daily_quotes）、財務（statements）、上場情報、マーケットカレンダー取得
  - 差分更新・バックフィル・保存（DuckDB への冪等保存）
  - run_daily_etl 等の ETL エントリポイント
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策・トラッキング除去・gzip 対応）
  - OpenAI を利用した銘柄別センチメント（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化
- データ品質管理
  - 欠損、重複、スパイク、日付不整合の検出（quality.run_all_checks）
- 監査ログ（監査テーブル初期化）
  - signal_events / order_requests / executions のスキーマ定義と初期化ユーティリティ
- 設定管理
  - .env 自動読み込み（プロジェクトルート基準） / 環境変数経由の設定（kabusys.config.Settings）

---

## セットアップ手順

前提
- Python 3.10 以上（typing の | 合成や dict[str, ...] を使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてインストール（開発インストール例）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```

2. 依存パッケージ（代表例）
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに requirements.txt があればそれを利用してください）

3. 環境変数を設定
   - 必須（実運用や一部機能で必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API 用パスワード（発注系で使用）
     - SLACK_BOT_TOKEN — Slack 通知用（必要な場合）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
   - OpenAI（ニュース・レジーム判定で使用）
     - OPENAI_API_KEY — OpenAI API キー（関数呼び出しで引数に渡すことも可能）
   - その他:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live。デフォルトは development）
     - LOG_LEVEL（DEBUG / INFO / ...。デフォルトは INFO）

   これらはプロジェクトルートの `.env` / `.env.local` から自動読み込みされます（.git または pyproject.toml をプロジェクトルート検出）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

4. DuckDB 用ディレクトリの準備（必要であれば）
   - デフォルトの DB パスが `data/kabusys.duckdb` なので親ディレクトリ `data/` を作成しておくと便利です。

---

## 使い方（代表的な利用例）

以下は Python からの利用例です。実行前に必要な環境変数（特に API キー類）を設定してください。

- 基本的な接続と ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを生成（OpenAI API キーを環境変数か引数で与える）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 例: target_date に対する前日15:00JST〜当日08:30JST の記事をスコア
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None -> ENV OPENAI_API_KEY を参照
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用 DB 初期化（監査専用 DB を分けたい場合）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.sqlite_path)  # Path or ":memory:"
  ```

- J-Quants クライアントを直接使う（トークン取得やフェッチ）
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  quotes = fetch_daily_quotes(id_token=id_token, date_from=..., date_to=...)
  ```

- データ品質チェック
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

注意:
- LLM を呼ぶ機能（news_nlp, regime_detector）は OpenAI API を使用します。API キーは `OPENAI_API_KEY` 環境変数、または関数の `api_key` 引数で渡してください。
- DuckDB の SQL 実行は接続オブジェクトに対して行います。既存の DB スキーマ（raw_prices / raw_financials / market_calendar / raw_news / news_symbols / ai_scores / market_regime 等）が必要です。ETL や save_* 関数はテーブル定義が前提です（プロジェクトにスキーマ初期化ユーティリティがある場合はそれを使ってください）。

---

## 環境変数（重要なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- SLACK_BOT_TOKEN — Slack 通知トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp/regime_detector 用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite/監査 DB パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

.env や .env.local にこれらを記載しておくと便利です（config モジュールが自動で読み込みます）。

---

## 注意点 / 実運用に関する補助情報

- .env 自動読み込みの振る舞い
  - プロジェクトルートは .git または pyproject.toml を基準に探索します。
  - 読み込み順序: OS 環境 > .env.local > .env
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- LLM の呼び出しはリトライとフェイルセーフを備えていますが、API 呼び出し回数はコストに直結します。運用時はバッチ化やレート管理を検討してください。
- J-Quants API はレート制限があります（コード内で制御）。大規模取得時は注意してください。
- DuckDB テーブルのスキーマは本コード中の保存関数の想定に基づきます。新規環境ではスキーマ初期化が必要です（プロジェクトに schema 初期化用のスクリプトがある場合はそれを利用）。

---

## ディレクトリ構成（主要ファイル）

以下は主要なモジュールの構成（src/kabusys 以下）です。各ファイルに機能単位で実装があります。

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント + 保存関数
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL インターフェース再エクスポート
    - calendar_management.py          — マーケットカレンダー管理
    - news_collector.py               — RSS ニュース収集
    - stats.py                        — 統計ユーティリティ（zscore_normalize）
    - quality.py                      — データ品質チェック
    - audit.py                        — 監査ログ（テーブル初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py              — ファクター計算（momentum, value, volatility）
    - feature_exploration.py          — forward returns, IC, rank, summary
  - ai/（一部は上に記載）
  - research/（上に記載）

パッケージルートは `src/` 配下にあります（セットアップ時に注意してください）。

---

## 開発時のヒント

- テストや一時実行で .env 自動ロードを無効にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し等をモックしたい場合、モジュール内の _call_openai_api などを unittest.mock.patch で差し替え可能です（コードでそのように想定されています）。
- DuckDB の executemany は空リストを渡せない箇所があるため、呼び出し前に空チェックが必要です（pipeline 等で既に考慮済み）。

---

必要であれば、README に使い方のサンプルスクリプト（ETL バッチ / ニュース集約ジョブ / 監査 DB 初期化など）を追加します。どのユースケースのサンプルが欲しいか教えてください。