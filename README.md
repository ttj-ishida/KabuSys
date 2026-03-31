# KabuSys

KabuSys は日本株のデータプラットフォームと研究／自動売買基盤を提供する Python パッケージです。J-Quants や kabuステーション、OpenAI 等と連携してデータ収集（ETL）、品質チェック、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、監査ログ（トレース）などを行うことを目的としています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 簡単な使い方（例）
- 環境変数一覧
- ディレクトリ構成（主要ファイルと役割）
- 補足・注意事項

---

## プロジェクト概要

このライブラリは以下の責務を持ちます。

- J-Quants API を使った株価・財務・カレンダーの差分取得と DuckDB への保存（ETL）
- ニュース RSS 収集と前処理、銘柄紐付け
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント（ai_scores）と市場レジーム判定
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal → order_request → executions のトレース）用スキーマ作成ユーティリティ
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量探索ユーティリティ

設計上の特徴:
- ルックアヘッドバイアスを避ける設計（日時参照は外部から与える target_date）  
- DuckDB を中心としたローカル DB 設計（ON CONFLICT / 冪等保存）
- API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
- ニュース収集で SSRF や XML 攻撃対策を実装

---

## 主な機能一覧

- data:
  - ETL（run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl）
  - J-Quants クライアント（fetch_*/save_*）
  - ニュース収集（fetch_rss）, news 前処理
  - カレンダー管理（is_trading_day / next_trading_day / get_trading_days）
  - データ品質チェック（run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai:
  - score_news(conn, target_date, api_key=None): ニュース → ai_scores 書き込み
  - score_regime(conn, target_date, api_key=None): 市場レジーム判定（ETF 1321 + マクロニュース）
- research:
  - calc_momentum / calc_volatility / calc_value（各ファクター）
  - calc_forward_returns / calc_ic / factor_summary / rank（特徴量探索・評価）

---

## セットアップ手順

前提:
- Python 3.10+ を推奨（型アノテーションに union 型等を利用）
- DuckDB をローカルに使える環境

1. リポジトリをクローン／チェックアウト

2. 仮想環境を作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

3. 依存ライブラリをインストール
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - なければ最低限以下をインストールしてください:
     ```
     pip install duckdb openai defusedxml
     ```
   - 実行時に urllib や標準ライブラリのみで動く箇所も多いですが、OpenAI/duckdb 等は必須機能で必要です。

4. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

5. 環境変数を設定（次節参照）。プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

---

## 簡単な使い方（例）

以下は Python REPL / スクリプトからの利用例です。

- Settings（環境変数アクセス）:
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.env, settings.is_live)
```

- DuckDB 接続を作り ETL を実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API key を環境変数 OPENAI_API_KEY に設定しておく）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", n_written)
```

- 市場レジーム判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB 初期化:
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit_duckdb.duckdb")
# これで監査テーブルが作成されます
```

- ニュース RSS を取得（単体）:
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["title"], a["datetime"])
```

注意: 各種関数は内部で target_date を引数として受け取り、datetime.today()/date.today() を直接参照しない設計です（バックテストでのルックアヘッド回避）。

---

## 環境変数一覧（必須/推奨）

必須（実行する機能により必要なもの）:
- JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD - kabuステーション API のパスワード（発注機能使用時）
- SLACK_BOT_TOKEN - Slack 通知を使う場合
- SLACK_CHANNEL_ID - Slack 通知先チャンネル ID
- OPENAI_API_KEY - OpenAI を使う AI 機能（score_news/score_regime）を使用する場合

オプション / デフォルトあり:
- KABUSYS_ENV - 環境 ("development", "paper_trading", "live")。デフォルト "development"
- LOG_LEVEL - ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")。デフォルト "INFO"
- DUCKDB_PATH - DuckDB ファイルパス（デフォルト "data/kabusys.duckdb"）
- SQLITE_PATH - 監視用 SQLite（デフォルト "data/monitoring.db"）
- PID_FILE_PATH - 実行監視用 PID ファイルパス（デフォルト "data/execution.pid"）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT - 監視閾値（%）

.env 自動読み込み:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みは無効になります（テスト時に便利）。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=DEBUG
```

---

## ディレクトリ構成（主要ファイルと説明）

パッケージルート: src/kabusys/

主要モジュール:
- __init__.py
  - パッケージメタ情報（__version__）とサブパッケージエクスポート
- config.py
  - 環境変数ロード・Settings（アプリ設定）クラス
- ai/
  - news_nlp.py — ニュースの LLM ベーススコアリング（score_news）
  - regime_detector.py — 市場レジーム判定（score_regime）
- data/
  - pipeline.py — ETL パイプラインと run_daily_etl 等
  - jquants_client.py — J-Quants API クライアント（fetch_*/save_*）
  - news_collector.py — RSS 取得と前処理（SSRF 対策・XML 防御）
  - calendar_management.py — 市場カレンダー管理（営業日/next/prev 等）
  - quality.py — データ品質チェック（欠損/スパイク/重複/日付）
  - audit.py — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats.py — zscore_normalize 等の統計ユーティリティ
  - etl.py — ETLResult の再エクスポート
- research/
  - factor_research.py — モメンタム・ボラティリティ・バリュー計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

（各ファイルは docstring に処理フロー・設計方針を詳述しています。実装の詳細は該当ファイルを参照してください。）

---

## 補足・注意事項

- OpenAI 呼び出し:
  - gpt-4o-mini を想定しており、JSON Mode を使う設計です。API の失敗やパースエラーはフェイルセーフで 0.0 にフォールバックする処理が含まれています。
  - テスト用に _call_openai_api をモック可能な実装になっています（単体テストが容易）。

- J-Quants API:
  - レート制御（120 req/min）や 401 リフレッシュ、ページネーション対応を実装済み。
  - ETL は差分取得とバックフィルを組み合わせて後出し修正に耐える設計です。

- ニュース収集:
  - RSS の読み込みは defusedxml を使い XML 攻撃を防止しています。SSRF 対策も実装（リダイレクト先検証、プライベート IP 拒否など）。

- トランザクション:
  - 重要な書き込み処理では BEGIN/COMMIT/ROLLBACK を用いた冪等・原子性の確保を行っていますが、DuckDB のバージョン差異に注意してください（executemany の制限など）。

- ロギング:
  - settings.log_level でログレベルを指定できます。デバッグ時は LOG_LEVEL=DEBUG に設定してください。

---

もし README に追加したい「実行スクリプト例」「CI / 開発フロー」「Schema 定義（DDL）」「より詳しい環境例（docker-compose 等）」があれば、必要な内容を教えてください。具体的なコマンド例やテンプレートも作成します。