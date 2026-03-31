# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM によるニュース解析、ファクター計算・探索、監査ログ（発注/約定トレーサビリティ）、および市場レジーム判定などを提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要条件・セットアップ手順
- 環境変数 (.env) と設定
- 使い方（サンプル）
- ディレクトリ構成（主要ファイル一覧）
- 補足 / 注意点

---

## プロジェクト概要

KabuSys は日本株のデータパイプライン、リサーチ、ならびに自動売買に必要な共通ユーティリティ群を提供する Python パッケージです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価日足、財務、JPX カレンダー）
- RSS を用いたニュース収集と前処理（SSRF対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（ai_score）や市場レジーム判定
- DuckDB を使ったデータ保存・品質チェック（quality）
- 監査ログ（signal_events / order_requests / executions）スキーマの初期化
- 研究用のファクター計算・特徴量探索ユーティリティ

設計上、バックテスト／学習での Look-ahead バイアスを避けるために、内部処理は明示的な target_date を受け取り、現在日時（datetime.today 等）に依存しない方針です。

---

## 主な機能一覧

- 環境設定管理
  - .env ファイルおよび OS 環境変数の自動読み込み（パスはリポジトリルートから検出）
- データ ETL（kabusys.data.pipeline / etl）
  - run_daily_etl: カレンダー→株価→財務→品質チェックの一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別 ETL
- J-Quants クライアント（kabusys.data.jquants_client）
  - fetch/save: daily_quotes, financial_statements, market_calendar, listed_info
  - トークン自動リフレッシュ、レートリミット、リトライ対応
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、前処理
- ニュース NLP（kabusys.ai.news_nlp）
  - calc_news_window / score_news：銘柄ごとのニュースセンチメント値を取得し ai_scores に保存
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200 日 MA 乖離とマクロニュースの LLM センチメントを合成して日次レジーム判定（bull/neutral/bear）
- リサーチ（kabusys.research）
  - calc_momentum, calc_volatility, calc_value（ファクター計算）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索）
  - zscore_normalize（data.stats）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合チェック
- 監査ログスキーマ（kabusys.data.audit）
  - signal_events / order_requests / executions テーブルの作成、インデックス
  - init_audit_db / init_audit_schema を提供

---

## 必要条件・セットアップ手順

推奨 Python バージョン: 3.9+

1. リポジトリをクローン
   ```
   git clone <このリポジトリ>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）
   - 必須ライブラリ（主要）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージを editable インストール:
     ```
     pip install -e .
     ```
     （setup.py / pyproject.toml がある場合）

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動読み込みされます（デフォルトは OS 環境変数優先）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 環境変数 (.env) と設定

主に以下の環境変数を使用します（必須は README 内で明示）。

- JQUANTS_REFRESH_TOKEN  … J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD      … kabuステーション API パスワード（必須）
- KABU_API_BASE_URL      … kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN        … Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID       … Slack チャンネル ID（必須）
- OPENAI_API_KEY         … OpenAI API キー（score_news / score_regime 実行時に使用）
- DUCKDB_PATH            … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH            … 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH          … 実行プロセスの PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT … 監視閾値
- KABUSYS_ENV            … environment ('development' / 'paper_trading' / 'live'), デフォルト 'development'
- LOG_LEVEL              … ログレベル ('DEBUG','INFO',...)、デフォルト 'INFO'

例（.env.example イメージ）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABU_API_PASSWORD=your_password
```

設定取得は:
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

自動 .env ロードは、プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行われます。

---

## 使い方（サンプル）

以下は代表的な利用例です。実運用ではログ設定・例外処理・API キー管理を適切に行ってください。

- DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントをスコアリングして ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書込み銘柄数:", n_written)
```

- 市場レジームを判定する
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数 OPENAI_API_KEY
```

- リサーチ（モメンタム等）を実行
```python
from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
```

- RSS をフェッチ（news_collector の低レベルユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```

---

## ディレクトリ構成（抜粋）

主要なモジュールと機能を示します。

- src/kabusys/
  - __init__.py                （パッケージ情報: __version__）
  - config.py                  （環境変数・設定管理）
  - ai/
    - __init__.py
    - news_nlp.py              （ニュースセンチメント解析: score_news）
    - regime_detector.py       （市場レジーム判定: score_regime）
  - data/
    - __init__.py
    - calendar_management.py   （市場カレンダーの判定と更新）
    - etl.py                   （ETL インタフェース再エクスポート）
    - pipeline.py              （ETL パイプライン：run_daily_etl 等）
    - jquants_client.py        （J-Quants API クライアント: fetch/save）
    - news_collector.py        （RSS 収集 / 前処理 / SSRF 対策）
    - stats.py                 （統計ユーティリティ: zscore_normalize）
    - quality.py               （品質チェック）
    - audit.py                 （監査ログスキーマ初期化）
  - research/
    - __init__.py
    - factor_research.py       （calc_momentum, calc_value, calc_volatility）
    - feature_exploration.py   （calc_forward_returns, calc_ic, factor_summary, rank）
  - monitoring/ (パッケージ参照のみ、監視関連コードは別に存在する想定)
  - strategy/, execution/     （戦略・約定関連のエントリはパッケージ公開に含める予定）

主要テーブル（コード中で参照される想定）
- raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at)
- raw_financials (code, report_date, period_type, eps, roe, fetched_at, ...)
- market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name)
- raw_news, news_symbols, ai_scores
- market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)
- signal_events, order_requests, executions（監査ログ）

---

## 補足・注意点

- OpenAI 呼び出し、J-Quants API 呼び出しはネットワークや課金が絡むため、実運用・テスト時には API キーやネットワーク制約に注意してください。score_news / score_regime は API キーが未設定の場合 ValueError を送出します。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に行います。テスト時に自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB をデータ格納に使用します。大きなデータを扱う場合はディスク配置やバックアップを検討してください。
- news_collector には SSRF 対策や受信サイズ制限、XML パースの安全対策（defusedxml）を組み込んでいますが、外部 URL を扱うため運用時のリスク管理は必須です。
- ETL は部分的な失敗を許容して他ステップを継続する設計です。run_daily_etl は ETLResult を返し、品質チェックの結果やエラー一覧を確認できます。

---

もし README をプロジェクト用にさらに詳細化（例: API リファレンス、CLI 実行例、.env.example の具体的なテンプレート、依存関係のロックファイル）したければ、用途に応じて追記します。どの部分を充実させたいか教えてください。