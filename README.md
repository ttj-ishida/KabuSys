# KabuSys

日本株向けのデータプラットフォームと自動売買支援ライブラリです。  
DuckDB をデータレイヤに、J-Quants / JPX / RSS / OpenAI 等の外部データ・API を組み合わせて、ETL、品質チェック、ファクター計算、ニュースNLP、マーケットレジーム判定、監査ログなどを提供します。

バージョン: 0.1.0

---

## 主な概要

- データ取得（J-Quants）→ DuckDB への ETL（差分取得・バックフィル）  
- データ品質チェック（欠損・重複・スパイク・日付不整合）  
- ニュース収集（RSS）とニュースを用いた AI センチメントスコア（OpenAI）  
- マーケットレジーム判定（ETF + マクロニュースの混合スコア）  
- ファクター計算（モメンタム、バリュー、ボラティリティ等）とリサーチ用ユーティリティ  
- 監査ログ（シグナル → 発注 → 約定 をトレースするテーブル群と初期化ユーティリティ）  
- 環境変数を中心とした設定管理（.env/.env.local の自動読み込み）

---

## 機能一覧

- data
  - J-Quants クライアント（取得・保存・認証・リトライ・レート制御）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、安全対策：SSRF・gzip・サイズ上限）
  - データ品質チェック（missing, duplicates, spike, date consistency）
  - 監査ログのスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュースセンチメント（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI とのやり取りは gpt-4o-mini（JSON mode）を想定。リトライ・フェイルセーフ設計あり
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数と設定（Settings クラス）
  - 自動 .env ロード（プロジェクトルート検出、.env → .env.local の順で読み込み）
- audit/monitoring 等の補助モジュール（監査・監視用 DB 指定など）

---

## セットアップ手順（開発環境向け）

1. Python 環境を用意（推奨: 3.10+）
2. リポジトリをクローンし、パッケージをインストール
   - 例:
     - git clone <repo>
     - cd <repo>
     - python -m venv .venv
     - source .venv/bin/activate  (Windows は .venv\Scripts\activate)
     - pip install -e .  または 必要な依存をインストール（下記参照）
3. 必要な Python パッケージ（一例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリ以外の依存があれば requirements.txt を参照）

4. 環境変数の設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を用意してください。
   - 自動読み込みはデフォルトで有効です。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 最低限必要な環境変数（Settings に基づく必須項目）
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - SLACK_BOT_TOKEN — Slack 通知に使う Bot トークン
     - SLACK_CHANNEL_ID — 通知先チャンネル ID
   - 推奨 / 任意
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
     - KABUSYS_ENV — development, paper_trading, live（デフォルト: development）
     - LOG_LEVEL — DEBUG/INFO/…（デフォルト: INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - .env の自動読み込みルール:
     - プロジェクトルート（.git または pyproject.toml を基準）を検出し、`.env` → `.env.local` の順で読み込みます。
     - OS 環境変数は保護され、.env による上書きは .env.local の override=True のみ行われます。

---

## 使い方（サンプル）

以下は Python REPL / スクリプトからの利用例です。DuckDB 接続は duckdb.connect() を使用します。

- 日次 ETL の実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使う場合は Path から文字列
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーを環境変数に設定）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を参照
print(f"書き込み件数: {n_written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- ファクター計算（リサーチ用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026,3,20))
vals = calc_value(conn, target_date=date(2026,3,20))
vols = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

注意点:
- LLM 呼び出しを伴う関数は API キー（OPENAI_API_KEY）を必要とします。テスト時は各モジュールの _call_openai_api をモックする設計になっています。
- run_daily_etl 等はデータベースのスキーマ・テーブルが事前に定義されていることを前提とする場合があります（スキーマ初期化ロジックを別途用意してください）。

---

## ディレクトリ構成（主要ファイル）

（抜粋）src/kabusys 以下:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py
  - pipeline.py
  - etl.py (ETLResult re-export)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*（ユーティリティ、ファクター・IC・summary 等）

（実際のリポジトリは他の top-level ファイルやドキュメントも含む想定です）

---

## 環境変数一覧（主要）

必須（実行に応じて必要なものが増えます）:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

OpenAI / 動作モード / ログ等:
- OPENAI_API_KEY (AI スコアリングに必要)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)

データベースパス:
- DUCKDB_PATH (デフォルト data/kabusys.duckdb)
- SQLITE_PATH (デフォルト data/monitoring.db)

自動 .env ロード制御:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化

---

## テストとモックポイント

- OpenAI 呼び出し: kabusys.ai.news_nlp._call_openai_api / kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替え可能
- news_collector._urlopen をモックすることでネットワークを切り離したテストが可能
- jquants_client._request は HTTP 層を包含しているため、外部呼び出しをモックして単体テストを行ってください

---

## ライセンス / 貢献

（リポジトリに LICENSE ファイルがあればその記載に従ってください）

---

README はプロジェクトの概要と使い方を簡潔にまとめたものです。実装の詳細（スキーマ定義、追加のユーティリティ関数、運用ジョブの cron/airflow 設定など）はリポジトリ内の該当ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。必要であれば README に追記します。