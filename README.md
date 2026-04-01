# KabuSys

日本株向け自動売買／データプラットフォーム用ライブラリ。  
データ取得（J-Quants）、ETL、ニュース収集・NLPスコアリング、マーケットレジーム判定、ファクター計算、監査ログ（発注・約定トレーサビリティ）等を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤向けに設計された Python モジュール群です。主に以下の領域をカバーします。

- J-Quants API を用いた株価 / 財務 / マーケットカレンダーの差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集と前処理、OpenAI を使ったニュースのセンチメント評価（銘柄単位）
- マクロニュースと ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
- ファクター（モメンタム / バリュー / ボラティリティ 等）計算、特徴量解析ユーティリティ
- 監査ログ（signal / order_request / executions）用スキーマの初期化ユーティリティ
- データ品質チェック、マーケットカレンダー管理等のデータ基盤機能

設計上の特徴として、ルックアヘッドバイアス対策、冪等保存（INSERT … ON CONFLICT DO UPDATE / DO NOTHING）、API リトライ／バックオフ、DB トランザクション保護、フェイルセーフな挙動（API失敗時のフォールバック）を重視しています。

---

## 機能一覧（主なモジュール）

- kabusys.config
  - .env / .env.local / 環境変数の読み込み管理
  - 設定値（J-Quants トークン、OpenAI、Slack、DB パス、監視閾値 等）
- kabusys.data
  - jquants_client: J-Quants からのデータ取得（日足、財務、カレンダー）と DuckDB への保存
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - news_collector: RSS 取得・前処理と raw_news への保存
  - calendar_management: 営業日判定・next/prev_trading_day 等
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログ（監査テーブル定義・初期化）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: 銘柄毎のニュースセンチメントを取得して ai_scores に保存
  - regime_detector.score_regime: マクロ×ETF 指標から市場レジーム（bull/neutral/bear）判定
- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- そのほか: execution / strategy / monitoring（各種実行・監視ロジックは別モジュールで想定）

---

## 要件

- Python 3.10+（typing の Union | 書式を使用）
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- （ネットワークアクセスが必要）J-Quants API、OpenAI API、RSS ソース など

依存パッケージはプロジェクト配布側で requirements.txt / pyproject.toml にまとめてください。

---

## セットアップ手順（例）

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -r requirements.txt
   （プロジェクトに requirements.txt がない場合は duckdb, openai, defusedxml 等を個別にインストール）

3. 環境変数の準備
   - プロジェクトルートに .env または .env.local を配置できます。
   - 自動ロード順序: OS 環境変数 > .env.local > .env
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 必要な外部 API キーを設定（.env の例）
   - JQUANTS_REFRESH_TOKEN=...
   - OPENAI_API_KEY=...
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...

5. データベース用ディレクトリを作成（デフォルト）
   - data/（DuckDB や SQLite を保存するパスがデフォルト）

---

## 環境変数（主要なキーとデフォルト）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI calls) — OpenAI API キー（score_news / score_regime で参照）
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot Token
- SLACK_CHANNEL_ID (必須) — Slack Channel ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値のパーセンテージ
- KABUSYS_ENV — 環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）

（設定が足りない場合は kabusys.config.Settings 経由で ValueError が発生することがあります）

.env のパースに関する挙動:
- コメント行と空行を無視
- export KEY=val 形式をサポート
- 値はシングル/ダブルクォートの内部でエスケープを解釈
- クォートなしの値は '#' が直前にスペース/タブある場合のみコメントとみなす

---

## 使い方（簡単なコード例）

以下はライブラリの主要な機能を呼び出す簡単な例です。実行には上記の環境変数が必要です。

- DuckDB 接続を開く（設定の duckdb_path を使う）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行（市場カレンダー・株価・財務の差分取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を省略すると今日が対象（ただしカレンダー調整あり）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメント解析（指定日分）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n = score_news(conn, target_date=date(2026, 3, 20))
print(f"written ai_scores: {n}")
```

- 市場レジーム判定（ETF 1321 + マクロセンチメント）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルへ書き込まれます
```

- 監査ログ用 DB 初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# テーブルとインデックスが作成されます
```

- ファクター計算・特徴量解析（研究用）
```python
from kabusys.research.factor_research import calc_momentum
from kabusys.data.stats import zscore_normalize
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- カレンダー操作ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
```

---

## 注意点 / 設計上の留意事項

- ルックアヘッドバイアス（未来情報の利用）を防ぐため、多くの関数は内部で date.today() や datetime.today() を参照しません。外部から target_date を明示的に渡すことでバックテストでの正確性を保ちます。
- OpenAI 呼び出しには API のリトライ・エラーハンドリングを実装していますが、API キー未設定だと例外となります。テスト時は該当モジュールの内部呼び出しをモックすることを推奨します。
- DuckDB の executemany に関する制約（一部バージョン）を考慮した実装になっています（空リストの executemany を避ける等）。
- RSS 取得は SSRF 対策・最大応答サイズ制限・トラッキングパラメータ除去等の安全対策を行っています。

---

## ディレクトリ構成（抜粋）

プロジェクト内の主要ファイル / モジュールツリー（src/kabusys 以下の抜粋）

- src/kabusys/
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
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETLResult エクスポート)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/...（factor/feature utilities）
  - ai/...（ニュース NLP、レジーム検出）
  - monitoring, execution, strategy（エントリポイント・実行ロジック用・実装想定）

---

## 貢献・開発メモ

- テスト時は環境自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI / J-Quants 呼び出し部は外部モックで差し替え可能（内部ヘルパー関数に注入や patch がしやすい設計）
- DuckDB スキーマ初期化・監査テーブル初期化は data.audit モジュールを利用

---

もし README にサンプルの .env.example、requirements.txt、または具体的な実行スクリプト（CLI、サービス化の方法）を追加したい場合は、その目標（例: ETL を cron で実行 / Docker コンテナ化 / systemd サービス化 等）を教えてください。環境に合わせた手順を追記します。