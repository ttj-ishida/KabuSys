# KabuSys

KabuSys は日本株向けのデータプラットフォーム＆自動売買基盤の一部実装です。J-Quants／RSS／OpenAI（LLM）などの外部データを取り込み、ETL・品質チェック・ニュース NLP・市場レジーム判定・監査ログなどの機能を提供します。

主な目的は「データ取得・前処理・特徴量算出・NLP によるセンチメント評価」を安定して行い、戦略層・実行層へ安全に受け渡せる土台を作ることです。

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート自動検出）
  - 必須環境変数チェック（Settings クラス）

- データ ETL（kabusys.data.pipeline）
  - J-Quants API から差分取得（株価・財務・カレンダー）
  - ページネーション・レートリミット・リトライ対応
  - DuckDB へ冪等保存（ON CONFLICT ベース）
  - ETL 結果の品質チェック（欠損・スパイク・重複・日付不整合）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - 営業日判定、前後営業日の取得、期間内営業日の取得
  - JPX カレンダーの夜間更新ジョブ

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 防止、リダイレクト検査、トラッキング除去）
  - テキスト前処理、raw_news / news_symbols への冪等保存

- ニュース NLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出
  - バッチ・トリミング・リトライ・レスポンス検証・DuckDB への書込み

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）200日移動平均乖離 + マクロニュース（LLM）を合成して日次レジーム判定
  - DB へ冪等書込み

- リサーチ支援（kabusys.research）
  - モメンタム、ボラティリティ、バリュー等ファクター計算
  - 将来リターン計算、IC（Spearman ρ）、ファクター統計サマリー
  - 汎用 zscore 正規化ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal → order_request → execution のトレースを保証する監査テーブル定義と初期化
  - DuckDB ベースで UTC タイムスタンプ管理、冪等的スキーマ作成

---

## 前提・依存（最低限）

- Python 3.10+
- DuckDB（Python パッケージ: duckdb）
- OpenAI Python SDK（openai）
- defusedxml（RSS パース）
- 標準ライブラリ（urllib 等）を利用

必要なパッケージはプロジェクトの requirements.txt を用意している前提で以下のようにインストールします:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

もし requirements.txt が無ければ少なくとも次をインストールしてください:

```bash
pip install duckdb openai defusedxml
```

---

## 環境変数（主なもの）

config.Settings で参照される環境変数（代表例）:

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: データ格納用 DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_FILL_MODE: Paper Trading の Fill モード（instant|partial|never|reject）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 実行監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: application 環境 (development|paper_trading|live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

設定値はプロジェクトルートの `.env`/.env.local に記載できます。プロジェクトルートは `.git` または `pyproject.toml` を基準に自動検出されます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## セットアップ手順（ローカル）

1. リポジトリをクローンしワークディレクトリへ移動
2. Python 仮想環境を用意して依存をインストール
3. data ディレクトリ等必要なディレクトリを作成（例: data/）
4. プロジェクトルートに `.env` を作成し必須変数を設定（.env.example を参考に）

例（最低限）:
```
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=yourpass
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

5. DuckDB ファイルは自動生成されるが、permissions 等を確認してください。

---

## 使い方（簡単な例）

以下は Python スクリプトや REPL から主要な関数を呼び出す例です。全て DuckDB の接続オブジェクト（duckdb.connect() で得る）を引数に取ります。

- ETL（日次一括処理）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントスコア付与（score_news）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で OPENAI_API_KEY を使用
print(f"scored {n_written} codes")
```

- 市場レジーム判定（score_regime）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: でインメモリ可能
```

- RSS フィード取得（ニュース収集の一部）

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["datetime"], a["title"])
```

---

## 実装上の注意点

- ルックアヘッドバイアス対策として、各モジュールは date / target_date を明示して内部で現在時刻 (today) を参照しない実装になっています。バッチ処理やバックテスト時には target_date を適切に与えてください。
- OpenAI API 呼び出しはリトライや JSON 検証を行いますが、API キー未設定時は ValueError を送出します。
- ETL・保存処理は冪等性を重視しており、既存レコードは ON CONFLICT DO UPDATE により上書きされます。
- news_collector は SSRF や XML 攻撃対策（defusedxml、ホスト検査、リダイレクト検査など）を実装しています。
- DuckDB の executemany に対し空リストを渡すとエラーとなるバージョンがあるため、適所で空チェックを行っています。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（Settings クラス、.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（OpenAI を用いた銘柄ごとのセンチメント）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロNL P）
  - data/
    - __init__.py
    - calendar_management.py — マーケットカレンダー管理・営業日判定
    - etl.py — ETL インターフェース再エクスポート
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログスキーマと初期化
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - news_collector.py — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 計算
    - feature_exploration.py — forward returns / IC / rank / summary
  - ai/、research/、data/ の詳細は各モジュールの docstring を参照してください。

---

## 開発・テスト

- 単体テストはプロジェクトに含まれていない前提です。テストを追加する場合は pytest 等を導入してください。
- LLM・外部 API を呼び出す部分はネットワークに依存するため、ユニットテストではモック（unittest.mock.patch）で _call_openai_api や jquants_client._request、news_collector._urlopen などを差し替えてください。
- config の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。テストで環境変数を制御する際に便利です。

---

## ライセンス・貢献

本リポジトリのライセンス情報・貢献ルールは別途 LICENSE / CONTRIBUTING ファイルを参照してください（このコードベースには明示されていません）。プルリクエスト・バグ報告は GitHub issue を通じてお願いします。

---

必要であれば README に追記する項目（例: 各テーブルスキーマの説明、.env.example のテンプレート、運用時の cron ジョブ例、監視・アラート設定例など）を作成します。どの情報を優先して追加しますか？