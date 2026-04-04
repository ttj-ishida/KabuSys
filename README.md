# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）。  
ETL、ニュース収集・NLP、ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを含む統合ライブラリです。

バージョン: 0.1.0 (src/kabusys/__init__.py)

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質チェック・研究・戦略実行に必要な機能をまとめた Python ライブラリです。主な用途は次のとおりです。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL
- RSS ベースのニュース収集とニューステキストの前処理（SSRF 対策等を実装）
- OpenAI（gpt-4o-mini）を使ったニュースセンチメント / 市場レジーム判定
- DuckDB を用いたデータ格納・監査ログテーブル初期化
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合検出）

設計上の特徴:
- ルックアヘッドバイアス防止（バックテスト用にdatetime.today()等の直接参照を避ける）
- 冪等的（ON CONFLICT / トランザクションを考慮した保存）
- API やネットワーク呼び出しに対するリトライ / バックオフ実装
- セキュリティ対策（RSS の SSRF 防止、defusedxml を利用した XML パース等）

---

## 機能一覧

- data
  - jquants_client: J-Quants API クライアント（株価・財務・カレンダー取得 / DuckDB 保存）
  - pipeline: 日次 ETL（run_daily_etl）と個別 ETL（prices/financials/calendar）
  - news_collector: RSS 取得・前処理・raw_news への保存ロジック
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 営業日判定・カレンダーバックフィル
  - audit: 監査ログテーブルの初期化（signal / order_request / executions）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp.score_news: ニュース記事の銘柄別センチメントを取得し ai_scores に書き込む
  - regime_detector.score_regime: ETF (1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime に書き込む
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

その他ユーティリティ:
- 環境設定管理: kabusys.config.settings（.env/.env.local の自動読み込み、環境変数アクセス）

---

## 必要要件

- Python 3.10 以上（PEP 604 の | 型等を使用）
- 推奨パッケージ（代表例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - そのほか標準ライブラリに含まれるものは不要

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# プロジェクトが pyproject.toml 等を提供している場合:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンしてプロジェクトルートに移動（pyproject.toml や .git がルート判定に使われます）:
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を用意して依存パッケージをインストール:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定 (.env / .env.local)
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須例:
     - JQUANTS_REFRESH_TOKEN=＜J-Quants のリフレッシュトークン＞
     - KABU_API_PASSWORD=＜kabu API のパスワード（必要に応じて）＞
     - OPENAI_API_KEY=＜OpenAI API キー＞
   - その他オプション:
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH, KILL_FLAG_PATH など

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=ya29.xxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB の初期化（監査ログテーブル等を作成）:
   - 例: 監査DB を作る
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db(settings.duckdb_path)  # または ":memory:"
     ```
   - あるいは既存接続にテーブルを追加:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect(str(settings.duckdb_path))
     init_audit_schema(conn, transactional=True)
     ```

---

## 使い方（代表例）

- 設定読み取り:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- 日次 ETL 実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（ai.news_nlp.score_news）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect(str(settings.duckdb_path))
  n_written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print("written:", n_written)
  ```

- 市場レジームスコア（ai.regime_detector.score_regime）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026,3,20), api_key=None)
  ```

- ファクター計算 / 研究:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect(str(settings.duckdb_path))
  moment = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- カレンダー操作（営業日判定など）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect(str(settings.duckdb_path))
  print(is_trading_day(conn, date(2026,3,20)))
  print(next_trading_day(conn, date(2026,3,20)))
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI 呼び出しを行う関数は api_key 引数でキーを渡すか、環境変数 OPENAI_API_KEY を使います。
- DuckDB 接続は duckdb.DuckDBPyConnection 型を利用します。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu API のパスワード
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector が使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG|INFO|...（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: "1" を設定すると .env 自動読み込みを無効化

---

## ディレクトリ構成

以下は主要ファイル・モジュールの抜粋です（src/kabusys 配下）:

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - calendar_management.py
  - etl.py
  - pipeline.py
  - stats.py
  - quality.py
  - audit.py
  - jquants_client.py
  - news_collector.py
  - etl.py (ETLResult re-export)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/*: ファクター計算・特徴量探索
- その他: strategy / execution / monitoring パッケージ群が __all__ に含まれる想定（実装次第で追加）

（各モジュール内に関数ドキュメント・設計方針コメントが含まれており、実装の意図や挙動が詳細に記載されています）

---

## 開発上の注意点 / 備考

- .env / .env.local はプロジェクトルートで自動ロードされます。テスト時に自動ロードを抑止したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany に空のリストを渡すと問題になるバージョン（0.10 系等）があるため、ライブラリ内で空チェックを行っています。
- OpenAI API 呼び出しはリトライや JSON パースの堅牢化を行っていますが、API 利用料に注意してください。
- RSS 取得には SSRF 対策（リダイレクト検査、プライベートIP検出）や XML の安全パーサ（defusedxml）を利用しています。

---

必要に応じて README に追加したい箇所（CI / テスト実行方法、ライセンス、より詳細な API 例など）があれば教えてください。