# KabuSys

日本株のデータプラットフォームと自動売買支援ライブラリ群。  
ETL（J-Quants連携）・ニュース収集・LLMによるニュースセンチメント評価・市場レジーム判定・ファクター計算・データ品質チェック・監査ログなど、自動売買システム構築に必要な共通機能を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の機能群を持つ Python パッケージです。

- J-Quants API 経由での株価・財務・マーケットカレンダーの差分取得（ETL）
- DuckDB を用いたデータ保存と冪等な保存ロジック
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去等）
- OpenAI（gpt-4o-mini）を使ったニュースのセンチメント解析（ai モジュール）
- ETF とマクロニュースを組み合わせた市場レジーム判定（regime_detector）
- ファクター計算・特徴量探索（research モジュール）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）初期化ユーティリティ
- 環境変数・設定管理（自動 .env 読み込み機構付き）

設計方針の特徴:
- ルックアヘッドバイアスを避ける設計（date.today() や現在時刻の暗黙参照を避ける）
- 冪等性を重視（DB への保存は ON CONFLICT で上書き）
- API 呼び出しはリトライ・バックオフ・レート制御を備える
- テストしやすいように外部呼び出しに差し替え可能な実装（モックしやすい）

---

## 主な機能一覧

- config
  - 環境変数読み込み（.env / .env.local 自動読み込み）
  - settings オブジェクトで設定値を取得

- data
  - jquants_client: J-Quants API クライアント（取得・保存関数）
  - pipeline / etl: run_daily_etl、run_prices_etl、run_financials_etl、run_calendar_etl など
  - calendar_management: 営業日判定・next/prev_trading_day・calendar_update_job
  - news_collector: RSS 取得・前処理・raw_news 保存支援
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit: 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の統計ユーティリティ

- ai
  - news_nlp.score_news: ニュースをまとめて LLM に送り銘柄ごとの ai_score を ai_scores テーブルへ保存
  - regime_detector.score_regime: ETF MA とマクロニュースセンチメントを合成して market_regime を作成

- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank

---

## セットアップ手順（開発環境向け）

前提
- Python 3.10+ を推奨（型ヒントに | を使用）
- DuckDB を利用するため実行環境に十分なディスクと Python 環境が必要

1. リポジトリをクローン／チェックアウト
   - (例) git clone ...

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 必須（代表例）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数の準備
   - プロジェクトルートに .env または .env.local を置くと、自動的に読み込まれます（優先度: OS 環境 > .env.local > .env）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

必須の主な環境変数:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（使用する場合）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知を使う場合

データベース・パス設定（任意、デフォルトあり）:
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABUSYS_ENV, LOG_LEVEL なども設定可能

例 .env（最小）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
LOG_LEVEL=INFO
```

---

## 使い方（代表的な利用例）

以下は簡単なコード例です。実行は仮想環境内で行ってください。

- DuckDB 接続を開いて日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントをスコアリングして ai_scores テーブルへ書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {n} codes")
```

- 市場レジーム判定を実行する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等の操作や照会が可能
```

- 営業日判定・カレンダー関連ユーティリティ
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
- OpenAI／J-Quants を呼ぶ関数は api_key や id_token の指定が可能です。未指定時は環境変数を参照します。
- 外部 API 呼び出しはリトライ・フェイルセーフする実装ですが、API キーやネットワークの設定を正しく行ってください。

---

## ディレクトリ構成

リポジトリ内の主要ファイル構成（src/kabusys 以下）:

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
    - etl.py (ETLResult 再エクスポート)
    - calendar_management.py
    - stats.py
    - quality.py
    - news_collector.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/__init__.py
  - その他（strategy / execution / monitoring 等は __all__ で公開候補）

ツリー（抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ calendar_management.py
│  ├─ news_collector.py
│  ├─ quality.py
│  ├─ stats.py
│  └─ audit.py
└─ research/
   ├─ __init__.py
   ├─ factor_research.py
   └─ feature_exploration.py
```

---

## 注意事項 / 運用上のヒント

- .env 自動読み込み
  - パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を基に .env を自動ロードします。
  - OS 環境変数が優先され、.env.local は .env を上書きします。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB スキーマ
  - jquants_client.save_* や audit.init_audit_schema 等は対象テーブルが存在することを前提とします。初期スキーマは別途提供される schema 初期化処理に従ってください（audit については init_audit_schema / init_audit_db を利用可）。

- API 使用上の制約
  - J-Quants: rate limit（120 req/min）に合わせた内部レート制御がありますが、運用側でも過剰な同時実行を避けてください。
  - OpenAI: レスポンスの JSON 形式を前提にしているため、モデルやレスポンス仕様の変更があるとパースエラーが発生する可能性があります。

- テスト容易性
  - 多くの外部呼び出しは内部関数をモックできるように設計されています（例: kabusys.ai.news_nlp._call_openai_api をパッチする等）。

---

## 貢献 / 開発フロー

- バグ修正・機能追加は PR を送ってください。テストケース（ユニットや統合）を添えると助かります。
- 外部 API キーやシークレットはリポジトリに含めないでください。.env.example を用意して運用してください。

---

この README はコードベースのコメント・ドキュメントからまとめた概要です。詳細な API 仕様やスキーマ定義は各モジュールの docstring を参照してください。必要であれば README に載せる具体的なスニペットや CI / デプロイ手順も追加できます。