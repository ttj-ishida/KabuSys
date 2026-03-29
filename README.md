# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。J-Quants からのデータ取得、DuckDB ベースの ETL、ニュースの NLP スコアリング（OpenAI）、ファクター計算や監査ログ機能を提供します。

- パッケージ名: kabusys
- バージョン: 0.1.0

---

## 概要

KabuSys は以下を目的とした Python ライブラリです。

- J-Quants API から株価・財務・市場カレンダー等を安全に取得して DuckDB に蓄積する ETL パイプライン
- RSS によるニュース収集と前処理（SSRF・サイズ制限・正規化対応）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析・市場レジーム判定
- ファクター計算（モメンタム／バリュー／ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 取引フローを追跡する監査（audit）テーブルの初期化・管理

設計上の特徴：
- DuckDB を使ったオンディスク/インメモリ高速処理
- API 呼び出しはリトライ・レート制御・フェイルセーフ実装
- Look-ahead バイアス防止のため関数は内部で現在日を直接参照しない設計
- .env ファイル／環境変数経由の設定管理（自動ロード機能あり）

---

## 機能一覧（主なモジュール）

- kabusys.config
  - 環境変数読み込み（.env / .env.local）と設定オブジェクト `settings`
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得・保存関数、認証・レート制御）
  - pipeline: 日次 ETL（run_daily_etl, run_prices_etl 等）と ETLResult
  - news_collector: RSS 取得・前処理（SSRF・サイズ制限等）
  - quality: データ品質チェック（missing/spike/duplicates/date_consistency）
  - calendar_management: 市場カレンダーの判定/更新ヘルパー
  - audit: 監査ログ用テーブル作成・初期化（init_audit_db 等）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- kabusys.ai
  - news_nlp.score_news: ニュースを LLM で評価し ai_scores に書き込む
  - regime_detector.score_regime: マクロニュース + ETF MA で市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, rank, factor_summary

---

## セットアップ手順

前提
- Python 3.10 以上（型注釈の | 演算子と未来注釈対応のため）
- DuckDB を使用するため環境でのインストールが必要

1. 仮想環境作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml

   必要に応じて logger やテスト用ライブラリも追加してください。

3. 環境変数 / .env
   プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（kabusys.config が自動的に読み込み）。
   自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

   推奨する .env の最小例:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. データディレクトリ
   - settings.duckdb_path の親ディレクトリが存在しない場合は、init 関数で自動作成されるモジュールもありますが明示的に作成しておくと安心です。
   - 例: mkdir -p data

---

## 使い方（主要な利用例）

以下は Python REPL やスクリプトから使う基本例です。

1) 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=None)  # target_date=None -> 今日（ただし関数内での調整あり）
print(result.to_dict())
```

3) ニューススコアリング（LLM を用いる）
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で指定
print(f"書き込み銘柄数: {n_written}")
```

4) 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数か引数で指定
```

5) 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")  # :memory: も可
```

6) ファクター計算 / 研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
momentum = calc_momentum(conn, date(2026, 3, 20))
# 結果は dict のリスト（date, code, mom_1m, mom_3m, mom_6m, ma200_dev）
```

注意点
- OpenAI 呼び出しは `OPENAI_API_KEY` を環境変数に設定するか、関数引数に明示的に渡してください。
- J-Quants API は `JQUANTS_REFRESH_TOKEN` が必須です（settings.jquants_refresh_token が参照されます）。
- ETL の一部関数はトランザクションを行うため、DuckDB 接続の取り扱いに注意してください。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM を使う機能で必須）
- KABU_API_PASSWORD: kabu ステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知連携用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視） DB パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: environment の指定（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化するには 1 を設定

config モジュールはプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動読み込みします。

---

## 注意・設計メモ（実運用上のポイント）

- Look-ahead バイアス対策: ニュースやレジーム判定等、多くの処理が target_date より前のデータのみを参照する設計です。内部で date.today() を直接参照せず、明示的な target_date 引数を受け取る関数が多いです。
- API のレート制御・リトライ: J-Quants クライアントは 120 req/min を守るための RateLimiter と指数バックオフを備えています。OpenAI 呼び出しも retries を実装しています。
- ニュース収集: RSS の取得は SSRF 対策、受信サイズ制限、URL 正規化、トラッキングパラメータ削除など安全策を講じています。
- データ品質: quality.run_all_checks を用いて ETL 後に品質レポートを取得できます（エラー/ワーニングの検出）。
- 監査ログ: order_requests / executions 等の監査スキーマを DuckDB 上に初期化するユーティリティを提供しています。監査は削除を前提としない方針です。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
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
  - audit.py
  - etl.py (alias exports)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py

（上記はコードベースに含まれる主要モジュールの抜粋です。実際のリポジトリにはさらに補助ファイルやテストが含まれるかもしれません。）

---

## 開発・テスト時のヒント

- 自動 .env ロードを無効にしてテストを隔離する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部ネットワーク呼び出しはユニットテストでモック可能な設計になっています（モジュール内の _call_openai_api などをパッチ）。
- DuckDB はインメモリモード ":memory:" を使えばテストを高速化できます（init_audit_db(":memory:") 等）。

---

## ライセンス・貢献

ソースコード上にライセンスファイルが含まれているかご確認ください。貢献・バグ報告はリポジトリの Issue / PR を通じて行ってください。

---

この README はコードベースの主要機能と使い方の概要を簡潔にまとめたものです。さらに詳しい API 仕様や設計ドキュメント（DataPlatform.md / StrategyModel.md に対応する箇所）はソース内の docstring を参照してください。