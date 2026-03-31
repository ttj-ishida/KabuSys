# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ群です。  
DuckDB を中心にデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、リサーチ用のファクター計算、ETL、監査ログ（オーダー／約定トレース）などを提供します。

---

## プロジェクト概要

KabuSys は次のような目的で設計されています。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得・保存する ETL パイプライン
- RSS ニュースの収集（SSRF 対策・トラッキング除去）と OpenAI を用いた銘柄別ニュースセンチメントスコア付与
- マーケットレジーム判定（ETF の MA とマクロニュースの LLM センチメントを組合せ）
- 研究用途のファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- データ品質チェック（欠損・重複・スパイク・日付不整合検出）
- 監査ログ（signal → order_request → executions のトレーサビリティ）を保存する監査スキーマ

設計方針の特徴:

- ルックアヘッドバイアスを避ける（内部で date.today() や datetime.now() を直接使う箇所を最小化）
- DuckDB を中心に SQL と最小限の標準ライブラリで実装（pandas 等に依存しない）
- 冪等操作（ON CONFLICT / idempotent）を重視
- 外部 API 呼び出しはリトライ・レート制御・フェイルセーフを備える

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env / .env.local 自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取得ラッパー settings

- kabusys.data
  - jquants_client: J-Quants API クライアント（認証・ページネーション・リトライ・保存関数）
  - pipeline: 日次 ETL(run_daily_etl) / 個別 ETL(run_prices_etl, run_financials_etl, run_calendar_etl)
  - news_collector: RSS 取得・前処理・raw_news への保存（SSRF 対策・gzip 上限）
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - calendar_management: 市場カレンダーの判定（営業日/次営業日等）とカレンダー更新バッチ
  - audit: 監査ログスキーマ作成・初期化（signal_events, order_requests, executions）
  - stats: zscore_normalize 等ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（gpt-4o-mini）に送り銘柄ごとの ai_score を ai_scores に保存
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロニュース LLM 評価を合成して market_regime を保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - その他 zscore_normalize を再利用可能

---

## セットアップ手順

前提: Python 3.10+（typing の型記述に依存）

1. リポジトリをクローン／ダウンロード

   git clone <repo-url>
   cd <repo-dir>

2. 必要ライブラリをインストール（最低限の例）

   pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt を用意していることが望ましいです。

3. パッケージをインストール（開発モード）

   pip install -e .

4. 環境変数を設定

   プロジェクトルート（.git または pyproject.toml がある場所）に `.env` または `.env.local` を置くと自動で読み込まれます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   推奨する最小 .env（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   KABU_API_PASSWORD=your_kabu_api_password
   ```

5. データベース用ディレクトリの作成（DuckDB のデフォルトパスに合わせる）

   デフォルト DuckDB path は `data/kabusys.duckdb`。親ディレクトリが存在しない場合は自動作成される関数も一部存在しますが、必要に応じて `mkdir -p data` 等で用意してください。

---

## 環境変数一覧（主要）

- 必須（実行する機能に応じて必須）
  - JQUANTS_REFRESH_TOKEN : J-Quants リフレッシュトークン（jquants_client.get_id_token で使用）
  - OPENAI_API_KEY         : OpenAI API キー（AI モジュールで使用）
  - SLACK_BOT_TOKEN        : Slack 通知（必要時）
  - SLACK_CHANNEL_ID       : Slack チャネル ID（必要時）
  - KABU_API_PASSWORD      : kabuステーション API 用パスワード（注文等で使用）

- 任意 / デフォルトあり
  - KABUSYS_ENV            : 実行環境 ("development" | "paper_trading" | "live"), default: development
  - LOG_LEVEL              : ログレベル ("DEBUG","INFO",...), default: INFO
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : 1 を設定すると .env の自動読み込みを無効化
  - KABU_API_BASE_URL      : kabu API ベース URL, default: http://localhost:18080/kabusapi
  - DUCKDB_PATH            : DuckDB ファイルパス, default: data/kabusys.duckdb
  - SQLITE_PATH            : 監視用 SQLite パス, default: data/monitoring.db

---

## 使い方（代表的な例）

下記は最小限のコード例です。実運用ではログ設定やエラーハンドリング・ジョブスケジューリングを行ってください。

- DuckDB 接続を作り ETL を実行する

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
print(f"書込銘柄数: {n_written}")
```

- マーケットレジームのスコアリング

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB を初期化する（監査専用 DB を作成）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- 市場カレンダー関連ユーティリティ

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しは gpt-4o-mini + JSON mode を想定しており、レスポンスのバリデーションやリトライロジックが実装されています。テスト時には内部の _call_openai_api をモックすることが想定されています。
- J-Quants API 呼び出しにはレート制御・リトライ・401 自動リフレッシュが組み込まれています。

---

## 実行例（CLI スクリプトがない場合の想定ワークフロー）

シンプルな cron / Airflow / GitHub Actions の job:

1. 深夜に run_daily_etl をスケジュール（データ取得）
2. ETL 終了後に quality.run_all_checks の結果を監視し、Slack 通知
3. ニューススクレイパー（news_collector.fetch_rss をラッパーで毎時間実行）
4. 朝に score_news（当該営業日のニュースウィンドウで）→ ai_scores を更新
5. レジーム判定（score_regime）→ market_regime を更新
6. 戦略別に research のファクターを使って signal を作成し、監査ログ・発注処理へ繋ぐ

---

## ディレクトリ構成（抜粋）

src/kabusys/
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
  - (その他: schema 初期化用ユーティリティ等)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research / data 間で再利用されるユーティリティ関数群

（上記は主要なモジュールの一覧です。実際のリポジトリはさらにファイルやテストが含まれることがあります。）

---

## 開発・テスト時のヒント

- .env の自動読み込みはプロジェクトルート（.git / pyproject.toml）から探索します。テスト時に環境汚染を避けるため `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。
- OpenAI / HTTP 周りはネットワーク依存が大きいので、ユニットテストでは内部の _call_openai_api、_urlopen、jquants_client._request 等をモックしてください（コード内でもモック対象であることがコメントに明記されています）。
- DuckDB はファイルパス (data/kabusys.duckdb) を使うか、":memory:" でインメモリ接続が可能です。監査 DB 初期化関数は親ディレクトリを自動作成します。

---

## ライセンス・貢献

この README はコードベースの一部情報をもとに作成しています。実プロジェクトでのライセンス表記や貢献方法（CONTRIBUTING.md）等は別途リポジトリルートのファイルを参照してください。

---

ご要望があれば、README に使い方の具体的な CLI サンプル、docker-compose 例、CI ワークフロー例、あるいは .env.example のテンプレートを追加で作成します。どれが必要か教えてください。