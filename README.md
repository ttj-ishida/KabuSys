# KabuSys — 日本株自動売買プラットフォーム（README）

概要
----
KabuSys は日本株向けのデータパイプライン、リサーチ、ニュースNLP、レジーム判定、監査ログなどを備えた自動売買システムのライブラリ群です。主に以下を目的とします。
- J-Quants API からのデータ取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたデータ保存・分析
- ニュース記事の収集と OpenAI を使った銘柄単位センチメント算出
- ETF とマクロセンチメントを組合せた市場レジーム判定
- ETL パイプライン、データ品質チェック、監査テーブル（発注 → 約定のトレース）

主な特徴
---------
- データETL（差分取得・バックフィル・品質チェック）: data.pipeline.run_daily_etl
- ニュース NLP スコアリング（OpenAI）: ai.news_nlp.score_news
- 市場レジーム判定（MA200 と LLM センチメントの合成）: ai.regime_detector.score_regime
- リサーチ用ファクター計算（モメンタム・ボラティリティ・バリュー等）: research.*
- DuckDB ベースの監査スキーマ初期化 / 専用 DB 作成: data.audit.init_audit_schema / init_audit_db
- RSS ベースのニュース収集ユーティリティ（SSRF 対策、正規化、前処理）: data.news_collector
- 環境変数ベースの設定管理（.env 自動ロード機能）: config.settings

セットアップ手順
----------------
1. Python 環境（推奨: 3.10+）を用意します。
2. 依存パッケージをインストールします（プロジェクトに requirements.txt がある想定）。
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   ※ 実際のプロジェクトでは他の依存がある可能性があります。pyproject.toml/requirements.txt を参照してください。

3. パッケージを開発モードでインストール（任意）:
   ```
   pip install -e .
   ```

4. 環境変数を設定します。プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。
   推奨する最小の環境変数例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD
   - OpenAI を使う機能は OPENAI_API_KEY を必要とします（または score_news/score_regime の api_key 引数で明示）。

5. DuckDB ファイル用ディレクトリを作成する（必要に応じて）。
   ```
   mkdir -p data
   ```

使い方（基本例）
----------------

- DuckDB 接続を作成して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント（OpenAI）で銘柄ごとの ai_scores を作成
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"Written scores: {n_written}")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は環境変数か引数で渡す
```

- 監査DB（監査ログ）を初期化して接続を取得
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブル等が作成されます
```

- リサーチ（ファクター計算）の例
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
m = calc_momentum(conn, target_date=date(2026,3,20))
v = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

設定（環境変数の要点）
---------------------
- 自動 .env ロード: パッケージはプロジェクトルート（.git または pyproject.toml を探索）を検出し、`.env` と `.env.local` を自動的に読み込みます。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化できます（テスト用途）。
- 主要なキー:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで必要）
  - KABU_API_PASSWORD: kabuステーション API パスワード
  - KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知用
  - DUCKDB_PATH: DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視等で使う SQLite のパス（デフォルト data/monitoring.db）
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

ディレクトリ構成（主要ファイル）
-------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースNLP（銘柄スコア算出）
    - regime_detector.py      — 市場レジーム判定
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - jquants_client.py       — J-Quants API クライアント（fetch/save 等）
    - news_collector.py       — RSS ニュース収集ユーティリティ
    - calendar_management.py  — マーケットカレンダー管理 / 営業日ロジック
    - stats.py                — 統計ユーティリティ（z-score）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログスキーマ初期化・DB 初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — momentum/value/volatility 等
    - feature_exploration.py  — 将来リターン、IC、統計サマリー
  - ai/..., research/..., data/... (上記参照)

注意事項 / ベストプラクティス
------------------------------
- Look-ahead バイアス防止: モジュールの多くは内部で date.today() を直接参照しない、または明示的 target_date を受け取る実装になっています。バックテストでは target_date を適切に渡してください。
- OpenAI 呼び出し: API エラー時はフェイルセーフ（スコア 0.0 やスキップ）で継続する実装が多いですが、実運用ではレートやコスト管理に注意してください。
- トークン管理: J-Quants の id_token は自動リフレッシュ/キャッシュ処理がありますが、呼び出し時の id_token 注入やテスト用モックも想定されています。
- テスト: config の自動 .env ロードはテストで影響することがあるため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使うか環境を明示的にセットしてください。
- セキュリティ: news_collector は SSRF 対策や XML の安全パースを実装していますが、運用時はネットワークアクセス制御・プロキシ設定なども考慮してください。

貢献・拡張
----------
- 新しい ETL の接続先（別 API）を追加する場合は jquants_client に倣いレートリミット・リトライ・冪等保存の方針で実装してください。
- AI モジュールは OpenAI の JSON mode を前提に堅牢なパース・バリデーションを行っています。別の LLM を使う場合はレスポンスフォーマットに注意してください。

ライセンス / 作者
-----------------
この README はコードベースの抜粋に基づき作成したドキュメントです。実際のライセンス表記・作者情報・詳細な開発フローはプロジェクトのルートにある LICENSE / CONTRIBUTING を参照してください。

付録: よく使う関数一覧
---------------------
- data.pipeline.run_daily_etl(conn, target_date, ...)
- data.pipeline.run_prices_etl / run_financials_etl / run_calendar_etl
- ai.news_nlp.score_news(conn, target_date, api_key=None)
- ai.regime_detector.score_regime(conn, target_date, api_key=None)
- data.audit.init_audit_db(path) / init_audit_schema(conn)
- data.jquants_client.fetch_daily_quotes / save_daily_quotes

必要であれば、実際の .env.example や詳細な API 使用例（Slack通知、kabu API を用いた発注処理のサンプル等）を追記します。どの情報を優先して追記しましょうか？