# KabuSys

日本株向け自動売買 / データプラットフォームライブラリ KabuSys の README（日本語）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・ETL、品質チェック、ファクター研究、ニュース NLP（LLM）によるセンチメント評価、マーケットレジーム判定、監査ログ（トレーサビリティ）などをまとめた内部ライブラリです。  
主にバックテスト・リサーチ・本番運用のデータ基盤とアルゴリズム層を想定しています。

主な設計方針：
- Look‑ahead bias を避ける（内部で date.today()/datetime.today() を直接使わない設計）
- DuckDB を中心としたローカルデータベース運用
- J-Quants API からの差分取得と冪等保存
- OpenAI（gpt-4o-mini 等）を用いたニュースの JSON モード評価（出力の検証付き）
- ETL／品質チェックは部分失敗を許容して継続（問題は収集して呼び出し側で判断）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 環境変数の必須チェック（settings オブジェクト経由）

- データ収集・ETL（kabusys.data）
  - J-Quants API クライアント（レート制御／リトライ／トークン自動更新）
  - 日次 ETL パイプライン（run_daily_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース RSS 収集（SSRF 対策・トラッキング除去・前処理）
  - データ品質チェック（欠損・重複・スパイク・日付整合性）
  - 監査ログテーブル/DB 初期化（init_audit_schema / init_audit_db）

- AI（kabusys.ai）
  - ニュース NLP：銘柄ごとのセンチメントスコア算出（score_news）
  - レジーム判定：ETF（1321）MA200乖離 + マクロニュースで日次レジーム判定（score_regime）
  - OpenAI 呼び出しは JSON Mode を前提にし、堅牢なリトライと検証を実装

- リサーチ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（calc_momentum, calc_value, calc_volatility）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化ユーティリティ

- 共通ユーティリティ
  - 統計ユーティリティ（zscore_normalize）
  - DuckDB を用いた効率的な SQL ベースの処理

---

## セットアップ手順

前提
- Python 3.10 以上（| 型注釈等を利用）
- DuckDB を利用可能な環境

推奨依存ライブラリ（最低限）：
- duckdb
- openai
- defusedxml

例：仮想環境作成・依存インストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# その他必要パッケージがあれば追加してください
```

パッケージを開発モードでインストールする（プロジェクトルートに pyproject.toml または setup.py がある場合）：
```bash
pip install -e .
```

環境変数 / .env
- プロジェクトルート（.git または pyproject.toml を基準）に `.env` と `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可能）。
- 必須の環境変数（代表例）:
  - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
  - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 呼び出し時に渡すことも可）
  - KABU_API_PASSWORD — kabuステーション API パスワード（使用する場合）
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知を使う場合
- データベースパス（任意）:
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB など。デフォルト data/monitoring.db）

例 .env（実プロジェクトでは秘密情報を入れないでください）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=...
DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
LOG_LEVEL=INFO
KABUSYS_ENV=development
```

---

## 使い方（主要な API の例）

以下はライブラリを利用する際の最小例です。DuckDB コネクションは `duckdb.connect()` で取得します。

1) 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

2) 日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースセンチメント（LLM）で銘柄別スコアを作成
```python
from kabusys.ai.news_nlp import score_news
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env の OPENAI_API_KEY が使われる
print(f"書き込み銘柄数: {n_written}")
```

4) 市場レジーム判定（1321ベース）
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

5) 監査ログ DB 初期化（監査専用 DB）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.duckdb")
# 以後 conn を監査ログ用に使う
```

6) リサーチ用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# records は [{"date": ..., "code": "XXXX", "mom_1m": ..., ...}, ...]
```

注意点
- score_news / score_regime は OpenAI API キーが必要です。api_key 引数で明示的に渡すか、環境変数 OPENAI_API_KEY を設定してください。
- 多くの関数は DuckDB の特定テーブル（raw_prices, raw_financials, raw_news, ai_scores, market_regime など）を前提とします。ETL を実行してスキーマ・データを準備してください。

---

## 自動環境読み込みの動作

- モジュールはプロジェクトルート（.git または pyproject.toml）を探索して `.env` と `.env.local` を自動読み込みします。
- 読み込み順序（優先度）:
  1. OS 環境変数（既存の環境変数は上書きされない）
  2. .env.local（存在する場合は上書き）
  3. .env（.env.local より下位）
- テスト等で自動読み込みを無効化するには環境変数を設定:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1

.env のパースはシェル風の形式（export KEY=VAL, コメント行, クォート・エスケープ処理）に対応しています。

---

## ディレクトリ構成

（コードベース内の主要ファイル・ディレクトリを抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境設定管理（settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP（score_news）
    - regime_detector.py — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch / save 系）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult 再エクスポート
    - calendar_management.py — 市場カレンダー管理
    - stats.py — 統計ユーティリティ（zscore_normalize）
    - quality.py — データ品質チェック
    - audit.py — 監査ログテーブル定義 / 初期化
    - news_collector.py — RSS ニュース収集（前処理・SSRF 対策）
  - research/
    - __init__.py
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / サマリー

各モジュールは DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理します。

---

## ロギングとモード

- settings.log_level でログレベルを制御できます（環境変数 LOG_LEVEL）。
- settings.env（KABUSYS_ENV）でモード（development / paper_trading / live）を指定。KABUSYS_ENV が不正な値の場合は例外が出ます。

---

## テストとモック

- OpenAI 呼び出しや外部ネットワーク呼び出しは内部で分離されており、ユニットテスト時には該当関数（例: kabusys.ai.news_nlp._call_openai_api, kabusys.data.news_collector._urlopen 等）をパッチしてモックできます。
- .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化できます。

---

## 貢献 / 開発メモ

- DuckDB の SQL 構文やバージョン依存の挙動（executemany の空リスト等）に注意して実装しています。
- LLM のレスポンスは厳密な JSON を期待しますが、実際のレスポンスに余計なテキストが混ざる場合を想定した復元処理と検証を実装しています。
- 監査ログは削除しない前提で設計されています（FK は ON DELETE RESTRICT）。

---

必要があれば、サンプル .env.example、requirements.txt、運用手順（cron ジョブ・systemd サービスの例）、または各モジュールの API リファレンスを追記します。どの情報を優先して追加しましょうか？