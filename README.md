# KabuSys

日本株向けのデータプラットフォーム兼自動売買補助ライブラリです。  
J-Quants / JPX を利用したデータ取得・ETL、ニュース収集とLLMによるセンチメント評価、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）等を備えたユーティリティ群を提供します。

主な想定用途:
- 日次のデータETL（株価・財務・マーケットカレンダー）
- ニュースに基づく銘柄センチメント評価（OpenAI）
- 市場レジーム判定（MA200 + マクロニュース）
- 研究用ファクター計算・統計解析
- 発注〜約定までの監査ログスキーマ初期化・管理

対応言語 / ランタイム:
- Python 3.10+

---

## 機能一覧

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務、上場情報、マーケットカレンダー）
  - 差分取得・ページネーション対応・トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- データ品質管理
  - 欠損チェック、スパイク検出、重複検出、日付整合性チェック
  - run_all_checks による一括実行
- ニュース収集
  - RSS フィード取得（SSRF リダイレクト保護、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存（設計により記事IDは正規化URLのハッシュ）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（gpt-4o-mini, JSON Mode）
  - チャンクバッチ、リトライ、レスポンス検証
- 市場レジーム判定
  - ETF(1321) の 200日MA乖離（重み70%）＋マクロニュースセンチメント（重み30%）で日次レジームを算出
  - レジームは 'bull' / 'neutral' / 'bear'
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン、IC（スピアマンランク相関）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル DDL とインデックスを提供
  - init_audit_db で DuckDB を初期化
- 設定管理
  - .env / .env.local / 環境変数読み込み、自動ロード機能（無効化フラグあり）

---

## 要件（主な依存）

必須
- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

その他（プロジェクトに応じて）
- requests 等（外部モジュール追加がある場合）

インストール例（仮の requirements.txt を使う場合）:
pip install duckdb openai defusedxml

プロジェクト配布が pip パッケージ化されている場合:
pip install -e .

---

## 環境変数（必須 / 重要）

以下はコード内で参照される主な環境変数です。テスト・運用環境に応じて .env/.env.local に設定してください。

必須（実行する機能により異なる）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（fetch / get_id_token 用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注等を実装する場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知に使用

データベース・監視系（デフォルトが用意されています）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH: 実行プロセスの PID ファイル（デフォルト: data/execution.pid）

その他
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）

自動.envロード:
- .env と .env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先）。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（概略）

1. Python 3.10+ の仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. 環境変数を用意
   - リポジトリルートに .env（または .env.local）を作成
   - 例 (.env):
     JQUANTS_REFRESH_TOKEN=あなたのリフレッシュトークン
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO

4. DuckDB を作成・監査ログスキーマ初期化（任意）
   - Python から init_audit_db を呼ぶ（下記「使い方」を参照）

---

## 基本的な使い方（例）

以下は Python スクリプトや REPL での簡単な利用例です。

共通インポート:
from datetime import date
import duckdb
from kabusys.config import settings

DuckDB 接続例:
conn = duckdb.connect(str(settings.duckdb_path))

1) ETL（日次パイプライン）を実行する
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())

2) ニュースのセンチメントスコアを算出して ai_scores に書き込む
from kabusys.ai.news_nlp import score_news
n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # api_key=None なら OPENAI_API_KEY を使用

3) 市場レジーム判定（market_regime テーブルへの書込み）
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key=None)

4) 監査DBの初期化
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" でインメモリ可

5) カレンダー関係のユーティリティ
from kabusys.data.calendar_management import is_trading_day, next_trading_day
is_trading = is_trading_day(conn, date(2026,3,20))
next_day = next_trading_day(conn, date(2026,3,20))

6) ファクター計算・研究用ユーティリティ
from kabusys.research import calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic
mom = calc_momentum(conn, date(2026,3,20))
fwd = calc_forward_returns(conn, date(2026,3,20))
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")

---

## 注意点 / 実装上の方針（開発者向け）

- Look-ahead バイアス防止:
  - 各種モジュールは target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない実装方針です。バックテスト時には明示的な日付を渡してください。
- 冪等性:
  - ETL → DuckDB への保存は ON CONFLICT DO UPDATE 等で冪等に設計されています。
- 外部API呼び出し:
  - J-Quants と OpenAI 呼び出しはリトライ・バックオフを備えています。401 は token refresh 対応（J-Quants）。
- セキュリティ:
  - RSS 収集は SSRF 対策（リダイレクト検査、プライベートアドレスブロック）や XML インジェクション対策（defusedxml）を実装しています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - (その他 jquants_client に依存するサブモジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/ (コードベースに含まれる想定の監視関連モジュール等)
- strategy/, execution/ (パッケージトップで __all__ に含まれている想定モジュール)

※ 上記はリポジトリ内の主要モジュールを抜粋した一覧です。実際のファイルツリーはプロジェクトルートを参照してください。

---

## よくある操作コマンド（例）

- Python REPL で ETL 実行:
  python -c "from datetime import date; import duckdb; from kabusys.config import settings; from kabusys.data.pipeline import run_daily_etl; c=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(c, date(2026,3,20)).to_dict())"

- 監査DB初期化（スクリプト）:
  python -c "from kabusys.config import settings; from kabusys.data.audit import init_audit_db; init_audit_db(settings.duckdb_path)"

---

もし README に含めたい追加の実行例（具体的な CLI スクリプトや systemd のサービス定義例、.env.example のテンプレート等）があれば、用途に合わせてサンプルを追記します。どの部分をより詳細に書くか教えてください。