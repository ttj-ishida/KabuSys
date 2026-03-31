# KabuSys

KabuSys は日本株のデータプラットフォームと研究・自動売買のためのライブラリ群です。J-Quants / kabuステーション / RSS / OpenAI 等の外部サービスと連携して、データ取得（ETL）、データ品質チェック、ニュース NLP（LLM）によるセンチメント評価、マーケットレジーム判定、ファクター計算、監査ログ管理までを含む一連の処理を提供します。

バージョン: 0.1.0

---

## 概要

主な目的は以下です。

- J-Quants API からの株価・財務・カレンダー取得（差分ETL、ページネーション対応、冪等保存）
- DuckDB を用いた時系列データの保存・クエリ処理
- RSS からのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄別・マクロ判定）
- 市場レジーム（bull/neutral/bear）判定
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索ユーティリティ
- データ品質チェックと監査ログ（発注〜約定のトレース性確保）
- 環境変数管理（.env/.env.local の自動ロード機能）

---

## 機能一覧

- 環境設定
  - .env/.env.local の自動ロード（プロジェクトルートの検出、OS 環境変数優先）
  - 必須環境変数を settings から取得可能

- データ取得（jquants_client）
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_* 系で DuckDB へ冪等保存（ON CONFLICT DO UPDATE）
  - レートリミッタ、リトライ、401 トークンリフレッシュ対応

- ETL パイプライン（data.pipeline）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult を返し、品質チェック結果・エラーを集約

- カレンダー管理（data.calendar_management）
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
  - calendar_update_job（J-Quants から差分取得して market_calendar を更新）

- データ品質チェック（data.quality）
  - 欠損データ検出 / スパイク検出 / 重複チェック / 日付整合性チェック
  - QualityIssue オブジェクトで問題を詳細に返す

- ニュース収集（data.news_collector）
  - RSS フィード取得、前処理、ID 生成、SSRF 対策、gzip 制限、トラッキング除去

- ニュース NLP（ai.news_nlp）
  - calc_news_window / score_news（銘柄別に LLM でセンチメントを算出して ai_scores に書き込み）
  - バッチ処理、JSON Mode、レスポンス検証、クリップ・リトライ処理

- 市場レジーム判定（ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロセンチメントを合成してレジーム判定
  - OpenAI 呼び出し、スコア合成、market_regime テーブルへ冪等書き込み

- 研究用ユーティリティ（research）
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank / zscore_normalize

- 監査ログ（data.audit）
  - signal_events, order_requests, executions テーブルの DDL・初期化（init_audit_schema / init_audit_db）
  - 監査のためのインデックス・UTC タイムゾーン設定

---

## 必要条件

- Python 3.9+（タイプヒントで union types 等を使用）
- 推奨パッケージ（requirements）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外に urllib, json, etc. は標準で利用）
- 外部 API アクセス
  - J-Quants API（リフレッシュトークン）
  - OpenAI API（OPENAI_API_KEY）
  - kabuステーション（必要に応じて）

---

## 環境変数

主に以下の環境変数を使用します（settings で参照）:

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で必要）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1 を設定）

.env 自動ロードの挙動:
- プロジェクトルート（.git または pyproject.toml のある親ディレクトリ）を基準に .env を読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env（.env.local は既存の OS 環境変数を保護しつつ上書き可）
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローンし、ワークディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   - 最低限:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発パッケージやその他ツールがある場合はプロジェクトの requirements.txt / pyproject.toml に従ってください。

4. 環境変数を設定
   - プロジェクトルートに .env を作成するか、環境変数として設定します（上記参照）。
   - 自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1。

5. データベースファイルの準備
   - デフォルトの DuckDB ファイルは settings.duckdb_path（例: data/kabusys.duckdb）です。初回は空のファイルを作成するか、必要なスキーマを初期化してください。
   - 監査用 DB を別に初期化する場合は data.audit.init_audit_db を使用します。

---

## 使い方（基本例）

以下は主要な機能を呼び出す際の簡単なサンプルです。全て DuckDB 接続（duckdb.connect）に対して操作します。

- DuckDB 接続の取得:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行:
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントのスコアリング（target_date に対して前日 15:00 JST 〜 当日 08:30 JST を対象）:
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written_count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None → 環境変数 OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written_count}")
```

- 市場レジーム判定:
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- ファクター算出（モメンタム例）:
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date":..., "code": "XXXX", "mom_1m": ..., "ma200_dev": ...}, ...]
```

- 監査ログ用 DB を初期化:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を用いて order/signals を記録可能
```

- RSS フィードの取得（ニュースコレクタの低レベル関数）:
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

注意点:
- OpenAI を利用する関数は api_key 引数でキー注入可能（テスト用）。None の場合は環境変数 OPENAI_API_KEY を参照します。未設定時は ValueError が発生します。
- ETL / データ取得は API レートやネットワークエラーを考慮した実装になっていますが、実行環境での API 制限に注意してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なモジュール構成は以下の通りです（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                          — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       — ニュース NLP（銘柄別スコア）
    - regime_detector.py                — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py                 — J-Quants API クライアント（取得・保存）
    - pipeline.py                       — ETL パイプライン（run_daily_etl 等）
    - etl.py                            — ETLResult のエクスポート
    - calendar_management.py            — 市場カレンダー管理
    - news_collector.py                 — RSS ニュース収集
    - quality.py                        — データ品質チェック
    - stats.py                          — 統計ユーティリティ（zscore 等）
    - audit.py                          — 監査ログ初期化 / DDL
  - research/
    - __init__.py
    - factor_research.py                — ファクター計算（momentum/value/volatility）
    - feature_exploration.py            — forward_returns, IC, summary, rank

各モジュールは単一責務を目指して設計されており、DuckDB 接続を受け取る関数は副作用を最小限にして明示的に DB 操作を行います。

---

## 補足・設計方針（抜粋）

- ルックアヘッドバイアス回避: バックテスト・スコア計算時に datetime.today() を不用意に参照しない設計。target_date を呼び出し側が渡すことで時点制御を行います。
- 冪等性: ETL / 保存処理は ON CONFLICT DO UPDATE を使い冪等に保存します。
- フェイルセーフ: LLM/API の失敗時はスコアを 0 にフォールバックする等、致命的な停止を避ける設計が随所にあります（ただし重要な設定未定義は例外）。
- セキュリティ: RSS 取得での SSRF 防止、XML パーサでの defusedxml 使用、レスポンスサイズ制限などを実装。

---

## 開発・拡張

- テスト: 各 LLM 呼び出しや外部 I/O はモック可能（モジュール内の _call_openai_api や _urlopen を差し替え）。ユニットテストで重要です。
- 追加機能: 発注実装、モニタリング / アラート、Slack 通知連携等は既存の設定 / テーブルを活用して拡張可能です。

---

ご不明点や README に追加したい利用例（例えば発注フロー、Slack 通知の使い方、具体的な DuckDB スキーマ）等があれば教えてください。必要に応じてサンプルスクリプトや .env.example を作成します。