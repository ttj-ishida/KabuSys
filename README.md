# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース NLP（OpenAI）・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、運用に必要な主要機能を備えています。

バージョン: 0.1.0

---

## 主要機能（概要）

- データ取得 / ETL
  - J-Quants API から株価日足、財務データ、JPX カレンダーを差分取得し DuckDB に冪等保存
  - 日次 ETL パイプライン (run_daily_etl) を提供

- ニュース NLP
  - RSS を収集して raw_news に保存（news_collector）
  - OpenAI を用いた銘柄ごとのニュースセンチメント集約と ai_scores への書き込み（score_news）
  - マクロ記事の LLM 評価と ETF (1321) MA 乖離を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター
  - モメンタム、バリュー、ボラティリティ等のファクター計算（research パッケージ）
  - 将来リターン計算、IC、統計サマリー等の解析ユーティリティ

- データ品質チェック
  - 欠損、重複、スパイク、日付不整合検出（quality モジュール）

- 監査ログ（トレーサビリティ）
  - signal → order_request → execution まで追跡可能な監査スキーマを DuckDB に初期化（init_audit_schema / init_audit_db）

- その他
  - カレンダー管理（営業日判定、next/prev_trading_day 等）
  - J-Quants クライアント（レート制御、リトライ、トークン自動リフレッシュ）
  - .env 自動読み込み（プロジェクトルートにある `.env` / `.env.local` を優先順で読み込む）

---

## 必要条件 / 推奨環境

- Python 3.10+
- 必要なパッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants / OpenAI / RSS）

インストール例（開発環境）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトルートに pyproject があれば
# pip install -e .
```

---

## 環境変数 / .env

プロジェクトは起点ファイルから親ディレクトリに `.git` または `pyproject.toml` を探し、見つかれば `.env` / `.env.local` を自動読み込みします（ただし環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動読み込みを無効化できます）。

主に使う環境変数（代表）:

- J-Quants
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OpenAI
  - OPENAI_API_KEY: OpenAI API キー（score_news / regime のデフォルト）
- kabuステーション API
  - KABU_API_PASSWORD
  - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- LINE通知（任意）
  - LINE_CHANNEL_ACCESS_TOKEN
  - LINE_USER_ID
- DB / ファイルパス
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
  - PID_FILE_PATH, KILL_FLAG_PATH
- 実行モード / ログ
  - KABUSYS_ENV: development / paper_trading / live
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL

必須のもの（実行用途により異なります）やサンプルは `.env.example` を参照して `.env` を作成してください。

注意: Settings を経由して値を取得し、必須設定が未設定の場合は例外が発生します。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／取得
2. 仮想環境を作成して依存をインストール
   - pip install duckdb openai defusedxml
3. プロジェクトルートに `.env` を作成（`.env.example` を参考）
   - 例: JQUANTS_REFRESH_TOKEN=xxxxx
   - optional: OPENAI_API_KEY=sk-...
4. DuckDB の保存先ディレクトリ（例: data/）を作成
   - mkdir -p data
5. 必要に応じて監査 DB を初期化

---

## 使い方（主な例）

以下は Python REPL / スクリプトからの利用例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続と簡単な ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を与えなければ today（内部で trading day に調整される）
print(result.to_dict())
```

- ニュース NLP（単日分のスコア生成）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# 明示的に api_key を渡すことも可能: score_news(conn, date(2026,3,20), api_key="sk-...")
written = score_news(conn, date(2026, 3, 20))
print("written:", written)
```

- 市場レジーム判定（regime score の算出）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20))  # OpenAI key は env OPENAI_API_KEY または api_key 引数
```

- 監査ログ DB の初期化
```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# テーブルが作成され、UTC タイムゾーンが設定される
```

- カレンダー関連ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出しは API 失敗時にフェイルセーフ（スコア 0 など）で継続する設計です。ただし API キーが未設定の場合は ValueError が投げられます。
- DuckDB に書き込む操作は冪等性を意識して作られています（ON CONFLICT 等）。

---

## 主要モジュールと API（簡易一覧）

- kabusys.config
  - settings: 各種設定プロパティ（jquants_refresh_token, duckdb_path, env, log_level など）
- kabusys.data
  - jquants_client: J-Quants API の fetch / save 関数
  - pipeline: run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
  - news_collector: fetch_rss / preprocess_text 等
  - quality: run_all_checks, check_missing_data, check_spike, check_duplicates, check_date_consistency
  - calendar_management: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job
  - audit: init_audit_schema, init_audit_db
  - stats: zscore_normalize
- kabusys.ai
  - news_nlp.score_news
  - regime_detector.score_regime
- kabusys.research
  - factor_research.calc_momentum / calc_value / calc_volatility
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank

---

## ディレクトリ構成（抜粋）

src/
  kabusys/
    __init__.py
    config.py
    ai/
      __init__.py
      news_nlp.py
      regime_detector.py
    data/
      __init__.py
      jquants_client.py
      pipeline.py
      etl.py
      news_collector.py
      quality.py
      stats.py
      calendar_management.py
      audit.py
      etl.py
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
    monitoring/ (※存在する場合)
    strategy/   (※存在する場合)
    execution/  (※存在する場合)

各モジュールは docstring と設計方針コメントが豊富に書かれているため、利用時は該当ファイルを参照してください。

---

## 運用上の注意 / ベストプラクティス

- Look-ahead バイアスに注意
  - research / ai モジュールは内部で「target_date 未満のみ使用」等の工夫があります。バックテストや再現性を担保するため、関数の `target_date` 引数を適切に設定してください。
- API キー管理
  - OPENAI_API_KEY や JQUANTS_REFRESH_TOKEN は `.env` に保存するか安全なシークレットストアを利用してください。
- リトライ / フェイルセーフ
  - 外部 API はリトライやフォールバックが入っていますが、頻度や料金に注意してください（OpenAI 呼び出しなど）。
- DuckDB ファイルは定期バックアップを推奨します。監査ログは削除しない前提で設計されています。

---

## さらに詳しく / 参考

- 各モジュールの docstring に設計方針や処理フローが詳細に記載されています。必要な機能の実装や拡張は該当ファイルを参照してください。
- .env 読み込みはプロジェクトルートの検出に基づくため、スクリプト実行時の CWD に依存しない設計です。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動読み込みを無効にできます。

---

不明点や README に追加したい内容があれば教えてください。必要に応じて実行例（より詳しいサンプルスクリプト）や environment 変数のテンプレート (.env.example) を作成します。