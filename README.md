# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログなどを含む統合モジュール群です。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数 / 設定項目
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株の自動売買プラットフォームで使う共通ユーティリティ群を提供します。
- データ層（J-Quants からの株価・財務・カレンダー取得）、ETL パイプライン、データ品質チェック、ニュース取得と LLM によるセンチメント評価、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（注文と約定のトレース）などを含みます。
- Look-ahead bias 回避や冪等性（INSERT ... ON CONFLICT など）、API のリトライ／レート制御、SSRF 対策など運用上の実装配慮がなされています。

---

主な機能一覧
- 環境設定読み込み（.env 自動ロード、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
- J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御）
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- ETL パイプライン（差分取得、バックフィル、品質チェック）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult 型で結果の集約
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news 保存）
- ニュース NLP（OpenAI を使った銘柄別センチメント評価）
  - score_news: raw_news / news_symbols → ai_scores
- 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュース LLM で daily レジーム判定）
  - score_regime: market_regime テーブルへ書き込み
- 研究用モジュール（ファクター計算、前方リターン、IC、統計サマリー）
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
  - init_audit_schema / init_audit_db

---

セットアップ手順（ローカル開発向け）
前提: Python 3.10 以降を推奨（型注釈で | を使用）。

1. リポジトリをクローン
   git clone <リポジトリURL>
   cd <リポジトリ>

2. 仮想環境を作成して有効化
   python -m venv .venv
   source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   requirements.txt がある想定です。なければ主な依存を直接インストールしてください：
   pip install duckdb openai defusedxml

   （実運用では他に sqlite3（標準）、logging 等が必要です。）

4. 環境変数設定
   プロジェクトルート（.git や pyproject.toml があるディレクトリ）に .env / .env.local を置くと自動で読み込まれます。
   自動読み込みを無効化する場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須環境変数（後述の一覧を参照）を設定してください。

5. データディレクトリ作成（必要に応じて）
   mkdir -p data

---

環境変数 / 設定項目
（config.Settings で参照される主なキー）

必須:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD     : kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN       : Slack 連携（通知等）に用いる Bot トークン
- SLACK_CHANNEL_ID      : 通知先チャンネル ID
- OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime 等で使用）

任意（デフォルトあり）:
- KABU_API_BASE_URL     : kabu API のベース URL （デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH         : 実行 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT : 監視閾値
- KABUSYS_ENV           : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL             : DEBUG/INFO/WARNING/ERROR/CRITICAL

メモ:
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。
- .env の読み込み挙動は .env → .env.local（.env.local が上書き）で、既存 OS 環境変数は保護されます。

---

簡単な使い方（コード例）
以下はいくつかの典型的な使い方例です。実行前に必須環境変数を設定してください。

- DuckDB 接続の取得（設定されたパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する
```python
from kabusys.data.pipeline import run_daily_etl

# conn は DuckDB 接続、target_date は datetime.date
result = run_daily_etl(conn, target_date=None)  # target_date を省略すると今日
print(result.to_dict())
```

- ニュースセンチメントスコア作成（OpenAI API キー必須）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n)
```

- 市場レジームスコア計算
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（独立 DB を使用）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions が作成される
```

- 研究用ファクター取得例
```python
from kabusys.research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
```

注意点:
- OpenAI 呼び出しや J-Quants API 呼び出しは外部サービスを使うため、テスト時は各 _call_openai_api や jquants_client._request 等をモックしてください。
- 関数群は Look-ahead バイアスに配慮して設計されています（内部で date.today() を直接参照しない等）。

---

ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主要モジュール一覧と役割）

- kabusys/
  - __init__.py
  - config.py                      : 環境変数 / .env 自動読み込み、Settings
  - ai/
    - __init__.py                   : score_news エクスポート
    - news_nlp.py                   : ニュースの LLM スコアリング（score_news）
    - regime_detector.py            : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             : J-Quants API クライアント（fetch/save）
    - pipeline.py                   : ETL パイプライン（run_daily_etl 等）
    - etl.py                        : ETLResult のエクスポート
    - quality.py                    : データ品質チェック
    - stats.py                      : zscore_normalize 等の統計ユーティリティ
    - calendar_management.py        : 市場カレンダー管理 / 営業日判定 / calendar_update_job
    - news_collector.py             : RSS 取得と raw_news 保存（SSRF 対策等）
    - audit.py                      : 監査ログテーブル定義 / 初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py            : calc_momentum / calc_value / calc_volatility
    - feature_exploration.py        : calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/ (想定：監視用コードが入る)
  - strategy/ (想定：戦略定義・シグナル生成)
  - execution/ (想定：発注・broker 接続)

（注）README が扱うコードベースは上記モジュールを中心に設計されています。strategy / execution / monitoring パッケージは __all__ に含まれているため、将来的な拡張や実装が想定されています。

---

運用・開発に関する注意
- DuckDB の executemany に空リストを渡すと例外となるバージョン（例: 0.10）があるため、コード中では空チェックを行っています。
- OpenAI / J-Quants API 呼び出しはリトライロジック・バックオフ・エラー時フォールバック（ゼロスコア等）を備えていますが、API コストやレートに留意してください。
- news_collector では SSRF / XML Bomb / 巨大レスポンス対策（defusedxml、リダイレクト検査、最大バイト数制限）を実装しています。
- 監査ログは削除しない前提で設計されています（トレーサビリティ確保）。

---

ライセンス / 貢献
- 本リポジトリに LICENSE ファイルがあればそちらに従ってください。コントリビュートはプルリクエストでお願いします。

---

補足
- この README はリポジトリ内のソースコードから主要機能・設定・使い方をまとめたものです。各関数の詳細な引数仕様や返り値、例外動作については該当ソース（src/kabusys 以下）を参照してください。質問や追加のドキュメントが必要であれば教えてください。