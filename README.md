# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ。J-Quants や RSS、OpenAI（LLM）を用いたデータ収集・品質管理・ニュースNLP・市場レジーム判定・ファクター計算・ETL パイプライン・監査ログ等のユーティリティを提供します。

主に研究（research）・データ（data）・AI（news NLP / regime 判定）・監査・ETL を支援するモジュール群で構成されており、実運用（kabuステーション経由の発注や監視）への橋渡しを想定しています。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（基本例）
- 環境変数（.env）一覧（例）
- ディレクトリ構成（主要ファイルと説明）
- 注意事項 / 運用上のヒント

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームとリサーチ／自動売買支援モジュール群です。特徴は以下の点です。

- J-Quants API からの差分取得（株価・財務・カレンダー）と DuckDB への冪等保存
- RSS ベースのニュース収集と前処理・銘柄紐付け
- OpenAI（gpt-4o-mini 想定）を用いたニュースセンチメント（銘柄別）およびマクロセンチメント評価
- ETF（1321）200日移動平均とマクロセンチメントを組み合わせた市場レジーム判定
- ファクター計算（モメンタム・ボラティリティ・バリュー等）および特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保存する DuckDB スキーマ
- ETL パイプライン（差分取得／保存／品質チェック）の一括実行

---

## 機能一覧（主要）

- data/jquants_client.py
  - J-Quants API クライアント（トークン取得、ページネーション、リトライ、レートリミッタ）
  - fetch/save: 日次株価、財務、上場情報、カレンダー
- data/pipeline.py
  - run_daily_etl: 市場カレンダー → 株価ETL → 財務ETL → 品質チェック の統合パイプライン
- data/quality.py
  - 欠損、重複、スパイク、日付整合性チェック
- data/news_collector.py
  - RSS 収集、安全性（SSRF防止）、正規化、raw_news への保存前処理
- ai/news_nlp.py
  - 銘柄別ニュースを LLM に渡して ai_scores に書き込む（バッチ、検証、リトライ）
- ai/regime_detector.py
  - ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して daily market_regime を算出
- research/
  - factor_research.py: モメンタム、ボラティリティ、バリュー計算
  - feature_exploration.py: 将来リターン計算・IC（Spearman）・統計サマリ
  - data/stats.py: zscore_normalize（共通統計ユーティリティ）
- data/audit.py
  - 監査スキーマ作成（signal_events / order_requests / executions）と初期化ユーティリティ
- config.py
  - .env / 環境変数の自動ロード（プロジェクトルート検出）と設定ラッパー

---

## セットアップ手順

前提
- Python 3.10+（typing の | 演算子や型ヒントを利用）
- DuckDB（Python パッケージ）
- OpenAI Python SDK（LLM 呼び出しに使用）
- defusedxml（RSS パースの安全化）

推奨インストール（リポジトリルートで）:

1. 仮想環境作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .\.venv\Scripts\Activate    (Windows PowerShell)

2. 依存パッケージのインストール
   - pip install duckdb openai defusedxml

   （Slack連携やその他の拡張がある場合は slack-sdk などを追加）

3. パッケージを開発モードでインストール（プロジェクトがパッケージ化されている場合）
   - pip install -e .

4. 環境変数の準備
   - プロジェクトルートに `.env` を置くと自動的に読み込まれます（config.py の自動ロード）。
   - 自動ロードを無効にする場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 環境変数（.env） — 必要/推奨項目（例）

以下は本コードベースで参照される主な環境変数です。必須マークはコード上で _require() によってチェックされます。

必須:
- JQUANTS_REFRESH_TOKEN ... J-Quants のリフレッシュトークン（ETL に必要）
- SLACK_BOT_TOKEN         ... Slack 通知を利用する場合
- SLACK_CHANNEL_ID        ... Slack 通知チャンネルID
- KABU_API_PASSWORD       ... kabuステーション API パスワード（発注関連がある場合）

