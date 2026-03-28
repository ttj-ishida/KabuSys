# KabuSys

日本株向けの自動売買／データ基盤ライブラリ KabuSys のリポジトリ向け README（日本語）。

概要、主な機能、セットアップ手順、簡単な使い方、ディレクトリ構成をまとめています。

注意: この README はコードベースから自動生成した説明を元にしています。実際の運用前に環境変数や API キーの管理、ネットワーク制約、実売買のリスクを十分に確認してください。

---

## プロジェクト概要

KabuSys は日本株のデータ収集（J-Quants）、ニュース収集・NLP、ファクター算出、ETL、監査ログ（発注／約定トレース）などを含むデータプラットフォーム／自動売買補助ライブラリです。DuckDB をデータストアとして用い、OpenAI（gpt-4o-mini 等）をニュースセンチメント解析に利用できます。

設計方針の一部:
- ルックアヘッドバイアス回避（内部で date.today() や datetime.today() を安易に参照しない）
- DuckDB を中心とした SQL + Python 実装
- 冪等性（ON CONFLICT / idempotent な保存）
- API 呼び出しに対する堅牢なリトライ・バックオフ処理
- テスト容易性（環境変数自動ロードの無効化フラグ等）

---

## 主な機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
  - settings オブジェクト経由で設定取得

- データ取得（J-Quants クライアント）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー取得
  - レートリミット制御・トークン自動リフレッシュ・ページネーション対応
  - DuckDB への冪等保存（save_* 関数）

- ETL パイプライン
  - 日次 ETL（run_daily_etl）: カレンダー・株価・財務の差分取得 + 品質チェック
  - 個別ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETLResult による実行結果の集約

- データ品質チェック
  - 欠損データ検出、スパイク検出、重複チェック、日付整合性チェック
  - QualityIssue オブジェクトで詳細を返す

- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存想定（保存処理は実装モジュールに依存）

- ニュース NLP（OpenAI）
  - 銘柄単位のニュース統合センチメント（score_news）
  - ニュースウィンドウやトークン肥大化対策、チャンク処理、JSON Mode を利用

- 市場レジーム判定
  - ETF (1321) の 200 日 MA 乖離とマクロニュースセンチメントを合成して日次レジーム判定（score_regime）
  - フェイルセーフ・リトライ・JSON 検証あり

- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Z スコア正規化

- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル DDL と初期化
  - init_audit_db で専用 DuckDB を初期化可能

---

## 必要環境 / 依存関係

- Python 3.10 以上（型アノテーションの | を使用）
- 主要パッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ: urllib, json, datetime, logging など

インストール時に requirements.txt を用意している場合はそちらを使ってください。ここでは主要パッケージの例を示します。

例:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （パッケージ一覧がある場合は pip install -r requirements.txt）

4. パッケージをインストール（開発モード）
   - pip install -e .

5. 環境変数の準備
   - プロジェクトルートに .env（または .env.local）を置くと、kabusys.config が自動で読み込みます（CWD に依存せず package 配布後も機能するように実装）。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...    （kabuステーションを使う場合）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO
   - 自動ロードを無効化したいテスト等では:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（簡単な例）

以下はライブラリの主要な公開 API を呼び出す基本的な例です。実際にはログ設定やエラーハンドリング、API キーの準備を行ってください。

- settings の参照（環境変数経由）
```python
from kabusys.config import settings
print(settings.duckdb_path)
```

- DuckDB 接続（デフォルト path は settings.duckdb_path）
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュースセンチメント計算（score_news）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# conn は DuckDB 接続
count = score_news(conn, target_date=date(2026, 3, 20))
print("Scored codes:", count)
```

- 市場レジーム判定（score_regime）
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
```

- 研究用ファクター計算
```python
from datetime import date
from kabusys.research.factor_research import calc_momentum

records = calc_momentum(conn, target_date=date(2026, 3, 20))
```

注意:
- OpenAI を使う関数（score_news, regime_detector）は OPENAI_API_KEY 環境変数、または api_key 引数が必要です。
- run_daily_etl は ETLResult を返します。品質チェックの結果やエラーは ETLResult 内に格納されます。

---

## 環境変数自動ロードの挙動

- 自動的にプロジェクトルートを探索して `.env` と `.env.local` を読み込みます（優先度: OS 環境 > .env.local > .env）。
- プロジェクトルートの判定は .git または pyproject.toml に依存します。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト用途など）。

---

## 開発・テストのヒント

- OpenAI 呼び出しや外部 API をテストする際は、モジュール内の HTTP 呼び出しや _call_openai_api、_urlopen 等をモックしてください（コード内で差し替えが想定されています）。
- settings の自動ロードを無効にして、テスト用の環境変数を明示的に設定すると安定します。
- DuckDB のインメモリ接続（":memory:"）を使うと簡単にユニットテストを行えます。

---

## ディレクトリ構成（主要ファイルの説明）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数管理・settings オブジェクト
  - ai/
    - __init__.py
    - news_nlp.py
      - score_news: ニュースのセンチメント算出と ai_scores テーブル書き込み
      - calc_news_window 等
    - regime_detector.py
      - score_regime: マクロ＋MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API との通信・保存ロジック（fetch / save_*）
    - pipeline.py
      - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl, ETLResult
    - etl.py
      - ETLResult の公開エイリアス
    - calendar_management.py
      - 市場カレンダー管理・営業日判定（is_trading_day / next_trading_day 等）
    - stats.py
      - zscore_normalize 等の統計ユーティリティ
    - quality.py
      - データ品質チェック（missing, spike, duplicates, date consistency）
    - audit.py
      - 監査ログ用 DDL / init_audit_db
    - news_collector.py
      - RSS 取得、前処理、SSRF 対策
  - research/
    - __init__.py
    - factor_research.py
      - calc_momentum, calc_value, calc_volatility
    - feature_exploration.py
      - calc_forward_returns, calc_ic, factor_summary, rank
  - (その他) strategy, execution, monitoring パッケージのプレースホルダがある想定（__all__ 参照）

---

## ライセンス・注意事項

- 本プロジェクトのライセンスはリポジトリに従ってください（README には明示されていません）。
- 本ソフトウェアを使用して実際の金銭取引を行う場合、法令順守、個別証券会社の API 制約、実行ミスによる損失リスクについて十分に検討・テストを行ってください。
- API キーやシークレット情報はソース管理に含めないこと。運用環境では適切なシークレット管理を行ってください。

---

もし README に追記してほしい具体的な内容（例: 実行可能な CLI、追加の example スクリプト、requirements.txt の内容、ライセンス情報）があれば教えてください。必要に応じてサンプル .env.example も作成します。