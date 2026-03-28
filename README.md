# KabuSys

日本株向けの自動売買プラットフォーム用ライブラリ（ライブラリ群）。  
データ取得・ETL、ニュース収集・NLP、リサーチ（ファクター計算）、監査ログ、マーケットカレンダー、J-Quants / kabuステーション クライアント等を含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要な以下の機能を提供する Python モジュール群です。

- J-Quants API を用いた株価・財務・上場情報・マーケットカレンダーの差分取得・永続化（DuckDB）
- ETL（run_daily_etl）により日次データ更新と品質チェックを実行
- RSS ベースのニュース収集（SSRF 対策・トラッキング除去・前処理）
- OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score）と市場レジーム判定
- 研究用ユーティリティ（モメンタム、ボラティリティ、バリュー、将来リターン、IC、Zスコア正規化等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログテーブル群（signal_events, order_requests, executions）の初期化・管理
- 環境設定管理（.env 自動ロード、必須環境変数のチェック）

設計上の留意点：
- ルックアヘッドバイアス回避（外部参照日時を内部で勝手に参照しない）
- API 呼び出しにはリトライ・指数バックオフ等の堅牢性を実装
- DuckDB をデータ格納に利用し、ON CONFLICT DO UPDATE で冪等性を担保

---

## 主な機能一覧

- data
  - jquants_client: J-Quants からの取得・DuckDB 保存（raw_prices, raw_financials, market_calendar など）
  - pipeline: 日次 ETL の実行（run_daily_etl）および個別 ETL ジョブ
  - calendar_management: 営業日判定 / next/prev_trading_day / calendar_update_job
  - news_collector: RSS 収集と raw_news への保存（SSRF 保護・gzip 制限など）
  - quality: データ品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - audit: 監査テーブルの DDL / 初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等の汎用統計ユーティリティ
- ai
  - news_nlp.score_news: 指定日のニュースを LLM で評価し ai_scores に保存
  - regime_detector.score_regime: ETF（1321）の MA とマクロニュースを組み合わせて市場レジーム判定
- research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank
- 設定管理
  - config.settings: .env 自動ロード（.env → .env.local）と必須環境変数のラッパー

---

## 動作要件（想定）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API, RSS フィード, OpenAI API 等）

（実際の package/dependency 管理はリポジトリの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - 例: git clone <repo>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存ライブラリのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - あるいはプロジェクトが requirements.txt / pyproject.toml を持つ場合:
     - pip install -r requirements.txt
     - または pip install -e .

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` および必要に応じて `.env.local` を置くと、自動で読み込まれます（config モジュール）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。

   推奨される .env のキー（必要に応じて設定）:

   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi  （デフォルト）
   - SLACK_BOT_TOKEN=...
   - SLACK_CHANNEL_ID=...
   - OPENAI_API_KEY=...
   - DUCKDB_PATH=data/kabusys.duckdb  （デフォルト）
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development|paper_trading|live
   - LOG_LEVEL=INFO|DEBUG|WARNING|ERROR|CRITICAL

   例（.env）:
   ```
   JQUANTS_REFRESH_TOKEN=ya29.xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

5. ディレクトリの準備
   - DuckDB や sqlite の格納先ディレクトリを作成：
     - mkdir -p data

---

## 使い方（主要な呼び出し例）

以下は Python REPL や小さなスクリプトからの利用例です。

- DuckDB 接続を開いて日次 ETL を実行する
```
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))  # target_date を指定
print(result.to_dict())
```

- ニュース NLP スコアを生成（ai_scores に書き込む）
```
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key 省略時は OPENAI_API_KEY を使用
print("wrote", n_written)
```

- 市場レジームを判定して market_regime テーブルへ書き込む
```
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する
```
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を用いて audit テーブルにアクセス可能
```

- 研究用ファクター計算例
```
import duckdb
from datetime import date
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

- データ品質チェックを実行
```
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意：
- OpenAI API を使用する機能（news_nlp, regime_detector）は OPENAI_API_KEY（または関数引数で api_key）を必要とします。
- J-Quants API を利用する ETL は JQUANTS_REFRESH_TOKEN が必要です（get_id_token 経由で ID トークンを取得します）。

---

## 設定管理の挙動（.env 自動ロード）

- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` → `.env.local` の順で自動読み込みを行います。
- 読み込み優先度: OS 環境変数 > .env.local (> .env)
- 自動ロード無効化: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`
- 必須値が unset の場合、Settings のプロパティは ValueError を送出します（例: settings.jquants_refresh_token）

---

## ディレクトリ構成（抜粋）

リポジトリはおおよそ以下の構成を想定します（src 配下）:

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
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
    - etl.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (※コードベースに監視用モジュールは想定されるが省略)
  - execution/ (発注・ブローカー連携モジュールは別途実装想定)
  - strategy/ (戦略定義用プレースホルダ)

（上記は提供されたコードファイルの主要なファイルを列挙しています）

---

## 注意事項 / 運用上のヒント

- Look-ahead バイアス対策のため、関数は内部で現在日時を盲目的に参照しない設計です。バックテスト実行時は target_date を明示してください。
- DuckDB に対する executemany の仕様（バージョン依存）に注意。pipeline 内では空パラメータの executemany を避ける処理があります。
- ニュース収集は RSS の規模や圧縮に依存するため、MAX_RESPONSE_BYTES 等の設定に注意してください。
- OpenAI 呼び出しはリトライ・バックオフを実装していますが、API 使用料・レート制限を考慮して運用してください。
- 本リポジトリの一部機能は外部 API（J-Quants、OpenAI、RSS提供元）に依存するため、ローカルでのユニットテストでは該当呼び出しをモックしてください（コード中にもモックしやすい設計の記述があります）。

---

## 貢献・拡張

- 新しい研究関数や戦略は `kabusys.research` / `kabusys.strategy` に追加してください。
- ブローカー接続（execution 層）や監視（monitoring）統合を行う場合は、audit テーブル群や order_request の冪等キー設計を尊重してください。

---

必要であれば、README にサンプル .env.example や requirements.txt、具体的なスクリプト（ETL cron ジョブ、Slack 通知連携など）のテンプレートを追加します。どの項目を優先して追記しましょうか？