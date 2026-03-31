# KabuSys

日本株向けのデータプラットフォームと自動売買補助ライブラリ群です。  
ETL（J-Quants）による市場データ取得、ニュースの収集・NLPによる銘柄スコアリング、研究用ファクター計算、監査ログ（発注／約定追跡）などのユーティリティを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を持つ Python パッケージです。

- J-Quants API から株価・財務・カレンダーを差分取得して DuckDB に保存する ETL パイプライン
- RSS からのニュース収集と前処理（SSRF 対策・トラッキング削除）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score、マクロセンチメント）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロセンチメントの合成）
- 研究用ファクター計算（モメンタム、バリュー、ボラティリティ等）および特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）テーブルと初期化ユーティリティ

設計上の特徴:
- ルックアヘッドバイアスに配慮（内部では date.today() や datetime.today() を不用意に参照しない）
- DuckDB をメインの永続層として想定
- 冪等性（ETL -> ON CONFLICT / INSERT … DO UPDATE、監査ログは削除しない前提）
- 外部 API 呼び出しにはレート制御・リトライ・フェイルセーフの実装

---

## 機能一覧

主なモジュールと機能（抜粋）

- kabusys.config
  - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）
  - 設定プロパティ（JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY / KABU_API_* / SLACK_* / DB パス 等）

- kabusys.data
  - jquants_client: J-Quants API クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット、リトライ）
  - pipeline: 日次 ETL（run_daily_etl）、個別 ETL（run_prices_etl, run_financials_etl, run_calendar_etl）
  - news_collector: RSS 取得・前処理・raw_news 保存ロジック（SSRF対策、gzip/サイズ制限）
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - audit: 監査ログスキーマ初期化・DB 作成ユーティリティ（init_audit_schema, init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ

- kabusys.ai
  - news_nlp.score_news(conn, target_date, api_key=None): ニュースを銘柄別にスコアリングして ai_scores に保存
  - regime_detector.score_regime(conn, target_date, api_key=None): 市場レジーム判定（1321 MA200 とマクロセンチメントの合成）

- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
  - data.stats の zscore_normalize を再利用可能

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union 型などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS の取得）

1. リポジトリをクローン
   ```
   git clone <this-repo>
   cd <this-repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール  
   （プロジェクトに requirements.txt がない場合は主要依存を手動インストール）
   ```
   pip install duckdb openai defusedxml
   ```
   追加で必要になる可能性のあるパッケージ: requests（任意）、slack_sdk（Slack 通知を実装する場合）など。

4. 環境変数設定  
   プロジェクトルートに `.env` または `.env.local` を作成すると自動で読み込まれます（ただし、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば自動読み込みを無効化できます）。
   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxx...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリの作成（必要な場合）
   ```
   mkdir -p data
   ```

---

## 使い方（サンプル）

以下は Python インタプリタやスクリプトから各種ユーティリティを使う最小例です。

- DuckDB 接続の作成（設定のパスを使う）
```python
from kabusys.config import settings
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査ログ DB 初期化（専用 DB を作る場合）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit は監査テーブルが初期化済みの接続
```

- 日次 ETL の実行
```python
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn)  # target_date を指定することも可能
print(result.to_dict())
```

- ニュースのスコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY を利用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, date(2026, 3, 20))  # 前日15:00～当日08:30 JST の記事を処理して ai_scores に書き込む
print("scored:", n_written)
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, date(2026, 3, 20))
```

- 研究用ファクター計算例
```python
from datetime import date
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

- データ品質チェックの実行
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 連携関数は api_key 引数で上書き可能。未指定時は環境変数 OPENAI_API_KEY を参照します。
- ETL / AI 関数はルックアヘッドを防ぐ設計（target_date 未満 or 前日時間ウィンドウ等）になっています。バックテスト等で使用する場合は、データの事前ロード・時点管理に注意してください。

---

## 環境変数（主要）

必須（本番で使用する場合）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリング）
- SLACK_BOT_TOKEN: Slack 通知を行う場合
- SLACK_CHANNEL_ID: Slack 通知チャンネル

認証・サービス設定:
- KABU_API_PASSWORD: kabu ステーション API パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

データベースパス:
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）

実行環境:
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

自動 .env 読み込み:
- デフォルトでプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` を読み込み、続けて `.env.local` を上書き読み込みします。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（抜粋 — 実際のリポジトリに合わせて調整してください）

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
      - news_collector.py
      - quality.py
      - calendar_management.py
      - stats.py
      - audit.py
      - pipeline.py
      - etl.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - monitoring/  (モニタリング関連、SQLite 接続等を想定)
    - execution/   (発注・約定ラッパー等を想定)
    - strategy/    (戦略ロジックの実装用パッケージ)

---

## 開発・テストのヒント

- テスト時は環境変数の自動読み込みを無効にする:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- AI 呼び出し箇所（_call_openai_api）やネットワークリクエストは unittest.mock.patch で差し替えてテスト可能に設計されています（news_nlp._call_openai_api や regime_detector._call_openai_api をモックする）。
- DuckDB はインメモリ接続（":memory:"）でテスト可能。audit.init_audit_db(":memory:") も利用可能。

---

## 注意事項 / セキュリティ

- RSS のフェッチやリダイレクト処理では SSRF 対策（リダイレクト先の検証・プライベート IP 拒否）を実装していますが、運用時はさらに適切なネットワーク制御を行ってください。
- API キーやパスワード等は .env に平文で置かれることが多いので、アクセス管理・CI シークレット管理には注意してください。
- 実際の発注実装（execution / broker 連携）はここに含まれないか限定的です。本番での自動発注を行う際は入念なリスク管理とステージング検証を行ってください。

---

もし README に追加したい具体的な使い方（例: ETL の cron 設定例、Slack 通知例、発注フローのサンプルコードなど）があれば教えてください。必要に応じて追記します。