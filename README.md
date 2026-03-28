# KabuSys

日本株のデータ基盤・リサーチ・自動売買を想定した内部ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP（OpenAI）、ファクター計算、監査ログなどを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株を対象とした内部システムのライブラリ群です。主な目的は以下：

- J-Quants API を用いたデータ取得（株価日足・財務・マーケットカレンダー等）
- DuckDB を中心としたデータ保存・ETL パイプライン
- ニュース収集（RSS）と LLM を使った銘柄センチメント算出
- 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- 研究用ファクター計算・特徴量解析ユーティリティ
- 監査ログ（signal → order → execution）のスキーマ初期化・管理
- データ品質チェック（欠損／重複／スパイク／日付不整合）

パッケージのルートは `src/kabusys` にあり、各責務ごとにサブパッケージが分割されています。

---

## 機能一覧（主要モジュール）

- kabusys.config
  - 環境変数/.env 自動読み込み、設定プロパティ（J-Quants トークン、OpenAI、DB パス等）
- kabusys.data
  - jquants_client: J-Quants API クライアント（ページネーション、レートリミット、リトライ、保存関数）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - calendar_management: マーケットカレンダー管理・営業日判定
  - news_collector: RSS 収集、前処理、raw_news 保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマ初期化（signal, order_requests, executions）
  - stats: zscore 正規化等の統計ユーティリティ
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM でスコアリングして ai_scores に保存
  - regime_detector.score_regime: MA とマクロセンチメントを合成して market_regime に記録
- kabusys.research
  - factor_research: momentum / value / volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等

---

## 前提 / 必要環境

- Python 3.10+
  - （ソース中で PEP 604 の型記法（`X | Y`）を使用しているため）
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

実際のインストール要件はプロジェクトの packaging / requirements に合わせてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、編集可能インストール（例）:
   - git clone ...
   - cd <repo>
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -e ".[dev]" または必要パッケージを手動でインストール
     - 例: pip install duckdb openai defusedxml

2. 環境変数（.env）を配置
   - プロジェクトルート（.git や pyproject.toml がある階層）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 代表的な環境変数（.env に設定する例）
   - JQUANTS_REFRESH_TOKEN=...      # J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY=...            # OpenAI API キー（news/regime で使用）
   - KABU_API_PASSWORD=...         # kabuステーション API パスワード（発注関連）
   - SLACK_BOT_TOKEN=...           # Slack 通知用トークン
   - SLACK_CHANNEL_ID=...          # Slack 通知先チャンネルID
   - DUCKDB_PATH=data/kabusys.duckdb   # DuckDB ファイルパス（省略可）
   - SQLITE_PATH=data/monitoring.db    # 監視用 SQLite（省略可）
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...      

4. データベース初期化（監査ログ用の例）
   - Python REPL またはスクリプトから:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")  # ディレクトリを自動作成
     - conn.close()

---

## 使い方（例）

以下は基本的な利用例です。各関数は DuckDB 接続（duckdb.connect(...)）を引数に取る設計です。

1. ETL（日次パイプライン）を実行する
   - 例（Python スクリプト）:
     - import duckdb
     - from datetime import date
     - from kabusys.data.pipeline import run_daily_etl
     - from kabusys.config import settings
     - conn = duckdb.connect(str(settings.duckdb_path))
     - result = run_daily_etl(conn, target_date=date(2026,3,20))
     - print(result.to_dict())
     - conn.close()

2. ニューススコアリング（OpenAI を用いる）
   - from datetime import date
   - import duckdb
   - from kabusys.ai.news_nlp import score_news
   - from kabusys.config import settings
   - conn = duckdb.connect(str(settings.duckdb_path))
   - n = score_news(conn, date(2026,3,20))  # api_key 引数を直接与えることも可
   - print("scored:", n)
   - conn.close()
   - 注意: OPENAI_API_KEY を環境変数に入れるか、score_news の api_key に渡す必要があります。

3. 市場レジーム判定
   - from kabusys.ai.regime_detector import score_regime
   - score_regime(conn, date(2026,3,20))  # OpenAI キーは env または引数で

4. ファクター計算 / 研究ユーティリティ
   - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
   - results = calc_momentum(conn, date(2026,3,20))

5. マーケットカレンダー関連
   - from kabusys.data.calendar_management import is_trading_day, next_trading_day
   - is_trading_day(conn, date(2026,3,20))
   - next_trading_day(conn, date(2026,3,19))

6. データ品質チェック
   - from kabusys.data.quality import run_all_checks
   - issues = run_all_checks(conn, target_date=date(2026,3,20))
   - for i in issues: print(i)

注意点:
- LLM 呼び出し（news_nlp / regime_detector）は OpenAI API を使用します。API の失敗時には安全側にフォールバック（スコア 0.0 等）する設計ですが、APIキーの準備は必須です。
- 各モジュールは Look-ahead bias を避ける設計（内部で date.today() を使わない等）になっています。バックテストで使用する場合は ETL で取得した時点のデータだけを使用してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数/.env 管理と Settings
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュース NLP（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             # J-Quants API クライアント（fetch/save 系）
    - pipeline.py                   # ETL パイプライン (run_daily_etl 等)
    - calendar_management.py        # マーケットカレンダー管理
    - news_collector.py             # RSS ニュース収集
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
    - stats.py                      # z-score 等の統計ユーティリティ
    - etl.py                        # ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            # Momentum / Value / Volatility 等
    - feature_exploration.py        # 将来リターン / IC / summary 等
  - research/（その他ファイル）
- pyproject.toml / setup.cfg / requirements.txt（存在する場合）

各ファイルはドメイン別に責務が分かれており、ETL・データ保存は duckdb 接続を渡す形、AI 関連は OpenAI クライアント（または環境変数）を参照して動作します。

---

## 設計上の注意 / 運用メモ

- .env の自動読込
  - プロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を読み込みます。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 環境（KABUSYS_ENV）
  - 有効値: `development`, `paper_trading`, `live`。誤った値は例外になります。

- OpenAI 呼び出し
  - gpt-4o-mini を想定した実装（JSON mode を利用）。API のレスポンスパース失敗やリトライ処理が組み込まれています。
  - テスト時は内部の `_call_openai_api` をモックして差し替える想定。

- J-Quants API
  - レート制限（120 req/min）を守るための RateLimiter とリトライを実装しています。
  - 401 時の自動トークンリフレッシュ機能あり。

---

## 開発・貢献

- コードはモジュールごとに分離され、単体テストが差し替え可能な形（モックしやすい内部関数命名や引数設計）で作られています。
- 新規モジュール追加時は settings に環境変数を追加し、.env.example を更新してください。

---

以上がこのコードベースの概要と基本的な使い方です。README に含めてほしい追加の操作例（CLI スクリプト例、CI の流れ、実データでの注意点など）があれば教えてください。