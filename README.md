# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買のユーティリティ群。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・特徴量解析、監査ログ/トレーサビリティ、マーケットカレンダー管理などを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスに配慮（内部で date.today() を直接参照しない等）
- DuckDB を用いたローカルデータストア
- API 呼び出しは再試行/指数バックオフ・レート制限を備える
- 冪等性・監査・データ品質チェックを重視

---


## 機能一覧

- 環境変数 / .env 自動読み込みと設定管理（kabusys.config）
  - 自動ロードはプロジェクトルート（.git / pyproject.toml）を基準に行う
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能

- データETL（kabusys.data.pipeline）
  - J-Quants API から株価（日次OHLCV）・財務データ・市場カレンダーを差分で取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行
  - ETL 実行結果を ETLResult オブジェクトで返す

- J-Quants クライアント（kabusys.data.jquants_client）
  - API トークン自動リフレッシュ、レート制限、リトライ、ページネーション対応
  - DuckDB への冪等保存関数（raw_prices, raw_financials, market_calendar 等）

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を収集、前処理、ID生成、SSRF / Gzip / XML 攻撃対策など安全対策を考慮

- ニュースNLP（kabusys.ai.news_nlp）
  - OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出し ai_scores テーブルへ保存
  - バッチ・チャンク処理、レスポンス検証、リトライを実装

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して market_regime を算出

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
  - z-score 正規化ユーティリティ（kabusys.data.stats）

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - DB と曜日フォールバックを併用した営業日判定、next/prev_trading_day、SQ判定、カレンダー更新ジョブ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions を含む監査スキーマを初期化・管理
  - 監査用 DuckDB 初期化ユーティリティ

- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付不整合を検出し QualityIssue を返す

---


## 要求環境 / 依存関係

- Python 3.10 以上（PEP604 の型表記を使用）
- 必要な主要パッケージ（一例）:
  - duckdb
  - openai
  - defusedxml

実行環境に応じて他の標準ライブラリを使用します（urllib 等）。プロジェクトでは各種依存を requirements.txt にまとめている想定です。

---


## セットアップ手順

1. リポジトリをクローン / ソースを配置

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   もし requirements.txt が無い場合は最低以下を入れてください:
   - pip install duckdb openai defusedxml

4. 環境変数の設定
   - プロジェクトルートに .env を配置すると、自動で読み込まれます（kabusys.config）。
   - 自動読み込みを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

環境変数の例（.env）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# kabuステーション API
KABU_API_PASSWORD=your_kabu_api_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-xxxx...

# Slack
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# システム設定
KABUSYS_ENV=development  # development|paper_trading|live
LOG_LEVEL=INFO

# DB パス（省略時 data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

必須環境変数（実行する機能により変わります）:
- JQUANTS_REFRESH_TOKEN
- OPENAI_API_KEY（AI モジュールを使う場合）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）
- KABU_API_PASSWORD（発注連携をする場合）

---


## 使い方（基本例）

以下は Python REPL / スクリプトから各主要 API を呼ぶ例です。

- DuckDB 接続の作成（デフォルトパスは settings.duckdb_path）:

```python
from pathlib import Path
import duckdb
from kabusys.config import settings

db_path = settings.duckdb_path  # Path オブジェクト
conn = duckdb.connect(str(db_path))
```

- 日次 ETL を実行する（データ取得・保存・品質チェック）:

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定（省略時は今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアを生成（OpenAI が必要）:

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"ai_scores に書き込んだ銘柄数: {n_written}")
```

- 市場レジーム判定（1321 MA とマクロニュースの合成）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに結果が保存されます
```

- 監査ログ用 DB の初期化:

```python
from kabusys.data.audit import init_audit_db
from pathlib import Path

audit_db_path = Path("data/audit.duckdb")
audit_conn = init_audit_db(audit_db_path)
# init_audit_db はテーブル定義とインデックスを作成します
```

- RSS フィードの取得（ニュース収集の一部）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
for a in articles[:5]:
    print(a["id"], a["datetime"], a["title"])
```

注意点:
- AI 関連関数は OPENAI_API_KEY を環境変数に設定するか、関数引数で api_key を渡してください。
- ETL / 保存処理は DuckDB 内のスキーマ（raw_prices / raw_financials / market_calendar 等）を前提とします。スキーマ作成ユーティリティが別にある想定です（schema 初期化処理を実行してください）。

---


## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込み、Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント生成（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py                   — ETL パイプライン / run_daily_etl
    - etl.py                        — ETL API 再エクスポート（ETLResult）
    - news_collector.py             — RSS 取得・前処理・安全対策
    - calendar_management.py        — 市場カレンダー管理・営業日判定
    - stats.py                      — z-score などの統計ユーティリティ
    - quality.py                    — データ品質チェック
    - audit.py                      — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py            — momentum / value / volatility
    - feature_exploration.py        — forward returns / IC / factor summary

上記以外に strategy / execution / monitoring 等のサブパッケージが想定されており、将来的に取引ロジックや注文実行、監視機能を統合できます（kabusys.__all__ にて公開）。

---

## 運用上の注意・設計に関するポイント

- ルックアヘッドバイアス対策
  - 多くのモジュールは内部で datetime.today() を直接参照せず、外部から target_date を渡す設計です。バックテストや再現性のために必ず target_date を明示して利用してください。

- 冪等性
  - DB 保存関数は可能な限り ON CONFLICT / INSERT ... DO UPDATE を用いて冪等に動作します。ETL を複数回実行しても重複や二重保存が起きにくい設計です。

- エラー耐性
  - 外部 API 呼び出しはリトライ・指数バックオフ・フェイルセーフ（失敗時はスキップして続行）を組み込んでいます。重大なエラーはログに記録され ETLResult.errors に集約されます。

- セキュリティ
  - news_collector は SSRF / XML Bomb / Gzip Bomb 等の対策を実装しています。
  - API トークンは環境変数で管理してください。

---

## サポート / テスト

- テストや CI の実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env ロードを無効化できます（テスト中に環境を管理しやすくするため）。
- OpenAI 呼び出し等は内部で _call_openai_api をラップしているので、ユニットテストではこの関数をモックして外部通信を防げます。

---

必要であれば README に以下を追加できます：
- 具体的なテーブル定義（DDL）の一覧
- example .env.example ファイル
- CI / GitHub Actions 用のサンプル
- 開発者向けコントリビュート手順

追加希望があれば伝えてください。