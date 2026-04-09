# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP、ファクター算出、監査ログ（トレーサビリティ）、研究用ユーティリティなどを含むモジュール群を提供します。

主にバックテスト用データ準備や、AI を用いたニュースセンチメント判定、監査付きの発注フロー実装などを想定しています。

---

目次
- プロジェクト概要
- 機能一覧
- 前提／依存関係
- セットアップ手順
- 簡単な使い方（コード例）
- 環境変数（主な設定）
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買に必要な基盤機能をまとめた Python パッケージです。  
主な目的は以下です。

- J-Quants API からの株価・財務・カレンダーの差分取得（ETL）と品質チェック
- RSS ベースのニュース収集と前処理
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント / 市場レジーム判定
- 研究用途のファクター計算・IC / 統計ユーティリティ
- 発注・約定の監査ログ（DuckDB）によるトレーサビリティ

設計では「ルックアヘッドバイアス防止」「冪等性」「API レート制御」「フォールバック（DB未整備時）」等に配慮しています。

---

## 機能一覧

- ETL（kabusys.data.pipeline）
  - 日次 ETL（株価、財務、マーケットカレンダー）の差分取得
  - 品質チェック（欠損、スパイク、重複、日付不整合）
- J-Quants クライアント（kabusys.data.jquants_client）
  - 認証（refresh_token → id_token）
  - fetch / save のラッパー（ページネーション・レート制御・リトライ）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、安全対策（SSRF/プライベートIP検査）と前処理
- ニュース NLP（kabusys.ai.news_nlp）
  - ニュースを銘柄ごとに集約して LLM でスコアリングし ai_scores に書込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定
- 研究モジュール（kabusys.research）
  - momentum / volatility / value 等のファクター計算
  - forward returns, IC（Spearman）、ファクター要約
- データ品質（kabusys.data.quality）
  - 各種チェックをまとめて実行可能（run_all_checks）
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの初期化ユーティリティ
  - 監査DBの初期化（init_audit_db, init_audit_schema）
- ユーティリティ（kabusys.config, stats 等）
  - 環境変数の簡易ロード・管理、Zスコア正規化など

---

## 前提／依存関係（主なもの）

※プロジェクトに requirements.txt がある想定がない場合の最小セット例

- Python 3.10+
- duckdb
- openai
- defusedxml

インストール例（開発環境）:
- python -m venv .venv
- source .venv/bin/activate
- pip install --upgrade pip
- pip install duckdb openai defusedxml

プロジェクトに setuptools/pyproject があれば:
- pip install -e .

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （必要に応じて他のパッケージを追加）

4. 環境変数を設定
   - プロジェクトルートに .env を置くと自動ロードされます（.git または pyproject.toml のある親ディレクトリを探します）。
   - 自動ロードを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

5. DuckDB ファイル / データディレクトリ作成
   - デフォルトの DB パスは data/kabusys.duckdb（設定で変更可）
   - 監査DB初期化などで親ディレクトリを自動作成します

---

## 環境変数（主要項目）

場所: .env（自動ロードされる）または OS 環境変数

必須／重要:
- JQUANTS_REFRESH_TOKEN = <J-Quants のリフレッシュトークン>
- KABU_API_PASSWORD = <kabu ステーション API パスワード>

任意／推奨:
- OPENAI_API_KEY = <OpenAI API Key>（news_nlp / regime_detector 用）
- KABU_API_BASE_URL = デフォルト "http://localhost:18080/kabusapi"
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID = LINE 通知用
- DUCKDB_PATH = data/kabusys.duckdb（デフォルト）
- SQLITE_PATH = data/monitoring.db（監視用）
- PAPER_FILL_MODE = instant | partial | never | reject（paper_trading 用）
- PAPER_TRADING_SQLITE_PATH = data/paper_trading.db
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START（監視用）
- KABUSYS_ENV = development | paper_trading | live
- LOG_LEVEL = DEBUG | INFO | WARNING | ERROR | CRITICAL

注意:
- 必須変数が未設定の場合、Settings プロパティを参照したときに ValueError が発生します。
- .env のパースはシェル風の export 形式や引用符、コメントなどに対応しています。

---

## 簡単な使い方（コード例）

下記は最小の実行例です。実際にはログ設定や例外処理を追加してください。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを計算して ai_scores テーブルに書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム（ma200 + macro）を評価
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って以後の監査ログ操作が可能
```

- 研究用ファクター取得例
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点:
- API キー（OpenAI / J-Quants）が必要な関数は api_key 引数か環境変数を設定してください。
- 関数はルックアヘッドバイアスを避ける設計で、target_date を明示して呼ぶことが推奨されます。

---

## 監査／運用に関する設定

- ETL 実行・監視プロセスは PID ファイルや KILL フラグファイルに対応する設定を持ちます（Settings.pid_file_path 等）。
- Paper Trading（模擬約定）は設定でフィルモードを切替可能（instant / partial / never / reject）。
- J-Quants API はモジュール内でレート制御とリトライ処理が組み込まれています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースを銘柄ごとに集約して LLM でスコア化
    - regime_detector.py  — MA200 と マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - pipeline.py         — ETL パイプラインと run_daily_etl
    - etl.py              — ETLResult 再公開
    - news_collector.py   — RSS 収集と前処理（SSRF 対策等）
    - calendar_management.py — 市場カレンダーと営業日ロジック
    - stats.py            — 統計ユーティリティ（zscore 正規化）
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py  — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns, IC, summary, rank
  - research/... (他)
- data/  — デフォルトデータ保存先（DuckDB 等）※実行時に自動作成されることがある

各モジュールはドキュメント文字列やログ出力を含み、設計方針（冪等性、フォールバック、ルックアヘッド対策等）が明記されています。

---

## 開発／テストに関して

- LLM・外部 API 呼び出し部は内部で差し替え（mock）可能なように設計されています（ユニットテスト時に _call_openai_api を patch 等）。
- DuckDB を使うため、テストでは ":memory:" を渡してインメモリ DB を利用できます（init_audit_db 等は対応）。
- .env の自動ロードは .git または pyproject.toml をルート判定に使用します。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化してください。

---

README は以上です。さらに、導入や運用の具体的なワークフロー（ETL のスケジューリング、監視、バックテスト連携、発注フロー実装のサンプル）を追加したい場合は、目的（例：本番運用／研究用／ローカル検証）を教えてください。必要に応じてサンプルスクリプトや systemd / cron ジョブ例も作成します。