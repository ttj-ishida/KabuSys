# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants / kabuステーション / OpenAI を用いたデータ収集・ETL、ニュースの NLP スコアリング、ファクター計算、監査ログ（発注追跡）などを提供します。

主な設計方針：
- バックテストでのルックアヘッドバイアスを防止する設計
- DuckDB を中心としたローカルデータプラットフォーム
- API 呼び出しはリトライ・レート制御・フェイルセーフを考慮
- ETL / 品質チェックは部分失敗を許容して問題を収集

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理（kabusys.config.settings）
  - 自動でプロジェクトルートの `.env` / `.env.local` をロード（無効化可）
- データ ETL（kabusys.data.pipeline）
  - J-Quants から株価、財務、マーケットカレンダーを差分取得・保存
  - 日次 ETL (`run_daily_etl`) と個別ジョブ（prices / financials / calendar）
- J-Quants API クライアント（kabusys.data.jquants_client）
  - レートリミッタ、リトライ、トークンの自動リフレッシュ、DuckDB への冪等保存
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、前処理、raw_news への保存に向けたユーティリティ
  - SSRF 対策、サイズ制限、トラッキングパラメータ除去等
- データ品質チェック（kabusys.data.quality）
  - 欠損、スパイク、重複、日付整合性などのチェック
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、次/前営業日の検索、カレンダー更新ジョブ
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions のスキーマ初期化・DB 管理
- AI（OpenAI）を用いた NLP
  - ニュースセンチメント（kabusys.ai.news_nlp.score_news）
  - 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン、IC 計算、統計サマリー
- 汎用統計ユーティリティ（kabusys.data.stats.zscore_normalize）

---

## 必要条件 / 依存

- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime, typing 等）

（実際の packaging / requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （またはプロジェクトに requirements.txt があれば pip install -r requirements.txt）
   - 開発インストール: pip install -e .

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を配置すると自動で読み込まれます。
   - 自動ロードを無効にする場合: `export KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
   - 必須環境変数（主な例）
     - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン
     - KABU_API_PASSWORD : kabuステーション API パスワード
     - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID : Slack 通知用
     - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector を使う際）
   - その他オプション:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
     - DUCKDB_PATH (default: data/kabusys.duckdb)
     - SQLITE_PATH (default: data/monitoring.db)
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env のパース仕様は多少柔軟（コメント・export 先頭指定・クォート対応）です。
   - `.env.example` を参考に `.env` を作成してください（プロジェクト内に例ファイルがある想定）。

---

## 使い方（主要な API サンプル）

以下はモジュールを直接インポートして使う例です。実行は Python スクリプト内で行います。

- DuckDB 接続を作成する（デフォルトパスは settings.duckdb_path）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア生成（OpenAI API キーは env または api_key 引数で指定）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を使用
  print(f"scored {written} symbols")
  ```

- 市場レジーム判定（ETF 1321 の MA とマクロ記事を用いる）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログスキーマを初期化（監査専用 DB）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

- 品質チェックを実行
  ```python
  from kabusys.data.quality import run_all_checks

  issues = run_all_checks(conn, target_date=None)
  for issue in issues:
      print(issue.check_name, issue.severity, issue.detail)
  ```

- J-Quants クライアントを直接使ってデータ取得（内部で rate limit 等を適用）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

  id_token = get_id_token()  # settings.jquants_refresh_token を使用
  rows = fetch_daily_quotes(id_token=id_token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

注意:
- AI を呼ぶ関数は OpenAI の API キーが必要です。api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 各関数はルックアヘッドバイアスを避けるため内部で現在日時を参照しない設計（target_date を明示することを推奨）。

---

## 環境変数（主な一覧）

- JQUANTS_REFRESH_TOKEN (必須 for J-Quants)
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (既定: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須 for Slack integration)
- OPENAI_API_KEY (必須 for AI モジュール  または api_key パラメータ)
- DUCKDB_PATH (既定: data/kabusys.duckdb)
- SQLITE_PATH (既定: data/monitoring.db)
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 にすると .env 自動ロードを無効化

---

## ディレクトリ構成（抜粋）

（実際のリポジトリは src/kabusys 配下に配置されています。本節は主要ファイルの一覧）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / 設定読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースの NLP スコアリング
    - regime_detector.py             — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETLResult のエクスポート
    - news_collector.py              — RSS 収集ユーティリティ
    - calendar_management.py         — マーケットカレンダー管理
    - quality.py                     — データ品質チェック
    - stats.py                       — 統計ユーティリティ（zscore 等）
    - audit.py                       — 監査ログ（テーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py             — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py         — forward returns / IC / summary
  - ai, data, research などの補助モジュール

---

## テスト・開発ノート

- 多くの外部依存（ネットワーク API、OpenAI）を含むため、ユニットテストでは外部呼び出しをモックすることを推奨します（コード内にもモックしやすい設計あり）。
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストで環境を切り替える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。

---

## ライセンス / 貢献

この README の末尾はプロジェクトの LICENSE や CONTRIBUTING を参照してください（実際のファイルが存在する場合）。

---

README はここまでです。利用時の具体的なスクリプトや運用手順（データベーススキーマ初期化、Cron / バッチの起動、監視設定など）は運用ポリシーに合わせて追加してください。必要であれば、README に入れるサンプル .env.example や運用チェックリストも作成します。