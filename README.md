# KabuSys

日本株向けのデータプラットフォームおよび自動売買支援ライブラリです。  
ETL、データ品質チェック、ニュースNLP（OpenAI 経由）、市場レジーム判定、研究用ファクター計算、監査ログ（約定トレーサビリティ）など、運用～研究に必要な機能群を提供します。

バージョン: 0.1.0

---

## 主な特徴

- ETL（J-Quants API からの差分取得／保存）
  - 株価（日足）、財務データ、JPXマーケットカレンダーの差分取得と冪等保存
  - ページネーション、トークン自動リフレッシュ、レート制限対応
- データ品質チェック
  - 欠損データ、スパイク（急騰／急落）、重複、日付不整合の検出
- ニュース収集・NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 回避・トラッキング除去）
  - OpenAI（gpt-4o-mini 等）を用いた銘柄別センチメントスコアリング（ai_scores へ書込）
  - マクロニュースを用いた市場レジーム判定（ma200 と LLM センチメントの合成）
- 研究用ユーティリティ
  - モメンタム、ボラティリティ、バリューなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）などの解析ツール
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）
  - シグナル→発注→約定までのトレーサビリティ用テーブルを用意
  - init_audit_db により DuckDB で監査データベース初期化が可能
- 設定管理
  - 環境変数 / .env / .env.local を自動読み込み（プロジェクトルート検出）
  - 必須設定は Settings 経由で取得（未設定時は明示的にエラー）

---

## 動作要件 / 依存関係（主なもの）

- Python 3.10+（型注釈や union 型表記を使用）
- duckdb
- openai（OpenAI Python クライアント）
- defusedxml
- （標準ライブラリ中心で実装されていますが、上記は必須）

pip でインストールする場合は requirements を用意してください（本リポジトリには同梱されていません）。

---

## 環境変数（主なもの）

最低限、外部 API を使うために以下を .env に設定してください：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: paper_trading 時のモック約定挙動（instant|partial|never|reject）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を探索）から `.env` → `.env.local` の順で読み込みます。
- OS 環境変数を優先し、`.env.local` は上書き可能。
- 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone ...

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # Unix/macOS
   - .venv\Scripts\activate     # Windows

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

   （プロジェクトを editable install する場合）
   - pip install -e .

4. .env を作成
   - リポジトリルートに `.env` を作成し、上記の環境変数を設定してください。
   - 例:
     - JQUANTS_REFRESH_TOKEN=xxxxx
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=...
     - DUCKDB_PATH=data/kabusys.duckdb

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの使用例です。各例では duckdb 接続を直接渡します。

- ETL（日次パイプライン）の実行例：

  ```python
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings
  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn)  # target_date を指定しなければ今日
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI を用いる）:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date に対する「前日 15:00 JST ～ 当日 08:30 JST」を対象にスコアを取得
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定:

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算例:

  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility, calc_value

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, target_date=date(2026,3,20))
  volatility = calc_volatility(conn, target_date=date(2026,3,20))
  value = calc_value(conn, target_date=date(2026,3,20))
  ```

- 監査DB 初期化（監査専用 DuckDB を作る）:

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は DuckDB 接続、監査テーブル群が作成済み
  ```

注意:
- OpenAI 呼び出しは API キーの設定（環境変数 OPENAI_API_KEY）が必要です。テスト時は各モジュールの内部 _call_openai_api をモックできます（ユニットテスト向けに設計されています）。
- J-Quants API 呼び出しは JQUANTS_REFRESH_TOKEN が必要です。

---

## 設定・挙動に関する補足

- KABUSYS_ENV（development / paper_trading / live）により挙動分岐（例: Paper Trading 設定）が行われます。Settings.is_paper / is_live / is_dev で判定できます。
- Paper Trading 用 SQLite とモックブローカー設定:
  - PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
  - PAPER_FILL_MODE（instant, partial, never, reject）
- 自動 .env 読み込みはプロジェクトルートを .git または pyproject.toml から検出して行います。テストで自動読み込みを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要モジュール一覧（要約）です。

- src/kabusys/
  - __init__.py
  - config.py             : 環境変数・設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースの LLM スコアリング（ai_scores への保存）
    - regime_detector.py  : 市場レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py    : J-Quants API クライアント / DuckDB への保存
    - pipeline.py         : ETL（run_daily_etl 等）
    - etl.py              : ETLResult 再エクスポート
    - news_collector.py   : RSS 収集・パース・保存
    - quality.py          : データ品質チェック（各種）
    - stats.py            : 統計ユーティリティ（zscore_normalize 等）
    - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
    - audit.py            : 監査ログ（監査テーブル・初期化）
  - research/
    - __init__.py
    - factor_research.py  : モメンタム / ボラティリティ / バリューの計算
    - feature_exploration.py : forward returns, IC, factor_summary, rank
  - ai/__init__.py
  - その他モジュール（strategy, execution, monitoring 等はパッケージ公開名として __all__ に含まれます）

（実際のプロジェクトルートには pyproject.toml やテスト、ドキュメント等が存在する想定です）

---

## 開発メモ / 設計方針（抜粋）

- ルックアヘッドバイアス対策:
  - モジュール内では datetime.today() / date.today() を直接参照しない関数設計がなされている（target_date を明示するスタイル）。
  - prices_daily などのクエリでは target_date 未満の条件などを用い、将来情報の参照を防止。
- 冪等性:
  - ETL の保存処理は ON CONFLICT DO UPDATE（DuckDB）で実装しており、再実行による重複を防止。
- フェイルセーフ:
  - LLM や API の失敗は多くの箇所でフォールバック（0.0 スコア等）して処理継続する設計。
- テストしやすさ:
  - 外部 API 呼び出しポイント（OpenAI 呼び出し、HTTP 開放など）は差し替え可能に実装（単体テストのために mock しやすい）。

---

## よくある問い（FAQ）

Q. OpenAI など外部 API の料金やレート管理はどうする？  
A. 本ライブラリは呼び出しごとに timeout とリトライ、バックオフを実装しています。実運用ではAPIコスト・レートを監視し、適切な課金プラン・呼び出し間隔を設定してください。

Q. DuckDB のスキーマはどこで定義される？  
A. ETL と保存関数は既定のテーブル名（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime など）を想定しています。スキーマ初期化はプロジェクト固有のスクリプトに依存します（audit 用の初期化は data.audit.init_audit_db を使用できます）。

---

必要に応じて README を拡張して、インストール要件ファイル（requirements.txt / pyproject.toml）、サンプル .env.example、スキーマ作成スクリプト、運用向け注意（API鍵管理・ログの保管・監視）などを追加することを推奨します。質問や補足したい箇所があれば教えてください。