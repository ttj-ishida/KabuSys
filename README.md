# KabuSys

KabuSys は日本株のデータパイプライン、ファクター研究、AI によるニュースセンチメント評価、監査ログ・発注監視などを含む自動売買／リサーチ基盤です。本リポジトリは DuckDB をデータ基盤として用い、J-Quants / kabuステーション / OpenAI 等の外部 API と連携してデータ取得・品質チェック・特徴量算出・監査ログを行います。

主な設計方針の要点：
- ルックアヘッドバイアスを避ける（内部で date.today() を直接用いない等）
- DuckDB に対して冪等保存（ON CONFLICT / upsert）を行う
- OpenAI / J-Quants 等の呼び出しにリトライ / フェイルセーフを実装
- ETL・品質チェックは部分失敗でも他処理を継続する（全件収集型）

バージョン: 0.1.0

---

## 機能一覧

- データ収集（J-Quants）
  - 株価日足（OHLCV）取得 / 保存（fetch_daily_quotes / save_daily_quotes）
  - 財務データ取得 / 保存（fetch_financial_statements / save_financial_statements）
  - JPX マーケットカレンダー取得 / 保存（fetch_market_calendar / save_market_calendar）
- ETL パイプライン
  - run_daily_etl: カレンダー取得 → 株価取得 → 財務取得 → 品質チェック
  - 個別 ETL ジョブ（run_prices_etl / run_financials_etl / run_calendar_etl）
- データ品質チェック（quality）
  - 欠損・重複・スパイク・日付不整合の検出
- カレンダー管理（calendar_management）
  - 営業日判定 / 前後営業日の取得 / カレンダーの夜間更新ジョブ
- ニュース収集（news_collector）
  - RSS から記事収集・前処理・冪等保存・銘柄紐付け
  - SSRF / GzipBomb 等の防御実装
- AI モジュール（OpenAI）
  - ニュースごとのセンチメント算出（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）
  - OpenAI 呼び出しは JSON mode を使用しバリデーション済みレスポンスを期待
- 研究用ユーティリティ（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル DDL と初期化ユーティリティ
  - 監査DBの初期化関数 init_audit_db / init_audit_schema
- その他ユーティリティ
  - 環境設定管理（config.Settings）
  - J-Quants クライアント（jquants_client）
  - 汎用統計（data.stats.zscore_normalize）

---

## 前提・要件

- Python 3.10+
- duckdb（Python パッケージ）
- openai（openai SDK：モジュールは OpenAI クライアントを想定）
- defusedxml（RSS パース用）
- ネットワーク接続（J-Quants / OpenAI / RSS 等）
- J-Quants のリフレッシュトークン、OpenAI API キー、kabuステーション API のパスワード等の認証情報

（実行環境に合わせて requirements.txt を作成してください）

---

## 環境変数（重要）

KabuSys は .env / .env.local や OS 環境変数から設定を読み込みます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。主な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必要な場合）
- KABU_API_PASSWORD — kabu API のパスワード（必要な場合）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）

オプション / デフォルト:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_kabu_password
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成して有効化（例: python -m venv .venv / source .venv/bin/activate）
3. 必要なパッケージをインストール
   - 例: pip install duckdb openai defusedxml
   - 実運用向けには requirements.txt を用意して pip install -r requirements.txt
4. .env をプロジェクトルートに作成（上記の環境変数を設定）
5. DuckDB データベース初期化（任意）
   - 監査ログ用 DB 初期化例（Python REPL から）:
     ```
     import duckdb
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # conn を保存して使う
     ```
6. 自動 ETL / バッチは cron や Airflow 等から run_daily_etl を呼び出して運用します。

---

## 使い方（主要な呼び出し例）

以下は最小限のサンプルコード例です。実行前に環境変数を設定してください（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）。

- DuckDB 接続準備:
```
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL 実行:
```
from kabusys.data.pipeline import run_daily_etl

result = run_daily_etl(conn, target_date=None)  # target_date=None は今日
print(result.to_dict())
```

- ニュースのセンチメント算出（AI）:
```
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None で env を参照
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定:
```
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20))
```

- 研究モジュール（ファクター計算例）:
```
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
vol = calc_volatility(conn, target)
val = calc_value(conn, target)
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

- カレンダー操作:
```
from kabusys.data.calendar_management import is_trading_day, next_trading_day, prev_trading_day, get_trading_days
from datetime import date

d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

- 監査 DB の初期化（例）:
```
from kabusys.data.audit import init_audit_db
adb = init_audit_db("data/audit.duckdb")  # 親ディレクトリを自動作成
```

- 直接 J-Quants からデータ取得（テストや手動取得用）:
```
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements
from datetime import date

recs = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
print(len(recs))
```

注意:
- OpenAI を使う関数は api_key 引数を受け取ります（None の場合は環境変数 OPENAI_API_KEY を使用）。
- 各書き込み処理は冪等（既存行は更新）を意図していますが、実運用ではバックアップや監査ログ等の運用設計を行ってください。

---

## ディレクトリ構成（要約）

リポジトリの主要なモジュール配置（src/kabusys）:

- kabusys/
  - __init__.py (パッケージ公開)
  - config.py — 環境変数・設定管理（Settings）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントスコア（OpenAI 統合）
    - regime_detector.py — マーケットレジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得・保存）
    - pipeline.py — ETL パイプライン（run_daily_etl 等）
    - etl.py — ETLResult の再エクスポート
    - news_collector.py — RSS 収集・前処理
    - calendar_management.py — 市場カレンダー管理・営業日ロジック
    - quality.py — データ品質チェック
    - stats.py — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py — 監査テーブル DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - ai/（上記）
  - research/（上記）

各モジュールはコード内にドキュメンテーションと設計方針が豊富に書かれているため、実装の詳細は各ファイルの docstring を参照してください。

---

## 運用上の注意 / ベストプラクティス

- 本コードは実取引 API（kabuステーション）や外部資金・注文を扱う部分と切り離した設計を基本としていますが、実際に発注を行う際は十分なテスト・ロギング・モニタリング・オフライン検証を行ってください。
- OpenAI を使う際は API コストに注意し、バッチサイズや呼び出し頻度を管理してください（本実装はバッチとバックオフを備えています）。
- J-Quants のレート制限に対応するため内部でスロットリングを実装しています。大量取得は時間がかかる可能性があります。
- .env やプロダクション設定は機密情報を含むため、アクセス制御・シークレット管理（Vault 等）を推奨します。

---

この README はプロジェクトの概要と初期運用に必要な情報をまとめたものです。より詳細な API の使い方や DB スキーマ、運用手順は各モジュールの docstring と設計ドキュメント（DataPlatform.md / StrategyModel.md 想定）を参照してください。必要があれば README に追加したい項目（例: デプロイ手順、CI/CD、具体的な運用 runbook 等）を教えてください。