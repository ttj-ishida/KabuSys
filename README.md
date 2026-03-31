# KabuSys

日本株向けのデータプラットフォーム & 自動売買基盤のライブラリ群です。  
このリポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、市場レジーム判定、リサーチ（ファクター計算）、および監査ログ（発注 → 約定のトレーサビリティ）を提供します。

主な設計方針
- ルックアヘッドバイアスを防止する（date.today()/datetime.today() をバックテスト内で使わない等）
- DuckDB を中心としたシンプルな ETL / ストレージ設計
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント評価（フォールバックとリトライ制御あり）
- J-Quants API と堅牢な HTTP / 認証・レート制御ロジック
- 監査ログは監査性を重視し削除しない前提で設計

---

## 機能一覧

- 環境変数・設定管理（自動 .env ロード）
- J-Quants API クライアント
  - 株価日足（OHLCV）取得・保存
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - レート制限、トークン自動リフレッシュ、リトライ
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI）による銘柄センチメント付与（ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、統計サマリー）
- 監査ログスキーマ定義と初期化（signal_events / order_requests / executions）
- 監視・実行用の各機能（監査 DB 初期化、ETL 実行、AI スコア計算など）

---

## 必要条件 / 推奨

- Python 3.10+
- 依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API アクセス（リフレッシュトークン）
- OpenAI API キー（ニュース NLP / レジーム判定）
- kabuステーション API パスワード（実行/発注に必要な場合）
- Slack トークン（通知に使用する場合）

インストール例（仮）:
```bash
python -m pip install -e .         # ローカル開発インストール
python -m pip install duckdb openai defusedxml
```

（実際の pyproject / requirements に合わせて調整してください）

---

## 環境変数（主なもの）

プロジェクトルート配下の `.env` / `.env.local` が自動でロードされます（優先順位: OS 環境 > .env.local > .env）。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途等）。

必須（モジュールで _require を使っているため未設定時は例外になるもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN: Slack Bot トークン（通知を使う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（通知を使う場合）
- KABU_API_PASSWORD: kabuステーション API のパスワード（発注など）

任意・デフォルトあり
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / ...（デフォルト: INFO）
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 監視用 SQLite データベース（デフォルト `data/monitoring.db`）
- OPENAI_API_KEY: OpenAI を使う関数で参照される（score_news / score_regime を呼ぶ場合）

例（.env）
```env
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境を作成・有効化（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ```bash
   python -m pip install -e .
   python -m pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（`.env` / `.env.local` をプロジェクトルートに配置）
   - 参考: 上の「環境変数」セクション
   - 自動ロードの挙動: OS 環境 > .env.local > .env

5. DuckDB データベースのディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な関数・例）

以下は Python スクリプトや REPL から呼び出す例です。DuckDB 接続には `duckdb.connect(path)` を使用します。

1) 日次 ETL 実行（run_daily_etl）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントのスコア付与（score_news）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にあるか、api_key 引数で指定する
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} symbols")
```

3) 市場レジーム判定（score_regime）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
res = score_regime(conn, target_date=date(2026, 3, 20))  # returns 1 on success
```

4) 監査ログ DB 初期化
```python
import duckdb
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

5) カレンダー更新バッチ（calendar_update_job）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn, lookahead_days=90)
print("saved:", saved)
```

6) 研究ユーティリティ（例: モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records: list of dicts with mom_1m / mom_3m / mom_6m / ma200_dev
```

注意:
- OpenAI 呼び出しを行う関数は `OPENAI_API_KEY` を環境変数から参照するか、関数引数で `api_key` を渡せます。
- ETL / データ保存系は DuckDB のスキーマ（raw_prices, raw_financials, market_calendar など）を前提とします。スキーマ作成は別の初期化処理が必要です（実運用では schema 初期化スクリプトを用意してください）。

---

## 開発／テストに関する補足

- 自動 .env ロードを無効化したい（ユニットテスト等）場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI やネットワーク呼び出しはユニットテストでモック可能に設計されています（内部呼び出し関数を patch することで差し替え可能）。

---

## ディレクトリ構成（主なファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理、自動 .env ロード、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         : ニュースを OpenAI で解析し ai_scores に書き込む
    - regime_detector.py  : ETF 1321 MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   : J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py         : ETL パイプライン（run_daily_etl 等）
    - etl.py              : ETL インターフェース再エクスポート
    - news_collector.py   : RSS ニュース収集・前処理（SSRF 対策等）
    - calendar_management.py : 市場カレンダー管理（営業日判定、更新ジョブ）
    - quality.py          : データ品質チェック
    - stats.py            : zscore_normalize 等の統計ユーティリティ
    - audit.py            : 監査ログスキーマ初期化（signal/events/order/executions）
  - research/
    - __init__.py
    - factor_research.py  : momentum / value / volatility 等のファクター計算
    - feature_exploration.py : 将来リターン計算、IC、統計サマリー等

---

## 参考・注意事項

- DuckDB のバージョンや SQL の挙動に依存する実装箇所があるため、実行環境の DuckDB バージョンに注意してください（コメント中に互換性に関する注意あり）。
- OpenAI のレスポンスは厳密な JSON を期待していますが、実際の運用ではレスポンスが想定外の形式となる可能性を扱うフォールバックが組み込まれています（パース失敗時はスコアを 0 にする等）。
- J-Quants API のレート制限およびトークン管理に関するロジック（リトライ・指数バックオフ・固定間隔レートリミット）が組み込まれています。

---

もし README に追加したい「実行スクリプト」「CLI」「初期スキーマ作成スクリプト（raw_prices などのDDL）」があれば、コードベースから抜粋して README に組み込みます。必要ならサンプル .env.example の作成も手伝えます。