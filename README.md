# KabuSys

日本株向けデータプラットフォーム + 自動売買支援ライブラリです。  
ETL（J‑Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、ファクター計算、監査ログ（発注トレース）など一連の処理を提供します。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- 要件 / 依存関係
- セットアップ手順
- 環境変数（.env）例
- 使い方（簡易サンプル）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株のデータ収集・品質検査・特徴量作成・ニュースNLP・市場レジーム判定・監査ログ等を行うライブラリ群です。
- DuckDB を内部データストアとして使い、J‑Quants API / RSS / OpenAI（gpt-4o-mini 等）を組み合わせて運用・研究用途に必要なコンポーネントを揃えています。
- バックテスト用ルックアヘッドバイアス対策、ETL の冪等化、API リトライ・レート制御、SSRF対策など実運用を意識した実装方針になっています。

主な機能
- data:
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J‑Quants クライアント（fetch / save 関数、トークン自動リフレッシュ、レートリミット）
  - market_calendar 管理（営業日判定・next/prev_trading_day など）
  - ニュース収集（RSS 取得、前処理、raw_news 保存ロジック）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize 等）
- ai:
  - ニュースのセンチメントスコアリング（score_news）
  - 市場レジーム判定（score_regime: ETF 1321 MA200 とマクロニュースの LLM 評価を合成）
  - LLM 呼び出しは OpenAI クライアントを使用（JSON mode を利用）
- research:
  - ファクター計算（momentum / volatility / value）
  - 特徴量探索（forward returns, IC, summary 等）
- monitoring / execution / strategy（パッケージとして公開される想定。README のコードベースでは主要部分が data/research/ai に集中）

要件 / 依存関係
- Python 3.10 以上（| タイプ構文を使用）
- 主な Python パッケージ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリを多く使用（urllib, json, logging, datetime など）

セットアップ手順（開発環境向け）
1. リポジトリをチェックアウト
   - git clone <repo>
2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)
3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （パッケージ化されていれば）pip install -e .
4. 環境変数の設定（下記 .env 例を参照）
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを無効にできます。

環境変数（.env）例
- 以下は最低限想定されるキーの例です（プロジェクトの機能により不要なキーは省略可）。

例 .env:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi     # 必要に応じて
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development        # development | paper_trading | live
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...         # score_news / score_regime を使う場合に必要

注意:
- settings（kabusys.config.Settings）は .env ファイルと環境変数を組み合わせて自動読み込みします。プロジェクトルートは .git または pyproject.toml により探索されます。
- 自動読み込みを無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

使い方（主要な API サンプル）

1) DuckDB 接続の準備
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))

2) 日次 ETL 実行（市場カレンダー / 株価 / 財務 / 品質チェック）
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())

3) ニュースセンチメントのスコア生成
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 19))
print(f"scored {n_written} codes")

4) 市場レジーム判定
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 19))  # OpenAI キーは環境変数か引数で渡す

5) 監査ログ DB 初期化（監査専用 DB を作る場合）
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) が作成されます

6) RSS フィードの取得（ニュース収集テスト）
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])

実運用上の留意点
- OpenAI の呼び出し（score_news / score_regime）は外部 API を使うため料金・レートに注意してください。API エラー時はフェイルセーフでスコアを 0 にするなどの設計になっていますが、運用ポリシーを検討してください。
- J‑Quants API のレート制限（120 req/min）に合わせて内部でレート制御を行っています。大量取得時は ETL の実行間隔を考慮してください。
- DuckDB の executemany で空リストを渡すと問題になるバージョンがあるため、内部で空チェックが行われています。
- 監査ログは削除しない前提で設計されています（トレーサビリティ確保のため）。

ディレクトリ構成（概要）
- src/kabusys/
  - __init__.py
  - config.py                     : 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  : ニュースセンチメントスコアリング（score_news）
    - regime_detector.py           : 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - pipeline.py                  : ETL パイプライン（run_daily_etl 等）と ETLResult
    - jquants_client.py            : J‑Quants API クライアント + DuckDB 保存関数
    - news_collector.py            : RSS 収集・前処理・ID 生成・保存ロジック
    - calendar_management.py       : market_calendar 管理・営業日判定
    - quality.py                   : データ品質チェック（欠損/重複/スパイク/日付不整合）
    - stats.py                     : 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                     : 監査ログスキーマ定義・初期化
    - pipeline.py                  : ETL 実装（差分取得 / 保存 / 品質チェック）
    - etl.py                       : ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py           : momentum / value / volatility の計算
    - feature_exploration.py       : forward returns / calc_ic / rank / factor_summary
  - ai/ (前述)
  - research/ (前述)
  - （その他 strategy / execution / monitoring 等のパッケージが公開される想定）

開発時の補足
- テストしやすさを考慮して、OpenAI の呼び出し箇所やネットワーク呼び出しはモックが差し替えられる実装になっています（例: kabusys.ai.news_nlp._call_openai_api を unittest.mock.patch で差し替え）。

ライセンスや貢献方法等
- この README はコードベースの説明に焦点を当てています。ライセンスやコントリビューションポリシーはリポジトリのトップレベル（LICENSE / CONTRIBUTING.md 等）を参照してください。

--- 

何か特定の機能（例: ETL の cron 実行、OpenAI の最適プロンプト調整、DuckDB スキーマ定義の確認、CI 設定など）について詳細ドキュメントが必要であれば教えてください。追加の使用例や運用ガイド（本番移行チェックリスト等）も作成できます。