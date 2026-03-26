# KabuSys

KabuSys は日本株のデータパイプライン、リサーチ、AI ベースのニュースセンチメント評価、監査ログ・発注監視までを備えた自動売買支援ライブラリです。本リポジトリは主に DuckDB を用いたデータプラットフォーム、J-Quants API 経由の ETL、OpenAI を用いたニュース NLP、ファクター計算・解析、監査ログ用スキーマなどを提供します。

---

## プロジェクト概要

- データ収集（J-Quants API + RSS ニュース）
- 日次 ETL（株価・財務・マーケットカレンダー）
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュースのセンチメント解析（OpenAI を利用、銘柄ごと）
- 市場レジーム判定（ETF の MA とマクロニュースの複合）
- リサーチ用ファクター計算（モメンタム、ボラティリティ、バリュー等）
- 監査ログスキーマ（シグナル→発注→約定のトレース可能なテーブル群）
- 設定管理（.env / 環境変数自動読み込み）

設計上の重要点:
- ルックアヘッドバイアスを避ける（target_date ベースの処理、datetime.today() を直接参照しないモジュール設計）
- DuckDB によるローカル DB 保持と冪等保存（ON CONFLICT / INSERT … DO UPDATE）
- API 呼び出しにはリトライ・バックオフを実装（J-Quants / OpenAI）
- ニュース収集は SSRF 対策や受信サイズ制限を導入

---

## 機能一覧

- kabusys.config
  - 環境変数/.env の自動読み込み（.env, .env.local）と設定ラッパー（settings）
- kabusys.data
  - jquants_client: J-Quants API の取得・保存ユーティリティ（レート制御・リトライ・トークンリフレッシュ）
  - pipeline / etl: 日次 ETL パイプライン（run_daily_etl 等）
  - calendar_management: 市場カレンダー管理・営業日判定
  - news_collector: RSS フィードの収集、前処理、raw_news への保存
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - stats: zscore正規化など統計ユーティリティ
  - audit: 監査ログ（signal_events / order_requests / executions）の初期化
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを生成して ai_scores に保存
  - regime_detector.score_regime: ma200 とマクロニュースで日次の市場レジーム判定
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: 将来リターン計算、IC、統計サマリ、ランク関数

---

## 必要な環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン
- KABU_API_PASSWORD：kabuステーション API のパスワード（発注連携時）
- SLACK_BOT_TOKEN：Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID：Slack 通知先チャンネル ID
- OPENAI_API_KEY：OpenAI 呼び出し時に利用（score_news / score_regime）

オプション（デフォルトあり）:
- KABUSYS_ENV：development / paper_trading / live（デフォルト: development）
- LOG_LEVEL：DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH：DuckDB の DB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH：監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化します（テスト用途など）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## セットアップ手順

1. Python 3.10+ を用意（typing|新しい Union 表記等を参照しているため現行の安定版を推奨）
2. 仮想環境を作成・有効化（任意）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール（最小）
```
python -m pip install --upgrade pip
python -m pip install duckdb openai defusedxml
```
（プロジェクトに requirements.txt / pyproject.toml があればそちらを使ってください）
4. 環境変数を設定（上記 .env を作成するか、シェルで export）
   - リポジトリルートに .env / .env.local を置くと kabusys.config が自動で読み込みます
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
5. データディレクトリを作成（デフォルト）
```
mkdir -p data
```
6. DuckDB 接続を準備（コードまたは init_audit_db で自動生成）

---

## 使い方（主要な例）

- 設定の参照:
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.is_live)
```

- DuckDB 接続を作って日次 ETL 実行:
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str("data/kabusys.duckdb"))
result = run_daily_etl(conn, target_date=date(2026, 3, 25))
print(result.to_dict())
```

- ニュースセンチメントのスコア（ai_scores への保存）:
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026,3,25), api_key="sk-...")
print(f"書込み銘柄数: {n_written}")
```

- 市場レジームの判定:
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026,3,25), api_key="sk-...")
```

- 監査ログ DB 初期化:
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions テーブルが作成されます
```

- ファクター計算例:
```python
from kabusys.research.factor_research import calc_momentum
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,3,25))
# records は各銘柄の辞書リスト
```

注意:
- OpenAI を使う関数は api_key 引数を直接渡すか、環境変数 OPENAI_API_KEY を設定してください。
- J-Quants を使う ETL は JQUANTS_REFRESH_TOKEN を必要とします。

---

## よくあるワークフロー

1. .env を作成して必要なトークンを設定
2. run_daily_etl をスケジューラ（cron / Airflow / GitHub Actions 等）から日次実行
3. ETL 後に score_news → score_regime を実行してマーケット指標や AI スコアを更新
4. research モジュールでファクター分析・バックテスト用データを生成
5. strategy / execution / monitoring コンポーネント（別途実装）と連携して実運用

---

## ディレクトリ構成（抜粋）

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
    - stats.py
    - quality.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - (strategy, execution, monitoring パッケージは __all__ に含まれていますが、実装は別または未配置)

各モジュールはコメントドキュメントに処理フローや設計方針が詳述されています。関数レベルの docstring を参照すると使用方法や副作用（DB 書き込み等）がわかります。

---

## 運用上の注意・設計に関するメモ

- Look-ahead バイアス防止のため、すべての「日次」処理は target_date を明示して実行する設計です。内部で date.today() / datetime.today() を参照しないようにモジュールが実装されています（ただし ETL のデフォルトは today）。
- J-Quants API はレート制限を守る必要があります。本クライアントは固定間隔スロットリングとリトライを実装しています。
- OpenAI への呼び出しはリトライ・フェイルセーフ（失敗時は中立スコア 0.0 にフォールバックするなど）を実装していますが、API コストとレートに注意してください。
- news_collector では SSRF 対策・受信サイズ制限・XML の安全処理を実装しており、任意の RSS を追加する場合はソースの妥当性を検討してください。
- DB 書き込みは可能な限り冪等になるよう ON CONFLICT / DELETE→INSERT の戦略を使用しています。

---

## トラブルシューティング

- 環境変数が不足すると kabusys.config.Settings のプロパティで ValueError が発生します。必須トークンを .env に設定してください。
- OpenAI レスポンスが期待した JSON でない場合、ログに警告が出て該当コードはスキップされることがあります（score_news/score_regime はフェイルセーフ設計）。
- DuckDB に対する executemany の空リストはバージョン依存で問題となるため、該当処理は空チェックを行っていますが、古い DuckDB を使う場合は挙動に注意してください。

---

もし README をプロジェクト用にさらにカスタマイズしたい（例: CI 実行方法、Dockerfile、requirements.txt の追加、具体的な cron / Airflow の例、strategy/execution 部分の使い方など）があれば詳細を教えてください。必要に応じてサンプル実行スクリプトや簡易の docker-compose 例も作成します。