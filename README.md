# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュースNLP、ファクター計算、監査ログ、J-Quants / kabuステーション クライアントなど、バックテスト・運用に必要な基盤機能をモジュール単位で提供します。

現在のバージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、特徴量計算、ニュースの自然言語処理による銘柄別スコアリング、ならびに売買監査ログ（トレーサビリティ）などを備えたライブラリです。内部では DuckDB をデータストアとして使用し、OpenAI（gpt-4o-mini）を利用した NLP 機能を実装しています。

主な設計方針
- ルックアヘッドバイアスを避ける（明示的な target_date を利用）
- API 呼び出しはリトライ / フェイルセーフ（失敗時は部分的に継続）
- DuckDB を使った冪等保存（ON CONFLICT / DELETE→INSERT）
- モジュールはテストしやすいように鍵関数が差し替え可能

---

## 機能一覧

- データ ETL
  - J-Quants から株価（日足）・財務データ・上場情報・マーケットカレンダーをフェッチ
  - 差分更新、バックフィル、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次パイプライン: run_daily_etl

- データ品質管理
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで問題を集約

- ニュース収集 / 前処理
  - RSS フィード取得（SSRF対策、URL正規化、トラッキングパラメータ除去）
  - raw_news などへの冪等挿入を想定した処理

- ニュース NLP（OpenAI）
  - 銘柄別ニュース統合スコアリング: score_news（gpt-4o-mini / JSON Mode）
  - マクロニュースを使った市場レジーム判定: score_regime

- 研究用ユーティリティ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（情報係数）、統計サマリ、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル等の DDL 定義と初期化補助
  - init_audit_db / init_audit_schema による監査 DB 初期化

- J-Quants クライアント
  - レートリミット、リトライ、401 → トークンリフレッシュ対応
  - save_* 系関数で DuckDB へ冪等保存

---

## 要件

- Python 3.10+
- 必要 Python パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ: urllib, json, datetime, logging など

（プロジェクトに requirements.txt / pyproject.toml がある想定です。なければ上記を pip でインストールしてください）

例:
pip install duckdb openai defusedxml

---

## 環境変数 / .env

KabuSys は .env / .env.local / 環境変数から設定を読み込みます（パッケージルートの検出: .git または pyproject.toml を探索）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（テストなどで利用）。

主要な環境変数
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須で ETL を動かす場合）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
- KABU_API_PASSWORD: kabuステーション API のパスワード
- KABU_API_BASE_URL: kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（監視機能に使用）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用
- KABUSYS_ENV: development / paper_trading / live
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

例 (.env)
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最小要件を個別に:
     pip install duckdb openai defusedxml

4. 環境変数設定
   - プロジェクトルートに .env を作成するか、OS 環境変数に設定
   - 上記「環境変数」セクション参照

5. ディレクトリ作成（デフォルトパスを使う場合）
   - mkdir -p data

6. 監査用 DuckDB の初期化（任意）
   - 以下のスクリプト例を実行して監査 DB を初期化できます。

Python スニペット:
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続

---

## 使い方（例）

以下は主要な API の簡単な使い方例です。実行は Python スクリプト／REPL から行います。

共通準備:
- settings からデフォルトの DB パスを取得できます。

例: DuckDB 接続取得
import duckdb
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))  # ファイルがない場合は作成されます

1) 日次 ETL を実行する
from datetime import date
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

2) ニュース NLP を実行して ai_scores テーブルに書き込む
from datetime import date
from kabusys.ai.news_nlp import score_news
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")

注意: score_news は OPENAI_API_KEY が必要です（api_key 引数でも渡せます）。

3) 市場レジーム判定を実行する
from datetime import date
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須

4) 監査テーブル初期化（監査ログ用）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブル等が作成されます

5) ファクター計算（研究用途）
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
momentums = calc_momentum(conn, target_date=date(2026, 3, 20))
values = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))

---

## 注意事項 / トラブルシューティング

- OpenAI
  - score_news / score_regime は OpenAI の Chat Completions(JSON mode) を利用します。APIキー（OPENAI_API_KEY）が必要です。
  - API 呼び出しはリトライしますが、失敗時は安全側のデフォルト（スコア 0.0）で継続します。

- J-Quants
  - J-Quants API の呼び出しにはレート制限（120 req/min）を考慮した実装になっています。大量の同時呼び出しは避けてください。
  - JQUANTS_REFRESH_TOKEN を設定しておくことで get_id_token が自動でトークンを取得／リフレッシュします。

- DuckDB スキーマ
  - ETL / save_* 関数は対象テーブル（raw_prices, raw_financials, market_calendar 等）が存在していることを前提としています。
  - 監査テーブルについては data.audit.init_audit_db で作成できます。その他のテーブルは設計ドキュメントに従って初期化してください。

- .env 自動ロード
  - パッケージインポート時にプロジェクトルート（.git / pyproject.toml）を探索して .env / .env.local を自動で読み込みます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要モジュール構成（src/kabusys 以下）:

src/kabusys/
- __init__.py
- config.py                          # 環境変数 / .env 管理
- ai/
  - __init__.py
  - news_nlp.py                       # ニュース NLP（score_news）
  - regime_detector.py                # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py                 # J-Quants API クライアント（fetch/save系）
  - pipeline.py                       # ETL パイプライン（run_daily_etl 等）
  - etl.py                            # ETL 公開インターフェース
  - news_collector.py                 # RSS ニュース収集
  - calendar_management.py            # 市場カレンダー管理（is_trading_day 等）
  - quality.py                         # データ品質チェック
  - stats.py                           # Zスコア等統計ユーティリティ
  - audit.py                           # 監査ログテーブル定義 / 初期化
- research/
  - __init__.py
  - factor_research.py                # ファクター計算（momentum/value/volatility）
  - feature_exploration.py            # 将来リターン / IC / 統計サマリ

その他:
- data/ (推奨データ格納用ディレクトリ、DuckDB ファイル等)
- .env.example（プロジェクトルートに作成することを推奨）

---

## ライセンス / コントリビュート

この README はコードベースの概要を示すもので、実際の運用では内部の設計ドキュメント（DataPlatform.md / StrategyModel.md 等）と合わせて利用してください。外部へ公開する際はライセンス表記を追加してください。

貢献: バグレポートや PR を歓迎します。API 変更・破壊的変更を加える場合は事前に議論してください。

---

必要に応じて README のサンプル .env.example を生成したり、簡単な起動スクリプトを追加することも可能です。どのような利用例（ETL の自動化 cron / systemd / Airflow での実行等）を README に追記したいか教えてください。