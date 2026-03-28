# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。J-Quants や RSS、OpenAI を利用してデータ収集（ETL）、データ品質チェック、ニュースセンチメント、マーケットレジーム判定、ファクター計算、監査ログ管理などを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（API失敗時の安全動作）」「外部サービスへの過度な依存を避ける（ETL と Research は発注系 API にアクセスしない）」です。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証（settings オブジェクト経由）
- データ ETL（J-Quants）
  - 日次株価（OHLCV）取得・保存（ページネーション対応・レートリミット対応・冪等保存）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - ETL の差分更新・バックフィル・品質チェック（欠損、重複、スパイク、日付不整合）
  - ETL 結果を表す ETLResult
- ニュース収集 / NLP
  - RSS 収集（SSRF 対策、サイズ制限、トラッキングパラメータ削除、正規化）
  - OpenAI を用いた銘柄別ニュースセンチメント（batch / JSON mode、リトライ、バリデーション）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメント混合）
- Research / Factor
  - モメンタム・ボラティリティ・バリューなどのファクター計算（DuckDB SQL ベース）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ
- データ品質管理
  - 各種品質チェック（欠損、スパイク、重複、日付不整合）
  - QualityIssue オブジェクトで問題を収集
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブルを初期化・管理
  - 監査用 DuckDB 初期化ユーティリティ（UTC タイムゾーン固定、冪等 DDL）
- ユーティリティ
  - J-Quants クライアント（リトライ、トークン自動リフレッシュ、レート制御）
  - DuckDB 保存用の効率的な executemany 実装

---

## セットアップ手順

前提:
- Python 3.10+（typing の union などを使用）
- DuckDB, openai クライアント等の依存パッケージ

1. リポジトリを取得（例）
   - git clone ...

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（例）
   - pip install -e .            # パッケージを開発モードでインストール
   - pip install duckdb openai defusedxml

   （プロジェクトの requirements.txt / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数を設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を置くと自動的に読み込まれます。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途）。

   最低限必要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key  （OpenAI を使う機能を利用する場合）
   - （任意）DUCKDB_PATH=data/kabusys.duckdb
   - （任意）SQLITE_PATH=data/monitoring.db
   - （任意）KABUSYS_ENV=development|paper_trading|live
   - （任意）LOG_LEVEL=DEBUG|INFO|WARNING|ERROR|CRITICAL

   例 .env（簡易）
   ```
   JQUANTS_REFRESH_TOKEN=...
   OPENAI_API_KEY=...
   SLACK_BOT_TOKEN=...
   SLACK_CHANNEL_ID=...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. データベースフォルダ作成（必要なら）
   - デフォルトの DUCKDB パスは `data/kabusys.duckdb`。親ディレクトリがなければ自動作成される場合がありますが、必要に応じて `mkdir -p data`。

---

## 使い方（基本的な例）

以下はコードでの利用例です。各 API は duckdb 接続や target_date（date オブジェクト）を受け取ります。内部で datetime.today() / date.today() を直接参照しない設計なので、バッチ処理やバックテストで明示的に日付を渡すことが推奨されています。

- 共通インポート例
  ```python
  import duckdb
  from datetime import date
  from kabusys.config import settings
  ```

- DuckDB 接続
  ```python
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを生成して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written: {written}")
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの混合）
  ```python
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- ファクター計算（例: モメンタム）
  ```python
  from kabusys.research.factor_research import calc_momentum

  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  # records: list of dict {"date","code","mom_1m","mom_3m","mom_6m","ma200_dev"}
  ```

- 将来リターン / IC / サマリー
  ```python
  from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary

  fwd = calc_forward_returns(conn, target_date=date(2026,3,20))
  # 結果を factor_records と結合して calc_ic を使う
  ```

- 監査ログ用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # audit_conn を使って監査テーブルにアクセス
  ```

- カレンダー更新ジョブ（夜間バッチ）
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  calendar_update_job(conn)
  ```

- RSS 取得（単体テスト / 独自収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  ```

注意点:
- OpenAI を呼ぶ関数は API キーを引数で渡すことが可能です（api_key 引数）。None の場合は環境変数 `OPENAI_API_KEY` を参照します。テスト時は内部の _call_openai_api をモックして差し替え可能です。
- ETL / News / Regime 判定はルックアヘッドバイアス対策のため、target_date 未満のみ参照する設計です。バックテストでは適切な日付管理を行ってください。
- DuckDB の executemany は空リストを受け付けないバージョンの挙動に配慮して、空チェックが組み込まれています。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード（発注周り）
- KABU_API_BASE_URL (任意) — kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー（news_nlp / regime_detector 等）
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — monitoring 用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env 読み込みを無効化

---

## ディレクトリ構成

主要ファイル / モジュール:

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースの LLM スコアリング、score_news
    - regime_detector.py            — マクロ + ETF MA200 を使った市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch/save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETLResult の公開再エクスポート
    - news_collector.py             — RSS 収集・正規化・保存ロジック
    - calendar_management.py        — マーケットカレンダーと営業日ロジック
    - quality.py                    — データ品質チェック（欠損・スパイク等）
    - stats.py                      — z-score 正規化 等の統計ユーティリティ
    - audit.py                      — 監査ログテーブルの DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum/value/volatility のファクター計算
    - feature_exploration.py        — forward returns / IC / summary / rank
  - (その他)
    - research/ 以下は研究用機能で、価格データに対する解析を行うが発注などの副作用は持たない

この README に記載した API 名・関数名はコードベースと一致します。詳細は各モジュールのドキュメント（docstring）を参照してください。

---

## 開発・テストに関するヒント

- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml がある場所）を起点に行われます。テストで環境を分離したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部でリトライ処理を持ちますが、ユニットテストでは _call_openai_api をモックしてレスポンスを制御してください（news_nlp/regime_detector の docstring に記載あり）。
- DuckDB を使ったテストは ":memory:" を渡してインメモリ DB で実行できます（init_audit_db などは ":memory:" をサポート）。

---

必要であれば README を拡張して、より具体的な API リファレンスや運用フロー（ETL スケジューリング例、Slack 通知フロー、発注監査フローなど）を追加できます。どの部分を詳しく説明したいか教えてください。