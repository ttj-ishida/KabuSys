# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータプラットフォームと自動売買（リサーチ・ETL・監査ログ・AI スコアリング）を支援する Python パッケージです。DuckDB をデータレイヤに、J-Quants API / RSS / OpenAI（LLM） を外部ソースとして利用し、ETL・データ品質チェック・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログ管理などの機能を提供します。

---

## 主要機能

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分取得、ページネーション、認証トークン自動リフレッシュ、レート制御、リトライ付き
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェックをまとめて実行
- ニュース収集 & 前処理
  - RSS フィードの取得、URL 正規化、前処理、SSRF 対策、サイズ制限
- AI ベースのニュースセンチメント
  - OpenAI（gpt-4o-mini を想定）を使った銘柄別ニューススコアリング（ai_scores）
  - マクロニュースの LLM 評価と ETF MA200 乖離を組み合わせた市場レジーム判定
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（Information Coefficient）、ファクターの統計サマリー
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までの追跡可能な監査テーブル（UUID ベースの冪等性）
- カレンダー管理（JPX カレンダー）: 営業日判定、next/prev 営業日取得など

---

## 必要条件（推奨）

- Python 3.9+
- パッケージ依存（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリのみで動作する部分も多いですが、AI／DB／XML 関連機能を使うには上記が必要です。

例:
pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを参照してください）

---

## 環境変数 / 設定

KabuSys はプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN: Slack 通知用 Bot Token
- SLACK_CHANNEL_ID: Slack 投稿先チャンネルID
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）

任意 / デフォルト設定:
- KABUSYS_ENV: 実行環境。`development`（デフォルト） / `paper_trading` / `live`
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1: 自動 .env 読み込みを無効化

.env の例（`.env.example` を参考に作成してください）:
export JQUANTS_REFRESH_TOKEN=xxxxxxxx
export OPENAI_API_KEY=sk-xxxxxxx
export SLACK_BOT_TOKEN=xoxb-...
export SLACK_CHANNEL_ID=C01234567
export KABU_API_PASSWORD=your_kabu_password
export KABUSYS_ENV=development
export LOG_LEVEL=INFO

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml / requirements.txt があればそれを利用）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境に設定してください。
   - 自動読み込みを無効にしたいテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB ファイルや監査 DB の初期化（必要に応じて）
   - 監査 DB を初期化する例は下記を参照

---

## 使い方（代表的な例）

以下は Python REPL / スクリプトからの利用例です。各例では既に必要な環境変数が設定されている前提です。

- DuckDB に接続して日次 ETL を実行する（run_daily_etl）
  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # target_date を指定しないと今日が対象（内部で調整あり）
  print(result.to_dict())
  ```

- ニュースセンチメント（指定日）をスコアリングして ai_scores に書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定（ma200 + マクロニュース）を実行
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化して接続を得る
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events, order_requests, executions が作成される
  ```

- RSS フィードを取得して raw_news に保存する処理は news_collector を利用（保存ロジックを呼び出す部分は実装例を参照）
  - fetch_rss(url, source) で記事リストが得られます

注意点:
- バックテストや研究用途では Look-ahead Bias に注意。多くの機能が「target_date 未満のみを参照」「取得日時（fetched_at）を記録」など Look-ahead を避ける設計になっています。API 呼び出しをバックテストの内部ループから直接行わないでください。
- OpenAI 呼び出しは API 費用が発生します。API キー・コスト管理に注意してください。

---

## よく使う API / 関数一覧

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(...)
- データ品質
  - kabusys.data.quality.run_all_checks(...)
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
- ニュース / AI
  - kabusys.data.news_collector.fetch_rss(...)
  - kabusys.ai.news_nlp.score_news(...)
  - kabusys.ai.regime_detector.score_regime(...)
- 研究
  - kabusys.research.calc_momentum(...)
  - kabusys.research.calc_volatility(...)
  - kabusys.research.calc_value(...)
  - kabusys.research.calc_forward_returns(...)
  - kabusys.research.calc_ic(...)
  - kabusys.research.factor_summary(...)

---

## ログと環境（動作モード）

- KABUSYS_ENV: development / paper_trading / live
  - settings.is_dev / is_paper / is_live で判定可能
- LOG_LEVEL 環境変数でログレベルを制御（デフォルト INFO）

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
  - パッケージのバージョンとサブモジュール公開

- config.py
  - 環境変数の読み込みと Settings クラス（.env 自動読み込み、必須変数チェック）

- ai/
  - news_nlp.py : 銘柄別ニュースセンチメントの LLM スコアリング（ai_scores へ書き込み）
  - regime_detector.py : ETF（1321）MA200 乖離 + マクロニュース LLM による市場レジーム判定

- data/
  - pipeline.py : 日次 ETL のオーケストレーション（run_daily_etl 等）
  - jquants_client.py : J-Quants API クライアント（取得・保存・認証・レート制御）
  - news_collector.py : RSS の取得・前処理・記事ID生成・SSRF対策
  - calendar_management.py : JPX カレンダー管理・営業日判定・calendar_update_job
  - quality.py : データ品質チェック群
  - stats.py : z-score 正規化など統計ユーティリティ
  - audit.py : 監査テーブルの DDL / 初期化 / init_audit_db
  - etl.py : ETLResult の再エクスポート

- research/
  - factor_research.py : モメンタム / バリュー / ボラティリティ等ファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、ランク関数
  - __init__.py : 研究用途のユーティリティ再エクスポート

- research パッケージを中心に、Data と AI が連携する設計になっています。

---

## テスト / 開発時のヒント

- .env 自動読み込みを無効にする: テスト環境で明示的に環境を作る場合 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- OpenAI / J-Quants 呼び出しは外部 API に依存するため、ユニットテストでは各モジュールの `_call_openai_api` / jquants_client._request など内部関数をモックする設計になっています。
- DuckDB はインメモリ（":memory:"）でも動作するため、テスト時はインメモリ DB を利用すると簡単に初期化できます。

---

## 注意事項 / 制約

- 実際の発注（kabu ステーション等）やライブ運用モジュールは本コードベースの一部に含まれますが、実際に本番口座で実行する場合はリスク管理・監査・ヒューマンレビューが必須です。
- LLM を利用する箇所は API コストと利用制限（レート・出力フォーマット）を考慮してください。レスポンスが期待通りでない場合はフォールバック（0.0 スコア等）する実装です。
- データ整合性・品質チェックは ETL 後に実行されます。品質の重大な問題が検出された場合は運用ルールに従ってください。

---

必要に応じて README を拡張します。特定の機能（例: news_collector の DB 保存手順、kabu 発注インターフェース、CI/テスト手順など）について詳細が必要であれば教えてください。