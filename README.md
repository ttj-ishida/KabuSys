# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリです。データ取得（J-Quants）、ETL、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、リサーチ（ファクター計算）および監査ログ（約定トレーサビリティ）などのユーティリティを提供します。

主な設計方針は「ルックアヘッドバイアス回避」「冪等性」「フェイルセーフ（API 失敗時は安全側動作）」「DuckDB によるローカルデータ管理」です。

---

目次
- プロジェクト概要
- 機能一覧
- 要件（依存ライブラリ）
- 環境変数
- セットアップ手順
- 使い方（簡単なコード例）
- ディレクトリ構成

---

プロジェクト概要
- J-Quants API を用いた日本株データ（株価日足、財務、マーケットカレンダー）の差分 ETL。
- RSS ニュースの収集と前処理、銘柄紐付け。
- OpenAI（gpt-4o-mini 等）を利用したニュースセンチメント / マクロセンチメント解析。
- ETF（1321）の MA や LLM センチメントを合成した市場レジーム判定。
- 研究用のファクター計算・特徴量探索ユーティリティ。
- 発注〜約定の監査ログ用スキーマ（DuckDB）と初期化ユーティリティ。
- データ品質チェック（欠損/スパイク/重複/日付不整合）。

---

機能一覧（ハイライト）
- データ取得 / 保存
  - J-Quants client: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）
- ETL パイプライン
  - run_prices_etl, run_financials_etl, run_calendar_etl, run_daily_etl（統合）
  - ETLResult による実行結果集約
- ニュース収集・NLP
  - RSS 収集（fetch_rss）、前処理、raw_news への保存（news_collector）
  - ニュースセンチメント解析: kabusys.ai.news_nlp.score_news
  - 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- リサーチ / ファクター計算
  - calc_momentum, calc_value, calc_volatility（kabusys.research）
  - calc_forward_returns, calc_ic, factor_summary, zscore_normalize
- データ品質
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks
- 監査ログ（オーダー〜実行）
  - init_audit_schema, init_audit_db（DuckDB 初期化＋テーブル作成）

---

要件（主な依存ライブラリ）
- Python 3.10+（タイプ注釈等を利用）
- duckdb
- openai（OpenAI SDK、Chat completions を使用する部分あり）
- defusedxml
- そのほか標準ライブラリのみで多くが実装されています

（プロジェクトの pyproject.toml / requirements.txt がある場合はそちらを参照してインストールしてください）

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack の投稿先チャンネル ID（必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境（development / paper_trading / live。デフォルト development）
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 呼び出し時に未指定なら参照される）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は 1 をセット

.env の自動ロード
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）から .env と .env.local を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン / コピー
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそちらを使用
4. .env を作成
   - プロジェクトルートに .env を置くと自動で読み込まれます（例は下記）
5. DuckDB ファイルの準備（自動で作成されますが、必要なら初期化ユーティリティを実行）

例: .env（最低限必要な項目）
- JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
- OPENAI_API_KEY=sk-...
- KABU_API_PASSWORD=your_kabu_password
- SLACK_BOT_TOKEN=xoxb-...
- SLACK_CHANNEL_ID=C01234567

---

使い方（簡単なコード例）

- DuckDB 接続を作って ETL を実行する（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコアを生成（score_news）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# API キーは環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env または api_key 引数
```

- 監査ログ用 DuckDB の初期化
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- リサーチ / ファクター計算の例
```python
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
momentum = calc_momentum(conn, d)
value = calc_value(conn, d)
volatility = calc_volatility(conn, d)
# 得られるのは (date, code) を含む dict のリスト
```

注意点
- OpenAI を使う関数は api_key を引数で受け取るか、環境変数 OPENAI_API_KEY を参照します。テスト時は関数単位でモック可能です。
- J-Quants の認証はリフレッシュトークンから id_token を取得する仕組みです（自動リフレッシュ・レートリミット・リトライあり）。
- ETL / API 呼び出しはネットワーク障害・API 制限に対してリトライ・フェイルセーフを組み込んでいますが、ログを確認し異常時は再実行してください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                  # 環境変数・自動 .env ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py              # ニュースセンチメント解析（score_news）
    - regime_detector.py      # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        # J-Quants API client（fetch / save）
    - pipeline.py              # ETL パイプライン（run_daily_etl 等）
    - calendar_management.py   # 市場カレンダー管理
    - news_collector.py        # RSS 取得 + 前処理
    - quality.py               # データ品質チェック
    - stats.py                 # 共通統計ユーティリティ（zscore_normalize）
    - audit.py                 # 監査ログスキーマ / 初期化
    - etl.py                   # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py       # モメンタム/ボラティリティ/バリュー
    - feature_exploration.py   # forward returns / IC / summary

各モジュールは docstring と関数レベルのコメントにより使用方法や設計思想が記載されています。API の詳細（引数・返り値・例外）は各モジュールの docstring を参照してください。

---

運用上の注意
- 本ライブラリは実際の売買システムに使えるような部品群を提供しますが、発注や実運用に用いる場合は十分なテストとリスク管理を行ってください（特に live 環境）。
- settings.is_live / is_paper / is_dev を用いて環境ごとの挙動切替ができます（KABUSYS_ENV により設定）。
- ETL や OpenAI 呼び出しには API レート制限、コスト面の考慮をしてください。

---

ライセンス / 貢献
- ここではライセンスは明記していません。実際のリポジトリ運用時は LICENSE を追加してください。
- コントリビューション、バグ報告、機能追加の提案は Issue / Pull Request を通して行ってください。

---

以上が README の概要です。必要であればサンプルスクリプトや .env.example を追記しますか？