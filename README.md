# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants と kabuステーション、OpenAI を連携し、
データ ETL、ニュース NLP、マーケットレジーム判定、リサーチ向けファクター計算、
監査ログ（発注／約定トレース）などを提供します。

主な用途：
- 日次 ETL（株価、財務、カレンダー）の取得・保存・品質チェック
- RSS ニュース収集と LLM を使った銘柄別センチメント付与
- マクロ + テクニカルを使った市場レジーム判定（bull/neutral/bear）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- 監査用テーブル（signal / order_request / executions）の初期化と運用補助

バージョン: 0.1.0

---

## 機能一覧（概要）

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動ロード（無効化可）
  - 必須環境変数のアクセス（settings オブジェクト）

- データ ETL（kabusys.data.pipeline）
  - J-Quants から差分取得（株価/財務/カレンダー）
  - DuckDB へ冪等保存（ON CONFLICT）
  - 品質チェック（欠損・重複・スパイク・日付不整合）

- J-Quants クライアント（kabusys.data.jquants_client）
  - レートリミッタ、リトライ、トークン自動更新
  - fetch / save 系ユーティリティ

- ニュース収集（kabusys.data.news_collector）
  - RSS から記事を取得・前処理・保存（raw_news）
  - SSRF 対策、サイズ上限、URL 正規化、記事 ID の SHA-256（先頭32文字）使用

- ニュース NLP（kabusys.ai.news_nlp）
  - gpt-4o-mini を用いた銘柄ごとのセンチメント付与（ai_scores に保存）
  - バッチ処理、JSON Mode、リトライ・検証ロジック

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成
  - OpenAI 呼び出しのリトライ・フォールバック実装

- リサーチ（kabusys.research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン、IC（Spearman）計算、Zスコア正規化等

- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions の DDL と初期化ユーティリティ
  - init_audit_db / init_audit_schema による冪等初期化

---

## セットアップ

必要条件（代表例）
- Python 3.10+（型注釈に union | を多用）
- パッケージ依存（主なもの）:
  - duckdb
  - openai
  - defusedxml

インストール（開発環境での例）:
```bash
# プロジェクトルートで
pip install -e .[dev]   # setup がある場合。なければ個別に duckdb, openai, defusedxml 等を pip install
```

環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: Slack 通知用 bot トークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
- KABUSYS_ENV: "development" / "paper_trading" / "live"（省略時 development）
- LOG_LEVEL: "DEBUG"/"INFO"/...（省略時 INFO）
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: デフォルト `data/monitoring.db`

.env の自動読み込み
- パッケージはプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、
  `.env` と `.env.local` を自動ロードします（OS 環境変数優先）。
- 自動ロードを無効化する場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

サンプル .env (README に例示)
```
JQUANTS_REFRESH_TOKEN=xxxx
KABU_API_PASSWORD=yyyy
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
```

---

## 使い方（簡単なコード例）

以下は Python REPL / スクリプト上での例です。DuckDB 接続は kabusys.data.jquants_client を使った ETL や
kabusys.ai.* の関数に直接渡します。

1) DuckDB 接続を作り ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成する（OpenAI API キーは環境変数 OPENAI_API_KEY、もしくは引数で指定）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定を行う
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit_duckdb.kdb")
# 初期化済み conn を使ってアプリケーション側で監査テーブルを利用
```

5) 設定値にアクセスする例
```python
from kabusys.config import settings
print(settings.jquants_refresh_token)
print(settings.duckdb_path)      # pathlib.Path
print(settings.is_live)
```

注意点：
- OpenAI 呼び出しはネットワーク・レートの影響を受けます。score_news / score_regime は内部でリトライやフォールバックを実装していますが、API キーや課金枠に注意してください。
- run_daily_etl 等は内部で date.today() を使う箇所があります（ETL の実行日取得等）。分析やバックテストでは明示的に target_date を渡すことを推奨します。

---

## ディレクトリ構成（主要ファイルと役割）

src/kabusys/
- __init__.py
- config.py
  - 環境変数読み込み、settings オブジェクトの提供（自動 .env ロード）
- ai/
  - __init__.py (score_news エクスポート)
  - news_nlp.py: ニュースの LLM スコアリング（銘柄別 ai_scores 書き込み）
  - regime_detector.py: マクロ + MA による市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得/保存/認証/レート制御）
  - pipeline.py: ETL パイプライン（run_daily_etl 等）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS 収集・前処理
  - calendar_management.py: 市場カレンダー管理 / 営業日判定 / calendar_update_job
  - stats.py: zscore_normalize 等の汎用統計ユーティリティ
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py: 監査ログ用 DDL と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py: calc_momentum / calc_value / calc_volatility
  - feature_exploration.py: calc_forward_returns / calc_ic / factor_summary / rank
- ai/（トップで触れた）
- research/（上記）

各モジュールは「DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）」を受け取る設計が多く、DB 層を疎結合に保ちます。

---

## 設計上の注記 / 運用注意

- Look-ahead bias 対策が随所に組み込まれています（target_date 未満のみ参照、fetch 時の fetched_at 記録等）。
- 外部 API 呼び出しはリトライ & フェイルセーフ（多くはフォールバック値で継続）を採用しています。重大なデータ欠損は品質チェックで検出できます。
- news_collector は SSRF・XML 攻撃・サイズ DoS 対策を実装していますが、RSS の任意実行環境では追加の防御（ネットワーク分離等）を推奨します。
- DuckDB の executemany 周りでバージョン依存の制約があるため、空のパラメータ群を渡さないよう実装されています（pipeline 等で配慮済み）。

---

必要な情報や追加の利用例（例: Slack 通知連携・kabuステーションの注文実行フロー等）を README に追記したい場合は、どの部分を詳しく書くか教えてください。