# KabuSys — 日本株自動売買プラットフォーム（README）

概要
---
KabuSys は日本株向けのデータ基盤・研究用ユーティリティ・AI 診断・監査/約定管理を備えた自動売買支援ライブラリです。主要コンポーネントは以下です。

- データETL（J‑Quants から日足・財務・カレンダーを取得して DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- マーケットカレンダー管理（営業日判定・前後営業日探索）
- ニュース収集（RSS）と銘柄紐付け
- ニュース NLP（OpenAI を用いた銘柄別センチメントスコア）
- 市場レジーム判定（ETF の MA200 乖離とマクロニュースの LLM スコアを合成）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal → order_request → executions を辿れる監査テーブル）
- J‑Quants クライアント（レート制御・リトライ・トークンリフレッシュ対応）

設計上の要点として、ルックアヘッドバイアスを避けるために内部で現在日時を恣意的に参照しない設計、DuckDB を中心とした idempotent な保存、外部 API 呼び出しに対するフェイルセーフ（API 失敗時は処理継続）を重視しています。

機能一覧
---
- ETL:
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得・バックフィル対応）
- J‑Quants API クライアント:
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, fetch_listed_info
  - save_daily_quotes, save_financial_statements, save_market_calendar（DuckDB へ冪等保存）
- データ品質:
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- ニュース:
  - fetch_rss, preprocess_text, news → raw_news 保存（SSRF・XML 攻撃対策、トラッキング除去）
- AI:
  - score_news (銘柄別ニュースセンチメント), score_regime (市場レジーム判定)
- 研究用:
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- 監査・約定:
  - init_audit_db, init_audit_schema（監査用 DuckDB 初期化）
- ユーティリティ:
  - 環境設定管理（kabusys.config.Settings）、.env 自動ロード機能

セットアップ手順
---
前提
- Python 3.10 以上（typing の | 演算子等を使用）
- ネットワークアクセス（J‑Quants / OpenAI / RSS）

1. リポジトリをクローン
   ```bash
   git clone <your-repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージインストール
   必要な主要パッケージ:
   - duckdb
   - openai
   - defusedxml

   例:
   ```bash
   pip install duckdb openai defusedxml
   # または開発向けに requirements を用意している場合はそれを使用
   # pip install -e .
   ```

4. 環境変数（.env）を準備
   プロジェクトルート（.git もしくは pyproject.toml があるパス）に `.env` または `.env.local` を置くと自動で読み込まれます（起動時）。
   自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   基本的に設定が必要なキー（例）
   - JQUANTS_REFRESH_TOKEN=...     # J‑Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY=...           # OpenAI API キー（score_news / regime に必要）
   - KABU_API_PASSWORD=...        # kabu ステーション API パスワード（発注等がある場合）
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意
   - LINE_CHANNEL_ACCESS_TOKEN=...  # 通知が必要なら
   - LINE_USER_ID=...               # 通知向けユーザID
   - DUCKDB_PATH=data/kabusys.duckdb  # DuckDB 保存先（デフォルト）
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|...

   ※ .env の書式はシェルの export/KEY=val やクォート等に対応しています。

5. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

初期化例（監査 DB）
```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)
# conn は duckdb の接続オブジェクトです
```

使い方（簡単な例）
---
以下は最小限の使い方例です。DuckDB の接続に settings.duckdb_path を使う想定です。

- 日次 ETL を実行する
```python
from duckdb import connect
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を与えて特定日を処理可能
print(result.to_dict())
```

- ニュースセンチメント（銘柄別）をスコア化（OpenAI API キー必須）
```python
from duckdb import connect
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news
from datetime import date

conn = connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
```

- 市場レジーム判定
```python
from duckdb import connect
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,20))
# market_regime テーブルへ結果を書き込みます
```

- ファクター計算（研究用）
```python
from duckdb import connect
from kabusys.research.factor_research import calc_momentum

conn = connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄の dict のリスト
```

- 監査スキーマ初期化（ファイル作成）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
```

設定の自動読み込みについて
---
- パッケージ起動時に .env / .env.local をプロジェクトルートから自動読み込みします（OS 環境変数が優先、.env.local が .env を上書き）。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 必須の設定値が未設定の場合、kabusys.config.Settings のプロパティで ValueError が発生します（例: JQUANTS_REFRESH_TOKEN）。

主要な API と挙動メモ
---
- J‑Quants クライアントは内部で固定間隔の RateLimiter を使い、最大リトライとトークン自動リフレッシュ（401→再取得）をサポートします。
- OpenAI 呼び出しは gpt-4o-mini を想定し、JSON mode を使って厳密な JSON を期待します。API エラー時はフェイルセーフでスコアを 0.0 にフォールバックする設計箇所があります。
- ETL は可能な限り冪等（ON CONFLICT DO UPDATE / DO NOTHING）で設計されています。
- 研究用モジュールはバックテストでのルックアヘッドバイアスを避けるため、内部で date.today() 等を直接参照しない設計です。

ディレクトリ構成（抜粋）
---
src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数 / 設定管理（.env 自動ロード）
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリング（銘柄別）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロニュース）
- data/
  - __init__.py
  - jquants_client.py — J‑Quants API クライアント（取得・保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - quality.py — データ品質チェック
  - news_collector.py — RSS ニュース取得・前処理
  - calendar_management.py — マーケットカレンダー管理
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - audit.py — 監査ログテーブル定義 / 初期化
  - etl.py — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等の計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- research/ 以下ファイル群 — 研究用補助関数

トラブルシューティング（よくある問題）
---
- OpenAI の API キーが未設定 → score_news / score_regime が ValueError を投げます。ENV: OPENAI_API_KEY を設定してください。
- J‑Quants トークンが未設定 → get_id_token が失敗します。ENV: JQUANTS_REFRESH_TOKEN を設定してください。
- DuckDB ファイルの書き込み権限がない → データ保存時にエラーになります。ディレクトリのパーミッションを確認してください。
- RSS 取得で XML パースエラー → 該当フィードをスキップします（ログに警告）。

貢献・拡張
---
- 新たなニュースソース追加は data/news_collector.DEFAULT_RSS_SOURCES に追加するか、外部で fetch_rss を呼んで raw_news に保存するワークフローを作成してください。
- 取引執行（kabu ステーション連携）部分は発注ロジックを追加することで統合可能です（現在は設定の枠組みと監査テーブルを提供）。

ライセンス
---
（リポジトリにライセンス情報があればここに記載してください）

---

必要であれば README に具体的な .env.example の例や、requirements.txt、簡単なワークフロー（cron での run_daily_etl、監視の仕組み等）を追記します。どの情報を追加したいか教えてください。