# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）の README。  
このリポジトリはデータ ETL、ニュースセンチメント（LLM）評価、ファクター計算、監査ログスキーマなどを含む内部ライブラリ群を提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けの内部ツール群です。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等のデータを差分取得して DuckDB に保存する ETL
- RSS ニュース収集と OpenAI を用いた銘柄／マクロのセンチメント評価
- ファクター計算、将来リターンやIC（Information Coefficient）などのリサーチユーティリティ
- 監査（audit）テーブルの初期化・運用（シグナル→発注→約定のトレーサビリティ）
- 市場カレンダーやデータ品質チェック、データ保存ユーティリティ

設計上の特徴として、バックテストにおけるルックアヘッドバイアス防止、冪等性（ON CONFLICT / idempotent save）、外部 API の適切なリトライとレート制御が考慮されています。

---

## 主な機能一覧

- データ取得・保存
  - J-Quants からの株価日足（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション／トークン自動リフレッシュ／レート制御）
  - DuckDB への冪等保存（ON CONFLICT）
- ETL
  - 日次 ETL パイプライン（calendar → prices → financials → 品質チェック）
  - 差分取得・バックフィル制御
- ニュース関連（NLP / LLM）
  - RSS 収集（SSRF 対策／トラッキング除去／前処理）
  - OpenAI（gpt-4o-mini）を使った銘柄ごとのニューススコアリング（ai_scores テーブルへ）
  - マクロセンチメントと ETF（1321）200日MA乖離の合成による市場レジーム判定（bull/neutral/bear）
  - API 呼び出しは堅牢なリトライ・バックオフ処理
- リサーチ
  - モメンタム/ボラティリティ/バリュー等のファクター計算
  - 将来リターンの計算、IC 計算、ファクター統計サマリー、Z スコア正規化等
- モニタリング／監査
  - 監査ログ用のスキーマ作成・初期化（signal_events / order_requests / executions 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合検出）
- 設定管理
  - .env ファイルまたは環境変数から設定を読み込む仕組み（自動ロードあり）

---

## 必要な依存パッケージ（例）

本リポジトリで使用される主な外部パッケージ（インストールする）:

- Python 3.10+
- duckdb
- openai
- defusedxml

（環境に応じて urllib / datetime など標準ライブラリを使用）

requirements.txt が用意されていない場合は手動でインストールしてください:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
```

---

## 環境変数 / .env の例

config.py で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略可、デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視 DB）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY — OpenAI API キー（ニュース / レジーム判定で使用）

自動的に .env と .env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。プロジェクトルートの特定は .git または pyproject.toml を基準とします。

例 (.env.example):

```
JQUANTS_REFRESH_TOKEN=...
OPENAI_API_KEY=...
KABU_API_PASSWORD=...
SLACK_BOT_TOKEN=...
SLACK_CHANNEL_ID=...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン

```bash
git clone <repo-url>
cd <repo-dir>
```

2. Python 仮想環境を作成して依存をインストール

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

（必要に応じて他のライブラリもインストールしてください）

3. 環境変数の準備

プロジェクトルートに .env を作成し、上記の必須変数を設定します。例:

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=your_slack_token
SLACK_CHANNEL_ID=your_channel_id
```

4. DuckDB データベースディレクトリ作成（必要なら）

```bash
mkdir -p data
```

---

## 使い方（主要なユーティリティの例）

以下は Python REPL やスクリプトから利用する例です。

- 日次 ETL の実行

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# DuckDB に接続（ファイルは settings.duckdb_path）
conn = duckdb.connect(str(settings.duckdb_path))
# ETL を実行（target_date を指定しなければ今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（銘柄単位）スコアリング

```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使用
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定（マクロセンチメント + ETF MA）

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を省略すると OPENAI_API_KEY を使用
```

- 監査 DB の初期化（監査テーブル作成）

```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

conn = init_audit_db(settings.duckdb_path)  # transactional=True/False は内部オプション
```

- リサーチ用ファクター計算（例: モメンタム）

```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{ "date":..., "code":..., "mom_1m":..., ...}, ...]
```

---

## よくあるトラブルシューティング

- .env が読み込まれない  
  - config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動読み込みします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI 呼び出しが失敗する（429/タイムアウト等）  
  - モジュールはリトライやフォールバック（ゼロスコア）を実装しています。APIキーやネットワーク、料金プランを確認してください。

- DuckDB に書き込めない権限エラー  
  - 指定した DUCKDB_PATH の親ディレクトリが存在するか、ファイルの書き込み権限があるか確認してください。

- J-Quants 認証エラー（401）  
  - config の `JQUANTS_REFRESH_TOKEN` が正しいか、`get_id_token` を呼んでリフレッシュが成功するか確認してください。モジュールは 401 時に自動でリフレッシュを試みます。

---

## ディレクトリ構成（抜粋）

以下はソースツリー（src/kabusys）内の主要ファイルと簡単な説明です。

- src/kabusys/
  - __init__.py — パッケージ定義（version）
  - config.py — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの LLM スコアリング（ai_scores への書き込み）
    - regime_detector.py — ETF MA とマクロセンチメント合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存関数）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再公開
    - calendar_management.py — 市場カレンダー管理（営業日判定など）
    - news_collector.py — RSS ニュース収集（SSRF 対策等）
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログテーブル定義・初期化
  - research/
    - __init__.py
    - factor_research.py — モメンタム／ボラティリティ／バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - monitoring/ (※実装がある前提なら監視用モジュール等)
  - execution/ (※約定/発注処理関連モジュール)
  - strategy/ (※戦略定義・シグナル生成関連)

（実際のファイル数・サブパッケージはリポジトリ全体を参照してください）

---

## 開発／テストについて

- モジュールは外部 API 呼び出し部を patch / モック可能な形で設計されています（例: news_nlp._call_openai_api のモックなど）。ユニットテストを書く場合は該当関数をモックして外部依存を切り離してください。
- DuckDB はインメモリ（":memory:"）でも動作します。テストでファイル I/O を避ける場合は `duckdb.connect(":memory:")` を使用できます。

---

もし README に追加したい「実行スクリプト」「CI 設定」「例の .env.example」などがあれば、リポジトリの該当箇所に合わせて追記します。必要であればサンプル .env.example を作成して出力します。