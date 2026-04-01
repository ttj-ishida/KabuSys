# KabuSys

KabuSys は日本株のデータ取得・ETL、ニュース NLP、ファクター研究、監査ログ、及び市場レジーム判定を備えた日本株自動売買システム向けのライブラリ群です。DuckDB をデータ格納に用い、J-Quants API や RSS/ニュース、OpenAI（LLM）を組み合わせてデータパイプラインと分析を行います。

## 主な機能
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分更新 / バックフィル / ページネーション対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合等のチェック
- ニュース収集
  - RSS を取得・正規化・保存、銘柄との紐付け
  - SSRF 対策、トラッキングパラメータ除去、受信サイズ制限などの安全対策実装
- AI（LLM）連携
  - ニュースごとのセンチメントスコア算出（ai_scores への保存）
  - マクロニュースとETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
  - OpenAI の JSON mode を用いた堅牢な API 呼び出し・リトライ実装
- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマを提供
  - 発注フローのトレーサビリティ確保（UUID ベース、冪等性）
- 研究用ユーティリティ
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- マーケットカレンダー管理
  - JPX カレンダーの差分取得と営業日判定ユーティリティ

## 必要条件・依存関係（想定）
- Python 3.10+
- 主要依存（抜粋）:
  - duckdb
  - openai (OpenAI SDK v1系想定)
  - defusedxml
- その他：標準ライブラリで多くを実装していますが、実行環境に応じて追加パッケージが必要になる場合があります。プロジェクトの requirements.txt があればそちらを参照してください。

## セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   - git clone … && cd project

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 依存パッケージのインストール
   - pip install -r requirements.txt
   - requirements.txt がない場合は少なくとも `duckdb openai defusedxml` をインストールしてください。

4. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると無効化可）。
   - 必須環境変数（主要）:
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD - kabuステーション API パスワード
     - SLACK_BOT_TOKEN - Slack 通知用ボットトークン
     - SLACK_CHANNEL_ID - Slack チャンネル ID
     - OPENAI_API_KEY - OpenAI API キー（AI モジュール利用時）
   - その他（オプション）:
     - KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH, PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG, INFO, WARNING, ERROR, CRITICAL)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=CXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB データベース初期化（監査テーブルなど）
   - Python REPL やスクリプトで:
     ```python
     import kabusys.data.audit as audit
     conn = audit.init_audit_db("data/audit.duckdb")  # ":memory:" も可
     ```
   - もしくは既存の DuckDB 接続に対して `audit.init_audit_schema(conn)` を呼び出してテーブルを追加できます。

## 使い方（主な API 例）

- DuckDB 接続作成例
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを算出して ai_scores テーブルへ保存
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定しておくか、api_key を渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", n_written)
  ```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組み合わせる）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  - OpenAI API キーを関数引数で渡すことも可能（api_key="sk-..."）。

- 監査 DB 初期化（別 DB に監査専用で作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/monitoring_audit.duckdb")
  ```

- マーケットカレンダーユーティリティ
  ```python
  from kabusys.data.calendar_management import is_trading_day, next_trading_day
  from datetime import date

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究系ユーティリティ（ファクター、IC 等）
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic

  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  forward = calc_forward_returns(conn, target_date=date(2026,3,20))
  ic = calc_ic(momentum, forward, factor_col="mom_1m", return_col="fwd_1d")
  ```

注意:
- AI 関連関数は OpenAI のレスポンスに依存するため、API キーと通信環境が必要です。API エラー発生時はフェイルセーフとしてスコアを 0.0 にフォールバックする実装が多く組み込まれています（例: レジーム判定・ニュース NLP）。
- 多くの関数はルックアヘッドバイアスを避ける設計（内部で date.today() を直接参照しない等）になっています。テスト時は target_date を明示的に渡すことを推奨します。

## 自動環境読み込みの仕様
- パッケージはプロジェクトルート（.git または pyproject.toml を探索）を起点に `.env` と `.env.local` を自動で読み込みます。
- 読み込み順: OS 環境 > .env.local > .env
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## 主要な環境変数一覧（まとめ）
- JQUANTS_REFRESH_TOKEN (必須): J-Quants のリフレッシュトークン
- OPENAI_API_KEY (AI 機能利用時必須)
- KABU_API_PASSWORD (kabu API)
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (監視用 DB パス)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT (監視設定)
- KABUSYS_ENV (development, paper_trading, live)
- LOG_LEVEL (DEBUG/INFO/...）

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（センチメント集約・ai_scores 書き込み）
    - regime_detector.py     — 市場レジーム判定（1321 MA200 + マクロセンチメント合成）
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得/保存/認証/リトライ/レート制御）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult の公開
    - news_collector.py      — RSS 収集と raw_news 保存
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore）
    - calendar_management.py — マーケットカレンダー管理
    - audit.py               — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py     — ファクター計算（momentum / volatility / value）
    - feature_exploration.py — 将来リターン / IC / summary / rank
  - ai/、research/、data/ 以下にそれぞれの実装が配置

（ファイルは上記以外にも多数のヘルパー関数・例外処理・ユーティリティを含みます）

## テスト・開発のヒント
- AI 部分の呼び出しは外部 API に依存するため、ユニットテスト時は該当モジュールの内部 API 呼び出し（例: news_nlp._call_openai_api や regime_detector._call_openai_api）をモックしてください。
- DuckDB をファイルではなく ":memory:" に接続するとテストが簡単です。
- .env を自動読み込みするので、CI 環境では必要な環境変数を明示的にセットしてください。

---

ご要望があれば、README に次の情報を追加できます:
- 具体的な requirements.txt（依存パッケージ一覧）
- 実行可能なコマンド例（CLI があれば）
- DB スキーマのサンプル DDL / テーブル一覧
- 運用フロー（ETL スケジュール、監視・アラート設定例）