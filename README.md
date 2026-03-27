KabuSys — 日本株自動売買システム
=================================

バージョン: 0.1.0

概要
----
KabuSys は日本株向けのデータプラットフォームと研究／戦略基盤を提供するライブラリです。  
J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）、ニュース収集・NLP による銘柄センチメント算出、研究用のファクター／特徴量モジュール、監査ログ（signal → order → execution のトレーサビリティ）、および ETL/品質チェック等を備えています。

設計上の特徴
- DuckDB を中心とした軽量で高速なデータストア
- J-Quants API / RSS / OpenAI（gpt-4o-mini）等外部 API に対する堅牢なリトライ・レート制御
- ルックアヘッドバイアス回避（日時参照の扱いに注意）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE などで保護）
- 各コンポーネントはテスト差し替えしやすい実装（API 呼び出しの差し替え/モックが容易）

主な機能一覧
- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）、財務データ、マーケットカレンダー取得（pagination・レート制御・トークン自動リフレッシュ対応）
  - day 毎の差分ETL と品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集・NLP
  - RSS フィード収集（SSRF対策、URL正規化、トラッキング除去）
  - OpenAI を使ったニュースセンチメント（ai_scores）算出（バッチ・JSON mode・リトライ）
  - マクロニュース + ETF MA を用いた市場レジーム判定（bull / neutral / bear）
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリ、Zスコア正規化
- 監査ログ（audit）
  - signal_events, order_requests, executions などの監査テーブル生成（DuckDB）
  - 監査DB 初期化ユーティリティ
- カレンダー管理
  - market_calendar による営業日判定、next/prev_trading_day、バッチ更新ジョブ

セットアップ手順
----------------
前提
- Python 3.10 以上（PEP 604 の | 型注釈を使用）
- ネットワークアクセス（J-Quants, OpenAI, RSS）

推奨インストール手順（ローカル開発）
1. リポジトリをクローン
   - git clone ...（省略）

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 最低限の依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   ※プロジェクト配布に requirements.txt がある場合はそれを使用してください。

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと、自動的にロードされます（ただしテスト時等に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - 任意 / デフォルトあり:
     - KABU_API_BASE_URL — kabuapi のベース URL（デフォルト http://localhost:18080/kabusapi）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV — development|paper_trading|live（デフォルト development）
     - LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト INFO）

   .env の例:
   (プロジェクトルートに .env を作る)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

使い方（簡単な例）
-----------------

1) DuckDB 接続を作って日次 ETL を実行する（Python スクリプト、REPL など）:
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

2) ニュースの AI スコアリング（特定日）:
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

3) 市場レジーム判定:
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査DB（order/execution 用）を初期化:
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査ログの INSERT 等を実行
```

5) 研究用ファクター計算の利用例:
```
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
recs = calc_momentum(conn, target_date=date(2026, 3, 20))
# recs は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

主要モジュール / API（抜粋）
- kabusys.config: 環境設定読み込み（.env 自動ロード、settings オブジェクト）
- kabusys.data.pipeline: ETL 実行（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- kabusys.data.jquants_client: J-Quants API クライアント（fetch_*, save_*）
- kabusys.data.news_collector: RSS 取得 / 前処理
- kabusys.ai.news_nlp: ニュースセンチメント算出（score_news）
- kabusys.ai.regime_detector: 市場レジーム判定（score_regime）
- kabusys.research: ファクター計算・解析ユーティリティ
- kabusys.data.audit: 監査テーブルの初期化（init_audit_schema / init_audit_db）
- kabusys.data.quality: 品質チェック（run_all_checks 等）

ディレクトリ構成
----------------
（プロジェクトパッケージ src/kabusys 以下の主なファイル/モジュール）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定ロード
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py     — マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（fetch/save）
    - pipeline.py            — ETL パイプライン（run_daily_etl など）
    - etl.py                 — ETLResult の再エクスポート
    - news_collector.py      — RSS 取得 / 前処理 & 保存ロジック
    - calendar_management.py — 市場カレンダーの管理
    - stats.py               — 統計ユーティリティ（zscore_normalize）
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等
    - feature_exploration.py — 将来リターン・IC・統計要約
  - ai/__init__.py

運用上の注意 / ベストプラクティス
----------------------------------
- API キー／シークレットは .env に保存するか、プロダクションではシークレットマネージャを利用してください。
- settings.env により環境（development / paper_trading / live）を切り替えられます。is_live 等のフラグが提供されています。
- OpenAI 呼び出しはコストがかかるため、バッチ単位やモデル選択に注意してください（デフォルトは gpt-4o-mini）。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB ファイルはデフォルト data/kabusys.duckdb。バックアップ・スナップショット戦略を運用で確立してください。
- J-Quants API のレート制限（120 req/min）を守るよう内部で制御していますが、大量のページネーションや並列化には注意してください。

テスト / モック
---------------
- ai モジュール内の OpenAI 呼び出しは _call_openai_api をモックしやすい設計です（unittest.mock.patch の利用推奨）。
- network IO を伴う関数（fetch_rss、jquants_client._request など）は差し替えやスタブ化が可能です。

ライセンス / コントリビューション
----------------------------------
- 本リポジトリに含まれるライセンスファイルに従ってください（ここでは省略）。

最後に
-----
本 README はコードベースの主要な機能と使い方をまとめたものです。詳細な設計方針や仕様は各モジュールの docstring に記載しています。実運用前に必ずローカルで ETL を実行して動作確認を行い、API キー／DB パス等の設定を適切に行ってください。ご不明点があれば、各モジュールの docstring を参照するか質問してください。