# KabuSys

KabuSys は日本株のデータパイプライン、ニュースNLP、研究（ファクター計算）や監査ログ管理を備えた自動売買／リサーチ基盤のコアライブラリです。DuckDB をローカル DB として利用し、J-Quants API や RSS、OpenAI（LLM）を組み合わせてデータ取得・前処理・AI スコアリング・ファクター算出・監査ログ保存までの主要処理を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（内部で datetime.today() を盲目的に参照しない）
- DuckDB を中心に SQL + 最小限の Python を組み合わせて高性能に処理
- 外部 API 呼び出しはリトライ・バックオフ・フェイルセーフを備える
- 冪等性（ON CONFLICT / idempotent 保存）を重視

---

## 機能一覧

- データ取得 / ETL
  - J-Quants から株価日足（OHLCV）・財務データ・マーケットカレンダーを差分取得して DuckDB に保存
  - ETL の差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS フィードからニュースを収集し raw_news に保存（SSRF 対策・トラッキングパラメータ除去・サイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースを用いた市場レジーム判定（score_regime）

- 研究用ユーティリティ
  - ファクター計算（momentum, volatility, value 等）
  - 将来リターン計算、IC（Spearman）、Zスコア正規化、統計サマリー

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルの初期化と管理
  - 監査DB 初期化ユーティリティ（UTC タイムスタンプ、冪等DDL）

- 設定管理
  - 環境変数 / .env の自動読み込み（プロジェクトルート検出）と Settings API

---

## 必要な環境変数

以下はコード内で参照される主な環境変数です。開発環境ではリポジトリルートに `.env` / `.env.local` を作成して設定することを想定しています（自動ロード順: OS 環境変数 > .env.local > .env）。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須 (使用ケースにより必須となるもの)
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知用トークン（通知が必要な場合）
- SLACK_CHANNEL_ID — Slack チャネル ID
- KABU_API_PASSWORD — kabuステーション API パスワード（発注連携を行う場合）

任意 / デフォルト値あり
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / regime_detector に未引数時に参照）
- KABUSYS_ENV — 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（default: data/monitoring.db）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（1）

---

## セットアップ手順

1. Python のインストール（推奨: 3.10+）
2. 仮想環境の作成（任意）
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を作成するか、OS 環境変数に設定します。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567

   自動ロードの仕組み:
   - パッケージ読み込み時に .git または pyproject.toml を起点にプロジェクトルートを探し、`.env` → `.env.local` を読み込みます（OS 環境変数が優先）。
   - テスト等で無効化したい場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. DuckDB 初期化（監査ログ用）
   - Python REPL やスクリプトで:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - これにより監査用テーブルとインデックスが作成され、TimeZone は UTC に固定されます。

---

## 使い方（代表的な例）

以下は基本的な Python API の呼び方例です。target_date には datetime.date を渡します。関数はルックアヘッドを防ぐため date を明示する設計です。

- DuckDB 接続の準備（デフォルトパスを使用）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL の実行（市場カレンダー・株価・財務・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（AI）スコアリング
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

n_written = score_news(conn, target_date=date(2026, 3, 20))  # ai_scores テーブルに書き込み
```

- 市場レジーム判定（MA + マクロニュース + LLM）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))  # market_regime テーブルへ書き込み
```

- 研究系：ファクター計算・正規化
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize
from datetime import date

momentum = calc_momentum(conn, date(2026,3,20))
vol = calc_volatility(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
zscoreed = zscore_normalize(momentum, columns=["mom_1m", "mom_3m", "mom_6m"])
```

- 監査用 DB 初期化（スクリプトで）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# conn_audit を使って order / signal / execution の挿入・クエリが可能
```

注意点：
- OpenAI 呼び出しを行う関数 (score_news / score_regime) は api_key 引数を受け取ります。None の場合は環境変数 OPENAI_API_KEY を参照します。
- ETL / ニュース収集などでネットワークエラーや API エラーが発生しても、設計上フェイルセーフ（部分失敗を許容して継続）することがあります。ログを確認してください。
- DuckDB への大量插入は executemany を利用しています。空リストを渡すと一部 DuckDB バージョンでエラーになるため、内部でガードしています。

---

## 主要モジュールとディレクトリ構成

リポジトリの主要なディレクトリ/モジュール構成（src/kabusys を想定）:

- kabusys/
  - __init__.py
  - config.py
    - 環境変数 / .env の自動読み込みと Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py       — ニュースの LLM ベースセンチメント集約と ai_scores への書き込み
    - regime_detector.py — ETF MA + マクロニュースを組み合わせた市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存・リトライ・レート制御）
    - pipeline.py       — ETL パイプライン（run_daily_etl 等）
    - etl.py            — ETL 公開インターフェース（ETLResult 等）
    - news_collector.py — RSS 収集（SSRF対策・前処理・raw_news 保存）
    - quality.py        — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - calendar_management.py — マーケットカレンダー操作（営業日判定等）
    - audit.py          — 監査ログ（signal/order/execution）スキーマおよび初期化
    - stats.py          — 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー等

---

## 開発・テストのヒント

- 自動 .env ロードを無効にしてテスト用に環境を制御する:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- OpenAI / J-Quants 呼び出し部分は内部で専用のラッパー関数を使っているため、ユニットテストではこれらの内部呼び出しをモック（unittest.mock.patch）して API をスタブ化できます。news_nlp/regime_detector の _call_openai_api は差し替え可能です。

- DuckDB はインメモリ接続（":memory:"）に対応しているため、テスト時は一時的にメモリ DB を利用して高速に検証できます。

---

以上が README の概要です。必要であれば以下を追加で作成できます：
- コマンドラインツールやサンプルスクリプト（ETL ジョブ、ニュース収集ジョブ、監査DB初期化スクリプト）
- .env.example のテンプレート
- requirements.txt / pyproject.toml（依存管理）
- 実行例に基づくワークフロー図（ETL → ニュース NLP → レジーム判定 → 発注フロー）