# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP スコアリング（OpenAI 利用）、市場レジーム判定、研究用ファクター計算、監査ログ（注文→約定のトレーサビリティ）などを提供します。

---

## 概要

KabuSys は以下の用途を想定した Python モジュール群です。

- J-Quants API からの差分 ETL（株価・財務・市場カレンダー）
- RSS によるニュース収集と OpenAI を使った銘柄別センチメントスコア算出
- ETF とマクロニュースを組み合わせた市場レジーム判定
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）と統計ユーティリティ
- DuckDB を用いた監査ログスキーマの初期化（注文→約定のトレーサビリティ）
- データ品質チェック（欠損・スパイク・重複・日付不整合）

設計上の要点：
- ルックアヘッドバイアスを避ける（内部で date.today() を直接参照しないなど）
- API 呼び出しはリトライ／バックオフ／フェイルセーフを備える
- DuckDB をデータプラットフォームの永続化に使用
- 冪等性（ON CONFLICT）を意識した保存処理

---

## 機能一覧（主要）

- data.jquants_client
  - J-Quants API クライアント（株価、財務、カレンダー、上場銘柄情報）
  - レートリミッタ、トークン自動リフレッシュ、ページネーション対応
  - DuckDB へ冪等保存（raw_prices, raw_financials, market_calendar など）
- data.pipeline
  - 日次 ETL パイプライン（run_daily_etl）・個別 ETL（run_prices_etl 等）
  - ETL の結果を ETLResult データクラスで返却
- data.news_collector
  - RSS 取得、前処理、raw_news への冪等保存（SSRF 対策・サイズ制限等）
- data.quality
  - 欠損、スパイク、重複、日付不整合のチェック（QualityIssue を返す）
- data.audit
  - 監査ログ（signal_events, order_requests, executions）の DDL と初期化関数
- ai.news_nlp
  - 銘柄ごとのニュース集約 → OpenAI（gpt-4o-mini）でスコア化 → ai_scores に書き込み
  - バッチ処理、JSON Mode、応答バリデーション、リトライ制御
- ai.regime_detector
  - ETF（1321）200 日 MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- research
  - calc_momentum / calc_value / calc_volatility
  - calc_forward_returns / calc_ic / factor_summary / rank
- data.stats
  - zscore_normalize（クロスセクション正規化）等ユーティリティ

---

## 前提・依存

- Python 3.10+（PEP 604 の union type（|）を使用）
- 主な依存パッケージ（サンプル）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている箇所も多い）
- 実行環境に応じて追加で urllib・ssl 標準機能等が必要です。

requirements.txt がない場合は以下を参考にインストールしてください（環境による）:

pip install duckdb openai defusedxml

---

## 環境変数（主な設定）

このパッケージは .env ファイルまたは環境変数から設定を読み込みます（自動ロード機能あり）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

重要な環境変数（Settings クラスで参照）：

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャネル ID（必須）
- DUCKDB_PATH: DuckDB のファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）ファイルパス（既定: data/monitoring.db）
- PID_FILE_PATH: 実行プロセスの PID 管理ファイル（既定: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: development / paper_trading / live（既定: development）
- LOG_LEVEL: DEBUG|INFO|...（既定: INFO）
- OPENAI_API_KEY: OpenAI API キー（news_nlp/regime_detector は引数で渡すことも可）

プロジェクトルートに `.env` / `.env.local` を置くと自動的にロードされます（ただし OS 環境変数が優先されます）。

---

## セットアップ手順（簡易）

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトで requirements.txt があれば pip install -r requirements.txt）
4. .env を作成（例は下記）
5. データディレクトリ等を作成
   - mkdir -p data

例 .env（本番では秘密情報を適切に管理してください）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（サンプル）

以下は Python で直接モジュール関数を呼ぶ簡単な例です。実際はスクリプトやジョブランナーから呼び出してください。

- DuckDB 接続を作成して日次 ETL を実行

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY か api_key 引数で指定）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"wrote {n_written} ai_scores")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- 研究用ファクター計算（例: モメンタム）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
print(len(records))
```

注意点：
- OpenAI 呼び出しを含む処理は API キーを必要とします。キーは環境変数 `OPENAI_API_KEY` を設定するか、関数の api_key 引数で渡してください。
- ETL は J-Quants の認証トークン（JQUANTS_REFRESH_TOKEN）を必要とします。

---

## 自動 .env ロードについて

kabusys.config はプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を自動で読み込みます。既存の OS 環境変数は保護され、`.env.local` は上書き可能です。テスト時に自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要なソース構成（src/kabusys 以下）:

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
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/  (監視・運用系モジュールがある想定)
  - strategy/    (戦略・発注ロジックが入る想定)
  - execution/   (発注・ブローカー連携が入る想定)

（各モジュールの詳細はソース内の docstring を参照してください）

---

## テスト・開発

- ユニットテストは各モジュールの公開関数をモックや一時的な DuckDB 接続で検証してください（多くの関数は duckdb.DuckDBPyConnection を引数に取ります）。
- OpenAI 呼び出しはテスト時にモック化（unittest.mock.patch）して外部 API を発生させないようにしてください。news_nlp と regime_detector はそれぞれ内部の _call_openai_api を差し替えられる設計です。

---

## 運用上の注意

- 本コードには実際の発注ロジック（マーケット接続）を含む箇所がある想定です。実稼働で使用する前に必ずペーパートレード環境で検証してください（KABUSYS_ENV=paper_trading など）。
- API キーやトークンなどの秘密情報は安全に管理してください（CI の Secrets、Vault、環境変数など）。
- DuckDB 等のデータファイルはバックアップ・ローテーションを検討してください。

---

必要に応じて README の補足（インストール手順の詳細、CI/CD、運用 Runbook、API の仕様書リンクなど）を追加します。追加したい項目があれば教えてください。