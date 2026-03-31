KabuSys
=======

バージョン: 0.1.0

概要
----
KabuSys は日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants からの時系列データ取得・ETL、ニュース収集と LLM を用いたニュースセンチメント評価、マーケットカレンダー管理、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、自動売買システムの主要コンポーネントを提供します。

主な特徴（機能一覧）
------------------
- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - run_daily_etl による日次 ETL パイプライン（品質チェック含む）
  - レート制限、リトライ、トークン自動リフレッシュに対応
- ニュース収集
  - RSS フィード取得（SSRF 対策、トラッキングパラメータ除去、サイズ制限）
  - raw_news / news_symbols への冪等保存を想定
- ニュース NLP（LLM）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコア算出（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）
  - JSON Mode、リトライ・フォールバックロジック、レスポンスバリデーション実装
- データ品質チェック
  - 欠損、重複、スパイク（前日比）や日付整合性チェック（run_all_checks）
- カレンダー管理
  - JPX カレンダーの差分取得と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）
- リサーチ / ファクター
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions 等の監査テーブル初期化・保守（init_audit_schema / init_audit_db）
- 設定管理
  - .env（.env.local）または環境変数から設定読み込み（自動ロードを無効化するフラグあり）
  - settings オブジェクト経由で各種秘密鍵パスなどを参照可能

セットアップ手順
----------------

前提
- Python 3.10 以上（型ヒントに | を使用）
- ネットワーク接続（J-Quants / OpenAI などへのアクセス）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要なパッケージをインストール
   - 主要依存（例）:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに pyproject.toml / requirements.txt があればそれに従ってください）
   パッケージを開発モードでインストールする場合:
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - 推奨: プロジェクトルートに .env / .env.local を置く（自動ロードされます）
   - 無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

必須の主な環境変数
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（get_id_token 用）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 用）
- KABU_API_PASSWORD     : kabuステーション API パスワード（発注等で使用）
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack 通知先チャネル ID

ファイル例（.env の最小例）
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C0123456789
```

使い方（簡単なコード例）
-----------------------

共通: DuckDB 接続を作成してモジュール関数に渡す。既定の DB パスは settings.duckdb_path（data/kabusys.duckdb）。

1) ETL（デイリー実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（AI）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"書き込み銘柄数: {written}")
```
- api_key を None にすると環境変数 OPENAI_API_KEY を参照します。

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ DB 初期化（独立 DB を使う例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.db")
# conn を使って監査テーブルにアクセス可能
```

5) ファクター計算／研究
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト
```

6) ニュース収集（RSS 取得）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
```
- fetch_rss は内部で SSRF や大容量応答、XML インジェクション対策（defusedxml）を行います。

設定管理のポイント
------------------
- settings オブジェクト（kabusys.config.settings）から各種パラメータにプログラム的にアクセス可能
- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を起点）を探索して .env / .env.local を読み込みます
- 自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

主な公開 API（抜粋）
-------------------
- kabusys.data.pipeline.run_daily_etl(...)
- kabusys.data.jquants_client.fetch_daily_quotes(...)
- kabusys.data.jquants_client.save_daily_quotes(...)
- kabusys.data.news_collector.fetch_rss(...)
- kabusys.ai.news_nlp.score_news(...)
- kabusys.ai.regime_detector.score_regime(...)
- kabusys.data.audit.init_audit_db / init_audit_schema(...)
- kabusys.research.factor_research.calc_momentum / calc_volatility / calc_value
- kabusys.research.feature_exploration.calc_forward_returns / calc_ic / factor_summary
- kabusys.data.quality.run_all_checks(...)

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py (パッケージ定義、バージョン)
- config.py (環境変数・設定管理)
- ai/
  - __init__.py
  - news_nlp.py (ニューススコアリング、OpenAI 呼出し)
  - regime_detector.py (市場レジーム判定)
- data/
  - __init__.py
  - jquants_client.py (J-Quants API クライアント + DuckDB 保存)
  - pipeline.py (ETL パイプライン)
  - etl.py (ETLResult の再エクスポート)
  - news_collector.py (RSS 収集)
  - calendar_management.py (マーケットカレンダー管理)
  - quality.py (データ品質チェック)
  - stats.py (統計ユーティリティ)
  - audit.py (監査ログスキーマ初期化)
- research/
  - __init__.py
  - factor_research.py (ファクター計算)
  - feature_exploration.py (将来リターン・IC 等)

注意事項 / ベストプラクティス
----------------------------
- Look-ahead バイアス防止:
  - モジュール内では datetime.today() / date.today() を不用意に参照せず、target_date を明示的に渡す設計です。バックテストや再現性を保つため呼び出し側で日付を明示してください。
- OpenAI 呼び出し:
  - API エラーやレート制限時のフォールバック（スコア = 0.0 やスキップ）を実装していますが、運用では API キーとコスト管理に注意してください。
- DuckDB:
  - executemany に空リストを渡すとエラーになるバージョンがあるため、呼び出し箇所で空チェックを行っています。DuckDB をアップデートする場合は互換性を確認してください。
- 自動 .env ロード:
  - 開発環境で .env を使う場合は .env.local を使ってローカル上書きすると、プロジェクト側で .env -> .env.local の順で読み込み・上書きされます。

ライセンス / コントリビューション
--------------------------------
（この README ではライセンス情報・貢献方法に関する記載は含めていません。必要に応じてプロジェクトルートに LICENSE / CONTRIBUTING.md を追加してください。）

サポート / 問い合わせ
--------------------
不具合や質問は Issue を立ててください。設計意図や API 詳細はソース内の docstring を参照してください。

---  
以上が KabuSys の概要と利用方法のまとめです。必要であれば README に含めるサンプル .env.example や CLI 実行例、依存関係ファイル（requirements.txt / pyproject.toml）のテンプレートも作成しますので指示ください。