# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ KabuSys のリポジトリ用 README です。

主にデータ取得（J-Quants）、ニュースNLP / LLM 評価、ファクター計算、ETL、監査ログ（監視・約定トレース）などのユーティリティ群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発および研究（リサーチ）で利用するための共通モジュール群です。主な目的は次のとおりです。

- J-Quants API からの日次株価・財務・カレンダーの差分 ETL
- RSS を利用したニュース収集と LLM によるニュースセンチメント評価
- 市場レジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- データ品質チェック、監査ログ / トレーサビリティ（発注〜約定の監査テーブル）
- データアクセス / DB ユーティリティ（DuckDB ベース）

設計上のポイント：
- ルックアヘッドバイアスを避けるため、各処理は target_date 引数を受け取り現在時刻の暗黙参照を避ける（テスト/バックテストに適合）
- DuckDB を主要な永続化先とし、ETL は差分取得と冪等保存を行う
- OpenAI / J-Quants 等外部 API 呼び出しには堅牢なリトライ・バックオフロジックを採用

---

## 主な機能一覧

- 環境設定読み込み（.env 自動読み込み、settings オブジェクト）
- J-Quants クライアント（取得・保存関数、認証自動更新、レートリミット管理）
- ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
- データ品質チェック（欠損、重複、スパイク、日付不整合など）
- ニュース収集（RSS -> raw_news、SSRF対策、前処理）
- ニュース NLP（gpt-4o-mini を利用した銘柄ごとのセンチメント score_news）
- 市場レジーム判定（ETF 1321 の MA200 乖離とマクロニュースを合成する score_regime）
- リサーチ用ファクター計算（calc_momentum, calc_volatility, calc_value）
- 統計ユーティリティ（zscore_normalize、rank、calc_ic、factor_summary）
- 監査ログ（signal_events, order_requests, executions の初期化・DB作成・接続ユーティリティ）
- カレンダー管理（is_trading_day / next_trading_day / calendar_update_job）

---

## 前提・依存関係

（主なランタイム依存パッケージ例）
- Python 3.10+（型ヒント union | を使用しているため）
- duckdb
- openai（OpenAI の v1 SDK）
- defusedxml
- その他標準ライブラリ（urllib, json, logging, datetime 等）

インストール例（開発環境）：
```bash
# 必要パッケージを個別にインストールする例
pip install duckdb openai defusedxml
# またはパッケージ配布がある場合
pip install -e .
```

プロジェクトに requirements.txt や pyproject.toml がある場合はそちらを参照してインストールしてください。

---

## 環境変数 / 設定

KabuSys は .env（および .env.local）または OS 環境変数から設定を読み込みます。自動読み込みはデフォルトで有効ですが、無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主な必須環境変数：
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL・API 呼び出し用）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector など）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必要に応じて）
- SLACK_BOT_TOKEN: Slack 通知用 Bot トークン（必要に応じて）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID

任意・デフォルト設定（settings 経由で参照可能）：
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH (default: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
- KABUSYS_ENV (development | paper_trading | live) (default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) (default: INFO)

簡単な .env.example（README 用）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxx
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. Python 環境を用意（推奨: venv / pyenv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   ```

3. 必要パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   # その他開発用ツールや linter があれば追加
   ```

4. .env を作成し、上記の必須環境変数を設定

5. DuckDB ファイル等のデータディレクトリを作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトでの代表的な呼び出し例です。

- settings を参照する
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- DuckDB 接続を作成して ETL を実行する（日次 ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
# target_date を省略すると今日（settings.env によらず）を使用
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメントをスコアリング（score_news）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
print("scored:", n_written)
```

- 市場レジームを判定（score_regime）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは環境変数を参照
```

- 監査ログ用 DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# これで signal_events, order_requests, executions 等のテーブルが作成される
```

- リサーチ用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026,3,20))
# records は各銘柄ごとの dict のリスト
```

注意点：
- これらの関数は内部で target_date 未満 / 以前のみ参照する設計になっており、明示的に date を渡してバックテストでのルックアヘッドを防止できます。
- OpenAI や J-Quants の API 呼び出しにはそれぞれの API キーが必要です。環境変数で指定するか、関数引数で api_key 等を注入してください。

---

## よく使うコマンド例

- ETL を cron / バッチとして実行（例: daily）
  - Python スクリプトを作り、run_daily_etl を呼ぶ（上記参照）
- 監査 DB を初期化（初回のみ）
  ```bash
  python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"
  ```

---

## ディレクトリ構成（主要ファイル）

（パッケージルートは src/kabusys/ を想定）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / settings 管理、.env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースの LLM スコアリング（score_news）
    - regime_detector.py    — マクロ + ETF で市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py           — ETL パイプライン / run_daily_etl 等
    - etl.py                — ETLResult の公開
    - quality.py            — データ品質チェック（missing/duplicates/spike/date consistency）
    - news_collector.py     — RSS 収集・前処理（SSRF 対策、トラッキング除去）
    - calendar_management.py— 市場カレンダー管理（is_trading_day, next/prev 等）
    - stats.py              — 統計ユーティリティ（zscore_normalize）
    - audit.py              — 監査ログ（DDL / 初期化 / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py    — Momentum/Volatility/Value の計算
    - feature_exploration.py— 将来リターン、IC、ランク、統計サマリー等
  - ai/、data/、research/ はさらに細分化されて機能別に整理されています。

---

## 開発・テストに関する注意

- 多くのモジュールは外部 API に依存するため、ユニットテストでは外部呼び出しをモックすることを推奨します（コード内にモック可能な内部関数が用意されています）。
- settings モジュールは起動時にプロジェクトルートの `.env` と `.env.local` を自動ロードします。テスト時に自動ロードを避けたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB の executemany に空リストを渡すと例外になるバージョンがあるため、該当実装では空チェックを入れてあります。

---

## ライセンス・貢献

本リポジトリのライセンス情報や貢献ガイドはリポジトリルートの LICENSE / CONTRIBUTING 等を参照してください。

---

README の内容はコードベース（src/kabusys）を参照してまとめています。具体的な API キーや運用手順、CI/CD、デプロイ手順などは運用ポリシーに応じて追記してください。必要なら README の英語版や各モジュールごとの詳細ドキュメント（API リファレンス、設定ファイル例、運用チェックリスト）も作成できます。