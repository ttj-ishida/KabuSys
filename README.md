# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリセットです。  
ETL（J-Quants）・ニュース収集・LLM 活用によるニュースセンチメント評価・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、トレーディング基盤に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local をプロジェクトルートから自動ロード（OS 環境変数が優先）
  - 必要変数未設定時に明確なエラーを返すユーティリティ（settings オブジェクト）

- データ取得 / ETL
  - J-Quants API クライアント（株価日足、財務データ、JPX カレンダー）
  - 差分取得、ページネーション対応、レート制御・リトライロジック
  - ETL パイプライン（run_daily_etl 等）と ETL 結果表現（ETLResult）

- ニュース収集・NLP（LLM）
  - RSS 取得・前処理・raw_news 保存ユーティリティ（SSRF 対策、URL 正規化）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別スコア）
  - 市場マクロ記事を組み合わせた市場レジーム判定（ETF 1321 の MA と LLM スコアの合成）

- 研究用ユーティリティ
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Zスコア正規化ユーティリティ

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue を返す）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の DDL と初期化
  - 監査用 DuckDB データベース初期化ユーティリティ（init_audit_db / init_audit_schema）

- カレンダー管理
  - market_calendar を元にした営業日判定・次/前営業日取得・期間内営業日取得
  - J-Quants からの差分更新ジョブ（calendar_update_job）

---

## セットアップ手順

前提:
- Python 3.10+（typing の union `|` を使用）
- DuckDB, OpenAI SDK 等のライブラリを利用

1. リポジトリをクローン / パッケージをチェックアウト

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要な主要パッケージ例:
     - pip install duckdb openai defusedxml

4. .env の準備
   - プロジェクトルートに `.env` または `.env.local` を置くと自動的に読み込まれます（読み込み順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI の API キー（score_news / score_regime 等で使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（必要に応じて）
     - KABU_API_BASE_URL: kabu API の base URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - 監視・閾値系: PID_FILE_PATH, KILL_FLAG_PATH, CPU_THRESHOLD_PCT, など

   例 (.env):
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb

5. データベース初期化（監査用など）
   - 監査ログ専用 DB を初期化する例:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
   - すでに接続済みの DuckDB に監査スキーマだけ追加する:
     from kabusys.data.audit import init_audit_schema
     init_audit_schema(conn, transactional=True)

---

## 使い方（主要な利用例）

以下は Python スクリプト/REPL での例です。必要に応じて cron / Airflow 等でスケジュール実行してください。

1) DuckDB 接続を作る（settings からパスを取得）
from duckdb import connect
from kabusys.config import settings
conn = connect(str(settings.duckdb_path))

2) 日次 ETL を実行（市場カレンダー → 株価 → 財務 → 品質チェック）
from kabusys.data.pipeline import run_daily_etl
from datetime import date
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())

3) ニュースセンチメント（銘柄別）を生成して ai_scores に保存
from kabusys.ai.news_nlp import score_news
from datetime import date
n = score_news(conn, target_date=date(2026, 3, 20))  # 曜日等を明示
print(f"scored {n} codes")

- score_news は OpenAI API キーを環境変数 OPENAI_API_KEY から取得します。api_key 引数で上書き可能。

4) 市場レジーム判定（ETF 1321 の 200 日 MA とマクロニュースを合成）
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20))

5) ファクター計算や研究用ユーティリティ
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
records = calc_momentum(conn, target_date=date(2026,3,20))
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

6) 監査テーブルの初期化（既存接続へ）
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)

7) J-Quants ID トークンの取得（テストや手動確認用）
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # settings.jquants_refresh_token を使う

注意:
- LLM 呼び出しはコストとレイテンシを伴います。OpenAIキーの管理・レート制御に注意してください。
- すべての「日付」はルックアヘッドバイアスを避けるため明示的に渡す設計です。内部で date.today()/datetime.today() を不用意に参照しないポリシーになっています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                -- 環境変数 / .env 自動ロード・settings
- ai/
  - __init__.py
  - news_nlp.py            -- ニュースセンチメント（銘柄別）
  - regime_detector.py     -- 市場レジーム判定（ETF + マクロLLM）
- data/
  - __init__.py
  - jquants_client.py      -- J-Quants API クライアント・保存ユーティリティ
  - pipeline.py            -- ETL パイプライン（run_daily_etl 等）
  - etl.py                 -- ETL 結果再エクスポート（ETLResult）
  - news_collector.py      -- RSS 取得・前処理
  - calendar_management.py -- 市場カレンダー管理・営業日判定
  - quality.py             -- データ品質チェック
  - stats.py               -- 共通統計ユーティリティ（zscore_normalize 等）
  - audit.py               -- 監査ログスキーマ初期化 / DB 作成
- research/
  - __init__.py
  - factor_research.py     -- ファクター計算（momentum/value/volatility）
  - feature_exploration.py -- 将来リターン / IC / 統計サマリー
- execution/ (発注関連のモジュール群はここに配置想定)
- monitoring/ (監視関連: PID / kill flag / resource閾値等)

（実際のファイルは上記以外にも多数のユーティリティが含まれます。README は主要モジュールの概要を示しています。）

---

## 運用上の注意

- 環境変数: 必須のトークン（JQUANTS_REFRESH_TOKEN、OPENAI_API_KEY 等）は漏洩に注意して管理してください。
- データベースのバックアップ: DuckDB ファイルは定期的にバックアップしてください。
- LLM の呼び出しは冪等性やフォールバックが設計に組み込まれていますが、コスト面での影響を考慮して頻度を制御してください。
- ETL は外部 API に依存するため一時的失敗を想定したリトライ・ログ監視を行ってください。
- test においては自動 .env ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

---

## 貢献・拡張

- CLI やスケジューラ統合（cron / systemd / Airflow）を追加して本番運用に組み込むことができます。
- 発注実装（kabuステーション連携）や position 管理、リスク管理モジュールを追加することで自動売買フルパイプラインを構築できます。
- ニュースソースの追加や LLM プロンプトチューニングで品質改善が可能です。

---

この README はコードベースの主要機能と利用方法の概要を説明しています。細かな挙動や引数仕様は各モジュール（kkabusys/data/*.py、kabusys/ai/*.py、kabusys/research/*.py）内の docstring を参照してください。