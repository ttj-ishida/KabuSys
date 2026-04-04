# KabuSys — 日本株自動売買プラットフォーム

KabuSys は日本株のデータプラットフォーム・リサーチ・シグナル生成・監査・AI ベースのニュースセンチメントを含む自動売買補助ライブラリです。本リポジトリは以下を目的としています。

- J-Quants からのデータ ETL（株価・財務・市場カレンダー）
- ニュース収集と LLM による銘柄別センチメント算出
- 市場レジーム判定（MA200 と マクロニュースの合成）
- ファクター算出・特徴量探索（リサーチ用ユーティリティ）
- データ品質チェック、監査ログ（トレーサビリティ）
- DuckDB ベースの永続化と冪等保存ロジック

バージョン: package 定義は `src/kabusys/__init__.py` の `__version__ = "0.1.0"`

---

## 主な機能一覧

- data
  - ETL パイプライン：日次差分取得（株価 / 財務 / カレンダー）と品質チェック（kabusys.data.pipeline）
  - J-Quants クライアント：API リクエスト、認証、ページネーション、レート制御（kabusys.data.jquants_client）
  - ニュース収集：RSS 取得、前処理、SSRF 対策、raw_news 保存（kabusys.data.news_collector）
  - カレンダー管理：営業日判定、next/prev_trading_day、calendar 更新ジョブ（kabusys.data.calendar_management）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）（kabusys.data.quality）
  - 監査ログスキーマ初期化（order/signals/executions）（kabusys.data.audit）
  - 汎用統計ユーティリティ（zscore 正規化）（kabusys.data.stats）

- ai
  - ニュース NLP（銘柄別センチメント算出、OpenAI 使用）（kabusys.ai.news_nlp）
  - 市場レジーム判定（ETF 1321 の MA200 と マクロニュース合成）（kabusys.ai.regime_detector）

- research
  - ファクター計算（モメンタム・バリュー・ボラティリティ等）（kabusys.research.factor_research）
  - 特徴量探索・将来リターン・IC 計算（kabusys.research.feature_exploration）

- config
  - 環境変数の自動読み込み・設定ラッパ（.env / .env.local 対応、設定プロパティ）（kabusys.config.Settings）

---

## 動作要件（想定）

最低限必要な Python パッケージ（実行時に使用される代表例）:

- Python 3.9+
- duckdb
- openai
- defusedxml

（プロジェクトの実際の requirements.txt がある場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化します。

   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows:
     - python -m venv .venv
     - .venv\Scripts\activate

2. 開発用にインストール（セットアップ方法は環境に合わせて）:

   - pip install -e . もしくは必要パッケージを個別にインストール:
     - pip install duckdb openai defusedxml

3. 環境変数を設定する:
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` を置くと自動で読み込まれます。
   - 優先順位: OS 環境変数 > .env.local > .env
   - 自動ロードを無効にしたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

4. データベース用ディレクトリ作成（必要に応じて）:
   - デフォルトでは `data/kabusys.duckdb`, `data/monitoring.db`, PID / フラグファイルも `data/` 下を参照します。必要に応じてディレクトリを作成してください。

---

## 環境変数（主要）

必須（最低限の動作に必要）:

- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（kabusys.data.jquants_client.get_id_token で使用）

- KABU_API_PASSWORD
  - kabuステーション等の API パスワード（発注実装がある場合）

任意 / 推奨:

- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector に使用）

- KABU_API_BASE_URL
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
  - LINE 通知を使う場合

- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- PID_FILE_PATH (デフォルト: data/execution.pid)
- KILL_FLAG_PATH (デフォルト: data/kill.flag)

- KABUSYS_ENV
  - 値: development / paper_trading / live（デフォルト: development）

- LOG_LEVEL
  - 値: DEBUG / INFO / WARNING / ERROR / CRITICAL

注意: `.env` のパースは引用・コメント・export 形式に対応しています。詳細は `kabusys.config` を参照してください。

---

## 使い方（簡単なコード例）

以下はパッケージ API を用いた代表的な利用例です。実行は仮想環境内で行ってください。

- DuckDB 接続を作って日次 ETL を実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースセンチメントを算出して ai_scores に書き込む

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム（bull/neutral/bear）を算出する

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY は環境変数で設定されている前提
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ専用 DB を初期化する

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- J-Quants トークンを明示取得（テスト等）

  ```python
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使う
  print(token)
  ```

注:
- AI（OpenAI）呼び出しは API 負荷・料金がかかります。テストではモックを利用してください。
- 各関数はルックアヘッドバイアスに配慮して設計されています（内部で date.today() を参照しない等）。

---

## 自動読み込み動作の注意点

- `kabusys.config` はプロジェクトルートを .git または pyproject.toml で検出し、`.env` と `.env.local` を自動で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` より優先されます。
- 自動読み込みを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。

---

## ディレクトリ構成（主要ファイル説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・Settings（プロジェクト設定）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースを銘柄別に集約して OpenAI でスコアリング、ai_scores へ書込
    - regime_detector.py
      - ETF 1321 の MA200 とマクロニュースを合成して market_regime に記録
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（認証・データ取得・保存）
    - pipeline.py
      - ETL パイプライン（run_daily_etl / 個別 ETL）
    - news_collector.py
      - RSS 収集・前処理・raw_news 保存（SSRF 対策あり）
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・calendar_update_job
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py
      - 監査ログスキーマの初期化（signal_events / order_requests / executions）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize 等）
    - etl.py
      - ETLResult の再エクスポートなど
  - research/
    - __init__.py
    - factor_research.py
      - Momentum / Value / Volatility / Liquidity の計算
    - feature_exploration.py
      - 将来リターン / IC / 統計サマリー 等
  - ai/（上記）
  - その他モジュール群（execution / strategy / monitoring）は __all__ に含まれており、実際の取引ロジックや監視はそれらの実装に依存します（このコードベースでは主にデータ取得・研究・NLP/監査周りが実装されています）。

---

## 開発・貢献

- リポジトリに対する変更は PR（プルリクエスト）でお願いします。
- テストを書く際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を活用して環境依存を排除してください。
- OpenAI / J-Quants など外部 API はモック化してユニットテストを実行してください。

---

## 免責・注意事項

- 本プロジェクトは自動売買の補助ライブラリです。実際の取引に使用する場合は自己責任で行ってください。
- 本コードは料金・API レート・API 利用規約に従って使用してください。
- AI による判断は完璧ではありません。フェイルセーフ設計（API 失敗時のフォールバック等）が入っていますが、必ず監督とリスク管理を行ってください。

---

必要に応じて README に追記します。例えば:
- 実際の依存関係の明示的な requirements.txt の内容
- CI / テスト実行方法
- 具体的なデータベーススキーマ（DDL）
など、追加で出力できます。どの部分を詳しく書きたいか教えてください。