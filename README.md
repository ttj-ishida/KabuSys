# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → ニュースNLP / 市場レジーム判定 → 監査ログ（発注/約定追跡）までをカバーするユーティリティ群を提供します。

主に DuckDB をデータレイヤに用い、OpenAI（gpt-4o-mini）をニュース分析に利用する設計です。

## 主な機能
- J-Quants からの差分 ETL（株価日足 / 財務 / 市場カレンダー）と保存（冪等）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と前処理・冪等保存（raw_news / news_symbols）
- ニュースの LLM による銘柄別センチメントスコアリング（ai_scores）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントの合成）
- ファクター計算（モメンタム / バリュー / ボラティリティ等）
- 研究ユーティリティ（将来リターン計算・IC・統計サマリ・Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions）の初期化・管理
- 環境変数ベースの設定管理（.env 自動読み込み）

---

## セットアップ手順

前提：Python 3.9+（typing の一部機能を使用）。プロジェクトは src レイアウトを想定しています。

1. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. インストール（開発）
   - pip install -e .

   もしくは最低限の依存を直接インストール：
   - pip install duckdb openai defusedxml

   必要に応じてロギング設定やその他パッケージを追加してください。

3. 環境変数 / .env
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   必須の環境変数（最低限）:
   - JQUANTS_REFRESH_TOKEN  ← J-Quants の refresh token（get_id_token に使用）
   - KABU_API_PASSWORD      ← kabuステーション API のパスワード（発注時）
   - SLACK_BOT_TOKEN        ← 通知用 Slack Bot Token
   - SLACK_CHANNEL_ID       ← 通知用 Slack チャネル ID
   - OPENAI_API_KEY         ← OpenAI 呼び出しに使用（news_nlp / regime_detector）

   （任意）
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 でパッケージ起動時の .env 自動ロードをオフ
   - KABUSYS_ENV (development | paper_trading | live)
   - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token_here
   OPENAI_API_KEY=sk-xxxx...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   KABU_API_PASSWORD=your_password
   ```

---

## 使い方（抜粋のサンプル）

以下はライブラリの代表的な呼び出し例です。実運用ではロギング設定や例外ハンドリングを適切に追加してください。

- DuckDB に接続して日次 ETL を実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコア生成（OpenAI API キーが必要）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written {n_written} scores")
```

- 市場レジーム判定
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログデータベースの初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
# テーブルが作成され、UTC タイムゾーンがセットされます
```

- ファクター計算（例: momentum）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dicts with keys ["date","code","mom_1m","mom_3m","mom_6m","ma200_dev"]
```

注意点:
- LLM を呼ぶ関数（score_news, score_regime）は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
- LLM 呼び出しは失敗時にフォールバック・スキップする設計（フェイルセーフ）です。ログを必ず確認してください。
- ETL / calendar_update_job 等はデータベースのスキーマが想定通り作成されていることを前提とします（スキーマ初期化処理は別途用意する想定）。

---

## 設計の重要なポイント / 注記

- Look-ahead bias 防止:
  - date.today() / datetime.today() を内部ループで直接参照しない方針。
  - ETL / スコアリング関数は target_date を明示的に受け取り、過去データのみを参照する実装です。
- 冪等性:
  - 保存処理（save_*）は ON CONFLICT（UPSERT）で冪等に書き込みます。
- API 呼び出しの耐障害性:
  - J-Quants クライアントはレートリミット保護とリトライ（指数バックオフ）を組み込んでいます。OpenAI 呼び出し側もリトライとフェイルセーフを持ちます。
- セキュリティ:
  - news_collector は SSRF 対策、XML パースの安全ライブラリ（defusedxml）、レスポンスサイズ制限などを実装しています。

---

## ディレクトリ構成（主要ファイル）
（src/kabusys 以下の主要モジュール）

- kabusys/
  - __init__.py
  - config.py                    ← 環境変数 / .env の自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                ← ニュースの LLM スコアリング（ai_scores へ書込）
    - regime_detector.py         ← 市場レジーム判定（1321 MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py          ← J-Quants API クライアント（fetch / save）
    - pipeline.py                ← ETL のメイン処理（run_daily_etl 等）
    - etl.py                     ← ETLResult の再エクスポート
    - quality.py                 ← データ品質チェック（複数チェック）
    - news_collector.py          ← RSS 収集・前処理
    - calendar_management.py     ← 市場カレンダー・営業日判定
    - stats.py                   ← 汎用統計（zscore_normalize）
    - audit.py                   ← 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py         ← ファクター計算（momentum/value/volatility）
    - feature_exploration.py     ← 将来リターン / IC / サマリ / rank
  - research/*.py (その他)

---

## 追加情報・運用ヒント
- ローカル開発時は OpenAI のコストに注意してモックやテストキーを使用してください。テストでは _call_openai_api をモックできるように設計されています。
- 自動 .env 読み込みを無効にしたいテストや CI では環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を用いるため、複数プロセスから同一ファイルに同時書き込みを行う場合は運用設計（排他）に注意してください。
- 各モジュールはログ出力を積極的に行うので、実行時に適切なログレベル（LOG_LEVEL）を設定して監視してください。

---

この README はコードベースから抽出した実装意図を元に作成しています。詳細な API 仕様や追加のユーティリティは、ソース内ドキュメント（docstring）を参照してください。必要であれば、README に含めるサンプルスクリプトやデータベーススキーマ初期化手順の追記を行います。どの部分を拡張したいか教えてください。