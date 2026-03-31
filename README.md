# KabuSys

日本株向けの自動売買 / データプラットフォームのコアライブラリ。  
ETL（J-Quants からのデータ取得・保存）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数ベースの設定管理（自動でプロジェクトルートの `.env` / `.env.local` を読み込む）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場情報、JPX カレンダー取得
  - レートリミット・リトライ・トークン自動更新対応
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl による統合処理（カレンダー取得→株価→財務→品質チェック）
- ニュース収集・NLP（OpenAI）
  - RSS 収集・前処理（SSRF 対策、トラッキング除去、gzip 対応）
  - ニュースを銘柄別に集約し gpt-4o-mini でセンチメントを算出（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
- 研究用ユーティリティ
  - モメンタム／バリュー／ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化ユーティリティ（DuckDB）

---

## 要件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係が記載されている想定です。

---

## セットアップ手順

1. リポジトリをクローン（パッケージ配布前の開発環境想定）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化
   ```
   python -m venv .venv
   source .venv/bin/activate      # macOS / Linux
   .venv\Scripts\activate         # Windows
   ```

3. 依存ライブラリをインストール
   - 例（pip を使う場合）:
     ```
     pip install duckdb openai defusedxml
     # またはプロジェクト内のパッケージを編集可能インストール
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を配置してください（config モジュールが自動読み込みします）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
     - KABU_API_PASSWORD — kabuステーション API パスワード（発注連携がある場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — 監視通知等で Slack を使う場合
   - DB パス（任意、デフォルトを変更する場合）:
     - DUCKDB_PATH（例: data/kabusys.duckdb）
     - SQLITE_PATH（監視用 DB など）
   - 自動 .env ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB 用ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

注意: ETL / 保存先のテーブルスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, news_symbols, prices_daily 等）はプロジェクト側で用意する必要があります。本リポジトリには監査ログ初期化ユーティリティ（data.audit.init_audit_db 等）を含みますが、フルスキーマは別途用意してください。

---

## 使い方（簡単な例）

以下は基本的な操作例です。各関数は DuckDB 接続（duckdb.connect() の戻り値）を受け取ります。

- DuckDB に接続する（ファイル or メモリ）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))  # settings.duckdb_path は Path オブジェクト
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの NLP スコアを算出して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数で設定するか api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- マクロ + MA200 で市場レジームを判定して market_regime に書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（発注ログ）専用 DB を初期化する
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # init_audit_db は DDL とインデックスを作成します（UTC timezone セット）
  ```

- カレンダー関連ユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  is_open = is_trading_day(conn, date(2026, 3, 20))
  nxt = next_trading_day(conn, date(2026, 3, 20))
  ```

---

## 主要モジュール（簡単な説明）

- kabusys.config
  - プロジェクトルートの .env 自動読み込み（.git / pyproject.toml を起点）
  - settings: 環境変数読み取りラッパー（必須キーは _require で検証）
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- kabusys.data.jquants_client
  - J-Quants API 呼び出し / レート制御 / リクエストリトライ / DuckDB への保存関数

- kabusys.data.pipeline
  - run_daily_etl 等の ETL ワークフロー実装
  - ETLResult（処理結果データクラス）

- kabusys.data.news_collector
  - RSS フィード収集・前処理（SSRF 対策・サイズ制限）

- kabusys.data.quality
  - データ品質チェック（欠損・重複・スパイク・日付不整合）

- kabusys.data.audit
  - 監査テーブル（signal_events / order_requests / executions）初期化

- kabusys.ai.news_nlp
  - 銘柄別ニュースをまとめて OpenAI に投げ、ai_scores を更新（score_news）

- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して市場レジームを判定（score_regime）

- kabusys.research
  - ファクター計算・探索（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic 等）

- kabusys.data.stats
  - zscore_normalize 等の統計ユーティリティ

---

## ディレクトリ構成

例: パッケージの主要ファイル/ディレクトリ
```
src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      calendar_management.py
      news_collector.py
      quality.py
      stats.py
      audit.py
      etl.py
      # ...（他ユーティリティ）
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    research/
      # ...
```

（上記はコードベースの抜粋に基づく主要ファイル一覧です）

---

## 注意事項 / 運用上のポイント

- OpenAI API 呼び出しはコストとレート制限があるため、テストではモックすることを推奨します。コード内で _call_openai_api を patch してテスト可能です。
- DuckDB のテーブルスキーマ（raw_prices, raw_financials, market_calendar, ai_scores, news_symbols など）は ETL/保存処理が期待する構造で事前に作成してください。監査ログ用スキーマは data.audit の init 関数で自動作成できます。
- 自動 .env ロードはプロジェクトルート検出に .git または pyproject.toml を使用します。配布後に別の配置で実行する場合は .env を明示的に読み込むか KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。
- 環境（KABUSYS_ENV）は development / paper_trading / live のいずれかを設定してください。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL。

---

もし README に追加したい「運用手順（cron 例）」「完全な DB スキーマ」「開発向けテスト手順」などがあれば、目的に合わせて追記します。どの部分をより詳しく書きたいか教えてください。