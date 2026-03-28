# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。ETL、ニュースNLP、ファクター研究、監査ログ、J-Quants / RSS クライアントなどを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を想定したモジュール群を含みます。

- J-Quants API からの株価・財務・マーケットカレンダー取得（レート制御・リトライ・トークン自動リフレッシュ）
- DuckDB を用いたデータ保存・ETL パイプライン（差分取得・バックフィル・品質チェック）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価と市場レジーム判定（JSON Mode を前提）
- 研究用ファクター計算（モメンタム／ボラティリティ／バリュー等）と統計ユーティリティ（Z-score 等）
- 監査ログ（signal → order → execution のトレーサビリティ）用スキーマ生成ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）

設計上のポイント:
- ルックアヘッドバイアスに配慮（内部で date.today()/datetime.today() を直接参照しない設計を意識）
- 冪等性（DB 保存は ON CONFLICT を使用）
- フェイルセーフ（外部 API 失敗時は処理継続、必要に応じてログ記録）
- 外部依存は最小限に（標準ライブラリ中心。DuckDB / OpenAI SDK / defusedxml 等は必要）

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl/run_prices_etl/run_financials_etl/run_calendar_etl）
  - J-Quants クライアント（fetch / save / get_id_token）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job）
  - ニュース収集（RSS → raw_news、SSRF 対策、前処理）
  - 品質チェック（missing_data / spike / duplicates / date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news: 銘柄ごとのニュースセンチメントを ai_scores に書き込み）
  - レジーム判定（score_regime: ETF 1321 の MA とマクロ記事の LLM センチメントを合成して market_regime に書き込み）
- research
  - ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 特徴量解析（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動読み込み（プロジェクトルートの `.env` / `.env.local` を探索して環境変数に設定）
  - Settings クラスで必要設定を取得

---

## セットアップ手順

前提:
- Python 3.10+（型注釈の union 型 `X | Y` を使用）
- DuckDB、OpenAI SDK、defusedxml 等が必要です

例: pip で最低限をインストールする
```
pip install duckdb openai defusedxml
```

開発環境でパッケージとして利用する場合（リポジトリルートで）:
```
pip install -e .
```
（setup / pyproject によるパッケージ化を想定）

環境変数設定:
- プロジェクトルート（このリポジトリのトップ）に `.env` または `.env.local` を置くと自動で読み込まれます。
- 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用等）。

主要な必須環境変数（Settings 参照）:
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネルID（必須）
任意・デフォルト:
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）（デフォルト: INFO）

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

依存ライブラリ（主要）:
- duckdb
- openai (OpenAI Python SDK)
- defusedxml

---

## 使い方（代表的な例）

以下は簡単な Python からの利用例です。すべて DuckDB 接続を引数に取るため、簡単にローカル DB と連携できます。

- DuckDB に接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 25))
print(result.to_dict())
```

- ニュースをスコアリングして ai_scores に保存する
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# api_key を明示するか、環境変数 OPENAI_API_KEY を設定する
n_written = score_news(conn, target_date=date(2026, 3, 25), api_key=None)
print(f"書き込んだ銘柄数: {n_written}")
```

- 市場レジームを判定して market_regime に書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 25), api_key=None)
```

- 監査ログ DB を初期化する（監査専用ファイル）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.db")
# テーブルが作成され、UTC タイムゾーンが設定されます
```

- 市場カレンダー関連ユーティリティ
```python
from kabusys.data.calendar_management import is_trading_day, next_trading_day

import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

ログ・環境:
- LOG_LEVEL と KABUSYS_ENV により挙動やログレベルが変わるため、デバッグ時は LOG_LEVEL=DEBUG を設定してください。

テスト時のヒント:
- 自動で .env をロードしたくないテストでは、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI API 呼び出し部分（news_nlp/_call_openai_api や regime_detector/_call_openai_api）は内部で分離されており、unittest.mock.patch で差し替えてモックにできます。

---

## ディレクトリ構成

以下はパッケージ内の主要ファイルとモジュール構成（抜粋）です。実際のリポジトリルートは `src/kabusys` を含みます。

- src/kabusys/
  - __init__.py
  - __version__ = "0.1.0"
  - config.py                      — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメントの取得と ai_scores 書き込み
    - regime_detector.py            — 市場レジーム判定（MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL 結果型エクスポート
    - calendar_management.py        — 市場カレンダー管理・バッチ
    - news_collector.py             — RSS 収集・前処理
    - quality.py                    — データ品質チェック
    - stats.py                      — 統計ユーティリティ（zscore_normalize）
    - audit.py                      — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            — ファクター計算（momentum/value/volatility）
    - feature_exploration.py        — 将来リターン・IC・統計サマリー
  - ai/__init__.py
  - research/__init__.py
  - data/etl.py

---

## 注意事項 / 運用上のポイント

- OpenAI API
  - gpt-4o-mini の JSON Mode を前提にレスポンス整形を期待しています。実稼働では API レートやコストに注意してください。
  - API 呼び出しはリトライロジックを備えていますが、quota・料金面は運用側で監視してください。

- J-Quants API
  - Rate limit（120 req/min）を守るため内部に固定間隔の RateLimiter を導入しています。
  - get_id_token は 401 に対してトークン自動リフレッシュします。環境変数 JQUANTS_REFRESH_TOKEN を設定してください。

- DuckDB スキーマ
  - 各保存関数は冪等設計（ON CONFLICT DO UPDATE）です。ETL を再実行しても上書き更新されますが、動作やデータ互換性には注意してください。

- セキュリティ
  - news_collector は SSRF 対策や XML パース防御（defusedxml）を行っています。ただし、追加のネットワーク制御（プロキシ、FW）を運用環境で検討してください。

---

## さらに詳しく / 開発

- ドキュメント中の関数 docstring に設計意図・注意点が書かれているため、実装変更や拡張の際は各モジュールの docstring を参照してください。
- テストでは外部 API 呼び出し（OpenAI / J-Quants / ネットワーク）をモックすることで高速に検証できます。特に news_nlp / regime_detector の _call_openai_api は差し替え可能です。

---

もし README に追加したいサンプルスクリプト（cron 用 ETL 実行例、CI 設定、DB スキーマ定義ファイル等）があれば教えてください。要望に合わせて追記します。