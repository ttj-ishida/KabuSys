# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants などからのデータ取得）、ニュース収集・NLP、研究用ファクター計算、監査ログ・約定トレーサビリティ、マーケットカレンダー管理などを備えたモジュール群を提供します。

## プロジェクト概要
本パッケージは以下を目的としています。

- J-Quants 等の外部 API から株価・財務・カレンダーを差分取得して DuckDB に保存（ETL）
- RSS ニュース収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）とマクロレジーム判定
- 研究用ファクター計算（モメンタム・バリュー・ボラティリティなど）と特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）を DuckDB に整備しトレーサビリティを確保
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（JPX 祝日/半日/SQ 判定）と営業日計算ユーティリティ

設計上の共通方針として「ルックアヘッドバイアスを避ける」「ETL は冪等」「外部 API エラーはフォールバックして継続する（可能な限り）」が採用されています。

## 主な機能一覧
- データ取得 / ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（kabusys.data.pipeline）
  - J-Quants API クライアント（kabusys.data.jquants_client）
- ニュース収集・NLP
  - RSS 取得・前処理・保存（kabusys.data.news_collector）
  - ニュースセンチメントスコアリング（kabusys.ai.news_nlp.score_news）
  - マクロニュース + ETF MA200 から市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- 研究・ファクター計算
  - calc_momentum / calc_value / calc_volatility（kabusys.research.factor_research）
  - 将来リターン計算 / IC / 統計サマリー（kabusys.research.feature_exploration）
  - Zスコア正規化ユーティリティ（kabusys.data.stats.zscore_normalize）
- 監査ログ（audit）
  - init_audit_db / init_audit_schema（kabusys.data.audit）
  - signal_events / order_requests / executions テーブル定義とインデックス
- データ品質チェック
  - check_missing_data / check_spike / check_duplicates / check_date_consistency
  - run_all_checks（kabusys.data.quality）
- 環境設定
  - settings（kabusys.config）: .env の自動読み込み、環境変数経由の設定取得

## 必要な環境・依存
- Python 3.10 以上（Union 型の | 表記や型ヒント等のため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib, datetime, logging 等を使用

（実際の requirements.txt / pyproject.toml は環境に応じて用意してください）

## 環境変数 / .env
パッケージはプロジェクトルート（.git または pyproject.toml を探索）にある `.env` / `.env.local` を自動で読み込みます（環境変数優先）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主な必須環境変数（config.Settings により参照されます）:
- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token
- KABU_API_PASSWORD — kabuステーション API パスワード
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャネル ID
- OPENAI_API_KEY — OpenAI を利用する機能（news_nlp / regime_detector）で必要
（また、以下はデフォルト値があり任意）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/...（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

.env.example を参考に .env を作成してください（コード内のエラー・メッセージも参照可）。

## セットアップ手順（例）
1. リポジトリをクローン
   - git clone <repo-url>
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - もしくはプロジェクトの pyproject.toml / requirements.txt があれば pip install -e . / pip install -r requirements.txt
4. .env を作成
   - プロジェクトルートに `.env` を置き、必要な環境変数を設定
5. DuckDB 初期化（監査ログなど）
   - Python REPL またはスクリプトで以下を実行（例は README 下の使い方参照）

## 使い方（簡単な例）
以下は代表的な利用例です。実行する前に .env と依存パッケージ、DuckDB のパス等を正しく設定してください。

- DuckDB に接続して監査 DB を初期化する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

# ファイルベースの DB を初期化（親ディレクトリを自動作成）
conn = init_audit_db(settings.duckdb_path)
# または、すでにある接続を渡してスキーマを追加:
# conn = duckdb.connect(settings.duckdb_path)
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

- 日次 ETL を実行する（株価・財務・カレンダー取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date.today())  # 引数省略で今日
print(result.to_dict())
```

- ニュースセンチメントスコアを生成する
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(settings.duckdb_path)
# OPENAI_API_KEY は環境変数または api_key 引数で渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム（マクロ + ETF MA200）を判定して保存する
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("<path-to-duckdb>")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須
```

- 研究用ファクターを計算する
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
import duckdb
from datetime import date

conn = duckdb.connect("<path-to-duckdb>")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
```

- データ品質チェックを実行する
```python
from kabusys.data.quality import run_all_checks
import duckdb
from datetime import date

conn = duckdb.connect("<path>")
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

補足:
- OpenAI を使う機能は環境変数 `OPENAI_API_KEY` によるキー指定を想定しています。テスト時には該当モジュールの内部 API 呼び出しをモックできます（コード内に patch しやすい設計あり）。
- テストや CI で自動 env ロードを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## ディレクトリ構成
（src 以下を想定した主なファイル/モジュール一覧）

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント / 保存ロジック
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult 再エクスポート
    - news_collector.py        — RSS 収集 / 前処理
    - calendar_management.py   — market_calendar 管理・営業日判定
    - quality.py               — データ品質チェック
    - audit.py                 — 監査ログ DDL / 初期化
    - stats.py                 — zscore_normalize 等統計ユーティリティ
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py   — forward returns / IC / summary
  - research/... その他ユーティリティ

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取って動作する設計が多く、DB 接続を共有して使うことを想定しています。

## 注意点・運用メモ
- ルックアヘッドバイアス防止のため、各処理は内部で date 引数を受け取り、datetime.today()/date.today() を直接参照しない設計が多いです。バッチ処理やバックテストでは target_date を明示的に渡してください。
- J-Quants / OpenAI 等の API 呼び出しはリトライ・バックオフの実装が行われていますが、API クォータやコストに注意してください。
- ETL / 保存処理は冪等性を意識しており、ON CONFLICT / DELETE→INSERT などで既存データを上書きする設計です。
- news_collector は SSRF 対策（リダイレクト検査 / プライベート IP 検査）や XML パースでの安全対策（defusedxml）を実装しています。
- DuckDB バージョン依存の振る舞い（executemany の空リストなど）を考慮した実装が各所にあります。使用する DuckDB バージョンに注意してください。

## 開発・テスト時のヒント
- 環境変数の自動ロードを無効にしたい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants へのネットワーク呼び出しは unittest.mock で _call_openai_api や jquants_client._request を patch してテスト可能な設計です。
- ETL の個別ステップは run_prices_etl / run_financials_etl / run_calendar_etl として分かれているため、単体テストしやすくなっています。

---

README は概要と主要な使い方、設定を中心にまとめました。詳細な API 仕様や DB スキーマ（テーブル定義）は各モジュール（kabusys/data/*.py, kabusys/data/audit.py 等）のドキュメント文字列をご参照ください。必要であればサンプル .env.example、requirements.txt、運用ガイド（ジョブスケジューリング例、監視・アラート例）などの追加ドキュメント作成も対応します。