OpenAI:
- OPENAI_API_KEY          ... AI モジュール（score_news / score_regime）で使用

DB / 設定（デフォルト値あり）:
- DUCKDB_PATH             ... デフォルト: data/kabusys.duckdb
- SQLITE_PATH             ... 監視用 SQLite: data/monitoring.db
- PID_FILE_PATH           ... 実行監視の pid ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT ... 監視しきい値

運用:
- KABUSYS_ENV             ... development / paper_trading / live（デフォルト: development）
- LOG_LEVEL               ... DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD ... 1 を設定すると .env 自動ロードを無効化

サンプル（.env.example のイメージ）:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（基本例）

以下は Python REPL やスクリプトから本ライブラリの関数を呼ぶ最小例です。

1) DuckDB 接続を作成して ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP（AI スコア）を生成
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
ret = score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

4) 監査ログ DB を初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn: DuckDB 接続、すぐに監査テーブルが使える
```

5) 監視・設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)   # Path object
print(settings.env)           # development/paper_trading/live
```

実運用スクリプトではログレベル設定、例外ハンドリング、再試行や監視（PID ファイル、リソース閾値監視）を組み込んでください。

---

## ディレクトリ構成（主要ファイルと説明）

（リポジトリ内 `src/kabusys` を想定）

- src/kabusys/__init__.py
  - パッケージ初期化。公開モジュール一覧を定義。

- src/kabusys/config.py
  - 環境変数/.env 自動ロードと設定アクセスラッパー（Settings）

- src/kabusys/ai/
  - news_nlp.py: 銘柄別ニュースセンチメントを LLM で評価し ai_scores に書き込む
  - regime_detector.py: ETF(1321) MA200 とマクロニュースで daily market_regime を算出
  - __init__.py: ai のエクスポート（score_news 等）

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得・保存ユーティリティ）
  - pipeline.py: ETL パイプライン（run_daily_etl など）
  - etl.py: ETLResult の公開ラッパー
  - news_collector.py: RSS 収集と前処理
  - calendar_management.py: 市場カレンダー管理（is_trading_day 等）
  - quality.py: データ品質チェック
  - audit.py: 監査スキーマ初期化 / init_audit_db
  - stats.py: 共通統計ユーティリティ（zscore_normalize）

- src/kabusys/research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリ等
  - __init__.py: 研究用 API の再エクスポート

- src/kabusys/ai/news_nlp.py, regime_detector.py などは OpenAI SDK を使います（api_key の注入可）。

---

## 注意事項 / 運用上のヒント

- OpenAI や J-Quants の API キーは機密情報です。公開リポジトリに含めないでください。`.env` を .gitignore に追加することを推奨します。
- config.py は自動でプロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込みます。テストや CI で自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- LLM 呼び出しは課金対象かつレイテンシが発生します。バッチサイズやリトライ設定は code 内の定数（_BATCH_SIZE, _MAX_RETRIES 等）で制御可能です。テスト時は API 呼び出し関数をモックすることを推奨します（コード内に差し替えや patch の想定あり）。
- DuckDB への executemany や型制約に由来する挙動（空リストの扱いなど）に注意してください。pipeline では空の場合の操作回避が実装されています。
- news_collector は SSRF・XML 脆弱性対策を講じています（_SSRFBlockRedirectHandler, defusedxml, 最大受信バイト制限等）。
- run_daily_etl はカレンダー取得 → 対象日の調整 → ETL の順で動作します。運用上は cron やバッチジョブでの定期実行を想定してください。
- 本パッケージは「研究／データ基盤」を中心に設計されており、実際の発注ロジック（kabuステーションとの注文フロー）は別モジュール（execution 系）で実装することを想定しています。発注系はリスクに十分留意して実装・検証してください。

---

もし README に追加したい具体的な例（.env.example の完全版、起動スクリプト、systemd ユニットファイル、CI 設定など）があれば教えてください。必要に応じてテンプレートを作成します。