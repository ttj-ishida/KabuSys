# KabuSys

日本株向けの自動売買・データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレース）などの機能を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するコア機能群をモジュール化した Python パッケージです。主に以下を目的としています。

- J-Quants API からの株価 / 財務 / カレンダーの差分 ETL
- ニュース収集（RSS）と LLM によるセンチメント計算（銘柄毎 / マクロ）
- 市場レジーム判定（MA と マクロセンチメントの合成）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 研究用ファクター計算（モメンタム・ボラティリティ・バリュー 等）
- 監査ログ（signal → order_request → executions のトレーサビリティ）
- DuckDB を中心としたオンプレ/ローカルデータ管理

設計上の重要点として、バックテストにおけるルックアヘッドバイアスを避けるため日時関数の直接参照を避ける（target_date を明示する）ことや、外部 API 呼び出しのリトライ/フェイルセーフ処理が組み込まれています。

---

## 主な機能一覧

- 環境設定管理（.env 自動読み込み、Settings クラス）
- J-Quants クライアント（取得・ページネーション・token リフレッシュ・保存用ユーティリティ）
- ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（missing / duplicates / spike / date consistency）
- ニュース収集（RSS、SSRF 対策、前処理、raw_news 保存）
- ニュース NLP（gpt-4o-mini を使った銘柄ごとのセンチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 の乖離 + マクロセンチメントの合成 score_regime）
- 研究モジュール（ファクター計算、将来リターン、IC、Zスコア正規化）
- 監査ログ（signal_events / order_requests / executions テーブルの初期化と管理）
- DuckDB ベースの保存ユーティリティ（監査DB 初期化 helper）

---

## セットアップ手順

前提:
- Python 3.10+（型注釈で Union | None 等を使用しているため）
- ネットワーク接続（J-Quants / OpenAI 等を利用する場合）

1. リポジトリをクローンしてパッケージをインストール（開発用）
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   python -m pip install -e .
   ```
   ※ プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を先にしてください。

2. 必要なライブラリ（主要なもの）
   - duckdb
   - openai
   - defusedxml
   - (標準ライブラリ以外は pip でインストールしてください)
   例:
   ```bash
   pip install duckdb openai defusedxml
   ```

3. 環境変数設定 (.env)
   プロジェクトルート（.git または pyproject.toml が存在する場所）に `.env` / `.env.local` を置くと自動で読み込まれます（ロード順: OS 環境 > .env.local > .env）。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限設定が必要な環境変数（Settings で必須となるもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY (score_news / score_regime 利用時)

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

4. デフォルト DB パス
   - DuckDB: data/kabusys.duckdb（settings.duckdb_path）
   - SQLite（監視用）: data/monitoring.db（settings.sqlite_path）
   必要に応じて .env で `DUCKDB_PATH` / `SQLITE_PATH` を上書きしてください。

---

## 使い方（簡単な例）

以下は主要な処理を Python REPL やスクリプトから呼び出す例です。

- DuckDB に接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date 指定（省略時は今日）:
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に保存する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY が環境変数にある場合 api_key 引数は不要
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム（market_regime テーブル）を判定する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions が作成されます
```

- 研究用関数の利用例（モメンタム計算）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は各銘柄ごとのファクターを含む dict のリスト
```

ログレベルは環境変数 `LOG_LEVEL` で変更可能（DEBUG/INFO/WARNING/ERROR/CRITICAL）。実行環境は `KABUSYS_ENV`（development / paper_trading / live）のいずれかである必要があります。

---

## 注意・運用メモ

- OpenAI / J-Quants などの API キーは機密情報です。`.env` をリポジトリに含めないでください。
- score_news / score_regime は OpenAI API を呼び出します。API 利用料とレート制限に注意してください。実装側でリトライ・バックオフを持ちますが、運用上の限度は別途設定してください。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンの考慮がコード内にあります。直接的な空挿入を避ける実装になっています。
- ニュース収集は RSS のサイズ制限（10MB）・SSRF 対策・XML パースの防護（defusedxml）などを実装していますが、RSS ソースの追加時は十分に検証してください。
- 自動 .env ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利です）。

---

## ディレクトリ構成（抜粋）

以下はパッケージ内の主要モジュール構成の抜粋です（src/kabusys 配下）。

- kabusys/
  - __init__.py
  - config.py             — 環境変数/Settings 管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント + DuckDB 保存関数
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult の公開エイリアス
    - quality.py          — データ品質チェック
    - news_collector.py   — RSS 取得・正規化・保存
    - calendar_management.py — 市場カレンダー判定・更新ジョブ
    - stats.py            — zscore_normalize 等の統計ユーティリティ
    - audit.py            — 監査ログ DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / summary 等

（実際のファイル構成はリポジトリの内容に従ってください）

---

## 開発・テスト

- 自動 .env 読み込みは config モジュールで行われます。ユニットテストで環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自前で環境を準備してください。
- OpenAI / ネットワーク呼び出しはモジュール内で個別関数（例: _call_openai_api や _urlopen）に抽象化しているため、ユニットテストでは patch/mocking して外部呼び出しを差し替えやすくなっています。
- DuckDB はファイル（例: data/kabusys.duckdb）または `":memory:"` を使ってテスト可能です。

---

## 参考・追加情報

- 環境変数の自動ロード順: OS 環境 > .env.local (override=True) > .env (override=False)
- Settings で利用可能なプロパティ:
  - jquants_refresh_token, kabu_api_password, kabu_api_base_url, slack_bot_token, slack_channel_id, duckdb_path, sqlite_path, env, log_level, is_live/is_paper/is_dev
- KABUSYS_ENV の有効値: development / paper_trading / live

---

問題報告・貢献方法:
- バグや改善希望がある場合は issue を立ててください。Pull Request は歓迎します。

以上。README の補足やサンプルスクリプトが必要であれば用途（ETL 自動実行 cron/コンテナ化 / バックテスト統合 等）を教えてください。必要に応じて追加例を書きます。