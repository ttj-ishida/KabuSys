# KabuSys

日本株向け自動売買 / データ基盤ライブラリ。ETL、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買運用・リサーチ基盤のための Python コード群です。主に以下を目的としています。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS ベースのニュース収集と記事前処理
- OpenAI を用いたニュースセンチメント分析（銘柄ごとの ai_score、マクロセンチメント）
- 市場レジーム（bull / neutral / bear）判定
- ファクター（モメンタム・バリュー・ボラティリティ等）計算と特徴量探索ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution）用スキーマの初期化・管理
- DuckDB を中核 DB として利用（設定によりファイル指定）

設計上の方針として、ルックアヘッドバイアスを起こさないために内部処理は target_date を明示して動作するようになっています（datetime.today()/date.today() を直接参照する処理を最小化）。

---

## 主な機能一覧

- data/
  - ETL パイプライン（prices, financials, market_calendar）
  - J-Quants API クライアント（認証、ページネーション、保存ロジック）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS、SSRF 対策、正規化、raw_news へ保存）
  - データ品質チェック（missing, spike, duplicates, date consistency）
  - 監査ログスキーマ初期化（signal_events, order_requests, executions）
  - 汎用統計ユーティリティ（Z-score 正規化）
- ai/
  - ニュース NLP（銘柄ごとのニュースセンチメント集計 -> ai_scores）
  - レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- research/
  - ファクター計算（momentum, value, volatility）
  - 特徴量探索（forward returns, IC, summary, rank）
- config.py
  - 環境変数の自動ロード（.env / .env.local）と Settings クラス
  - 主要環境変数の getter（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY 等）

---

## セットアップ手順

1. Python インストール
   - Python 3.10+ を推奨（DuckDB / OpenAI SDK と互換のあるバージョン）

2. リポジトリをクローン / コピー

3. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

4. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージの例:
     - pip install duckdb openai defusedxml

   （実際のプロジェクトでは setuptools / pyproject.toml に依存が定義されている前提です）

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト：OS環境 > .env.local > .env）。
   - 自動ロードを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 必要な環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須、ETLで使用）
   - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行/発注機能使用時）
   - KABU_API_BASE_URL: kabuステーションのベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH 等の監視関連

   .env の例（プロジェクトルートに .env を作成）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡易例）

以下はライブラリ関数を Python から呼ぶ基本的な例です。多くの処理は関数呼び出しで完結します。

- DuckDB 接続を作って日次 ETL を実行する例:

```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB ファイルへ接続（デフォルト設定を使用）
conn = duckdb.connect(str(settings.duckdb_path))

# ETL 実行（target_date を指定しない場合は today が使用される）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコア（銘柄ごとの ai_score）を計算する例:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"wrote {written} ai_scores")
```

- 市場レジーム（daily）を判定して保存する例:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026,3,20), api_key=None)
```

- 監査ログ DB 初期化（監査専用 DuckDB）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# テーブル（signal_events 等）が作成されます
```

注:
- OpenAI 呼び出しは API キーを環境変数 OPENAI_API_KEY で解決します。api_key 引数で明示的に渡すことも可能です。
- 多くの関数は target_date を引数に受け取り、ルックアヘッドバイアスを避ける設計になっています。バックテスト用途では必ず適切な target_date を渡してください。

---

## 主要 API（抜粋）

- kabusys.config.settings
  - settings.jquants_refresh_token
  - settings.duckdb_path, settings.sqlite_path
  - settings.env / is_live / is_paper / is_dev

- ETL / データ
  - kabusys.data.pipeline.run_daily_etl(...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
  - kabusys.data.jquants_client.fetch_daily_quotes / save_daily_quotes / get_id_token

- ニュース / AI
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

- 研究用ユーティリティ
  - kabusys.research.calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
  - kabusys.data.stats.zscore_normalize

- 品質チェック
  - kabusys.data.quality.run_all_checks(conn, target_date, ...)

- 監査ログ
  - kabusys.data.audit.init_audit_db(path) / init_audit_schema(conn)

---

## ディレクトリ構成（抜粋）

プロジェクトは src/kabusys 以下にモジュールを配置しています。主要ファイルを抜粋します。

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
      - calendar_management.py
      - news_collector.py
      - quality.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
      - (その他ユーティリティ)
    - research/__init__.py

上記以外にも strategy / execution / monitoring 等のサブパッケージが想定されています（パッケージ __all__ に列挙）。

---

## 注意点 / 運用メモ

- 環境変数の自動ロード:
  - config.py はプロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を自動読み込みします。テストなどで自動ロードを抑止する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼出し:
  - API 呼び出しはリトライ・バックオフを備えていますが、API 使用量やコストに注意してください。レスポンスバリデーションを行い、失敗時はフォールバック（0.0 など）する設計です。
- DuckDB との相性:
  - 一部処理は DuckDB の executemany の制約（空リストを渡せない等）を考慮した実装になっています。DuckDB のバージョン差異に注意してください。
- セキュリティ:
  - news_collector では SSRF 対策（リダイレクト検査、プライベート IP 判定）、defusedxml による XML パース保護を行っています。
- 監査ログ:
  - 監査テーブルは削除しない前提で設計されています。order_request_id は冪等キーとして二重発注防止に利用可能です。

---

この README はリポジトリ内のソース注釈をもとに作成しています。実運用前に依存パッケージの固定、テスト、設定ファイル整備（.env.example の作成）、および運用手順書の追加を推奨します。必要であれば README にサンプル .env.example や systemd / supervisor 用の起動スクリプト例、テスト方法を追加しますので指示ください。