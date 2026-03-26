# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants）によるマーケットデータ取得、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注・約定トレーサビリティ）などを含むモジュール群を提供します。

対応 Python バージョン: 3.10+

---

## プロジェクト概要

KabuSys は日本株のデータ取得・前処理・特徴量生成・AIによるニュース分析・市場レジーム判定・監査ログ管理までをカバーする内部ライブラリです。  
主に以下用途で利用されます。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄別 ai_scores）およびマクロセンチメントを用いた市場レジーム判定
- 研究用ファクター計算（Momentum/Value/Volatility 等）と統計ユーティリティ（Z スコア正規化、IC 計算等）
- 監査ログ（signal / order_request / executions）スキーマの初期化・管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）

---

## 主な機能一覧

- data:
  - J-Quants API クライアント（取得 + DuckDB への冪等保存）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS→raw_news、SSRF 対策、トラッキング除去）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）

- ai:
  - ニュースセンチメント解析（score_news: 銘柄別 ai_scores 生成、OpenAI）
  - 市場レジーム判定（score_regime: ETF 1321 MA200 乖離 + マクロセンチメント合成）

- research:
  - ファクター生成（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索・評価（calc_forward_returns, calc_ic, factor_summary, rank）

- config:
  - 環境変数管理（.env / .env.local 自動読み込み、必須チェック）

---

## セットアップ手順

1. リポジトリをクローンして Python 仮想環境を作成（推奨: venv / pyenv）:

   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要なパッケージをインストール（最低限）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml に依存関係を記載してください。

3. 環境変数を用意する（プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます）。
   自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると無効化できます。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabuステーション API ベース URL（省略可能、デフォルト http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack Bot トークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH: SQLite（監視DB）パス（デフォルト data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

   例 `.env`（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=xxx
   OPENAI_API_KEY=sk-xxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマ（監査ログなど）が必要な場合は初期化します（init_audit_db を使用）:
   - Python スクリプト例は下記「使い方」を参照。

---

## 使い方（主要な利用例）

以下はライブラリの代表的な利用方法のサンプルコードです。関数は DuckDB 接続（duckdb.connect(...））を受け取ることが多いです。

- ETL（デイリー実行）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作成）:

  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # 以後、conn を使って監査テーブルにアクセス
  ```

- 研究用ファクター計算:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  print(len(records), "records")
  ```

注意点:
- score_news / score_regime は OpenAI API を呼び出すため、OPENAI_API_KEY が必要です（または api_key を引数で渡す）。
- config.Settings は起動時にプロジェクトルートの `.env` と `.env.local` を自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
- DuckDB に対する INSERT は多くの場合 ON CONFLICT により冪等的に書き込みます。

---

## ディレクトリ構成（抜粋）

src/kabusys 以下の主要ファイル／モジュールと簡易説明:

- __init__.py
  - パッケージエントリ（version / export）

- config.py
  - 環境変数読み込み・管理（.env 自動読み込み、必須チェックを提供する Settings）

- ai/
  - news_nlp.py
    - ニュースの銘柄別センチメント解析 → ai_scores 書き込み
  - regime_detector.py
    - ETF(1321) の MA200 乖離 + マクロニュースセンチメントの合成で market_regime を書き込む

- data/
  - jquants_client.py
    - J-Quants API クライアント（取得 + DuckDB 保存用ユーティリティ）
  - pipeline.py
    - 日次 ETL パイプライン（run_daily_etl 等）
  - calendar_management.py
    - 市場カレンダー管理（営業日判定など）
  - news_collector.py
    - RSS 取得・前処理・raw_news 保存（SSRF 対策・トラッキング除去）
  - quality.py
    - データ品質チェック（欠損 / 重複 / スパイク / 日付不整合）
  - stats.py
    - 汎用統計ユーティリティ（zscore_normalize）
  - audit.py
    - 監査ログ用 DDL / 初期化（signal_events / order_requests / executions）
  - etl.py
    - ETLResult を公開（pipeline.ETLResult の再エクスポート）
  - (その他: pipeline 内に ETL の細かな実装)

- research/
  - factor_research.py
    - Momentum / Value / Volatility / Liquidity 等の計算
  - feature_exploration.py
    - 将来リターン計算 / IC / 統計サマリー / ランク

---

## 環境変数・設定（まとめ）

自動読み込みの優先順位:
- OS 環境変数（最優先）
- .env.local（存在する場合、上書き）
- .env（上書きしない）

自動読み込みの無効化:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な必須環境変数:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

オプション:
- OPENAI_API_KEY（ai モジュール利用時は必須）
- DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL, KABU_API_BASE_URL

設定未提供時は Settings プロパティが ValueError を投げるため、起動前に `.env` を用意してください。

---

## トラブルシューティング

- 「環境変数が設定されていません」エラー:
  - Settings の必須キーが不足しています。`.env` を作成するか OS 環境変数を設定してください。

- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY を設定。ネットワーク問題・レート制限はリトライロジックで一部緩和されますが、API 利用上限に注意してください。

- J-Quants API エラー（401 等）:
  - J-Quants のリフレッシュトークンが無効、または設定が不足しています。get_id_token がトークンを取得します。

- RSS 取得でリダイレクトや内部アドレスに弾かれる:
  - SSRF 対策のため内部アドレスや非 http/https スキームは拒否されます。許容ドメインを使用してください。

---

## ライセンス・コントリビュート

（プロジェクト固有のライセンスやコントリビュート指針をここに記載してください）

---

README は本コードベースの主要機能と利用イメージをまとめたものです。さらに具体的な拡張・運用（デプロイ、監視、CI、バックテスト統合等）はプロジェクト要件に応じて追加してください。