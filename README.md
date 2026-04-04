# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、ETL、データ品質チェック、ニュースNLP（OpenAI を用いたセンチメント）、市場レジーム判定、リサーチ用ファクター計算、監査ログ用スキーマなど、バックテスト／運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

## 主要機能

- 環境変数/設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証（settings オブジェクト）
- データ ETL（J-Quants 経由）
  - 日次株価（OHLCV）取得・保存（ページネーション・レート制御・リトライ）
  - 財務データ（四半期）取得・保存
  - JPX マーケットカレンダー取得・保存
  - 差分取得／バックフィル対応
  - ETL の結果を ETLResult として返却
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出
  - QualityIssue オブジェクトで詳細を返す
- ニュース収集（RSS）
  - RSS 取り込み、前処理、URL 正規化、SSRF 対策、raw_news への冪等保存想定
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースをまとめて LLM に送りセンチメントを算出（ai_scores に保存）
  - JSON Mode を使用したレスポンス検証・バッチ処理
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュースセンチメントを重み付け合成して日次レジーム判定
  - OpenAI を用いたマクロセンチメント評価（フェイルセーフあり）
- リサーチ / ファクター計算
  - Momentum, Volatility, Value 等のファクター計算
  - 将来リターン計算、IC（Spearman ランク相関）、統計サマリー
  - Z-score 正規化ユーティリティ
- 監査・トレーサビリティ
  - signal_events / order_requests / executions 等の監査テーブルの DDL と初期化ユーティリティ
  - DuckDB 用の init_audit_db / init_audit_schema を提供

---

## 動作要件（推奨）

- Python 3.10 以上（型ヒントに | 演算子を使用）
- 依存ライブラリ（代表例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、OpenAI、RSS ソース など）

具体的なパッケージは pyproject.toml / requirements.txt に依存します。開発環境では以下一例でインストールできます:

pip install duckdb openai defusedxml

（プロジェクト配布物に pyproject.toml があれば pip install -e . を利用してください）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウトし、開発環境を作成します。

   git clone <repo>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate

2. 依存ライブラリをインストールします（例）:

   pip install -U pip
   pip install -e .    # pyproject.toml がある場合
   # or
   pip install duckdb openai defusedxml

3. 環境変数を設定します（.env をプロジェクトルートに配置するか、OS 環境変数で設定）。

必須・主要な環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注系）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）

任意・デフォルト値あり
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト INFO）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）

自動 .env 読み込みについて
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml）を探し、.env → .env.local の順で読み込みます。
- 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（代表的な利用例）

以下はライブラリ関数の簡単な使用例です。実行前に必要な環境変数を設定してください。

- 設定参照

```python
from kabusys.config import settings

print(settings.duckdb_path)
token = settings.jquants_refresh_token  # 必須: 未設定なら例外
```

- DuckDB に接続して日次 ETL を実行

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコアリング

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY を利用
print(f"scored {n_written} codes")
```

- 市場レジーム判定

```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作成）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- J-Quants の ID トークンを取得（直接利用する場合）

```python
from kabusys.data.jquants_client import get_id_token

token = get_id_token()  # settings.jquants_refresh_token を使用
```

---

## 主要モジュール / API 概要

- kabusys.config
  - settings: 設定オブジェクト（環境変数からプロパティ参照）
- kabusys.data
  - pipeline.run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - jquants_client.get_id_token, fetch_daily_quotes, fetch_financial_statements, save_* 関数
  - quality.run_all_checks / check_missing_data / check_spike / check_duplicates / check_date_consistency
  - news_collector.fetch_rss / preprocess_text 等
  - stats.zscore_normalize
  - audit.init_audit_schema / init_audit_db
  - calendar_management.is_trading_day / next_trading_day / get_trading_days / calendar_update_job
- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- kabusys.research
  - factor_research.calc_momentum / calc_volatility / calc_value
  - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
- パッケージ公開: kabusys.__all__ に data, strategy, execution, monitoring（strategy/execution/monitoring は運用向けモジュール名として公開されますが、このコードベースの一部は含まれていない可能性があります）

---

## ディレクトリ構成（主要ファイル）

（プロジェクトの src ディレクトリ内構成の抜粋）

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
      - stats.py
      - quality.py
      - audit.py
      - news_collector.py
      - calendar_management.py
      - etl.py
      - pipeline.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/（その他）
    - (strategy/, execution/, monitoring/ は公開対象として想定されています）

---

## 開発上の注意点・設計方針（抜粋）

- Look-ahead bias 回避:
  - 多くの関数は date.today()/datetime.today() を直接参照せず、外部から target_date を受け取る設計です。バックテストや再現性を保つため、呼び出し時に対象日を明示してください。
- 冪等性:
  - J-Quants から得たデータ保存は ON CONFLICT DO UPDATE を利用して冪等に保存します。
  - ニュース収集は URL 正規化 + ハッシュで冪等を想定。
- フェイルセーフ:
  - OpenAI 呼び出し等の外部 API が失敗した場合、多くの処理はゼロ値やスキップで継続する設計です（ログに警告を出力）。
- セキュリティ:
  - RSS 取得は SSRF 対策（リダイレクト検査、プライベートIPブロック）を実装。
  - defusedxml を用いて XML パースの安全性を担保。

---

## ログ / 監視関連

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- 監視に関する設定（PID ファイルパス、kill フラグ、CPU/MEM/DISK の閾値）は settings から取得します。

---

## よくある質問

Q. OpenAI が応答しない／課金が不安なときは？  
A. news_nlp / regime_detector は API 呼び出し失敗時にスコアを 0.0 にフォールバックするなどのフェイルセーフ実装があります。テスト時は API 呼び出し部分をモックしてテストしてください（モジュール内で _call_openai_api をパッチ可能）。

Q. ローカルで DuckDB ファイルを使いたい  
A. デフォルトは data/kabusys.duckdb です。環境変数 DUCKDB_PATH を設定するか、settings.duckdb_path を参照して接続してください。

---

## 貢献 / 開発

- コードはタイプヒントやロギングが充実しており、ユニットテストを追加しやすい構成です。外部 API 呼び出し部分は簡単にモック可能な作りを意識しています。
- PR の際はユニットテストと簡潔な変更説明を添えてください。

---

以上がこのコードベースの概要と利用方法のまとめです。README の補足やサンプル CLI、CI 設定などを追加したい場合は、目的（例: ETL の定期実行スケジュール、監視アラート設定、バックテストワークフロー）を教えてください。必要に応じて具体的なコマンド例・テンプレートを作成します。