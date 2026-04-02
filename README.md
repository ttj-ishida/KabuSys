# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J‑Quants API からのデータ取得（ETL）、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ（トレーサビリティ）、リサーチ／ファクター計算等のユーティリティを提供します。

## プロジェクト概要
KabuSys は以下を目的とした Python パッケージです。

- J‑Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（DuckDB 保存）
- RSS ニュース収集と OpenAI を用いた銘柄別ニュースセンチメント評価（ai_scores テーブル）
- マクロ + テクニカル（ETF 1321 の MA200 乖離）を組み合わせた市場レジーム判定（bull/neutral/bear）
- 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
- 研究用ファクター計算、統計ユーティリティ、データ品質チェック

設計の共通方針として、ルックアヘッドバイアス回避（内部で datetime.today() を直接参照しない）、DuckDB ベースの冪等保存、外部 API 呼び出しのリトライやフェイルセーフ処理を重視しています。

## 機能一覧
- データ取得・ETL
  - fetch / save: 株価日足（raw_prices）、財務（raw_financials）、マーケットカレンダー（market_calendar）
  - run_daily_etl: ETL の一括実行（カレンダー → 株価 → 財務 → 品質チェック）
- ニュース & NLP
  - RSS 収集（news_collector.fetch_rss）、前処理、raw_news への保存ロジック
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（kabusys.ai.news_nlp.score_news）
- レジーム判定
  - kabusys.ai.regime_detector.score_regime: ETF 1321 の MA200 乖離（70%）とマクロニュースセンチメント（30%）の合成判定
- 研究（Research）
  - モメンタム / ボラティリティ / バリューファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン、IC 計算、ファクター統計（feature_exploration）
  - zscore 正規化ユーティリティ（data.stats）
- データ品質チェック（data.quality）
  - 欠損・スパイク・重複・日付不整合の検出
- 監査ログ（data.audit）
  - 監査テーブルの DDL と初期化ユーティリティ（init_audit_schema / init_audit_db）
- 設定管理（config）
  - .env 自動読み込み（プロジェクトルートを検出）、Settings クラスによる環境変数アクセス

## 必要条件 / 依存関係
主な依存ライブラリ（実行環境に応じて pip インストールしてください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（標準ライブラリで賄われている部分も多くあります。実行する機能により追加のライブラリが必要になる場合があります。）

例:
pip install duckdb openai defusedxml

## セットアップ手順
1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存関係をインストール
   - pip install duckdb openai defusedxml
4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.git または pyproject.toml があるディレクトリをルートと判定）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

### 推奨する .env（例）
必要に応じて以下を `.env` に設定してください（実際の値はご自分の環境に合わせてください）:

- JQUANTS_REFRESH_TOKEN=（J-Quants リフレッシュトークン）
- KABU_API_PASSWORD=（kabuステーション API パスワード）
- KABU_API_BASE_URL=（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN=（Slack ボットトークン）
- SLACK_CHANNEL_ID=（通知先チャンネルID）
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PID_FILE_PATH=data/execution.pid
- CPU_THRESHOLD_PCT=90.0
- MEMORY_THRESHOLD_PCT=85.0
- DISK_THRESHOLD_PCT=90.0
- KABUSYS_ENV=development
- LOG_LEVEL=INFO
- OPENAI_API_KEY=（OpenAI API キー。score_news / score_regime が必要とする）

Settings は必要な環境変数が未設定の場合に ValueError を投げます（必須項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。

## 使い方（簡単な例）
以下は Python REPL やスクリプトから利用する例です。DuckDB 接続は `duckdb.connect(path)` で取得します。

1) 監査 DB の初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# コネクションに対してその他の操作が可能
```

2) 日次 ETL の実行（J‑Quants トークンは settings から自動取得）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

3) ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY で指定）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {written}")
```

4) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

5) 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
m = calc_momentum(conn, target_date=date(2026, 3, 20))
v = calc_volatility(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
```

注意:
- score_news / score_regime は OpenAI API を呼び出すため API キー（OPENAI_API_KEY、または関数引数 api_key）が必要です。
- ETL / save 系関数は DuckDB 上のスキーマ（raw_prices, raw_financials, market_calendar 等）が前提です。スキーマ作成は別途用意するか、ETL 初回実行前にスキーマ初期化処理を実行してください（プロジェクトにスキーマ初期化ユーティリティがあればそちらを使用）。

## ディレクトリ構成（主要ファイル）
パッケージ名: kabusys

- kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み（.env/.env.local）と Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースの集約・OpenAI による銘柄別センチメント算出（score_news）
    - regime_detector.py
      - ETF 1321 の MA200 とマクロニュースを組み合わせたレジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py
      - market_calendar を用いた営業日判定、next/prev_trading_day 等
    - pipeline.py
      - run_daily_etl 等、ETL のオーケストレーション
    - etl.py
      - ETLResult の再エクスポート
    - jquants_client.py
      - J‑Quants API 呼び出し、リトライ、ページネーション、DuckDB 保存関数
    - news_collector.py
      - RSS 取得、前処理、SSRF 対策、記事 ID 正規化
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - audit.py
      - 監査ログ用 DDL、init_audit_schema / init_audit_db
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank

各モジュールはドキュメント文字列およびログ出力で挙動を詳細に説明しています。利用時は各関数の docstring を参照してください。

## 動作上の注意点
- OpenAI / J‑Quants API を使用する処理はそれぞれの API キー／トークンが必要です。API 呼び出しにはリトライやレート制御が組み込まれていますが、利用制限や課金に注意してください。
- DuckDB スキーマ（テーブル定義）はプロジェクト外で管理されている想定の箇所があります。ETL を行う前にテーブル定義を準備してください。
- 自動 .env 読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テストでこれを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

追加の使い方サンプルや運用手順（cron や CI での ETL スケジュール、Slack 通知連携、kabuステーション経由の発注フロー等）が必要であれば、目的に応じて README を拡張します。どの操作を自動化したいか教えてください。