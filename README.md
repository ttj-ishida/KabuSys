# KabuSys

日本株向け自動売買 / データパイプライン基盤ライブラリ

---

## プロジェクト概要

KabuSys は日本株向けのデータプラットフォームと自動売買基盤を提供する Python パッケージです。  
主な目的は以下のとおりです。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM（OpenAI）を用いた記事センチメントの銘柄別スコア化
- 市場レジーム判定（ETF とマクロニュースの組合せ）
- ファクター計算・研究用ユーティリティ（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）テーブル初期化ツール
- データ品質チェック、ニュース収集（RSS）、J-Quants クライアント等

パッケージは軽量な依存（duckdb, openai, defusedxml など）で構成され、ルックアヘッドバイアスへの配慮や冪等性／フェイルセーフ設計が各所に組み込まれています。

---

## 主な機能一覧

- データ ETL
  - 日次 ETL（run_daily_etl）：市場カレンダー → 日足 → 財務 → 品質チェック
  - 差分取得（ページネーション・レート制御・トークンリフレッシュ対応）
- ニュース NLP
  - ニュース記事を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメント評価（score_news）
  - リトライ、レスポンス検証、チャンク処理、スコアのクリップ等を実装
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジームを判定（score_regime）
- リサーチ用計算
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ等
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の DDL 定義と初期化（init_audit_schema / init_audit_db）
- ニュース収集
  - RSS フィードの取得・前処理・SSRF 対策・データベース保存準備（news_collector）
- 設定管理
  - 環境変数ベースの Settings（自動 .env 読込（.env, .env.local） / KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）

---

## セットアップ手順

前提:
- Python 3.10+（typing の | 型合成などを使用）
- システムに DuckDB を導入済み（pip で duckdb がインストールされます）

1. リポジトリをクローンしてパッケージをインストール（開発モード推奨）
   ```
   git clone <repo-url>
   cd <repo>
   pip install -e .
   ```
   または最小依存を手動で入れる場合:
   ```
   pip install duckdb openai defusedxml
   ```

2. 必須環境変数を設定する（.env をプロジェクトルートに置くと自動で読み込まれます）
   - 必須:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD     : kabuステーション API パスワード（発注系を使う場合）
   - 任意・推奨:
     - OPENAI_API_KEY        : OpenAI API キー（ニュース NLP / レジーム判定）
     - KABUSYS_ENV           : development | paper_trading | live（デフォルト: development）
     - LOG_LEVEL             : DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_FILL_MODE       : Paper Trading の約定モック動作（instant|partial|never|reject）
   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   KABU_API_PASSWORD=your_kabu_password
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   ```

3. 自動 .env 読み込みの挙動
   - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を基準）から .env → .env.local を自動ロードします。
   - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時に有用）。

---

## 使い方（代表的な例）

以下は Python REPL やスクリプトからの利用例です。

- Settings を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作って日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（銘柄別センチメント）を生成する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は duckdb 接続
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を環境変数で使う
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ用 DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査テーブルが作成された DuckDB 接続
```

- ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dict (date, code, mom_1m, mom_3m, mom_6m, ma200_dev)
```

- ニュース収集（RSS 取得部分）
  news_collector.fetch_rss は SSRF 対策や最大受信サイズ制御を組み込んでいます。直接呼び出す場合は URL のスキームやホスト制約に注意してください。

---

## 主要 API（モジュールと関数の抜粋）

- kabusys.config
  - settings: Settings インスタンス（環境変数をラップ）
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...): 日次 ETL（主入口）
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL
  - ETLResult: 実行結果データクラス
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.audit
  - init_audit_schema(conn, transactional=False)
  - init_audit_db(db_path)
- kabusys.research
  - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.news_collector
  - fetch_rss(...) と前処理ユーティリティ

各関数の詳細はソース内ドキュメンテーション（docstring）を参照してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (ニュース NLP / レジーム判定で使用。未指定時は関数が ValueError を投げます)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PAPER_FILL_MODE (instant|partial|never|reject)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db)
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START（監視用）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視閾値）
- KABUSYS_ENV (development|paper_trading|live)
- LOG_LEVEL (DEBUG|INFO|...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 を設定すると自動 .env 読み込みを無効化)

---

## 注意事項 / 設計上のポイント

- Look-ahead bias の排除:
  - 多くの処理（ETL・ニュース・レジーム判定・ファクター計算）は date 引数を明示的に受け取り、内部で datetime.today() を参照しない設計です。バックテスト等で将来データを参照しないように注意して利用してください。
- 冪等性:
  - ETL の保存処理は ON CONFLICT DO UPDATE で冪等的に設計されています。
- フェイルセーフ:
  - LLM API の失敗時やネットワーク障害時はフェイルセーフ（スコア 0.0 など）で継続する設計が多く採用されています。
- セキュリティ:
  - news_collector には SSRF 対策（リダイレクト検査、プライベートアドレス拒否）や XML パースの安全化（defusedxml）があります。
- テスト性:
  - OpenAI 呼び出し部分は内部関数をモックしやすく設計されています（ユニットテストで差し替え推奨）。

---

## ディレクトリ構成（抜粋）

以下は主要なモジュールとファイルの概観（src/kabusys 以下）。

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
    - stats.py
    - quality.py
    - calendar_management.py
    - news_collector.py
    - audit.py
    - etl.py (ETL 公開インターフェース)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research, monitoring, execution, strategy (パッケージエクスポート候補)

（ソース内に多くの docstring があり、関数ごとの挙動や設計方針、引数・戻り値の説明が記載されています。）

---

## 追加情報 / 運用メモ

- ローカル実行時は DUCKDB_PATH をプロジェクト配下に設定しておくと便利です（デフォルト: data/kabusys.duckdb）。親ディレクトリが存在しない場合は自動生成されます。
- OpenAI を多く叩く処理（news scoring / regime detector）は API コストとレート制限に注意してください。内部でリトライとバックオフを行いますが、API キーの管理（レート・コスト管理）は運用者側で行ってください。
- Paper Trading 用の設定があり、PAPER_FILL_MODE 等でモック約定の挙動を制御できます。
- ETL のログ・品質チェック結果は ETLResult にまとまるため、監査ログや運用ダッシュボードに出力すると運用しやすくなります。

---

必要であれば、README にサンプル .env.example、docker-compose / systemd サービス定義、具体的な運用手順（Cron で run_daily_etl を日次実行する例）や CI 用のテスト方法等を追加できます。どの項目を優先して追加しましょうか？