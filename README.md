# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株向けのデータプラットフォーム／リサーチ／自動売買支援ライブラリです。  
主に以下を目的とします。

- J-Quants API からのデータ取得（OHLCV、財務、JPXカレンダー）
- DuckDB を用いたデータ格納・ETL パイプライン
- ニュースの NLP（LLM）による銘柄センチメント算出
- 市場レジーム判定（MA200 とマクロニュースの組合せ）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）スキーマ提供
- 研究用ファクター計算・特徴量解析ユーティリティ

主な機能
--------
- data/jquants_client: J-Quants API クライアント（取得・保存・ページネーション・リトライ・レート制御）
- data/pipeline: 日次 ETL（価格・財務・カレンダー）および品質チェック（欠損・スパイク・重複・日付不整合）
- data/news_collector: RSS 収集、前処理、raw_news 保存（SSRF対策・トラッキング削除・gzip/size保護）
- data/calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
- data/audit: 監査ログ（signal_events / order_requests / executions）スキーマ初期化
- ai/news_nlp: ニュースを LLM（gpt-4o-mini）でバッチ評価して ai_scores テーブルへ書き込む
- ai/regime_detector: ETF(1321)のMA200乖離とマクロニュースセンチメントを合成して市場レジーム判定
- research: ファクター計算（モメンタム・バリュー・ボラティリティ）と特徴量解析ユーティリティ
- config: 環境変数管理（.env / .env.local 自動ロード、必須チェック）

動作環境・依存
---------------
- Python 3.10+
- 必須パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリに依存する部分が多く、上記主要ライブラリのみ追加してください。

インストール（開発環境例）
------------------------
1. 仮想環境作成・アクティベート:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール:
   - pip install duckdb openai defusedxml

3. （推奨）パッケージを編集可能インストール:
   - pip install -e .

環境変数 / .env
----------------
パッケージは起動時にプロジェクトルート（.git または pyproject.toml を含むディレクトリ）を探索し、以下の順で自動的に .env を読み込みます:

1. OS 環境変数（最優先）
2. .env.local（存在すれば上書き）
3. .env（存在すれば読み込み）

自動読み込みを無効にするには環境変数を設定:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主要な環境変数（必須は明記）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- OPENAI_API_KEY — OpenAI 呼び出しに使用（ai モジュールを使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 動作モード: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

セットアップ手順（概要）
---------------------
1. 必要パッケージをインストール（上記参照）
2. .env を作成し必須キーを設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）
3. DuckDB データベース用ディレクトリを作成（例: mkdir -p data）
4. ETL 等を実行して初期データを取り込む

使い方（代表的なコード例）
------------------------

- DuckDB 接続を作り日次 ETL を実行する例:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("wrote", n_written)
```

- 市場レジーム判定を実行する:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する:
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセスできます
```

主要 API / エントリポイント
--------------------------
- kabusys.data.pipeline.run_daily_etl(...) — 日次 ETL のメイン
- kabusys.data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl — 個別 ETL ジョブ
- kabusys.data.quality.run_all_checks(...) — データ品質チェック
- kabusys.data.jquants_client.fetch_* / save_* — J-Quants API 経由の取得・保存ユーティリティ
- kabusys.ai.news_nlp.score_news(...) — LLM によるニューススコアリング
- kabusys.ai.regime_detector.score_regime(...) — 市場レジーム判定
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログ初期化
- kabusys.research.* — 研究用ファクター・統計ユーティリティ（calc_momentum 等）

ディレクトリ構成（抜粋）
-----------------------
プロジェクトは src/kabusys 配下にモジュールが配置されています（主要ファイル）:

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py
- src/kabusys/data/
  - jquants_client.py
  - pipeline.py
  - etl.py (alias)
  - calendar_management.py
  - news_collector.py
  - quality.py
  - stats.py
  - audit.py
  - __init__.py
  - その他（etl / schema utilities）
- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- src/kabusys/monitoring, execution, strategy など（パッケージ公開対象として __all__ に含まれることを想定）

注意点・開発メモ
----------------
- Look-ahead バイアス回避: 多くの関数は組み込みの date.today() / datetime.today() に依存せず、明示的な target_date を引数で受け取る設計です。バックテスト用に非常に重要です。
- .env のパースはシェル風（export 対応・クォート・コメント対応）に実装されています。特殊な書式の .env を使用する場合は注意してください。
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode を利用します（response_format={"type": "json_object"}）。API の失敗時はフェイルセーフでスコアを 0.0 にフォールバックする設計です。
- RSS 収集は SSRF 対策、gzip/BOM 対策、最大受信サイズ制限などを備えています。
- DuckDB への一括書き込みでは executemany を活用し、空パラメータによる互換性問題（DuckDB 0.10 等）に配慮しています。
- KABUSYS_ENV によって実行モードが変わります（development / paper_trading / live）。本番環境では is_live フラグ等を利用して安全策を導入してください。

ライセンス・貢献
----------------
このリポジトリのライセンス情報はプロジェクトルートの LICENSE を参照してください。バグ報告や機能追加は Issue / PR を通して行ってください。

お問い合わせ
------------
実運用向けの設定や API キー管理、モニタリング設計については README に記載の連絡先（Slack 等）にお問い合わせください。README 内で使われる Slack 関連設定は SLACK_BOT_TOKEN / SLACK_CHANNEL_ID を利用します。

以上。必要があれば README に「実行例の詳細」「.env.example 例」「DB スキーマ定義」を追加します。どの追加情報が必要か教えてください。