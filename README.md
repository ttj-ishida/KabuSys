# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

---

## 目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単な例）
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は、日本株のデータプラットフォームとアルゴリズム取引のための内部ライブラリ群です。  
主に以下をカバーします。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への保存（ETL）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と NLP による銘柄別センチメント評価（OpenAI）
- 市場レジーム判定（ETF MA + マクロニュースの LLM センチメントの合成）
- 研究用ファクター計算、特徴量探索ユーティリティ
- 監査ログスキーマ（シグナル→発注→約定をトレースするテーブル群）
- kabuステーション連携のための設定（発注は別実装に委譲する想定）

設計方針として、ルックアヘッドバイアスを避けるために内部で date.today()/datetime.today() を直接参照しない実装方針が採られています。

---

## 主な機能一覧
- データ取得 / ETL
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（J-Quants）
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - ETLResult による処理結果の集約
- データ品質チェック
  - check_missing_data / check_duplicates / check_spike / check_date_consistency
  - run_all_checks
- ニュース収集・処理
  - RSS フェッチ（SSRF 対策、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存（冪等）
- ニュース NLP（OpenAI）
  - score_news: 銘柄ごとにニュースをまとめて LLM でセンチメントを算出し ai_scores に保存
  - gpt-4o-mini を JSON Mode で使用（レスポンスを厳密な JSON として期待）
- 市場レジーム判定
  - score_regime: ETF(1321) の MA200 乖離 + マクロニュースセンチメントを合成して market_regime を更新
- リサーチ / ファクター
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / zscore_normalize
- 監査ログ（トレーサビリティ）
  - init_audit_schema / init_audit_db: signal_events, order_requests, executions などのスキーマ初期化

---

## セットアップ手順

1. リポジトリをクローン（例）
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を用意（推奨: venv / pyenv）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存ライブラリをインストール  
   本コードで使用している主なライブラリ:
   - duckdb
   - openai
   - defusedxml
   - そのほか標準ライブラリのみで実装されている箇所が多いです。  
   requirements.txt がある場合は:
   ```
   pip install -r requirements.txt
   ```
   明示的にインストールする例:
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージのインストール（開発モード）
   ```
   pip install -e .
   ```

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 環境変数（.env）
設定は .env または OS 環境変数から読み込まれます。パッケージは自動的にプロジェクトルート（.git または pyproject.toml がある場所）から `.env` と `.env.local` を読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

重要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須: ETL 実行時）
- KABU_API_PASSWORD: kabuステーション API のパスワード（本番の注文連携など）
- KABU_API_BASE_URL: kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用途（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading のモック約定方式（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: 実行監視用
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: 環境（development | paper_trading | live）
- LOG_LEVEL: ログレベル（DEBUG | INFO | WARNING | ERROR | CRITICAL）

サンプル `.env`（最小例）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- `.env.local` は `.env` を上書きします（OS 環境変数は常に最優先で保護されます）。
- Settings クラスは未設定の必須変数を要求すると ValueError を出します。

---

## 使い方（主要ユースケース）

以下はライブラリの代表的な使用方法の例です。実運用ではエラーハンドリングやロギング設定を行ってください。

1) DuckDB 接続を作り日次 ETL を実行する
```python
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# settings.duckdb_path は Path を返すので文字列に変換して接続
conn = duckdb.connect(str(settings.duckdb_path))

# target_date を指定しない場合は今日（ただし内部で営業日に調整されます）
result = run_daily_etl(conn)
print(result.to_dict())
```

2) OpenAI を使ってニューススコアを算出し ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print(f"scored {n_written} tickers")
```

3) 市場レジーム判定（ma200 + マクロニュース）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログ用 DuckDB を初期化する
```python
from kabusys.data.audit import init_audit_db

# :memory: でも可。ファイルパスを与えると親ディレクトリを自動作成します。
audit_conn = init_audit_db("data/audit.duckdb")
```

5) ETL の個別実行（株価のみ取得）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_prices_etl

conn = duckdb.connect("data/kabusys.duckdb")
fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print(f"fetched={fetched} saved={saved}")
```

---

## 実装上の注意・振る舞い
- ルックアヘッドバイアス防止: 多くの関数が target_date を明示的に受け取り、内部で datetime.today() を参照しない設計です。バックテストや再現性ある実行のため必ず target_date を管理してください。
- .env の自動読み込み: プロジェクトルートが特定できない場合やテスト時は自動ロードがスキップされます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出し: gpt-4o-mini を想定。API 呼び出し失敗時やパースエラー時はフェイルセーフ（ゼロスコアやスキップ）で処理を継続するように実装されています。
- J-Quants API: レート制限（120 req/min）や 401 自動リフレッシュ・リトライ・ページネーションに対応しています。
- DuckDB 互換: 一部の挙動（executemany の空リスト）がバージョン依存なので、ETL 実装はこれを考慮しています（空リストは渡さないようガードが入っています）。

---

## ディレクトリ構成（主なファイル）
（src/kabusys 以下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py            # ニュース NLP（score_news 等）
  - regime_detector.py     # 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py # 市場カレンダー管理
  - etl.py                 # ETL インターフェース再エクスポート
  - pipeline.py            # ETL パイプラインと run_daily_etl 等
  - stats.py               # zscore_normalize 等の統計ユーティリティ
  - quality.py             # データ品質チェック
  - audit.py               # 監査ログスキーマ / 初期化
  - jquants_client.py      # J-Quants API クライアント（fetch/save）
  - news_collector.py      # RSS ニュース収集
- research/
  - __init__.py
  - factor_research.py     # calc_momentum / calc_value / calc_volatility
  - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank

---

## 開発・テストに関する補足
- 自動環境読み込みを無効にしてユニットテストから isolation を保つには:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し部はユニットテストでモック差し替えしやすい設計（内部 _call_openai_api を patch する）になっています。
- ネットワーク呼び出し（RSS、J-Quants、OpenAI）はリトライ・タイムアウト・エラーハンドリングが組み込まれていますが、テストでは外部依存をモックしてください。

---

もし README に追加したい具体的なコマンドや例（CI のセットアップ、Docker 化、requirements.txt の想定内容など）があれば教えてください。必要に応じて .env.example のテンプレートやサンプルスクリプトも用意できます。