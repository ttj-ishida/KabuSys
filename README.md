# KabuSys

日本株向け自動売買プラットフォームのライブラリ群（データETL / ニュースNLP / 研究用ファクター / 監査ログ等）。  
このリポジトリはデータ収集から品質チェック、ファクター計算、AIを使ったニュースセンチメント評価、監査ログの初期化までをモジュール単位で提供します。

バージョン: 0.1.0

---

## 機能一覧

- 環境変数・設定管理
  - .env / .env.local を自動読み込み（プロジェクトルートに .git または pyproject.toml がある場合）
  - 必須設定の取得とバリデーション
- Data（データプラットフォーム）
  - J-Quants API クライアント（差分取得、ページネーション、IDトークンリフレッシュ、レート制御）
  - ETL パイプライン（株価・財務・カレンダーの差分取得、保存、品質チェック）
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
  - 市場カレンダー管理（営業日判定 / next/prev / 範囲取得 / 夜間更新ジョブ）
  - ニュース収集（RSS 取得、SSRF/サイズ/トラッキングパラメータ対策、raw_news 保存用の前処理）
  - 監査ログ（signal_events / order_requests / executions のDDL・初期化処理）
  - 各種ユーティリティ（統計、Zスコア正規化 等）
- AI（OpenAI を利用した機能）
  - ニュースセンチメント（銘柄単位に LLM でスコア化、ai_scores へ書き込み）
  - 市場レジーム判定（ETF 1321 の MA とマクロニュース LLM を合成し bull/neutral/bear を判定）
  - API 呼び出しに対するリトライ・フォールバック実装
- Research（研究用ユーティリティ）
  - ファクター計算（Momentum, Value, Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク変換

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈に | を使用しているため）
- システムに duckdb がインストール可能であること

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (macOS / Linux)
   - .venv\Scripts\activate     (Windows PowerShell)

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 最低限必要な主要パッケージ:
     - pip install duckdb openai defusedxml

   （プロジェクトの実行に Slack クライアント等が必要な場合は別途追加）

4. 環境変数を設定
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます（ただし、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすれば自動ロードを無効化できます）。
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_api_password>
     - OPENAI_API_KEY=<openai_api_key>           (score_news / score_regime で使用)
     - SLACK_BOT_TOKEN=<slack_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...

   - settings モジュールからプログラム上でアクセス可能:
     - from kabusys.config import settings
     - settings.jquants_refresh_token など

注意: .env の読み込み優先順位は OS 環境変数 > .env.local > .env です。OS環境変数は保護され、.env からは上書きされません。

---

## 使い方（主要な API と実行例）

以下は Python スクリプトや REPL から直接呼び出す典型的な利用例です。

1. DuckDB 接続の作成
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2. 日次 ETL（市場カレンダー、株価、財務、品質チェックを一括で実行）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3. ニューススコアリング（OpenAI が必要）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# api_key を明示的に渡すか、環境変数 OPENAI_API_KEY を設定
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {n} codes")
```

4. 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5. 監査ログ用 DB の初期化（監査専用 DB を分けて運用する場合）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# init_audit_schema は init_audit_db 内で transactional=True で実行済み
```

6. 市場カレンダーの判定ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 3, 20)
is_open = is_trading_day(conn, d)
next_open = next_trading_day(conn, d)
```

7. J-Quants からデータを直接取得（ETL 層を使わず fetch_* を呼ぶ）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token

id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
quotes = fetch_daily_quotes(id_token=id_token, date_from=date(2026,1,1), date_to=date(2026,3,20))
```

8. RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
```

注意点:
- OpenAI の呼び出しは gpt-4o-mini などを用い、レスポンスは JSON Mode を期待しています。API の失敗時はフォールバック（ゼロスコア等）を行う実装が含まれていますが、APIキーは必須です。
- DuckDB 側のスキーマは前提となるテーブル名（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime 等）を使います。ETL やスキーマ初期化処理は別途用意されている、または手動で作成する必要があります（README 内のスキーマ初期化関数を参照）。

---

## よく使うモジュール一覧（簡易説明）

- kabusys.config
  - 環境変数の読み込み / settings オブジェクト
- kabusys.data.jquants_client
  - J-Quants API との通信・保存ロジック（fetch_*/save_*）
- kabusys.data.pipeline
  - ETL の上位統括（run_daily_etl 他）
- kabusys.data.quality
  - データ品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.calendar_management
  - 市場カレンダー管理（is_trading_day, next_trading_day 等）
- kabusys.data.news_collector
  - RSS 取得・前処理（SSRF/サイズ制限/トラッキング除去）
- kabusys.ai.news_nlp
  - 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に書き込む
- kabusys.ai.regime_detector
  - マクロニュース + ETF MA を合成して市場レジームを判定
- kabusys.research.*
  - ファクター・特徴量解析ユーティリティ（calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank）
- kabusys.data.audit
  - 監査ログ（signal_events / order_requests / executions）DDL と初期化関数

---

## ディレクトリ構成

リポジトリの主要ファイル配置（抜粋・概略）:

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（factor / feature exploration modules）
- src/kabusys/ai, src/kabusys/data, src/kabusys/research はそれぞれ上記機能群を提供

（実際のリポジトリには上記以外にもユーティリティや追加モジュールが入る可能性があります）

---

## 補足・運用上の注意

- Look-ahead bias 回避: 多くのモジュールで date や target_date を明示的に受け取り、datetime.today() を内部で用いない設計になっています。バックテスト等で過去の状態を再現する際は target_date を必ず明示してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）から探索します。CIやテストで自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API のレート制御やリトライ等は jquants_client 内で実装されています。API の仕様変更やレート上限変更があった場合は該当モジュールの調整が必要です。
- OpenAI 呼び出しは外部 API のため、コストとレイテンシを考慮してバッチサイズやトークン使用量の調整を行ってください。

---

この README はコードベースからの要約です。具体的な運用（DB スキーマ初期化スクリプト、CI、デプロイ手順、requirements.txt 等）はプロジェクト固有のポリシーに従って整備してください。必要であれば README に追加したい運用手順やサンプル .env.example を提供します。