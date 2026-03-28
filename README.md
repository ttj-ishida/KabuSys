# KabuSys

日本株向けのデータプラットフォーム & 自動売買補助ライブラリです。  
DuckDB を用いたデータETL、ニュースのNLPスコアリング（OpenAI）、市場レジーム判定、ファクター計算、監査ログ（トレーサビリティ）などを含みます。

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- J-Quants API から株価・財務・カレンダー等を差分取得し DuckDB に保存する ETL パイプライン
- RSS ニュースの収集・前処理と OpenAI による銘柄別ニュースセンチメント算出（ai_scores）
- マクロニュースと ETF（1321）の MA200 乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- 研究用に各種ファクター（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 発注〜約定の監査ログ（監査テーブル・初期化ユーティリティ）

設計上のポイント:
- ルックアヘッドバイアスを避ける（内部で date.today() などを不用意に参照しない）
- 外部API呼び出しはリトライ/バックオフ・レートリミット制御あり
- DuckDB を主な永続層とし、冪等保存（ON CONFLICT）を行う

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（fetch / save 関数）
  - calendar 管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - news_collector: RSS 取得・正規化・保存（SSRF 対策 / gzip / トラッキング除去）
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 発注〜約定の監査スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore 正規化ユーティリティ
- ai
  - news_nlp.score_news: ニュースの銘柄別センチメント算出・ai_scores 書き込み
  - regime_detector.score_regime: マクロ + MA200 を合成した市場レジーム判定
- research
  - factor_research: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config: .env 自動読み込み、環境設定ラッパー（settings）

---

## 必要条件（依存関係）

主な Python パッケージ（抜粋）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（標準ライブラリを多数使用します。環境に応じて requirements.txt を作成してください。）

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン・配置（例: ソースは `src/kabusys` に配置されています）。

2. 仮想環境の作成（任意推奨）:
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール:
   pip install duckdb openai defusedxml

4. 環境変数（.env）を用意する。プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動で読み込まれます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

例: `.env`（最低限必要なキー）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_slack_channel_id
# 任意:
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development  # development | paper_trading | live
LOG_LEVEL=INFO
```

5. データディレクトリ作成（デフォルト DB パスに合わせる）:
   mkdir -p data

---

## 使い方（簡単なコード例）

以下は Python REPL やスクリプトから呼び出す想定の例です。

- DuckDB 接続の作成と日次 ETL の実行
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI APIキーが環境変数にある前提）
```
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定
```
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DBの初期化
```
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でも可
# conn を用いて以降の監査テーブル操作を行う
```

- カレンダー判定ユーティリティ
```
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- OpenAI 呼び出し、J-Quants API 呼び出しはそれぞれ API キーやトークンが必要です。キー未設定時は ValueError が発生します。
- ETL / API 呼び出しはネットワーク・API制限を伴うため、本番・テスト環境では適切に設定してください。
- .env 読み込みはパッケージ import 時に自動で行われます（ルート検出: .git か pyproject.toml が基準）。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須 for J-Quants client）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite モニタリング DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動的に .env をロードしない

---

## よくあるトラブルシューティング

- ValueError: "OpenAI API キーが未設定です"  
  → OPENAI_API_KEY を環境変数または関数引数で渡してください。

- J-Quants の 401 エラーやトークン関係  
  → JQUANTS_REFRESH_TOKEN が正しいか確認。モジュールは 401 時に自動リフレッシュを試みます。

- DuckDB のテーブルが存在しない / クエリエラー  
  → 初期スキーマ作成処理（別途 schema 初期化関数がある想定）または既存DBを確認してください。audit.init_audit_schema / init_audit_db は監査テーブル初期化に使用できます。

---

## ディレクトリ構成（抜粋）

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
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py (ETL のエントリ等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*.py
  - その他（strategy / execution / monitoring 等のプレースホルダが __all__ に宣言されていますが、ここでは主に data/ai/research を提供）

※ 実際のリポジトリではさらにモジュール（strategy, execution, monitoring など）が存在する可能性があります。

---

## 開発・テスト

- 自動 .env ロードは config モジュールが import された際に行われます。テスト中に .env 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants の外部通信部分は個別関数（_call_openai_api や _urlopen）をモックしやすく設計されています。ユニットテストではモックを活用してください。

---

この README はコードベースから主要な機能と使い方を抜粋してまとめたものです。追加で README に欲しい情報（例えば具体的な CLI、ユースケース別の詳細なスクリプト例、パッケージ化手順など）があれば指示してください。