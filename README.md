# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI でのセンチメント解析）、市場レジーム判定、研究用ファクター計算、データ品質チェック、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやデータプラットフォームで必要となる以下の機能群をモジュール化して提供する Python パッケージです。

主な目的：
- J-Quants API を用いたデータ ETL（株価、財務、JPX カレンダー）
- RSS ベースのニュース収集と OpenAI を用いた銘柄別センチメント解析
- マーケットレジーム判定（ETF + マクロニュース → レジームスコア）
- 研究用途のファクター計算・特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（信号→発注→約定）を格納する監査スキーマ初期化

設計上の特徴：
- Look-ahead バイアスを避けるため、関数内で `datetime.today()` 等を安易に参照しない設計
- DuckDB を利用したローカル DB（高速な分析用）
- OpenAI（gpt-4o-mini）を使った JSON Mode 呼び出しを想定
- 冪等性、トランザクション管理、リトライ・レートリミット制御を重視

---

## 機能一覧

- 環境設定管理: kabusys.config.Settings（.env の自動ロード挙動含む）
- J-Quants クライアント: kabusys.data.jquants_client
  - fetch / save: 日足（OHLCV）、財務、上場銘柄情報、JPX カレンダー
  - レート制限、トークン自動リフレッシュ、リトライ実装
- ETL パイプライン: kabusys.data.pipeline.run_daily_etl 等
- データ品質チェック: kabusys.data.quality（欠損・スパイク・重複・日付整合）
- ニュース収集: kabusys.data.news_collector.fetch_rss（SSRF対策、トラッキング除去）
- ニュース NLP（銘柄別スコア）: kabusys.ai.news_nlp.score_news
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 研究用ユーティリティ:
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - kabusys.research.feature_exploration（forward returns, IC, summary）
  - kabusys.data.stats.zscore_normalize
- 監査ログスキーマ: kabusys.data.audit.init_audit_schema / init_audit_db

---

## セットアップ手順

前提
- Python 3.10+（typing の Union 型表記や型ヒントを多用しているため）を推奨
- DuckDB, OpenAI SDK, defusedxml 等の依存が必要

1. リポジトリをクローン（パッケージ配布形態により適宜）
   - 例: git clone <repo-url>

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (macOS/Linux)
   - .venv\Scripts\activate     (Windows)

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   実際のプロジェクトでは requirements.txt / pyproject.toml を用意して管理してください。

4. 環境変数（必須）
   以下は最低限必要な環境変数です（.env ファイルに記載できます）。

   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - SLACK_BOT_TOKEN       : Slack 通知に使う Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャネル ID（必須）
   - KABU_API_PASSWORD     : kabu ステーションの API パスワード（必須）
   - OPENAI_API_KEY        : OpenAI を使う関数を呼ぶときに必要（score_news / score_regime）

   オプション（デフォルト値あり）:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : 'development' / 'paper_trading' / 'live'（デフォルト: development）
   - LOG_LEVEL             : ログレベル（'DEBUG','INFO',...、デフォルト: INFO）

   .env の自動ロード:
   - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から .env を自動で読み込みます。
   - 読み込み順: OS 環境 > .env.local > .env
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途等）。

5. DB 初期化（監査ログ用）
   - 監査スキーマを用いる場合、DuckDB 接続を作成し初期化します（例は後述）。

---

## 使い方（主要な利用例）

以下は典型的な呼び出し例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続を作る（デフォルトのパスを settings から取得）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査用 DB を初期化して接続を得る
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も指定可能
```

- 日次 ETL を実行（J-Quants からデータ取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースをスコアリングして ai_scores テーブルに書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 19), api_key="sk-...")
print(f"書き込んだ銘柄数: {written}")
```
※ api_key を None にすると環境変数 OPENAI_API_KEY を参照します。未設定だと ValueError が出ます。

- 市場レジームをスコアリングして market_regime テーブルに書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 03, 19), api_key=None)  # OPENAI_API_KEY を使う場合
```

- 研究用ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 19))
# records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]
```

