KabuSys
=======

日本株向けのデータプラットフォームおよび自動売買／リサーチ用ライブラリ群です。  
DuckDB をデータレイヤに、J-Quants / JPY マーケットカレンダー / RSS ニュース / OpenAI を組み合わせて、ETL → 品質チェック → ファクター計算 → AI ニュース評価 → 市場レジーム判定 → 監査ログ（発注／約定追跡）までのワークフローを提供します。

主な特徴
--------

- データ収集（J-Quants）／保存（DuckDB）／品質チェック（欠損・重複・スパイク・日付整合性）
- 日次 ETL パイプライン（prices, financials, calendar）
- ニュース収集（RSS）と前処理（URL 除去、正規化、SSRF 対策）
- OpenAI によるニュース NLP（銘柄別センチメント）およびマクロセンチメントを使った市場レジーム判定
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Z スコア正規化）
- 監査ログスキーマ（signal_events / order_requests / executions）の初期化と DB ヘルパー
- 設定は環境変数（.env/.env.local）で管理（自動ロード機構あり）

機能一覧（主要モジュール）
---------------------------

- kabusys.config
  - 環境変数読み込み（.env 自動ロード）、必須設定の取得（settings オブジェクト）
  - 主要 env 名: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- kabusys.data.jquants_client
  - J-Quants API からの取得（株価 / 財務 / 上場一覧 / カレンダー）
  - DuckDB への保存（冪等; ON CONFLICT）
  - id_token 自動リフレッシュ、レートリミット、リトライ
- kabusys.data.pipeline / etl
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による結果集約と品質チェックの実行
- kabusys.data.quality
  - 品質チェック（欠損、重複、スパイク、日付不整合）
- kabusys.data.news_collector
  - RSS 取得・正規化・前処理・raw_news への保存支援
  - SSRF 対策、受信サイズ制限、URL 正規化、記事 ID 生成
- kabusys.data.calendar_management
  - JPX マーケットカレンダーの管理、営業日判定、next/prev_trading_day 等
- kabusys.data.audit
  - 監査ログの DDL / インデックス定義と初期化（init_audit_schema / init_audit_db）
- kabusys.ai.news_nlp
  - 銘柄別ニュースをまとめて OpenAI（gpt-4o-mini）へ送り、ai_scores テーブルへスコアを保存するロジック（バッチ、検証、リトライ、クリップ等）
- kabusys.ai.regime_detector
  - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に日次判定を保存
- kabusys.research
  - calc_momentum / calc_value / calc_volatility / calc_forward_returns / calc_ic / factor_summary / rank など、バックテスト・研究用の数理処理
- kabusys.data.stats
  - zscore_normalize（クロスセクションの Z スコア正規化）

セットアップ手順
----------------

前提
- Python 3.9+（ソースで typing や union 表記を使用）
- DuckDB が必要（pip でインストール可能）
- OpenAI クライアント（openai）を利用する箇所があるため OpenAI API キーが必要

例: 仮想環境作成と依存関係インストール（プロジェクトに requirements.txt がある場合はそれを使ってください）

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
# 必要なパッケージの例
pip install duckdb openai defusedxml
# （必要に応じて他の依存パッケージを追加）
```

環境変数設定
- プロジェクトルートに .env / .env.local を置くと kabusys.config が自動で読み込みます（ただしプロジェクトルート判定は .git または pyproject.toml を基準に探索します）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

例: .env（最低限の例）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

初期 DB 作成（監査ログ用など）
- 監査ログ用 DB を初期化する例:

```python
import duckdb
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でインメモリ可
```

使い方（代表的なワークフロー）
------------------------------

1) 設定取得

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

2) 日次 ETL の実行

```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date None -> 今日
print(result.to_dict())
```

3) ニュース NLP（銘柄別センチメント）を実行（OpenAI API キーは env または引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20))  # 書き込んだ銘柄数を返す
```

4) 市場レジーム判定

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 監査ログスキーマの初期化（既存接続への追加）

```python
from kabusys.data.audit import init_audit_schema
conn = duckdb.connect(str(settings.duckdb_path))
init_audit_schema(conn, transactional=True)
```

6) 研究用途: ファクター計算・IC 等

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
forward = calc_forward_returns(conn, target_date=date(2026, 3, 20))
ic = calc_ic(momentum, forward, "mom_1m", "fwd_1d")
```

注意点 / 動作設計方針
--------------------

- 「ルックアヘッドバイアス防止」を強く意識した実装: target_date を明示的に渡す設計、date.today()/datetime.today() を直接参照しない関数が多くあります（テストやバックテスト対応）。
- OpenAI 呼び出しはリトライ・パース検証・クリッピングを行い、API 失敗時はフェイルセーフ（0.0 やスキップ）で継続する設計です。
- DuckDB に対する executemany の空リスト扱い、ON CONFLICT の扱いなど実運用での互換性を考慮した実装がなされています。
- news_collector は SSRF 対策（リダイレクト時の検査やプライベートホスト拒否）、受信サイズ制限、XML 安全パーサ（defusedxml）を採用しています。

ディレクトリ構成（主要ファイル）
-------------------------------

- src/
  - kabusys/
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
      - quality.py
      - news_collector.py
      - calendar_management.py
      - audit.py
      - stats.py
      - (その他 data 関連ユーティリティ)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（統計・ユーティリティ）
- pyproject.toml / setup.cfg / requirements.txt（プロジェクト依存管理ファイルがあればここに）

開発・テスト
------------

- 単体テストは各モジュールの外部依存（ネットワーク、OpenAI、J-Quants）をモックして実行する設計が前提です（例: news_nlp._call_openai_api を patch）。
- .env 自動ロードはデフォルトで有効。テスト時に自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

ライセンス / 貢献
-----------------

（ここにプロジェクトのライセンス情報、貢献ガイドライン、連絡先等を記載してください。）

補足
----

本 README はソースコードのドキュメント（関数 docstring）を基に要点をまとめています。実運用時は各設定や DB スキーマ、J-Quants / OpenAI の利用規約・レート制限に注意して下さい。必要であれば、具体的な運用手順（cron / Airflow などによるスケジューリング、ログ・監視設定、Slack 通知の実装例）も追記できます。