# KabuSys

KabuSys は日本株のデータプラットフォーム、リサーチ、AI ニュース分析、そして自動売買監査ログまでを含む総合ライブラリです。本リポジトリは以下の主要コンポーネントを提供します。

- データ ETL（J-Quants から株価・財務・カレンダーを差分取得し DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集・NLP（RSS → raw_news、OpenAI を使った銘柄別センチメント）
- 市場レジーム判定（ETF の MA とマクロニュースを組合せ）
- 研究用ファクター計算（モメンタム／バリュー／ボラティリティ等）
- 発注・約定の監査ログ（監査テーブルの初期化ユーティリティ）

以下は開発者向けの README（セットアップ、使い方、ディレクトリ構成など）です。

---

## 主な機能

- ETL パイプライン（差分取得・バックフィル・品質チェック）
- J-Quants API クライアント（レート制御、リトライ、トークン自動リフレッシュ）
- DuckDB への冪等保存（ON CONFLICT を用いた更新）
- ニュース収集（RSS、SSRF 対策、前処理）
- OpenAI を用いたニュースセンチメント（銘柄単位のバッチ評価、JSON Mode 利用）
- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントの合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- 監査ログスキーマ初期化（signal_events / order_requests / executions）

---

## 必要な環境変数（代表）

以下はコード内で必須とされている主要な環境変数です（.env/.env.local に設定可能）。

必須（Settings により _require_ として取得されるもの）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- SLACK_BOT_TOKEN
- SLACK_CHANNEL_ID

その他（モジュール利用時に必要）
- OPENAI_API_KEY（AI モジュール：score_news / score_regime）
- KABUSYS_ENV（development / paper_trading / live、省略時 `development`）
- LOG_LEVEL（DEBUG/INFO/...、省略時 `INFO`）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT（監視設定）

自動ロードについて:
- パッケージは .git または pyproject.toml を基準にプロジェクトルートを検出し、`<root>/.env` → `<root>/.env.local` を自動的に読み込みます（OS 環境変数優先）。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（ユニットテストなどで便利です）。

---

## 依存パッケージ（例）

少なくとも以下を pip でインストールしてください（バージョンは適宜調整）。

- python >= 3.10
- duckdb
- openai
- defusedxml

例:
```bash
pip install duckdb openai defusedxml
```

プロジェクト配布が pip パッケージになっている場合は:
```bash
pip install -e .
```

（requirements.txt / pyproject.toml がある場合はそちらを参照・利用してください）

---

## セットアップ手順（簡易）

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_dir>
   ```

2. 仮想環境の作成（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb openai defusedxml
   ```

4. 環境変数の設定
   プロジェクトルートに `.env` を作成して必須キーを設定します（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   OPENAI_API_KEY=sk-...
   ```

5. DuckDB データベース用ディレクトリ作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なユースケース）

以下は最小限の利用例です。コードは Python スクリプトや REPL で実行できます。

- DuckDB へ接続して日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの銘柄別センチメントをスコアリング（OpenAI API キーが必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))  # api_key を引数で渡すことも可
print("scored:", count)
```

- 市場レジーム判定を実行（ETF 1321 の MA200 とマクロ記事で判定）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- カレンダー更新ジョブ（JPX カレンダーを J-Quants から差分取得）
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import calendar_update_job

conn = duckdb.connect("data/kabusys.duckdb")
saved = calendar_update_job(conn)
print("saved calendar rows:", saved)
```

- 監査ログ用の DuckDB を初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests / executions 等の操作を行える
```

- J-Quants の ID トークンを取得（内部でトークンキャッシュ・リフレッシュあり）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()
print(token[:20], "...")
```

注意:
- AI 系の関数（score_news, score_regime）は OPENAI_API_KEY を引数または環境変数で受け取ります。
- 各 ETL 関数は DuckDB 上のテーブル構造（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores 等）を前提としています。初期スキーマ作成のユーティリティは別途提供されている設計想定です（プロジェクトの schema 初期化手順を参照してください）。

---

## 実装上の重要な設計点・注意点

- Look-ahead bias（未来情報の参照）を避けるため、ほとんどの関数は内部で date.today() や datetime.today() を直接参照せず、明示的に target_date を受け取ります。
- J-Quants クライアントはレート制限（120 req/min）を守る実装とリトライ、401 でのトークン自動リフレッシュを持ちます。
- ニュース収集は SSRF 対策、受信バイト制限、XML パースセキュリティ対策（defusedxml）を組み込んでいます。
- OpenAI 呼び出しは JSON Mode（response_format={"type":"json_object"}）を用いる設計で、パース／検証に堅牢性を持たせています。API エラーは堅牢にハンドリングして、失敗時にはフェイルセーフ（スコア=0 など）で処理を続けます。
- データ保存は冪等性を意識（ON CONFLICT DO UPDATE / INSERT ... DO UPDATE など）しているため、再実行可能です。

---

## ディレクトリ構成（主要ファイル）

（プロジェクトのルートに `src/kabusys` があり、以下のモジュールが含まれます）

- kabusys/
  - __init__.py
  - config.py
    - .env/.env.local の自動読み込み、Settings クラス（環境変数管理）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースセンチメント（銘柄別スコア）
    - regime_detector.py — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - etl.py                — ETLResult 再エクスポート
    - pipeline.py           — 日次 ETL パイプライン / 個別 ETL ジョブ
    - stats.py              — Zスコア正規化など統計ユーティリティ
    - quality.py            — データ品質チェック
    - audit.py              — 監査ログ（テーブル定義・初期化）
    - jquants_client.py     — J-Quants API クライアント（取得・保存）
    - news_collector.py     — RSS 収集・前処理・保存ユーティリティ
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Value/Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数

---

## 開発・テストに関するヒント

- 自動環境変数読み込みをテストから隔離したい場合、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してからモジュールをインポートしてください。
- OpenAI 呼び出しや外部 HTTP 呼び出しはユニットテストでモックできるように、呼び出しを内部関数（例: _call_openai_api, _urlopen）に切り出しています。unittest.mock.patch を利用して置換してください。
- DuckDB に対する executemany の空リストバインドなど、実装上の細かな互換制約があるため、テストでは実データを用意して動作確認を行ってください。

---

この README はコードベースの概要と典型的な利用フローをまとめたものです。さらに詳しい API ドキュメントやスキーマ定義（テーブル DDL）、運用ジョブ（cron/systemd 用）のテンプレートが必要であれば、追って作成・追加できます。必要な項目を教えてください。