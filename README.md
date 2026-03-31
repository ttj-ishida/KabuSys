# KabuSys

日本株向けの自動売買データプラットフォーム兼リサーチ基盤。  
J-Quants / RSS / OpenAI（LLM）等を組み合わせて、データ取得（ETL）、品質チェック、ニュースセンチメント分析、マーケットレジーム判定、ファクター計算、監査ログ管理などを行うモジュール群を提供します。

---

## 主な特徴（機能一覧）

- データ取得（ETL）
  - J-Quants API から株価日足（OHLCV）、財務データ、上場銘柄情報、JPXマーケットカレンダーを差分取得して DuckDB に保存
  - 差分更新 / バックフィル制御 / ページネーション対応 / リトライ・レート制御
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複検出、日付整合性チェック（未来日・非営業日）
- ニュース収集
  - RSS フィード取得、前処理、記事ID生成（URL正規化＋ハッシュ）による冪等保存、銘柄紐付け
  - SSRF 対策、受信サイズ制限、XML パース耐性
- ニュースNLP（LLM）
  - OpenAI（gpt-4o-mini）を用いた銘柄単位のニュースセンチメント算出（ai_scores テーブルへ書き込み）
  - バッチ処理・チャンク化・リトライ・レスポンス検証（JSON Mode）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースの LLM センチメント（30%）を合成して日次で 'bull'/'neutral'/'bear' を判定
  - DuckDB の prices_daily / raw_news からルックアヘッドバイアスを排除して計算
- リサーチ（ファクター計算 / 特徴量探索）
  - Momentum / Volatility / Value 等ファクターの計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z-score 正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査スキーマを提供
  - 監査DBの初期化ユーティリティ（UTC タイムゾーン、冪等DDL）

---

## 必要条件（依存ライブラリの一例）

本リポジトリのコードは以下のライブラリを想定しています（バージョンは環境に合わせて調整してください）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。）

インストール例（開発環境）:
```bash
python -m pip install -U pip
python -m pip install duckdb openai defusedxml
# 開発用にパッケージを編集可能にインストールする場合
pip install -e .
```

---

## 環境変数（設定）

自動で `.env` / `.env.local` をプロジェクトルートから読み込みます（優先度: OS 環境 > .env.local > .env）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

主な環境変数（名前と用途）:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しで使用）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack Bot トークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視しきい値（%）
- KABUSYS_ENV — 環境 (development / paper_trading / live)。デフォルト: development
- LOG_LEVEL — ログレベル (DEBUG / INFO / WARNING / ERROR / CRITICAL)

サンプル .env（README 用）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリを取得
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. Python 仮想環境（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   ```bash
   pip install -r requirements.txt     # もしあれば
   # または
   pip install duckdb openai defusedxml
   ```

4. 環境変数を設定（.env をプロジェクトルートに作成）
   - README 上のサンプルを参考に .env を作る
   - 開発時は .env.local を用いてローカル値を上書き可能

5. DuckDB データベースの初期化（必要に応じて）
   - 監査ログ専用 DB を作成する例は下記「使い方」を参照

---

## 使い方（簡単なコード例）

以下は代表的なユースケースの Python スニペット例です。プロジェクト内の関数は DuckDB 接続オブジェクト（duckdb.connect(...) が返す接続）を引数に取る設計です。

- 日次 ETL を実行する（株価・財務・カレンダー）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントを算出して ai_scores に書き込む
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジームを判定する
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査DBを初期化する（別 DB を使う例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # :memory: も可
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- RSS を取得する（ニュース収集の一部）
```python
from kabusys.data.news_collector import fetch_rss

articles = fetch_rss(
    url="https://news.yahoo.co.jp/rss/categories/business.xml",
    source="yahoo_finance",
    timeout=30,
)
for a in articles:
    print(a["id"], a["datetime"], a["title"])
```

注意:
- OpenAI への呼び出しは外部 API を使うため、API キーとネットワーク接続が必要です。
- LLM 呼び出しについてはテスト時にモックしやすいように内部呼び出し関数を差し替え可能です（例: unittest.mock.patch）。
- 多くの関数は内部で例外処理・フェイルセーフを備えていますが、DB 書き込みエラー等は上位へ伝播することがあります。

---

## ディレクトリ構成（抜粋）

プロジェクトは Python パッケージ `kabusys` 配下に機能別モジュールが分離されています。主要ファイル・モジュールの説明を示します。

- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン情報等）
  - config.py — 環境変数 / 設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント算出（OpenAI を利用）
    - regime_detector.py — マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存ユーティリティ）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETL の公開型（ETLResult の re-export）
    - calendar_management.py — マーケットカレンダー管理（営業日判定等）
    - news_collector.py — RSS 収集・前処理・保存ロジック
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログスキーマ定義・初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - research/ 以下は研究用途で DuckDB を用いた分析に関するユーティリティ群

（上記のほかに execution, monitoring, strategy 等のサブパッケージが想定されていますが、ここでは主要な data/ai/research の抜粋を示しています。）

---

## 開発・テスト時の注意事項

- .env 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に環境を汚したくない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI の呼び出しはモック可能な箇所が用意されています（各モジュール内の `_call_openai_api` 等を patch）。
- DuckDB の executemany はバージョン依存の制約（空リスト渡せない等）があるため、すでに対策済みのコードになっています。
- すべての日時は原則 UTC（DB 内の TIMESTAMP）または明示的に JST/UTC 変換を行う設計ルールに従っています。Look-ahead バイアスを避けるため、関数は内部で date.today() を無条件に参照しない設計です（引数で基準日を受け取る）。

---

## ライセンス / 貢献

本 README はコードベースの説明です。実際のライセンスやコントリビュートルールはリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

この README はコードの主要な設計方針・使い方をまとめたものです。実運用ではログ設定、ジョブスケジューラ（cron / Airflow 等）、監視・アラート設定（Slack 通知等）を追加して運用してください。必要ならば README を実行手順（CI/CD、初期スキーマ作成コマンド等）に合わせて追記します。