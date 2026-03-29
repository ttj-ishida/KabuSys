# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）など、量的運用（Quant / Algo）に必要な基盤機能を提供します。

---

## 特徴（機能一覧）

- データ取得（J-Quants API）
  - 日次株価（OHLCV）、財務データ、上場銘柄情報、JPX マーケットカレンダーの差分取得と保存（冪等保存）
  - レートリミットとリトライ処理を備えたクライアント実装

- ETL パイプライン
  - run_daily_etl による日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得／バックフィル対応、品質チェックの統合

- ニュース収集
  - RSS フィードからの安全な収集（SSRF 対策、gzip 上限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存ロジック（記事ID は正規化 URL の SHA-256）

- ニュース NLP（OpenAI）
  - gpt-4o-mini を用いた銘柄別センチメント（score_news）
  - チャンク分割・バッチ呼び出し、JSON モードでの検証、リトライポリシー

- 市場レジーム判定
  - ETF(1321) の 200 日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で判定（score_regime）

- 研究用ユーティリティ（research）
  - Momentum / Volatility / Value といったファクター計算
  - 将来リターン算出、IC（スピアマン）計算、統計サマリー、Z スコア正規化

- データ品質チェック
  - 欠損・スパイク・重複・日付不整合検出（QualityIssue を返す）

- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査スキーマを提供、init_audit_db で DuckDB に初期化可能
  - 発注フローの完全トレース（UUID ベースの冪等キー設計）

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート自動検出）
  - 必須環境変数を Settings クラスで取得

---

## 前提・依存

主な Python パッケージ（例）:
- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK、v1 系)
- defusedxml
- typing_extensions（必要に応じて）
- その他（標準ライブラリで実装されている部分が多い）

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンし、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール（例）
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject があればそちらを利用してください）
   - pip install -e .

3. 環境変数を準備
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local は上書き）
   - 自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定

4. 必須の環境変数（一部）
   - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   - KABU_API_PASSWORD=your_kabu_api_password
   - SLACK_BOT_TOKEN=your_slack_bot_token
   - SLACK_CHANNEL_ID=your_slack_channel_id
   - OPENAI_API_KEY=your_openai_api_key
   - （DB パスは省略可。デフォルトは data/kabusys.duckdb など）

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=REPLACE_ME
   OPENAI_API_KEY=REPLACE_ME
   KABU_API_PASSWORD=REPLACE_ME
   SLACK_BOT_TOKEN=REPLACE_ME
   SLACK_CHANNEL_ID=REPLACE_ME
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL やスクリプトから主要機能を実行するサンプルです。

1. DuckDB 接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメントを算出して ai_scores に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written {n_written} scores")
```

3. 市場レジームを算出して market_regime に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4. 監査ログ用 DB を初期化する
```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

db_path = Path("data/audit.duckdb")
conn = init_audit_db(db_path)
# 以降 conn を使って監査テーブルにアクセス可能
```

5. 研究用ファクター計算（例：モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{'date':..., 'code':..., 'mom_1m':..., ...}, ...]
```

---

## よく使うエントリポイント（モジュール一覧）

- kabusys.config.Settings
  - 環境変数の取得・必須チェック・.env の自動ロード

- kabusys.data.jquants_client
  - get_id_token, fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar

- kabusys.data.pipeline
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - ETLResult dataclass

- kabusys.data.news_collector
  - fetch_rss（RSS 取得）、記事前処理、ID 生成ロジック

- kabusys.ai.news_nlp
  - score_news（銘柄別ニュースセンチメント解析）

- kabusys.ai.regime_detector
  - score_regime（市場レジーム判定）

- kabusys.data.quality
  - run_all_checks（欠損・重複・スパイク・日付不整合の検出）

- kabusys.data.audit
  - init_audit_schema / init_audit_db（監査テーブル初期化）

- kabusys.research
  - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

---

## ディレクトリ構成

（主なファイル / モジュールを抜粋）

- src/kabusys/
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
    - news_collector.py
    - calendar_management.py
    - stats.py
    - quality.py
    - audit.py
    - (その他：schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (監視系モジュール等、存在する場合)
  - strategy/ (戦略層の実装を置く場所、存在する場合)
  - execution/ (発注関連の統合、存在する場合)

※ 上記はリポジトリ内のモジュール構成に対応しています。詳細は各モジュールの docstring を参照してください。

---

## 注意点 / 設計方針（抜粋）

- ルックアヘッドバイアス対策
  - 各モジュールは内部で datetime.today() / date.today() を直接参照しない設計（target_date を明示的に渡す）。
  - ETL / スコアリング関数は target_date 引数を使用して過去データのみ参照します。

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）失敗時はフェイルセーフなデフォルト値で継続（例：macro_sentiment=0.0、空スコアはスキップ）する箇所がある一方で、DB 書き込み失敗は例外を伝播させるものがあります。

- 冪等性
  - DB への保存関数は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE 等で冪等性を考慮している箇所が多いです。

- セキュリティ
  - news_collector は SSRF 対策、XML インジェクション対策（defusedxml）、レスポンスサイズ制限などを行っています。

---

## 開発・テストについて

- 自動環境読み込みを無効化してユニットテストを行う場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して .env 自動ロードを抑制できます。

- OpenAI API / J-Quants API を使う箇所は外部呼び出しをモック化して単体テストすることを推奨します（モジュール内の _call_openai_api はテスト容易性のため差し替え可能に設計されています）。

---

この README はソースコード内の docstring / 設計コメントに基づいて作成しています。さらに詳しい使い方や運用手順（CI/CD、ジョブスケジューリング、監視・アラート、Slack 通知等）は運用ドキュメントを別途作成してください。