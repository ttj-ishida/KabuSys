# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータプラットフォーム・リサーチ・AI スコアリング・監査・ETL を含む自動売買基盤のコアライブラリです。本リポジトリは以下の機能群を提供します。

- データ取得・ETL（J-Quants 経由で株価・財務・カレンダー）
- ニュース収集・NLP（OpenAI を用いた銘柄ごとのニュースセンチメント）
- 市場レジーム判定（ETF とマクロニュースの合成）
- ファクター計算・特徴量探索（モメンタム / バリュー / ボラティリティ等）
- データ品質チェック・監査ログ（トレーサビリティ用テーブル）
- 各種ユーティリティ（カレンダー管理、統計ユーティリティ等）

この README ではプロジェクト概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成を日本語でまとめます。

## 主な機能一覧

- ETL パイプライン（daily ETL：株価・財務・市場カレンダーの差分取得と保存）
- J-Quants API クライアント（ページネーション・レート制限・トークン自動更新を含む）
- DuckDB への冪等保存（ON CONFLICT DO UPDATE で重複防止）
- ニュース収集（RSS、SSRF 対策、記事正規化、raw_news 保存）
- ニュース NLP（gpt-4o-mini を用いた銘柄別センチメントスコアリング）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを組み合わせ）
- 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 研究用モジュール（ファクター計算・IC/統計・Zスコア正規化）

## 要件（推奨）

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境によってはさらに sqlite3、urllib 等の標準ライブラリが必要です）

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

3. 必要パッケージをインストール
   - 最低限必要なライブラリをインストールする例:
     ```bash
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージを editable インストールする場合:
     ```bash
     pip install -e .
     ```
     （setup.py / pyproject.toml がある場合はそちらを利用してください）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動ロードされます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須環境変数（例）
   - J-Quants / API:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
   - kabu ステーション:
     - KABU_API_PASSWORD — kabu API のパスワード（必須）
     - KABU_API_BASE_URL — （任意、デフォルト: http://localhost:18080/kabusapi）
   - Slack 通知:
     - SLACK_BOT_TOKEN — Slack ボットトークン（必須）
     - SLACK_CHANNEL_ID — 送信先チャンネル ID（必須）
   - DB パス（デフォルト値あり）:
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — SQLite（監視等）パス（デフォルト: data/monitoring.db）
   - システム:
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
   - OpenAI:
     - OPENAI_API_KEY — OpenAI API キー（ai モジュールを呼び出す時に必要）

   .env のサンプル（プロジェクトルートに .env を作成）:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   KABU_API_PASSWORD=xxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

## 基本的な使い方（サンプル）

以下は Python REPL / スクリプト上での基本的な呼び出し例です。DuckDB 接続を作成して、ETL や NLP、レジーム判定を実行できます。

- DuckDB 接続作成例:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")  # デフォルトのパス
  ```

- 日次 ETL（run_daily_etl）の実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を指定しない場合は今日が対象
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を使う）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
  written = score_news(conn, target_date=date(2026,3,20))
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OpenAI API key は env または api_key 引数で指定
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB の初期化:
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # 必要に応じて監査テーブルに対する操作を行う
  ```

- ファクター計算・リサーチ:
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  target = date(2026,3,20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意点:
- ai モジュール（news_nlp / regime_detector）は OpenAI にリクエストします。テスト時は内部の _call_openai_api をモックできるよう設計されています。
- 各関数はルックアヘッドバイアスを避ける設計（内部で date.today() を参照しない関数が多い）です。バックテスト用途には target_date を正確に指定してください。

## 自動 .env 読み込みの挙動

- 起動時に自動的にプロジェクトルート（.git または pyproject.toml が見つかる場所）を探索し、以下の順で読み込みます:
  1. OS 環境変数（最優先）
  2. .env.local （存在する場合、OS を上書きしない範囲で上書き）
  3. .env
- 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に機能ごとのモジュール群を配置しています。主要部分を抜粋します。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（.env 自動読み込み含む）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（銘柄別センチメントスコアを書き込み）
    - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult エクスポート
    - news_collector.py      — RSS 収集（SSRF 対策・正規化）
    - calendar_management.py — マーケットカレンダー（営業日判定・更新ジョブ）
    - quality.py             — データ品質チェック（欠損・スパイク・重複等）
    - stats.py               — 統計ユーティリティ（Zスコア正規化等）
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility の計算
    - feature_exploration.py — 将来リターン計算、IC、統計サマリー
  - research/*               — 研究用ユーティリティ群

各モジュールは DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取り、DB 上のテーブルを参照／更新する設計が中心です。

## 開発・テストについて（補足）

- OpenAI 呼び出しや外部 API 呼び出しは内部で抽象化されており、ユニットテストでは該当関数（例: news_nlp._call_openai_api、regime_detector._call_openai_api、news_collector._urlopen）をモックしてテストできます。
- DuckDB はインメモリ（":memory:"）でのテスト実行に対応しているため、テスト用の DB を用意して処理の検証が容易です。
- ETL や API 呼び出しはリトライ／レート制御を組み込んでいますが、実運用では API レートや鍵の管理に注意してください。

## 想定される発展・注意点

- 本ライブラリは「データ取得・解析・監査」の基盤部分を提供することを意図しており、実際の発注ロジック（broker 接続／kabu ステーションへの送信）やフル運用監視は別モジュール・運用スクリプト側で構築する想定です。
- "live" 環境での稼働時は十分な安全チェック（発注前のリスク管理、二重送信防止、テストカバレッジ）を行ってください。

---

不明点や README の補足希望（例: より詳細な .env.example、サンプル DB スキーマ、運用手順）などあれば教えてください。必要に応じて README を拡張します。