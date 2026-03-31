# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリ群です。  
DuckDB をデータレイクとして用い、J-Quants からのデータ取り込み（ETL）、ニュース収集・NLP（OpenAI を用いたセンチメント評価）、リサーチ用ファクター計算、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な用途例:
- 日次 ETL パイプラインで株価・財務・市場カレンダーを取得・保存
- ニュースを収集して銘柄ごとに AI によるセンチメントスコアを生成
- マクロニュースと移動平均乖離から市場レジームを判定
- 研究用のファクター計算（モメンタム・バリュー・ボラティリティ等）
- 発注・約定の監査ログ（DuckDB）を初期化・管理

---

## 機能一覧

- 設定管理
  - .env ファイルや環境変数から設定を読み込む自動ロード機能（プロジェクトルート検出）
  - 必須環境変数チェック
- データ ETL
  - J-Quants API から株価（日次）・財務データ・市場カレンダーを差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT / UPDATE）
  - 日次 ETL の統合ランナー（run_daily_etl）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
- ニュース収集 / NLP
  - RSS 取得（SSRF 対策、gzip 上限検査、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF MA200 乖離を組み合わせた市場レジーム判定（score_regime）
- リサーチ
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計要約
  - Z スコア正規化ユーティリティ
- 監査（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
  - 監査用 DuckDB データベース初期化関数（init_audit_db / init_audit_schema）
- ユーティリティ
  - JPX カレンダー管理（営業日判定、next/prev trading day）
  - J-Quants API クライアント（Rate limit 対処、トークン自動リフレッシュ、リトライ）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の型記法などを使用）
- DuckDB を利用可能

推奨パッケージ（最低限）
- duckdb
- openai
- defusedxml

例: 仮想環境作成〜インストール
```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install duckdb openai defusedxml
# パッケージをローカル編集可能モードでインストールする場合
# (プロジェクトルートに setup.py / pyproject.toml がある想定)
pip install -e .
```

環境変数 / .env
- 自動でプロジェクトルート（.git または pyproject.toml）を探索して .env を読み込みます。
- 自動ロードを無効化する場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

主な必須環境変数
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知チャンネル
- OPENAI_API_KEY — OpenAI を使う処理（score_news / score_regime 等）で必要

任意 / デフォルト
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）

.example .env（README 用）
```
# 必須
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=your_openai_api_key
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id

# 任意
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

## 使い方（主要な API / コマンド例）

以下は Python API を直接使う例です。各関数は duckdb コネクションを受け取るので、テストやバッチで容易に組み合わせられます。

1) DuckDB に接続
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメントを計算して ai_scores に保存する
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# API キーは環境変数 OPENAI_API_KEY または api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("written:", n_written)
```

4) 市場レジームをスコアリングして market_regime に保存する
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

5) リサーチ用ファクター計算（例: モメンタム）
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は dict のリスト（各要素に date, code, mom_1m, ... が含まれる）
```

6) 監査ログ用データベース初期化
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit_duckdb.db")
# init_audit_db は監査テーブルを作成済みの DuckDB 接続を返す
```

7) カレンダー操作（営業日判定）
```python
from datetime import date
from kabusys.data.calendar_management import is_trading_day, next_trading_day

is_open = is_trading_day(conn, date(2026, 3, 20))
next_day = next_trading_day(conn, date(2026, 3, 20))
```

注意点
- AI 関連関数（score_news, regime_detector）は OPENAI_API_KEY を要求します。api_key 引数で明示的に渡すこともできます。
- run_daily_etl 等は ETL の途中で例外が起きても他ステップを続行する設計です。戻り値 (ETLResult) で品質問題やエラーを確認してください。
- デフォルトの DuckDB パスは settings.duckdb_path で参照できます。

---

## ディレクトリ構成（主要ファイルと説明）

（root）/src/kabusys/
- __init__.py
  - パッケージのトップレベル（__version__ 等）
- config.py
  - .env / 環境変数の自動読み込みと Settings クラス
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能
- ai/
  - __init__.py
  - news_nlp.py
    - news を集約して OpenAI に投げ、ai_scores テーブルへ書き込む score_news
  - regime_detector.py
    - ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して market_regime を更新する score_regime
- data/
  - __init__.py
  - jquants_client.py
    - J-Quants API クライアント（認証、ページネーション、保存関数）
  - pipeline.py
    - 日次 ETL 実行ロジック（run_daily_etl 等）および ETLResult
  - etl.py
    - ETLResult の再エクスポートインターフェース
  - news_collector.py
    - RSS 収集・前処理・raw_news 保存機能（SSRF 対策、gzip 上限等）
  - calendar_management.py
    - market_calendar の管理と営業日判定ユーティリティ
  - quality.py
    - データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats.py
    - zscore_normalize などの統計ユーティリティ
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）の DDL と初期化関数
- research/
  - __init__.py
  - factor_research.py
    - モメンタム / バリュー / ボラティリティ計算関数
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク変換など

その他
- data/kabusys.duckdb（デフォルトの DuckDB ストレージパス。settings.duckdb_path で変更可能）
- data/monitoring.db（デフォルトの sqlite path）

---

## ログ・環境（運用メモ）

- KABUSYS_ENV は development / paper_trading / live のいずれか。live では実際の執行等に注意。
- ログレベルは LOG_LEVEL で制御（DEBUG/INFO/...）
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）から行います。パッケージ化後やテスト時は環境に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## テストとモックのヒント

- OpenAI / ネットワーク呼び出しは内部の _call_openai_api などを patch / monkeypatch して差し替え可能です（テストで安定化）。
- news_collector._urlopen や jquants_client の HTTP 層も同様にモックできます。
- DuckDB は ":memory:" を使ってインメモリ DB を作成し、テーブル操作をテストできます。

---

README はここまでです。特定のワークフロー（例: CI での ETL スケジュール、Slack 通知の実装、kabuステーション への実注文フロー）について詳しい手順が必要であれば、用途に応じた別ページ（運用ガイド / デプロイ手順）を作成します。必要であれば教えてください。