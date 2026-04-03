# KabuSys

日本株向け自動売買プラットフォームのライブラリ群です。データ取得（J-Quants）、ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログなどのユーティリティを提供します。

主な設計方針は以下です：
- バックテストでのルックアヘッドバイアスを避ける（target_date を明示的に渡す設計）
- DuckDB を中核データストアとして利用（冪等保存・トランザクション制御）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価はフォールバック/リトライを厳密に扱う
- J-Quants API とのやり取りはレート制限・リフレッシュトークン管理・リトライを実装

## 機能一覧
- データ ETL（J-Quants）  
  - 株価（日次 OHLCV）、財務データ、JPX マーケットカレンダーの差分取得と DuckDB への保存（冪等）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等
- データ品質チェック（quality）  
  - 欠損、スパイク、重複、日付不整合の検出
- ニュース収集（news_collector）  
  - RSS 取得、前処理、raw_news への冪等保存、SSRF 対策・トラッキングパラメータ除去
- ニュース NLP（ai.news_nlp）  
  - OpenAI を用いた銘柄別ニュースセンチメントのバッチ評価、ai_scores への書き込み
- 市場レジーム判定（ai.regime_detector）  
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成してレジーム判定（bull/neutral/bear）
- 研究用ユーティリティ（research）  
  - モメンタム / ボラティリティ / バリュー計算、将来リターン、IC 計算、Z スコア正規化
- 監査ログ（data.audit）  
  - signal_events / order_requests / executions 等の監査テーブル初期化と DB ユーティリティ
- J-Quants クライアント（data.jquants_client）  
  - トークン取得、自動リフレッシュ、レート制御、保存ユーティリティ
- 設定管理（config）  
  - .env / .env.local の自動読み込み（プロジェクトルート検出）、Settings オブジェクト経由で環境変数を型安全に取得

## 必要な環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector 用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視設定
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルトは development
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化（テスト等で利用）

config.Settings クラスで上記を取得できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

## セットアップ手順（ローカル開発）
1. Python と仮想環境
   - 推奨: Python 3.10+
   - 仮想環境作成:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. パッケージと依存関係のインストール
   - プロジェクト ルート（src を含むディレクトリ）で:
     - pip install -e .
   - 追加で必要な外部ライブラリ（含まれていれば setup.py / pyproject で指定される想定）:
     - duckdb, openai, defusedxml
     - 例: pip install duckdb openai defusedxml

3. 環境変数設定
   - プロジェクトルートに .env を置くか、OS 環境変数で設定
   - 例 .env:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

   - 自動読み込みは .git または pyproject.toml を基準にプロジェクトルートを検出して行われます。
   - テストで自動読み込みを無効にする場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 初期化（監査DB など）
   - 監査 DB を作る例（ファイル DB /memory 両方可）:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

## 使い方（代表的な例）
以下は Python REPL やスクリプト内での使用例です。

- DuckDB 接続の作成
  from duckdb import connect
  conn = connect(str(settings.duckdb_path))

  ※ settings は kabusys.config.settings を使うと環境変数読み込み済みの Path が取れます。

- 日次 ETL 実行
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日が使われる
  print(result.to_dict())

- ニューススコアリング（1 日分）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect(str(settings.duckdb_path))
  n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う

- 市場レジーム判定（1 日分）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査スキーマ初期化（既存接続に追加）
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect(str(settings.duckdb_path))
  records = calc_momentum(conn, target_date=date(2026,3,20))

注意点:
- OpenAI 呼び出しや J-Quants API はネットワーク/レートの影響を受けます。score_news や score_regime はリトライ・フォールバックロジックを持ちますが、API キーの設定は必須です（例外が発生します）。
- DuckDB の接続はスレッドセーフ性やトランザクション運用に注意して使ってください（モジュール内で BEGIN/COMMIT/ROLLBACK を使う機能あり）。

## 主要モジュールとディレクトリ構成
以下はコードベースの主要ファイルと役割の簡易ツリーです（src/kabusys 配下）。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数/.env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                — ニュースのバッチ NLP スコアリング
    - regime_detector.py         — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          — J-Quants API クライアント / 保存ユーティリティ
    - pipeline.py                — ETL パイプライン（run_daily_etl 等）
    - etl.py                     — ETLResult 再エクスポート
    - calendar_management.py     — JPX カレンダー管理・営業日ユーティリティ
    - news_collector.py          — RSS ニュース収集・前処理
    - quality.py                 — データ品質チェック
    - stats.py                   — 共通統計ユーティリティ（zscore_normalize 等）
    - audit.py                   — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py         — Momentum/Value/Volatility 等の計算
    - feature_exploration.py     — 将来リターン / IC / 統計サマリー
  - monitoring / strategy / execution (パッケージ想定)  — （README の範囲外だが __all__ 等で参照）

（上記ファイルは本リポジトリ内の機能の主要部分を抜粋しています）

## ヒント・運用上の注意
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。CI やテストで手動管理したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を利用してください。
- OpenAI のレスポンスパース失敗や API エラー時は多くの関数が「0.0（中立）」やスキップでフェイルセーフに動作します。ログ（LOG_LEVEL）を適切に上げて検知してください。
- J-Quants API はレート制限が厳格に扱われます（120 req/min）。jquants_client 内で RateLimiter を実装していますが、外部で頻繁に呼び出す場合は考慮してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、本ライブラリは空チェックを行っています。DuckDB のバージョン依存に注意してください。
- すべてのタイムスタンプは UTC を前提とする箇所があります（監査ログ等）。データ格納・比較時の timezone 混在に注意してください。

---

README に記載の例は開発時の導入・運用手順を想定した基本的な使い方です。詳細な API 仕様や追加のユーティリティは各モジュールの docstring を参照してください。必要であれば、README を拡張して CLI コマンド例、CI 設定、デプロイ手順、テスト手順などを追記できます。