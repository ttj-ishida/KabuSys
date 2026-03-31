# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。ETL、ニュースNLP、ファクター計算、監査ログ、J-Quants / kabu ステーション連携など、バックテスト・運用に必要な共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータパイプラインと研究/運用コンポーネントを含むモジュール群です。主な目的は次のとおりです。

- J-Quants API を使った株価・財務・マーケットカレンダーの差分 ETL
- RSS ニュース収集・前処理、および OpenAI を使った記事・銘柄ごとのセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースを統合）
- ファクター（モメンタム／バリュー／ボラティリティ等）の計算・探索用ユーティリティ
- DuckDB を用いたデータ保存・品質チェック・監査ログテーブル初期化
- kabu ステーション経由の実行・監視（モジュール分割済み）

設計上の方針として、ルックアヘッドバイアスを避けるために日付参照は明示的に行い、外部 API 呼び出しは適切にリトライ・フェイルセーフしています。

---

## 主な機能一覧

- data
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch, save）
  - ニュース収集（RSS）と前処理（SSRF 対策・トラッキングパラメータ除去）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）
  - 監査ログテーブル初期化（signal_events / order_requests / executions）
- ai
  - ニュース NLP（score_news：銘柄ごとのセンチメント）
  - 市場レジーム判定（score_regime：ETF MA とマクロセンチメントの合成）
  - OpenAI 呼び出しは JSON モード／リトライ実装
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
  - 統計ユーティリティ（zscore_normalize）
- config
  - 環境変数管理（.env / .env.local の自動読み込み、必須変数検査）
- data.audit
  - 監査 DB の初期化ユーティリティ（init_audit_schema / init_audit_db）

---

## セットアップ手順

以下はローカル開発環境での一般的な手順の例です。

1. Python 環境の準備（推奨: 3.10+）
   - pyenv / venv 等で仮想環境を作ることを推奨します。

2. リポジトリをクローンしてパッケージをインストール
   - 開発中であれば editable インストールが便利です:
     ```
     python -m pip install -e .
     ```
   - 実際の依存パッケージは pyproject.toml / requirements を参照してください（本コード断片には依存表が含まれていませんが、実行には duckdb, openai, defusedxml 等が必要です）。

3. 環境変数（.env）を用意する
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能）。
   - 必須環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     ```
   - 任意設定:
     ```
     KABUSYS_ENV=development   # development|paper_trading|live
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```
   - config モジュールは `.git` または `pyproject.toml` の位置からプロジェクトルートを探索して `.env` / `.env.local` を読み込みます。`.env.local` は `.env` の上書きとして読み込まれます。

4. データベース準備
   - DuckDB ファイルはデフォルト `data/kabusys.duckdb`（settings.duckdb_path）になります。必要に応じてパスを `.env` で変更してください。
   - 監査用 DB を独立させたい場合は init_audit_db() を使えます（例は下記）。

---

## 使い方（主要な例）

以降は Python REPL / スクリプトからの利用例です。すべて明示的に DuckDB 接続を渡す設計になっています。

- 簡単な接続と ETL 実行（J-Quants トークンは .env から取得）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY、または引数で渡す）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("scored:", n_written)
  ```

- 市場レジーム判定（1321 の MA とマクロニュースを統合）
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの duckdb 接続オブジェクト
  ```

- ファクター計算・研究用 API
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(res), res[:3])
  ```

注意点:
- OpenAI 関連関数は api_key 引数で明示的にキーを与えるか、環境変数 OPENAI_API_KEY を設定してください。API 呼び出しはリトライとフェイルセーフ（失敗時はスコア=0 にフォールバックなど）を含みます。
- 日付参照は関数引数で渡す設計（datetime.today() 等を内部で参照しない）なので、バックテスト等で安全に使用できます。

---

## 環境変数（主要）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD — kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN — Slack 通知に使用する Bot トークン
  - SLACK_CHANNEL_ID — Slack 通知先チャネル ID
- OpenAI:
  - OPENAI_API_KEY — OpenAI 呼び出しに必要（ai.score_news, ai.score_regime）
- オプション/運用:
  - KABUSYS_ENV — development / paper_trading / live
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — 自動 .env ロードを無効化（テスト用）

.env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` → `.env.local` の順で読み込みます。

---

## ディレクトリ構成（主要ファイルと説明）

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン & エクスポート）
  - config.py — 環境変数管理 (.env 自動読み込み、settings オブジェクト)
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを銘柄別に集約して OpenAI でスコア付与（score_news）
    - regime_detector.py — ETF MA とマクロニュースから市場レジームを判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save / 認証 / rate limiter）
    - pipeline.py — ETL パイプライン（run_daily_etl 他）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 取得・前処理・保存のユーティリティ
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査ログテーブル定義・初期化（signal / order_request / executions）
  - research/
    - __init__.py
    - factor_research.py — モメンタム・バリュー・ボラティリティの計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - research/（その他ファイルはファクター研究用）
  - （将来的に strategy, execution, monitoring などのモジュールを想定）

各モジュールは DuckDB 接続を引数に受け取る設計です（グローバルな DB 接続を隠蔽せず、テスト容易性と明示性を保っています）。

---

## 開発・運用上の注意点

- ルックアヘッドバイアス対策:
  - 日付は関数引数で渡す（内部で date.today() を参照しない設計）。
  - J-Quants 取得データには fetched_at を付与し、いつデータを得たかをトレース可能にしています。
- API 呼び出し:
  - J-Quants はレート制限（120 req/min）をモジュール内で管理します。
  - OpenAI 呼び出しはリトライ・JSON 検証を行い、失敗時はフェイルセーフ動作をします。
- セキュリティ:
  - news_collector は SSRF 対策（ホスト/リダイレクト先のプライベート IP 検査）や XML の安全パーサ（defusedxml）を使っています。
- テスト:
  - 自動 .env 読み込みを防ぎたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
  - OpenAI / ネットワーク呼び出し箇所はモックしやすいように実装（内部呼び出しを差し替え可能）されています。

---

必要に応じて README を拡張して、セットアップの詳細、CI / CD、Docker イメージ例、pyproject/依存一覧、実行スクリプトなどを追加してください。必要があればサンプル .env.example を作成するテンプレートも用意します。どの内容を優先して追加しますか？