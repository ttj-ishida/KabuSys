# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ集です。  
データ取得（J-Quants）、ETL、ニュースNLP（OpenAI）、市場レジーム判定、研究用ファクター計算、監査ログ（DuckDB）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような機能を持つモジュール群から構成される Python パッケージです。

- データ収集・ETL（J-Quants API 連携、DuckDB 保存）
- ニュース収集と LLM を用いた銘柄センチメント算出（gpt-4o-mini）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコアを合成）
- 研究用ユーティリティ（ファクター計算・特徴量解析・Zスコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（シグナル→発注→約定のトレーサビリティ、DuckDB スキーマ）

設計方針の一部:
- ルックアヘッドバイアスを排除（内部で date.today()/datetime.today() を直接参照しない）
- DuckDB を中心としたローカルデータ管理（ETL の冪等性を考慮）
- OpenAI / J-Quants 呼び出しはリトライ・バックオフ等を備えた安全実装
- 外部 API キーは環境変数 / .env で管理（自動ロード機構あり）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / 認証トークン更新・レート制御）
  - マーケットカレンダー管理（is_trading_day / next_trading_day / get_trading_days 等）
  - ニュース収集（RSS パーシング、SSRF 対策、前処理）
  - データ品質チェック（欠損、スパイク、重複、将来日付）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

---

## 要件（代表）

主な依存パッケージ（環境に応じて適宜調整してください）:

- Python 3.10+（型ヒントに依存）
- duckdb
- openai
- defusedxml

インストール例（pip）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはパッケージ配布用に setup/pyproject があれば:
# pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を用意、依存パッケージをインストールする。

2. 環境変数を用意する（.env または .env.local）。パッケージはプロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動で読み込みます（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

3. 必要な主要環境変数（例）
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

# OpenAI
OPENAI_API_KEY=sk-...

# kabuステーション（発注連携が必要な場合）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルト）

# Slack（通知等）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス（任意、デフォルト: data/kabusys.duckdb）
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development  # 有効値: development / paper_trading / live
LOG_LEVEL=INFO
```

.env 自動ロード優先度:
- OS 環境変数（既存の値） > .env.local > .env
- .env.local は .env の上書き（override=True）
- テストで自動ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## 使い方（簡単な例）

以下は基本的な操作例です。Python REPL / スクリプト内で実行します。

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
print(settings.env, settings.is_live)
```

- DuckDB 接続を開き ETL を実行（日次 ETL）
```python
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings
conn = duckdb.connect(str(settings.duckdb_path))
# target_date を指定しない場合は今日を対象（内部で営業日に調整）
result = run_daily_etl(conn)
print(result.to_dict())
```

- ニュースセンチメントのスコア算出
```python
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
# target_date はスコア生成日（news window は前日15:00 JST ～ 当日08:30 JST）
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from kabusys.config import settings
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化（監査専用 DB を作成してスキーマを適用）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って監査テーブルにアクセス可能
```

- マーケットカレンダーや営業日関数の利用例
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day
import duckdb
from datetime import date
conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- OpenAI の呼び出しは API キー（OPENAI_API_KEY）が必要です（引数で明示的に渡すことも可）。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必要です。
- ETL / API 呼び出しはネットワーク/課金が発生するため実行前に設定とコストを確認してください。

---

## ディレクトリ構成（主なファイル）

リポジトリの主要モジュール構成例:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                 — ニュース NLP（score_news）
    - regime_detector.py          — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py           — J-Quants API クライアント + 保存ロジック
    - pipeline.py                 — ETL パイプライン（run_daily_etl 等）
    - etl.py                      — ETL インターフェース再エクスポート
    - news_collector.py           — RSS 収集（SSRF 対策・正規化）
    - calendar_management.py      — マーケットカレンダー管理
    - quality.py                  — データ品質チェック
    - stats.py                    — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                    — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py          — ファクター計算（momentum / value / volatility）
    - feature_exploration.py      — 将来リターン計算・IC・統計サマリー
  - monitoring/ (予備: 監視用 DB / スクリプト用)
  - execution/ (実際の注文送信モジュールなど、外部実装を想定)
  - strategy/ (戦略実装用のインターフェース)

---

## 注意事項 / 運用上のポイント

- 環境（KABUSYS_ENV）:
  - 有効値: development / paper_trading / live
  - live 環境では発注等の重大操作に特別な注意が必要です。

- .env の自動読み込み:
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動で読み込みます。
  - テストや CI で自動ロードを防ぎたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- API の取り扱い:
  - OpenAI（gpt-4o-mini）呼び出しはコストとレート制限に注意してください。内部にリトライ・バックオフが組み込まれていますが、運用ではクォータ管理を行ってください。
  - J-Quants はレート制限を想定して実装済み（120 req/min）。認証はリフレッシュトークンを使用します。

- DuckDB スキーマの互換性:
  - 一部の実装は DuckDB のバージョン依存の挙動（executemany の空リストなど）を考慮しています。DuckDB のバージョンアップ時は動作確認を行ってください。

---

## 開発・テストのヒント

- テスト時に OpenAI 呼び出しをモックするには、モジュール内の _call_openai_api 関数を unittest.mock.patch で差し替えられるように実装しています（news_nlp / regime_detector）。
- .env の自動ロードを無効化してローカルテストを制御する:
```bash
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
pytest
```

---

## サポート / 貢献

- バグ報告・機能要望は Issue にてお願いします。
- コントリビュートの際はコードスタイルやテスト追加をお願いします。

---

以上が README の要点です。必要であれば、インストール用の requirements.txt やサンプル .env.example を追記したバージョンも作成できます。どの情報を追加したいか教えてください。