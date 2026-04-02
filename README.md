# KabuSys

KabuSys は日本株向けのデータプラットフォーム兼リサーチ・自動売買基盤のプロジェクトです。  
DuckDB をローカル DB として用い、J-Quants API からのデータ取得（株価/財務/カレンダー）、ニュース収集・NLP（OpenAI）によるセンチメント計算、ファクター計算・探索、監査ログ（トレーサビリティ）、ETL パイプラインなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を不用意に参照しない）
- DuckDB を中心に SQL と軽量 Python 実装で処理
- 外部 API 呼び出しにはリトライ／レート制御／フェイルセーフを組み込む
- 冪等性（upsert）や監査ログによるトレーサビリティを重視

---

## 機能一覧

- データ取得・保存（J-Quants API）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得と DuckDB への冪等保存
  - rate limit / retry / token refresh 対応（jquants_client）
- ETL パイプライン
  - 日次 ETL（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（quality）
  - 欠損、スパイク、重複、日付整合性チェック
- ニュース収集（news_collector）
  - RSS 取得（SSRF 対策、トラッキングパラメータ除去）、raw_news への冪等保存、news_symbols との紐付け想定
- ニュース NLP / AI スコアリング（ai.news_nlp）
  - OpenAI（gpt-4o-mini 想定）を使った銘柄ごとのセンチメント算出（バッチ・チャンク処理、JSON mode）
- 市場レジーム判定（ai.regime_detector）
  - ETF(1321) の 200 日 MA 乖離 + マクロニュース LLM センチメントを合成して日次レジーム（bull/neutral/bear）を判定
- 研究用ファクター計算（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算、将来リターン計算、IC 計算、統計サマリー
- 監査ログ（data.audit）
  - signal_events, order_requests, executions などの監査テーブル定義と初期化ユーティリティ
- 設定・環境変数管理（config）
  - .env 自動ロード（プロジェクトルート検出）、必須設定チェック、各種パスや閾値設定のラッパー

---

## 必要条件 / 依存パッケージ（代表例）

- Python 3.10+
- duckdb
- openai
- defusedxml

（このコードベースには requirements.txt が含まれていません。実行環境に合わせて上記パッケージをインストールしてください。）

例：
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数（主なキー）

必須（少なくとも利用する機能に応じて設定）：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（jquants_client）
- SLACK_BOT_TOKEN — Slack 通知を利用する場合
- SLACK_CHANNEL_ID — Slack 通知先
- KABU_API_PASSWORD — kabuステーション API を使う部分がある場合

OpenAI：
- OPENAI_API_KEY — ai.news_nlp / ai.regime_detector などで使用（関数呼び出し時に引数で渡すことも可）

オプション（デフォルト値あり）：
- KABUSYS_ENV — development / paper_trading / live（デフォルト development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
- KABU_API_BASE_URL — kabu API ベース（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）（デフォルト data/monitoring.db）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- PID_FILE_PATH — 実行プロセスの PID ファイルパス
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — プロセス起動時の .env 自動ロードを無効化（テスト用）

config.Settings からこれらを参照できます（例: from kabusys.config import settings; settings.jquants_refresh_token）。

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # 他に必要なパッケージがあれば追加してください
   ```

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` / `.env.local` を作成すると自動でロードされます（config モジュール）。  
   - 例（.env.example 的な内容）:
     ```
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - 自動ロードを無効にする場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB スキーマ初期化（監査テーブル等）
   - 監査用 DB を初期化する例:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     # または
     conn = init_audit_db(":memory:")
     ```
   - 他テーブルのスキーマ初期化ロジック（data.schema 等）がある場合はそちらを呼ぶ想定です（本サンプルコードでは audit の初期化関数を提供）。

---

## 使い方（代表的な例）

- 日次 ETL の実行
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの AI スコアリング（銘柄別センチメント）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定するか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（別 DB に監査テーブルを作る）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# 以降 conn を使って監査テーブルへアクセス
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

---

## 開発者向けメモ

- テスト時に .env の自動ロードを無効にする:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数にセット
- OpenAI 呼び出しはモジュール内で _call_openai_api を介しており、ユニットテストでは patch により差し替え可能
- J-Quants クライアントは内部でレートリミッターとトークンキャッシュを持つため、大量ページングの際でも自動的にトークンを共有
- DuckDB における executemany の空パラメータ制約など、実運用での互換性処理が組み込まれている

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py (ニュース NLP スコアリング)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント、fetch/save)
  - pipeline.py (ETL パイプライン、run_daily_etl 等)
  - etl.py (ETLResult 再エクスポート)
  - news_collector.py (RSS 収集)
  - calendar_management.py (市場カレンダー管理)
  - quality.py (データ品質チェック)
  - stats.py (zscore_normalize 等統計ユーティリティ)
  - audit.py (監査ログテーブル定義と初期化)
- research/
  - __init__.py
  - factor_research.py (モメンタム/ボラティリティ/バリュー計算)
  - feature_exploration.py (forward returns, IC, summary, rank)

（ここに示したのは主要ファイルの抜粋です。実際のリポジトリに応じて細かなファイルが存在します。）

---

## ライセンス / 貢献

本 README はコードベースの概要説明です。実際に運用する際は、API トークンや個人情報の管理、発注ロジックの安全性、ライブ口座でのリスク管理（paper_trading モードの活用）に十分ご注意ください。

貢献やバグ報告は pull request / issue を通じてお願いします。

---

以上。必要であれば README にサンプル .env.example や requirements.txt、起動スクリプト例（systemd ユニット、cron / Airflow 例）を追加します。どの情報を追加したいか教えてください。