# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP スコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、クオンツ運用に必要な共通処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株アルゴリズム運用に必要な共通機能をモジュール化して提供するライブラリです。主な目的は以下です。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL
- RSS ベースのニュース収集と OpenAI を用いた記事センチメント（銘柄別）スコアリング
- マクロニュース + ETF（1321）の 200 日 MA 乖離を用いた市場レジーム判定（LLM 統合）
- ファクター算出（モメンタム / バリュー / ボラティリティ 等）と特徴量分析ユーティリティ
- データ品質チェック、マーケットカレンダー管理、監査ログ（シグナル→発注→約定のトレース）
- DuckDB を主な永続化層として利用（監査用 DB もサポート）

設計上の特徴：
- ルックアヘッドバイアスを避ける設計（内部で datetime.today() を直接参照しないなど）
- 冪等性（DB 保存は ON CONFLICT / INSERT … DO UPDATE 等）を重視
- API 呼び出しにはリトライ・バックオフ・レートリミットを備える
- セキュリティ対策（RSS の SSRFガード、XML ディフェンス等）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl、個別 ETL ジョブ）
  - J-Quants クライアント（fetch / save / id_token 管理 / rate limiter）
  - カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得・前処理・raw_news 保存）
  - 品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマの初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore 正規化）
- ai/
  - news_nlp.score_news(conn, target_date): 銘柄別ニュースセンチメントを ai_scores に書き込む
  - regime_detector.score_regime(conn, target_date): 市場レジーム（bull/neutral/bear）を算出して market_regime に書き込む（ETF 1321 とマクロニュースの組合せ）
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数・.env 自動読み込み（プロジェクトルートを探索）
  - settings オブジェクト経由で設定を参照（例: settings.jquants_refresh_token）

---

## 必要環境・依存

（プロジェクトの requirements.txt があることを想定します。ここは実際の要件に合わせて調整してください）

必須（想定）
- Python 3.9+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

例:
pip install duckdb openai defusedxml

---

## 環境変数（主なもの）

config.Settings で参照される主要な環境変数（必須は README 上で明記）:

必須
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD: kabu ステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN: Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID: Slack 通知対象チャンネル ID
- OPENAI_API_KEY: OpenAI を使う機能を実行する場合（score_news / score_regime）

任意（デフォルトあり）
- KABUSYS_ENV: development / paper_trading / live（default: development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（default: INFO）
- KABU_API_BASE_URL: kabu API のベース URL（default: http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）

自動 .env 読み込みについて:
- プロジェクトルート（.git または pyproject.toml を探索）から .env / .env.local を自動で読み込みます。
- 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（開発用・最小手順）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   または最小例:
   - pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルートに .env を作成し、上記の必須変数を記載してください。
   例 (.env):
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     KABUSYS_ENV=development

   - 自動でロードされます（.env.local が優先して上書き）

5. DuckDB 初期化（監査ログ用など）
   - 監査スキーマを含めた DB を初期化する例は下記「使い方」を参照

---

## 使い方（簡単なコード例）

以下はライブラリを用いて ETL 実行や AI スコアを実行する最小例です。実行前に環境変数を設定してください。

- DuckDB 接続を作る（既存の db ファイルを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 監査 DB の初期化（ファイルがなければ作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db(settings.duckdb_path)  # ":memory:" も可
```

- 日次 ETL 実行
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュース NLP スコアリング（OpenAI API キーを環境変数に設定しておく）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込んだ銘柄数: {written}")
```

- 市場レジーム判定（1321 の MA200 とマクロニュースを組合せ）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算（例: モメンタム）
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト。例: {"date": ..., "code": "7203", "mom_1m": 0.05, ...}
```

注意点:
- score_news / score_regime は OpenAI API を呼び出します。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- ETL は J-Quants API を呼び出します。JQUANTS_REFRESH_TOKEN が必要です。

---

## 主要 API（抜粋）

- kabusys.config.settings — 環境設定
- kabusys.data.pipeline.run_daily_etl — 日次 ETL（市場カレンダー・株価・財務・品質チェック）
- kabusys.data.jquants_client — fetch / save / get_id_token 等（J-Quants 連携）
- kabusys.data.news_collector.fetch_rss — RSS の取得と前処理
- kabusys.data.quality.run_all_checks — データ品質チェック
- kabusys.data.calendar_management.is_trading_day / next_trading_day / prev_trading_day / get_trading_days
- kabusys.ai.news_nlp.score_news — 銘柄別ニュースセンチメント算出 & ai_scores 書込
- kabusys.ai.regime_detector.score_regime — 日次市場レジーム判定 & market_regime 書込
- kabusys.research.* — ファクター計算・解析ユーティリティ
- kabusys.data.audit.init_audit_schema / init_audit_db — 監査ログスキーマ生成

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル / ディレクトリ構成（省略あり）

```
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
      quality.py
      stats.py
      calendar_management.py
      news_collector.py
      audit.py
      etl.py
      # ... (その他: schema / helpers)
    research/
      __init__.py
      factor_research.py
      feature_exploration.py
      # ...
    research/
    ai/
    monitoring/    # (READMEが示す他のサブモジュールがある想定)
    strategy/      # (戦略関連モジュールは別途)
    execution/
```

主要テーブル（コード中で扱うテーブル例）
- raw_prices / prices_daily
- raw_financials
- market_calendar
- raw_news / news_symbols / ai_scores
- market_regime
- signal_events / order_requests / executions（監査ログ関連）

---

## 運用上の注意・ベストプラクティス

- OpenAI API 呼び出しはコストとレイテンシが発生します。バッチサイズや呼び出し頻度を運用要件に合わせて調整してください。
- ETL は差分更新とバックフィルを行います。バックテスト等で再現性が必要な場合、データ取得開始日や fetched_at の扱いに注意してください（Look-ahead bias を避ける設計が組み込まれていますが運用側でも取得タイミングを管理してください）。
- .env ファイルには機密情報（API トークン等）が含まれるため、リポジトリにコミットしないでください（.gitignore を推奨）。
- DuckDB ファイルは大きくなる可能性があります。バックアップとストレージ管理を行ってください。
- news_collector は外部 URL を取得するため SSRF 等のリスク対策（コード内で実装済）がありますが、運用ネットワークポリシーも併せて検討してください。

---

## ライセンス / 貢献

（ここにライセンス情報・コントリビューションルールを記載してください。リポジトリの実情に合わせて追記してください。）

---

README に書かれている通りの利用方法で始められますが、実運用や資金を扱う処理を行う場合は充分なテスト・監査・リスク管理を行ってください。必要であれば、利用したい具体的な機能（ETL 実行スクリプト、CI ジョブ、Slack 通知等）に合わせた README の追記やサンプルスクリプトを作成します。必要であれば教えてください。