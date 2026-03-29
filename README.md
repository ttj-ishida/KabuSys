# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。データ収集（J-Quants / RSS）、ETL、データ品質チェック、リサーチ用ファクター計算、AI を使ったニュースセンチメントや市場レジーム判定、監査ログ（発注・約定トレーサビリティ）などを包括的に提供します。

主な用途
- 日次データパイプライン（株価・財務・市場カレンダー）の差分取得・保存
- ニュース収集・NLP による銘柄センチメント算出（OpenAI）
- ファクター計算・特徴量探索・IC 計算（リサーチ用途）
- 市場レジーム判定（ETF + マクロニュースの LLM 判定の融合）
- 監査ログ用スキーマと DuckDB 初期化ユーティリティ

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env 自動読み込み（プロジェクトルートを検出）
  - 必須設定の取得（Settings クラス経由）
- データ収集 / ETL
  - J-Quants API クライアント（差分取得・ページング・トークン自動リフレッシュ・レートリミット）
  - ETL パイプライン（run_daily_etl / 個別ジョブ run_prices_etl, run_financials_etl, run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day）
- ニュース収集・処理
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキング除去）
  - raw_news / news_symbols への冪等保存（実装内）
- AI（OpenAI）連携
  - ニュースセンチメント（score_news: 銘柄ごとの ai_score / sentiment_score）
  - 市場レジーム判定（score_regime: ETF の MA とマクロニュースを統合）
  - JSON Mode / リトライ・バックオフ・フェイルセーフ設計
- リサーチ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合チェック（QualityIssue を返す）
- 監査ログ（Audit）
  - signal_events / order_requests / executions 用の DDL と初期化ヘルパー
  - init_audit_db による DuckDB 初期化（UTC タイムスタンプ設定）
- ユーティリティ
  - DuckDB 用の保存関数（冪等 INSERT/UPDATE）
  - J-Quants 用ユーティリティ変換関数（_to_float / _to_int 等）

---

## セットアップ手順

前提: Python 3.10+（型注釈に | を使用しているため）を想定しています。

1. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

2. 必要パッケージのインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject.toml を用意して `pip install -e .` や `pip install -r requirements.txt` を利用してください。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）に `.env` / `.env.local` を配置すると自動読み込みされます（読み込みは config モジュールで行われます）。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時など）。

   例（`.env`）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

4. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

5. （任意）パッケージ開発インストール
   ```
   pip install -e .
   ```

---

## 使い方（サンプル）

ここでは主要な利用例を示します。実行は Python スクリプトまたは REPL で可能です。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL（日次パイプライン）を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを算出（OpenAI API key 必須）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY が環境変数に設定されていること
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {n_written}")
  ```

- 市場レジーム判定（ETF 1321 + マクロニュース）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査データベース初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants の ID トークンを取得（内部的には settings.jquants_refresh_token を使います）
  ```python
  from kabusys.data.jquants_client import get_id_token

  token = get_id_token()
  ```

- 設定値を参照
  ```python
  from kabusys.config import settings

  print(settings.jquants_refresh_token)  # 必須: 未設定なら ValueError
  print(settings.is_live)
  ```

注意点
- OpenAI 呼び出し関数はリトライ・バックオフやフェイルセーフ設計を組み込んでいますが、API キーや通信環境が必要です。テスト時は内部の _call_openai_api をモックできます。
- ETL / データ操作は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar, raw_news 等）が前提です。初期スキーマが必要な場合はプロジェクトの schema 初期化処理を用意してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用（必須）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLU / レジーム判定等で使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（data/kabusys.duckdb）
- SQLITE_PATH: 監視等の SQLite パス（data/monitoring.db）

.env の自動読み込みについて
- パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を上向きに探索し、見つかれば `.env` と `.env.local` を読み込みます。OS 環境変数が優先されます。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト等で便利です）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートの src/kabusys 以下を要約しています）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースセンチメント（score_news）
    - regime_detector.py      — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント & 保存関数
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETL インターフェース（ETLResult 再エクスポート）
    - news_collector.py       — RSS 収集（SSRF 対策、正規化、保存）
    - calendar_management.py  — マーケットカレンダー管理（営業日判定等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック（欠損・スパイク等）
    - audit.py                — 監査ログDDL / 初期化ヘルパー
  - research/
    - __init__.py
    - factor_research.py      — Momentum / Value / Volatility 等
    - feature_exploration.py  — 将来リターン, IC, rank, summary
  - monitoring/                — 監視関連（README内コードに含まれる可能性あり）
  - strategy/                  — 戦略層（Signal 生成等）※今回コードベースに含まれる関数への参照が想定される

各モジュールには docstring と設計方針が詳細に書かれており、テスト容易性やルックアヘッドバイアス回避、冪等性、フェイルセーフ等に配慮した実装になっています。

---

## 開発・テスト時のヒント

- OpenAI / J-Quants / 外部 HTTP を呼ぶ関数はモック化してユニットテストを作成してください。各モジュールにテスト用差し替えポイント（例えば _call_openai_api を patch する等）が用意されています。
- 自動 .env ロードを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてからインポートしてください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョン（0.10 系）を考慮した実装が随所にあります。テスト環境の DuckDB バージョンに注意してください。
- 監査ログ初期化は init_audit_db で transactional=True にして使うと DDL を一括で原子的に作成できます（呼び出し元がトランザクション中でないことを確認してください）。

---

## 参考（よく使う関数一覧）

- kabusys.config.settings — 設定取得
- kabusys.data.jquants_client.get_id_token(...) — トークン取得
- kabusys.data.jquants_client.fetch_daily_quotes(...) — 株価取得
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL
- kabusys.ai.news_nlp.score_news(...) — ニューススコア算出 & ai_scores 書き込み
- kabusys.ai.regime_detector.score_regime(...) — 市場レジーム判定 & market_regime 書き込み
- kabusys.research.factor_research.calc_momentum(...) — モメンタム算出
- kabusys.research.feature_exploration.calc_forward_returns(...) — 将来リターン

---

もし README に加えてサンプルスクリプト、schema 初期化 SQL、requirements.txt や pyproject.toml を作成する必要があれば、そのテンプレートも作成します。必要な場合は用途（開発用 / 本番用 / docker 化 など）を教えてください。