- データ品質チェックを単体で実行
```python
from kabusys.data.quality import run_all_checks
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
issues = run_all_checks(conn, target_date=date(2026,3,19))
for i in issues:
    print(i)
```

注意点:
- OpenAI を呼ぶ機能（news_nlp / regime_detector）は API クォータ・エラーハンドリング・リトライを持ちますが、API キーは必ず指定してください（引数または環境変数）。
- 多くの関数は Look-ahead バイアスを避けるため、target_date を外部から明示して与える想定です。内部で日付を自律的に参照しない実装方針です。

---

## 環境変数（まとめ）

必須:
- JQUANTS_REFRESH_TOKEN
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID
- KABU_API_PASSWORD

OpenAI:
- OPENAI_API_KEY（news_nlp / regime_detector 実行時に必要）

オプション:
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV ('development', 'paper_trading', 'live'。デフォルト: development)
- LOG_LEVEL ('INFO' 等)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1（自動 .env 読み込み無効化）

例 (.env)
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
```

---

## ディレクトリ構成

リポジトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                         -- .env 自動読み込み、Settings
    - ai/
      - __init__.py
      - news_nlp.py                     -- ニュースの OpenAI スコアリング
      - regime_detector.py              -- 市場レジーム判定（ETF + マクロ）
    - data/
      - __init__.py
      - jquants_client.py               -- J-Quants API クライアント（fetch/save）
      - pipeline.py                     -- ETL パイプライン（run_daily_etl 等）
      - etl.py                          -- ETL インターフェース再エクスポート
      - news_collector.py               -- RSS 収集（SSRF 対策等）
      - calendar_management.py          -- 市場カレンダー管理・営業日判定
      - stats.py                        -- zscore_normalize 等
      - quality.py                      -- データ品質チェック
      - audit.py                        -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py              -- momentum/value/volatility 等
      - feature_exploration.py          -- forward returns / IC / summary
    - monitoring/ (想定: 監視関連モジュールが入る)
    - execution/ (想定: 発注ロジック等)
    - strategy/ (想定: 戦略定義)
- pyproject.toml / setup.cfg / README.md (このファイル)

（上記は現在のコードベースに実装されている主要モジュールと想定ファイルです）

---

## 開発・運用上の注意

- DuckDB のバージョン互換性: executemany に空リストを投げると失敗するバージョンがあるため、コード側で空チェックを行っています。DuckDB のバージョン差異に注意してください。
- OpenAI のレスポンスは JSON Mode を使いますが、余分な出力が混在する場合に備えた堅牢なパース処理を実装しています。
- ニュース収集では SSRF / XML Bomb / Gzip Bomb に対する対策を実施していますが、運用時に取り込む RSS ソースは信頼できるものに限定してください。
- ETL・API 呼び出しでの例外は基本的にキャッチしてログに残し他処理を継続する設計（フェイルセーフ）です。運用での監視・アラートは別途組み合わせてください。

---

## もう少し詳しい参照関数

- 設定: kabusys.config.settings (プロパティで必要な環境変数を取得)
- ETL 全体: kabusys.data.pipeline.run_daily_etl
- ニューススコア: kabusys.ai.news_nlp.score_news
- レジーム判定: kabusys.ai.regime_detector.score_regime
- 監査スキーマ初期化: kabusys.data.audit.init_audit_db / init_audit_schema

---

## ライセンス / コントリビューション

（この README にはライセンス情報を含めていません。実際のプロジェクトでは LICENSE を追加してください。）  

コントリビューションや issue の提案は PR / Issue を通じて行ってください。機密情報（APIキー等）は絶対に公開しないでください。

---

以上が KabuSys の簡易 README です。必要であれば、.env.example、requirements.txt、具体的な運用手順（cron や Airflow での ETL スケジューリング例）、および各モジュールの API リファレンスを別途追加します。どちらを優先して作成しますか？