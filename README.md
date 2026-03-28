# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注/約定トレース）などを一貫して提供します。

---

## プロジェクト概要

KabuSys は以下を目的としたモジュール群から構成されます。

- J-Quants API を用いた市場データ（株価日足 / 財務 / 上場情報 / カレンダー）の差分取得と DuckDB への永続化（ETL）
- ニュース収集（RSS）とニュースに対する LLM ベースのセンチメント評価（gpt-4o-mini を想定）
- ETF・マクロニュースを用いた市場レジーム判定（bull/neutral/bear）
- 研究系ユーティリティ（ファクター計算・将来リターン・IC/統計）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）の初期化ユーティリティ
- 設定管理（環境変数 / .env 自動読み込み）

設計上、ルックアヘッドバイアス対策・冪等性・フェイルセーフ（API失敗時のグレースフルな挙動）を重視しています。

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（取得 + 保存、ページネーション / トークン自動リフレッシュ / レート制御 / リトライ）
  - カレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF対策・トラッキング除去・前処理）
  - 品質チェック（欠損 / スパイク / 重複 / 日付整合性）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news: ニュースを銘柄ごとに LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF MA200 とマクロセンチメントを合成して market_regime を作成
- research/
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / ranking）
- config
  - 環境変数管理（.env 自動読み込み、必須キーの検証）
- monitoring / execution / strategy 等の上位モジュール（README のコードベースではエクスポートのみ）

---

## 必要条件 / 依存パッケージ

- Python 3.10 以上（型ヒントの union 演算子 `X | Y` を使用）
- 推奨パッケージ（インストール例は下記参照）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, json, datetime, logging など）

具体的なバージョン管理用の requirements.txt がある場合はそちらを利用してください。無い場合の最低限のインストール例は次項参照。

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要パッケージをインストール（最低限）
   ```
   pip install duckdb openai defusedxml
   ```
   開発用途であれば `pip install -e .` や requirements.txt を用いてください。

4. 環境変数 (.env) を準備  
   プロジェクトルート（.git や pyproject.toml と同じ階層）に `.env` または `.env.local` を置くと自動で読み込まれます（モジュール起動時に自動ロード。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必要な環境変数（主なもの）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（発注関連）
   - SLACK_BOT_TOKEN: Slack 通知用ボットトークン
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）

   .env の例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=yourpassword
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下はライブラリをインポートして使う最小例です。DuckDB のファイルはデフォルトで data/kabusys.duckdb を想定しています（Settings.duckdb_path）。

- Settings（環境変数の利用）
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 必須値は設定されていなければ例外
  ```

- DuckDB 接続を作って ETL を実行（日次ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（AI）を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（発注/約定トレーサビリティ）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

注意点:
- AI 系関数は OpenAI の API キーを引数で渡すか環境変数 OPENAI_API_KEY を設定してください。未指定時は ValueError を送出します。
- run_daily_etl は ETL の各ステップで発生したエラーを結果の ETLResult.errors に蓄え、全体を止めずに継続する設計です。戻り値の has_errors / has_quality_errors を確認して運用判断をしてください。
- .env 自動読み込みはプロジェクトルート検出に基づいて行います。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 主要 API（概要）

- kabusys.config.settings
  - 環境設定（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, DUCKDB_PATH など）
- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult 型を提供
- kabusys.data.jquants_client
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar
  - get_id_token
- kabusys.data.news_collector
  - fetch_rss, ニュースの前処理・保存に関するユーティリティ
- kabusys.data.quality
  - run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
- kabusys.ai.news_nlp.score_news
  - ニュースを銘柄ごとに LLM で評価して ai_scores に保存
- kabusys.ai.regime_detector.score_regime
  - ETF + マクロニュースで市場レジーム判定・market_regime へ保存
- kabusys.data.audit.init_audit_db / init_audit_schema
  - 監査ログスキーマ初期化

---

## ディレクトリ構成（主要ファイル）

プロジェクトのソースは src/kabusys 配下にまとまっています。主要ファイルと役割は次の通りです。

- src/kabusys/__init__.py
  - パッケージのバージョン・公開API定義
- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（自動 .env 読込）
- src/kabusys/data/
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - etl.py — ETL インターフェースエクスポート
  - pipeline.py — ETL パイプラインの主要実装（run_daily_etl 等）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付整合性）
  - audit.py — 監査ログスキーマ定義・初期化（signal/order_request/executions）
  - jquants_client.py — J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
  - news_collector.py — RSS 収集・前処理・SSRF 対策
- src/kabusys/ai/
  - news_nlp.py — ニュース NLP スコアリング（LLM 呼び出し・バッチ処理・結果検証）
  - regime_detector.py — 市場レジーム判定ロジック（ETF MA200 + マクロセンチメント合成）
- src/kabusys/research/
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ / ランク関数 等
  - __init__.py（研究系ユーティリティの公開）
- src/kabusys/ai/__init__.py, src/kabusys/data/__init__.py, src/kabusys/research/__init__.py
  - 各サブパッケージの公開 API 整理

（上記に記載のない小さなユーティリティ関数や内部関数群が各モジュールに含まれます）

---

## 運用上の注意

- Look-ahead バイアス対策として、各モジュールは原則として date.today() や datetime.today() を内部で使わず、明示的に target_date を引数で渡す設計になっています。バッチ実行時は対象日を明示してください。
- OpenAI / J-Quants 等の外部 API 呼び出しにはレート制限や課金が関わります。運用時は API キーの管理、コスト管理を行ってください。
- DuckDB の executemany など一部の実装はバージョン依存の挙動（空リストバインド不可等）を考慮したコードになっています。DuckDB バージョン差異で問題が起きた場合はローカル環境のバージョン確認を行ってください。
- 監査ログは削除しない前提の設計です（データ保持方針に注意）。

---

## 開発/貢献

- コーディング規約・ユニットテスト・CI 等はリポジトリの方針に従ってください（README では省略）。
- 単体テストを行う際、環境変数の自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば、この README に具体的なコマンド例、requirements.txt の推奨内容、あるいはサンプル .env.example ファイルを追加で作成します。どの形式（簡易 / 詳細 / デプロイ手順付き）をご希望か教えてください。