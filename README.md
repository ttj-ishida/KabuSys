# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
DuckDB を用いたデータプラットフォーム、J-Quants からの ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つモジュール群です。

- J-Quants API から株価・財務・市場カレンダーなどを差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と前処理（raw_news）
- OpenAI を利用したニュースのセンチメント解析（銘柄ごとの ai_score）およびマクロセンチメントによる市場レジーム判定
- 研究用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 発注から約定までの監査ログ（audit テーブル群）
- 環境設定管理（.env 自動ロード、環境変数アクセス）

設計上の特徴：
- ルックアヘッドバイアス対策（date.now の無自覚参照を避けるなど）
- 冪等性（DB 保存は ON CONFLICT / DELETE → INSERT で置換）
- 外部 API 呼び出しに対するリトライとレート制御
- テスト容易性（API 呼び出し箇所の差し替えを想定した実装）

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）
- ニュース
  - RSS 収集（kabusys.data.news_collector）
  - OpenAI を用いたニュースセンチメント（kabusys.ai.news_nlp）
  - 市場レジーム判定（kabusys.ai.regime_detector）
- 研究（Research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC・統計サマリ（kabusys.research）
- データユーティリティ
  - カレンダー管理（is_trading_day, next_trading_day 等）
  - データ品質チェック（kabusys.data.quality）
  - 統計ユーティリティ（zscore_normalize）
- 監査（audit）
  - 監査テーブル初期化 / 専用 DB 初期化（kabusys.data.audit）
- 設定管理
  - 環境変数・.env 自動ロード（kabusys.config.Settings）

---

## 必要条件 / 前提

- Python 3.10 以上（PEP 604 の型記法や typing の利用のため）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（OpenAI API を使う場合）
- defusedxml（RSS パース時の安全対策）
- （任意）その他標準ライブラリのみで HTTP は urllib を使用

推奨インストールパッケージ（最低限）:
- duckdb
- openai
- defusedxml

例:
pip install duckdb openai defusedxml

プロジェクトをパッケージとして開発環境に追加するには:
pip install -e .

（requirements.txt がある場合はそれに従ってください）

---

## 環境変数（主なもの）

KabuSys は .env / .env.local をプロジェクトルートから自動読み込みします（優先度: OS 環境 > .env.local > .env）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な環境変数:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite パス（監視用, デフォルト: data/monitoring.db）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を実行する場合）
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト development
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

.env の例（.env.example があればそれを参照）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）

1. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   pip install -e .
   pip install duckdb openai defusedxml

   （プロジェクトが requirements.txt を提供していればそれを使用）

3. プロジェクトルートに .env を作成（.env.example を参考に）
   - 必須トークン・キー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY）を設定

4. DuckDB 用ディレクトリを作成（必要なら）
   mkdir -p data

5. 監査用 DB を初期化（任意）
   Python REPL またはスクリプトで:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")

---

## 使い方（代表的な呼び出し例）

下記は Python スクリプト / REPL から直接利用する例です。各関数は duckdb.DuckDBPyConnection を受け取るため、まず接続を生成してください。

- DuckDB 接続作成（例: settings に従う）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニューススコアを付ける（OpenAI 必須）
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  # api_key を明示するか環境変数 OPENAI_API_KEY を設定
  num_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {num_written}")

- 市場レジーム判定（OpenAI 必須）
  from kabusys.ai.regime_detector import score_regime
  res = score_regime(conn, target_date=date(2026, 3, 20))
  print("score_regime result:", res)

- ファクター計算（研究用）
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))

- 監査スキーマの初期化（既存接続へ）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

ログレベルは環境変数 LOG_LEVEL で制御します。実行環境（paper_trading/live）は KABUSYS_ENV で切り替えます。

注意事項:
- score_news / score_regime は OpenAI API を呼びます。API キーを必ず設定してください（引数 api_key で直接渡すことも可）。
- ETL / J-Quants クライアントはネットワーク IO を伴いリトライやレート制御を行います。API キー切れ等はログに出力されます。
- データベース操作は DuckDB を想定しています。ファイルパスを変更したい場合は DUCKDB_PATH を設定してください。

---

## ディレクトリ構成（主なファイルとモジュール）

src/kabusys/
- __init__.py
- config.py
  - 環境変数の読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py          — ニュースの NLP スコアリング（OpenAI）
  - regime_detector.py   — マクロ + MA を使った市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py    — J-Quants API クライアント（取得・保存）
  - pipeline.py          — ETL パイプライン（run_daily_etl 等）
  - etl.py               — ETLResult 再エクスポート
  - news_collector.py    — RSS ニュース収集
  - quality.py           — データ品質チェック
  - stats.py             — 統計ユーティリティ（z-score）
  - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
  - audit.py             — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py   — Momentum / Value / Volatility 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- ai/ (上記)
- research/ (上記)
- その他: strategy / execution / monitoring 等はパッケージ公開用に __all__ が定義されています（将来的な拡張領域）

---

## 運用上の注意点

- 環境変数は機密情報です。公開リポジトリに .env をコミットしないでください。
- OpenAI 呼び出しはエラー時にフォールバック（0.0 など）を取る箇所があり、完全失敗でもシステム全体が停止しない設計です。ただし品質や結果を確認してください。
- J-Quants API のレート制限を尊重していますが、長時間の大量呼び出しには注意してください。
- DuckDB executemany は空のパラメータリストを受け付けないバージョン制約への対処が各所で実装されています（0.10 系など）。DuckDB のバージョン互換性に注意してください。

---

## コントリビュート / テスト

- 追加機能やバグ修正はプルリクエストで受け付けてください。ユニットテストを追加していただけると助かります。
- 外部 API 呼び出し箇所（OpenAI / J-Quants / RSS）には差し替え可能な内部ラッパーがあるため、モックによる単体テストが容易にできます。

---

必要であれば README に下記を追加できます（ご希望を教えてください）:
- より詳細な .env.example（実際のキー名と説明）
- 実運用のデプロイ手順（systemd / Docker / Kubernetes 例）
- 典型的な DAG / バッチスケジューラ構成（Airflow / cron）
- 各テーブルのスキーマ（DDL 抜粋）

以上。必要に応じてサンプル .env.example や運用スクリプト例を作成しますか？