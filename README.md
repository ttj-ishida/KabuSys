# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → AI ニュースセンチメント → 監査ログ（約定トレース）までを一貫して提供します。

主に研究（research）、データ（data）、AI（news sentiment / regime 判定）、監視・実行層の基盤機能を含みます。

---

## 特長（概要）

- J-Quants API からの差分取得（株価・財務・JPX カレンダー）と DuckDB への冪等保存
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- ニュースの収集・前処理（RSS）、OpenAI を用いた銘柄ごとのニュースセンチメントスコア化
- マーケットレジーム判定（ETF 1321 の MA200 乖離 × マクロニュースセンチメント）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zscore 正規化）
- 監査ログスキーマ（signal → order_request → execution のトレースを完全保存）
- 自動環境変数ロード（プロジェクトルートの `.env` / `.env.local` から）

---

## 機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS の取得・正規化・SSRF 対策）
  - データ品質チェック（check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news: 銘柄ごとの AI スコア作成）
  - レジーム判定（score_regime: MA + マクロニュースで bull/neutral/bear 判定）
- research/
  - ファクター計算（momentum / value / volatility）
  - 特徴量探索（forward returns / IC / summary / rank）
- config.py
  - 環境変数管理（.env 自動ロード、必須チェック、設定プロパティ）
- audit schema
  - signal_events / order_requests / executions の DDL とインデックス

---

## 必要環境 / 依存

- Python 3.10+
- 必要な外部パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリ（urllib, datetime, json, logging など）

（プロジェクトに requirements.txt や Poetry 設定がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <REPO_URL>
2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - またはプロジェクト配布の requirements.txt / poetry を利用
4. パッケージを開発編集モードでインストール（任意）
   - pip install -e .
5. 環境変数設定
   - プロジェクトルート（`.git` または `pyproject.toml` があるディレクトリ）に `.env` を作成すると、自動で読み込まれます（`.env.local` は `.env` を上書き）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

必須の環境変数（最低限）：
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携等）

OpenAI を使う機能を使う場合：
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に未指定時に使用）

その他（任意・デフォルトあり）：
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など監視用設定
- KABUSYS_ENV（development / paper_trading / live）
- LOG_LEVEL（DEBUG/INFO/...）

注意: config.Settings 中の `settings.jquants_refresh_token` などは未設定時に ValueError を出します。`.env.example` を参考にしてください。

---

## 基本的な使い方（コード例）

以下は Python スクリプトからライブラリ機能を利用する例です。どの関数も「target_date」を明示的に受け取る設計で、ルックアヘッドバイアスを避けられます。

- DuckDB 接続準備（設定の DB パスを利用）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査 DB 初期化（監査用の独立 DB を初期化）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- 日次 ETL 実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API 必須）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使う
print(f"written: {n_written}")
```

- マーケットレジーム判定（OpenAI API 必須）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監視用ユーティリティ（例: カレンダー判定）
```python
from kabusys.data.calendar_management import is_trading_day
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
print(is_trading_day(conn, date(2026, 1, 1)))
```

- 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

---

## 注意点 / 設計上の要点

- Look-ahead バイアス対策:
  - 多くの処理は target_date を明示的に受け取り、内部で datetime.now()/date.today() を参照しないよう設計されています。バッチ実行やバックテストで安全に使えます。
- 自動環境ロード:
  - `config.py` はプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に `.env` / `.env.local` を読み込みます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能です。
- 冪等性:
  - ETL の保存は ON CONFLICT DO UPDATE を使うことで冪等。
  - 監査ログの order_request_id / broker_execution_id 等は冪等キー設計。
- 外部 API エラー: J-Quants / OpenAI 呼び出しにはリトライ・バックオフが実装されています。API 失敗時は安全側（スコア 0 やスキップ）で継続するケースが多いです。
- RSS ニュース収集では SSRF 対策、受信サイズ制限、XML パースの安全化（defusedxml）などの対策を実装しています。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメントのスコアリング（OpenAI）
    - regime_detector.py  — ETF MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - pipeline.py         — ETL パイプラインと run_daily_etl
    - calendar_management.py — 市場カレンダー管理
    - news_collector.py   — RSS 収集と前処理（SSRF 対策）
    - quality.py          — データ品質チェック
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
    - etl.py              — ETLResult のエクスポート
  - research/
    - __init__.py
    - factor_research.py  — momentum, value, volatility の計算
    - feature_exploration.py — forward return / IC / summary / rank
  - research/（上記）
  - ai/（上記）

各モジュールの docstring に設計方針や処理フローが詳述されています。運用や拡張の際はそれらを参照してください。

---

## よくある運用ワークフロー（例）

1. nightly cron:
   - run_daily_etl を呼んでデータを更新・保存 → 品質チェックを実行して問題を通知
2. news pipeline（夜間バッチ）:
   - RSS を収集して raw_news に保存 → score_news を呼んで ai_scores を更新
3. daily regime scoring:
   - score_regime を呼んで market_regime テーブルを更新（戦略のモード切替に利用）
4. 研究:
   - research モジュールでファクター算出 → zscore 正規化 → バックテスト用データ生成
5. 実行・監査:
   - 発注系は監査ログ（order_requests / executions）を用いて完全トレースを保持

---

## 最後に

この README はコードベースの主要機能と使い方の要点をまとめたものです。各モジュール内の docstring（関数やクラスの説明）を参照するとより詳細な実装意図や注意点が書かれています。実運用・本番発注を行う場合は設定（KABUSYS_ENV）や監査フロー、発注の冪等性・リスク管理を十分にレビューしてください。