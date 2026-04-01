# KabuSys

KabuSys は日本株のデータプラットフォーム、リサーチ、AI ベースのニュース解析、そして自動売買のための監視・監査機能を備えたライブラリ群です。本リポジトリは、J-Quants や kabu ステーション等の外部 API と連携してデータを取得・整備し、DuckDB をデータ基盤として利用することを想定しています。

主な設計方針：
- ルックアヘッドバイアスを避ける（date/target_date を明示的に扱う）
- DuckDB を中心に SQL + Python で処理を記述
- 外部 API 呼び出しはリトライ・レート制御を行いフェイルセーフ化
- ETL / 品質チェック / 監査テーブルは冪等性を重視

---

## 機能一覧

- データ取得・ETL
  - J-Quants から株価日足 (OHLCV)、財務データ、JPX カレンダーを差分取得・保存（jquants_client）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）

- ニュース収集・NLP（AI）
  - RSS フィード収集と前処理（news_collector）
  - ニュースを銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価（news_nlp.score_news）
  - マクロニュース + ETF (1321) MA200 の乖離から市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクターを計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- カレンダー管理
  - market_calendar の管理、営業日判定、次/前営業日取得（data.calendar_management）

- 監査（Audit / Tracing）
  - signal_events, order_requests, executions の監査スキーマ定義と初期化（data.audit.init_audit_schema / init_audit_db）

- ユーティリティ
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ラッパ（kabusys.config.settings）

---

## 前提 / 必要条件

- Python >= 3.10
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース 等）

インストール方法（例）：
```
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb openai defusedxml
# 開発パッケージやその他依存があれば requirements.txt / pyproject.toml を使用してください
```

---

## 環境変数 / 設定

kabusys.config.Settings で利用される主要な環境変数（一部）：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH (任意, デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
- OPENAI_API_KEY — OpenAI 呼び出し時に使用（score_news / score_regime の api_key を省略した場合に参照）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/...

自動 .env 読み込み：
- プロジェクトルート（.git または pyproject.toml を基準）にある .env および .env.local を自動読み込みします。
  - 優先順位: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをチェックアウト
2. 仮想環境作成・有効化
3. 依存パッケージをインストール（上記参照）
4. プロジェクトルートに .env または .env.local を作成し、必須環境変数を設定
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     KABU_API_PASSWORD=your_kabu_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX
     DUCKDB_PATH=data/kabusys.duckdb
     ```
5. DuckDB 用ディレクトリの作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（基本的な例）

以下は Python REPL / スクリプトでの簡単な利用例です。

- DuckDB 接続を作成して ETL を実行する：
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# ETL を今日で実行
res = run_daily_etl(conn, target_date=date.today())
print(res.to_dict())
```

- ニューススコア（銘柄別 ai_scores の作成）：
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
# target_date に対する前日 15:00 JST ～ 当日 08:30 JST のニュースを対象にスコアを作成
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定（score_regime）：
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査データベースの初期化（監査専用 DB を使う場合）：
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# 別ファイルに監査DBを置くことも可能
audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- カレンダー / 営業日ユーティリティ：
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

各モジュールの関数は例外やログを通じてエラーを報告します。OpenAI や J-Quants 呼び出しには API キーが必要です（関数呼び出し時に api_key を直接渡すことも可能）。

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定の読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py — ニュースの集約・OpenAI による銘柄別センチメント評価
  - regime_detector.py — ETF + マクロニュースを用いた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — 日次 ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult の再エクスポート
  - news_collector.py — RSS 収集・前処理・保存
  - calendar_management.py — JPX カレンダー管理、営業日判定
  - quality.py — データ品質チェック
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログスキーマ初期化・監査DBユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等
- research/*, data/*, ai/* の各関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、データ参照／更新を行います。

---

## ログ / 監視

- 設定（LOG_LEVEL）でログ出力レベルを制御できます。
- monitoring 関連の設定（PID ファイルパスや CPU/MEM/DISK の閾値）は settings から取得します（現コードベースでは設定項目が定義されています。実際の監視機能は別モジュールで実装されます）。

---

## 注意事項

- OpenAI / J-Quants API の呼び出しにはそれぞれ API キーやトークンが必要です。キー管理は .env や環境変数で行ってください。
- DuckDB の executemany の空引数に関する注意（コード内で対処済み）。
- RSS 取得では SSRF 対策やレスポンスサイズ制限等の安全措置を講じていますが、運用環境での追加検証を推奨します。
- 本ライブラリは自動売買のためのコンポーネントを含みますが、発注や実運用前には十分なテスト・リスク管理が必須です。

---

必要であれば、README に「インストール手順（pyproject・requirements）」「CI / テスト実行方法」「API キー発行手順（J-Quants / OpenAI / Slack）」等の詳しい項目を追記できます。どの項目を追加したいか教えてください。