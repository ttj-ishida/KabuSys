# KabuSys

日本株向けのデータプラットフォーム兼自動売買（Research / Strategy / Execution）ユーティリティ群。  
DuckDB を中心に、J-Quants からのデータ取得（株価・財務・カレンダー）、ニュース収集・NLP（OpenAI）、ファクター計算、ETL、監査ログなどを提供します。

---

## 概要

KabuSys は以下の用途を想定したライブラリ群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- ニュース収集（RSS）と OpenAI によるニュースセンチメント評価（ai_scores）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを統合）
- ファクター計算・特徴量探索（モメンタム・バリュー・ボラティリティ・IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- J-Quants / kabu API クライアント、ニュース収集のセキュリティ対策（SSRF 対策等）

設計上の重点:
- ルックアヘッドバイアスを避ける（date 引数ベース・datetime.today() を介さない実装）
- DuckDB をデータレイヤとする軽量・効率的な SQL ベース処理
- 外部 API 呼び出しはリトライ・レート制御・フォールバックを実装

---

## 主な機能一覧

- ETL
  - run_daily_etl: 市場カレンダー・株価・財務の差分取得と品質チェック
  - run_prices_etl / run_financials_etl / run_calendar_etl：個別ジョブ
- データクライアント
  - J-Quants クライアント（fetch / save / token refresh / rate limit 対応）
- ニュース
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去）
  - score_news: OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを ai_scores に書き込み
- 市場レジーム
  - score_regime: ETF 1321 の MA200 乖離 + マクロニュース（LLM）で daily regime を決定
- Research / Factor
  - calc_momentum, calc_value, calc_volatility: ファクター計算
  - calc_forward_returns, calc_ic, factor_summary, rank: 特徴量探索・評価
- データ品質
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- 監査ログ
  - init_audit_db / init_audit_schema: 監査テーブルの初期化・接続生成

---

## 前提 / 要件

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
  - （標準ライブラリ以外の依存は requirements.txt を用意していればそちらを参照）
- J-Quants のリフレッシュトークン（API アクセス用）
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- ローカルに DuckDB ファイルを格納するディスク領域

---

## セットアップ手順

1. リポジトリをチェックアウト（パッケージ化されている前提）
   - 例: git clone ... && cd project

2. 仮想環境の作成と依存パッケージのインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （開発用に editable install を行う場合）
     - pip install -e .

3. 環境変数 / .env の準備
   - プロジェクトルート（pyproject.toml または .git があるディレクトリ）に .env / .env.local を配置すると自動読み込みされます（優先順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。
   - 必須の環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime を使う場合）
   - 任意/推奨:
     - KABU_API_PASSWORD, KABU_API_BASE_URL
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用: data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, その他監視用閾値

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. DuckDB スキーマ（テーブル定義）は ETL 実行や初期化関数で作成する想定です。監査DBを別途初期化する場合は init_audit_db を使用します（下の「使い方」参照）。

---

## 使い方（サンプル）

以下は主要 API の簡単な使用例です。実行前に必要な環境変数と DuckDB のパスを設定してください。

- DuckDB 接続の取得例:
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行する（デフォルトは今日）:
```python
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn)
print(result.to_dict())
```

- 個別 ETL（株価）:
```python
from kabusys.data.pipeline import run_prices_etl
from datetime import date

fetched, saved = run_prices_etl(conn, target_date=date(2026, 3, 20))
print(f"fetched={fetched}, saved={saved}")
```

- ニュースセンチメント評価（score_news）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY が環境変数に設定されている場合、api_key 引数は省略可
n_written = score_news(conn, target_date=date(2026, 03, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（score_regime）:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 03, 20))
```

- 監査 DB を初期化して接続を得る:
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル（signal_events, order_requests, executions 等）が作成される
```

- 研究用関数（例: モメンタム算出）:
```python
from cabusys.research.factor_research import calc_momentum
from datetime import date

mom = calc_momentum(conn, target_date=date(2026,3,20))
# list[dict] が返る
```

注意点:
- score_news / score_regime は OpenAI を呼び出すため API キーと課金に注意してください。API エラー時はフォールバック動作（0.0）をする実装が多いです。
- ETL / save_* 関数は DuckDB へ冪等に保存するよう ON CONFLICT 等を使っています。

---

## 環境変数一覧（代表的なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD: kabu API パスワード（発注連携がある場合）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知連携用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視DBパス（default data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: ロギングレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 にすると .env 自動読み込みを無効化

---

## 補足 / 実装上の注意

- 自動 .env ロードはパッケージ内の logic によりプロジェクトルート（.git または pyproject.toml を含むディレクトリ）から行われます。テストや特殊実行時は無効化可能です。
- OpenAI 呼び出しはモデル gpt-4o-mini を想定し、JSON Mode（response_format={"type": "json_object"}）での解析を行っています。API 仕様変更や JSON パースエラーに対するフォールバックが実装されています。
- J-Quants クライアントは 120 req/min のレートリミットを守るために固定間隔スロットリングを実装しています。API の 401 は自動リフレッシュ処理を行い、429 / 5xx は指数バックオフでリトライします。
- ニュース収集は SSRF 対策、トラッキングパラメータ除去、XML の defusedxml による安全なパースを行っています。

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
  - etl.py (公開エイリアス)
  - quality.py
  - stats.py
  - news_collector.py
  - calendar_management.py
  - audit.py
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- research/factor_research.py, feature_exploration.py など（ファクター・IC 計算）

（README では主要ファイルを抜粋しています。実装全体は src/kabusys 配下にあります。）

---

## 開発・テストのヒント

- OpenAI 呼び出し部分はモックしやすいように内部の呼び出し関数（例: kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api）を patch してテスト可能です。
- DuckDB はインメモリ ":memory:" を使ってユニットテストを行うことができます（例: duckdb.connect(":memory:")）。
- .env の自動ロードは設定ファイルを使ったテストで副作用が出る場合があるため、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして明示的に環境を構築してください。

---

## ライセンス / 貢献

（ここにプロジェクトのライセンス情報や貢献方法を記載してください。）

---

この README はコードベースの主要な機能と利用法をまとめた抜粋です。より詳細な仕様やデータスキーマ、運用フローはコード内の docstring（各モジュールヘッダ）や別途用意された設計ドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。