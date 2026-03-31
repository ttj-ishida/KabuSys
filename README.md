# KabuSys

KabuSys は日本株のデータプラットフォーム・研究・AIスコアリング・監査ログ・ETL を含む自動売買支援ライブラリです。J-Quants / JPX データの取得、ニュースの収集・NLP スコアリング、ファクター計算、ETL パイプライン、監査ログ（発注〜約定のトレーサビリティ）などを提供します。

主な設計方針は「ルックアヘッドバイアスの排除」「冪等性」「フェイルセーフ（部分失敗時も継続）」「外部 API の堅牢なリトライ/レート制御」です。

バージョン: 0.1.0

---

## 機能一覧

- 環境設定管理
  - .env / .env.local 自動読み込み（プロジェクトルート検出）
  - 必須環境変数の検証
- データ取得・ETL（J-Quants API）
  - 日次株価（OHLCV）取得・保存（ページネーション対応、冪等保存）
  - 財務データ取得・保存（四半期 BS/PL）
  - JPX マーケットカレンダー取得・保存
  - ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損データ検出、スパイク検出、重複検出、日付整合性チェック
- ニュース収集・NLP
  - RSS フィード取得（SSRF 対策、トラッキング除去、前処理）
  - OpenAI（gpt-4o-mini）による銘柄別ニュースセンチメント（ai_scores へ保存）
  - マクロニュースを使った市場レジーム判定（ma200 + macro sentiment）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルの初期化
  - 監査用 DB 初期化ユーティリティ（UTC タイムスタンプ、冪等）

---

## 動作要件

- Python 3.10 以上（型表記に | が使われています）
- 推奨パッケージ（主要依存）
  - duckdb
  - openai
  - defusedxml

requirements.txt の例（プロジェクトルートに作成して利用してください）:
```
duckdb
openai
defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン／取得
   - pip install -e . を前提にパッケージ化している場合はプロジェクトルートでインストールできます。

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Unix/macOS)
   - .venv\Scripts\activate     (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml

4. 環境変数を設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

例: .env.example
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# kabuステーション（必要に応じて）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# OpenAI
OPENAI_API_KEY=sk-...

# Slack（通知用）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB パス等
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# システム
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意:
- Settings により JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD 等は必須としている箇所があります。設定漏れは ValueError を投げます。

---

## 使い方（主な API 例）

以下は Python から直接呼ぶ例です。duckdb 接続はパスを指定して接続してください。

1) DuckDB に接続する
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

2) 日次 ETL を実行する（データ取得・保存・品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

# target_date を省略すると今日を基準に処理します
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

3) ニュースのスコアリング（ai_scores に書き込む）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

# OPENAI_API_KEY は環境変数か api_key 引数で指定
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"書込銘柄数: {n}")
```

4) 市場レジーム判定（market_regime に書き込む）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

r = score_regime(conn, target_date=date(2026, 3, 20))
print("完了:", r)
```

5) 監査ログ DB を初期化する（監査専用 DuckDB を作る）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# これで signal_events / order_requests / executions 等が作成されます
```

6) 研究用ファクター計算
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

---

## 注意事項 / トラブルシューティング

- 環境変数が不足していると Settings のプロパティ呼び出しで ValueError が発生します。エラーメッセージに従って .env を作成してください。
- OpenAI 呼び出しは外部 API を使用するためコストとレート制限に注意してください。ライブラリ側でリトライ・バックオフは実装されていますが、API キーの管理は利用者側で行ってください。
- J-Quants API もレート制限・認証トークンの有効期限等があります。get_id_token / _request で自動リフレッシュを試みますが、credentials の管理は利用者の責任です。
- RSS フィード取得時は SSRF 対策やコンテンツサイズ制限が実装されています。fetch_rss は拒否される URL があることに注意してください。
- DuckDB の executemany はバージョンによって空リストの扱いが異なる場合があるため、コード内では空チェックが入っています。

---

## 主要ディレクトリ / ファイル構成

- src/kabusys/
  - __init__.py
  - config.py
    - 環境設定・.env 自動ロードロジック・Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメント（OpenAI 呼び出し、ai_scores 書き込み）
    - regime_detector.py  — ETF(1321) MA200 とマクロセンチメントを合成して market_regime 判定
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py         — ETL（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - news_collector.py   — RSS 取得・前処理・raw_news 保存
    - quality.py          — 品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py            — zscore_normalize 等共通統計ユーティリティ
    - calendar_management.py — マーケットカレンダー管理（is_trading_day 等）
    - audit.py            — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py  — モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - ai, data, research 以下にユーティリティや主要処理が実装されています。

---

## 開発・テスト

- 自動環境変数読み込みはデフォルトで有効です。ユニットテスト環境などで自動読み込みを無効にしたい場合は環境変数:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- OpenAI 呼び出しや外部ネットワークを使う部分はモック化してテストすることが想定されています（コード内で差し替え可能なヘルパー関数を用意）。

---

## ライセンス / 貢献

本リポジトリはプロジェクト方針に沿って拡張・保守してください。外部ライブラリや API の利用規約に従って利用してください。

---

README は以上です。必要であれば以下の補足を追加します:
- 詳細な .env.example（全項目）
- 実行スクリプト例（cron / systemd / Docker）
- テーブルスキーマ一覧（raw_prices, raw_financials, market_calendar, ai_scores 等）