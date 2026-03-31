# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
市場データの ETL、ニュースの NLP スコアリング、レジーム判定、ファクター計算、データ品質チェック、監査ログなど、バックテスト／実運用に必要な基盤機能を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 設定（環境変数 / .env）
- 使い方（主要 API の例）
- ディレクトリ構成（主要ファイル説明）

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API から日本株データ（株価日足・財務・マーケットカレンダー等）を取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント分析（銘柄毎）
- マクロニュースと ETF（1321）200日移動平均乖離を組み合わせた市場レジーム判定
- 研究用途のファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 監査ログ（signal -> order_request -> execution のトレーサビリティ）
- 複数コンポーネントのユーティリティ（統計処理、カレンダー管理、J-Quants クライアント等）

設計方針としては、Look-ahead bias を避ける設計、DB（DuckDB）中心の処理、API 呼び出しのリトライ・レート制御、フェイルセーフ（API 失敗時に処理継続）などを重視しています。

---

## 機能一覧

主な機能（モジュール別）

- kabusys.config
  - .env 自動読み込み（.env / .env.local、プロジェクトルート検出）
  - 設定プロパティ（J-Quants トークン、kabu API、Slack、DB パス、実行環境など）

- kabusys.data
  - jquants_client: J-Quants API からのデータ取得・保存（差分取得・ページネーション・保存の冪等性）
  - pipeline: 日次 ETL の統合エントリ（run_daily_etl）
  - calendar_management: 市場カレンダー管理と営業日判定ユーティリティ
  - news_collector: RSS 取得・前処理・raw_news への保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付整合性）
  - stats: zscore 正規化などの統計ユーティリティ
  - audit: 監査ログ用テーブルの初期化・ユーティリティ

- kabusys.ai
  - news_nlp.score_news: ニュースを LLM（OpenAI）で銘柄別にスコアリングして ai_scores に保存
  - regime_detector.score_regime: ETF（1321）MA とマクロニュースセンチメントを合成して market_regime に保存

- kabusys.research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
  - data.stats.zscore_normalize（正規化ユーティリティ）

---

## 前提条件

- Python 3.10+
- 主要依存ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

実際のプロジェクトでは pyproject.toml / requirements.txt に依存関係を明示してください。

---

## セットアップ手順

1. リポジトリをクローンして開発用インストール（例）

   ```bash
   git clone <repo-url>
   cd <repo>
   pip install -e ".[dev]"  # または必要なパッケージを個別に pip install
   ```

2. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成することで自動読み込みされます（既定で有効）。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

3. DuckDB 用ディレクトリを作成（デフォルトは data/kabusys.duckdb）
   - `settings.duckdb_path` の親ディレクトリは自動作成される箇所もありますが、必要に応じてディレクトリ作成をしてください。

---

## 設定（環境変数 / .env）

必須（実行に必要なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード
- SLACK_BOT_TOKEN: Slack Bot Token（通知等に使用する場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID

OpenAI 関連
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 使用時に参照）

任意 / デフォルト
- KABUSYS_ENV: 実行環境（development / paper_trading / live）デフォルト `development`
- LOG_LEVEL: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）デフォルト `INFO`
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト `data/kabusys.duckdb`）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト `data/monitoring.db`）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: `1` をセットすると .env の自動ロードを無効化

.env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

---

## 使い方（主要 API の例）

以下は主要な操作のコード例です。実行前に必要な環境変数を設定してください。

- DuckDB 接続の取得（簡単な例）

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# conn: DuckDB 接続、target_date: ETL 対象日（None で今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコア付与（OpenAI 必須）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# APIキーを引数で明示することも可能（None の場合 OPENAI_API_KEY 環境変数を参照）
count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"scored {count} symbols")
```

- 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 監査ログ DB 初期化（独立 DB を使う例）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn に対して監査テーブルが利用可能
```

- カレンダー関連ユーティリティ

```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

d = date(2026, 4, 1)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

- 研究用途のファクター計算（例: モメンタム）

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄の dict のリスト
```

ログレベルや挙動の切り替えは環境変数 `LOG_LEVEL`, `KABUSYS_ENV` で制御します。

注意点:
- OpenAI や J-Quants への API 呼び出しは実 HTTP リクエストを行います。API キー・トークンの管理に注意してください。
- DuckDB のテーブルスキーマはアプリケーション側で期待される形になっている前提です（ETL 実行時に必要なテーブルがなければ作成処理を追加してください）。

---

## ディレクトリ構成（主要ファイル）

以下はリポジトリの主要ソースファイルと簡単な説明（パスは src/kabusys/ 以下）:

- __init__.py
  - パッケージのバージョンと公開モジュールリスト

- config.py
  - 環境変数の読み込みと Settings クラス（J-Quants, kabu, Slack, DB パス、実行環境）

- ai/
  - news_nlp.py: ニュースの LLM ベースセンチメント分析（score_news）
  - regime_detector.py: ETF MA とマクロニュースを統合して市場レジーム判定（score_regime）

- data/
  - jquants_client.py: J-Quants API クライアント（取得・保存関数、レートリミット・リトライ・ID トークン管理）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - calendar_management.py: 市場カレンダーの管理、営業日判定、calendar_update_job
  - news_collector.py: RSS フィード取得と raw_news への保存（SSRF 対策、XML 安全パーサ）
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats.py: z-score 正規化などの統計ユーティリティ
  - audit.py: 監査ログ（signal_events / order_requests / executions テーブルの DDL と初期化）
  - etl.py: ETLResult を再エクスポート

- research/
  - factor_research.py: モメンタム / ボラティリティ / バリュー等の計算
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数
  - __init__.py: 研究用ユーティリティの公開

---

## 補足 / 運用上の注意

- 自動ロードされる .env ファイルはプロジェクトルート（.git または pyproject.toml のあるディレクトリ）を検出して読み込みます。テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を利用して自動読み込みを無効にできます。
- OpenAI の呼び出しは JSON mode を利用する点に依存している箇所があり、レスポンスの検証やフォールバックロジックが組み込まれていますが、API の変化に応じて調整が必要になる場合があります。
- DuckDB のバージョン差異により executemany / 型バインドの挙動差があるため、コード中で互換性考慮の実装が行われています。DuckDB のバージョンアップ時には注意してください。
- 実運用（特に live）での注文送信や約定連携部分は外部ブローカー API の実装に依存します。本コードは監査ログ・発注の枠組みを提供しますが、実際の発注実装（execution モジュール等）を接続する必要があります。

---

必要なら、README にサンプル .env.example、CI / テスト手順、開発ガイドライン（ブランチ運用・コードスタイル）なども追加できます。必要な内容を教えてください。