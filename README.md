# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータプラットフォームと自動売買基盤のライブラリ群です。  
ETL（J-Quants 経由の株価・財務・カレンダー取得）、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

---

## 特徴（機能一覧）

- ETL パイプライン
  - 日次 ETL（株価、財務、マーケットカレンダーの差分取得・保存）
  - 差分更新／バックフィル／ページネーション対応
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- データ連携（J-Quants クライアント）
  - 株価日足、財務データ、JPX カレンダー、上場銘柄情報の取得
  - レートリミット、リトライ、トークン自動リフレッシュ対応
  - DuckDB への冪等保存（ON CONFLICT）

- ニュース収集・NLP
  - RSS 収集（SSRF/サイズ制限/トラッキング除去等の安全対策）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）生成
  - マクロニュースを用いた市場レジーム判定（ETF 1321 + LLM 合成）

- リサーチ支援
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー
  - Zスコア正規化ユーティリティ

- データ品質 & カレンダー管理
  - market_calendar を用いた営業日判定（next/prev/get_trading_days 等）
  - calendar_update_job による夜間カレンダー更新

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブルによる監査
  - 監査 DB 初期化ユーティリティ（DuckDB）

---

## 前提（Prerequisites）

- Python >= 3.10
- 必要パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- J-Quants API のリフレッシュトークン
- OpenAI API キー（ニュース NLP / レジーム判定で使用）
- （任意）kabu API のパスワード（発注機能を利用する場合）
- SQLite（監視用など）や DuckDB を格納するファイル用の書き込み権限

推奨: 仮想環境（venv / poetry / pipx 等）を使用してください。

---

## インストール（例）

1. 仮想環境作成・有効化
   - python -m venv .venv && source .venv/bin/activate

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

（プロジェクトに requirements.txt / pyproject.toml があればそちらを使用してください）

---

## 環境変数（設定）

設定は .env または OS 環境変数から読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われ、優先順位は OS 環境変数 > .env.local > .env です。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（ライブラリ内部で必須チェックあり）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード（発注機能がある場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID

任意（デフォルトあり／OpenAI は関数引数で渡すことも可能）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite ファイルパス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）

例 .env（簡易）
JQUANTS_REFRESH_TOKEN=xxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（主要な利用例）

以下はライブラリ内の主要関数の利用例です。DuckDB 接続は duckdb.connect(path) で作成します。

- 日次 ETL を実行する
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント（ai_scores）を生成する
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print("written:", n_written)
```

- 市場レジーム（market_regime）をスコアリングする
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

- 監査ログ用 DuckDB の初期化
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

- カレンダー・営業日ユーティリティ
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print("is trading:", is_trading_day(conn, d))
print("next trading:", next_trading_day(conn, d))
```

- リサーチ機能（ファクター計算等）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
date0 = date(2026, 3, 20)
mom = calc_momentum(conn, date0)
val = calc_value(conn, date0)
vol = calc_volatility(conn, date0)
```

注意:
- OpenAI 呼び出しを行う関数は api_key 引数でキーを渡すことができます（引数優先）。引数が None の場合は環境変数 OPENAI_API_KEY を参照します。
- 多くの関数は DuckDB の既存テーブル（raw_prices, raw_financials, raw_news, news_symbols, ai_scores, market_regime 等）を前提としています。スキーマ初期化は別途行ってください。

---

## 典型的なワークフロー

1. .env を用意して必要な API キーを設定する
2. DuckDB を用意（デフォルト: data/kabusys.duckdb）
3. 初回は run_daily_etl を実行してデータを投入
4. 定期的に（夜間） run_daily_etl を cron などで実行
5. 毎朝ニューススコア（score_news）・レジーム判定（score_regime）を実行
6. 監査ログ（init_audit_db）を初期化して、戦略→発注→約定のトレースを保存

---

## ディレクトリ構成（主なファイルと説明）

プロジェクトの主要モジュール構成（src/kabusys 配下）:

- __init__.py
  - パッケージ情報（__version__）や主要サブパッケージの公開設定

- config.py
  - 環境変数読み込み・設定管理（.env 自動読み込み、Settings クラス）

- ai/
  - __init__.py
  - news_nlp.py — ニュースの NLP スコアリング、OpenAI 呼び出し・バッチ処理・レスポンス検証
  - regime_detector.py — ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して市場レジーム判定

- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）、ETLResult 定義
  - etl.py — ETL の公開インターフェース（ETLResult の再エクスポート）
  - calendar_management.py — マーケットカレンダー管理・営業日判定・calendar_update_job
  - news_collector.py — RSS フィード収集・前処理・raw_news 保存
  - stats.py — 汎用統計ユーティリティ（zscore_normalize）
  - quality.py — データ品質チェック（欠損/スパイク/重複/日付不整合）
  - audit.py — 監査ログ用テーブル定義・初期化ユーティリティ

- research/
  - __init__.py — 研究用ユーティリティの公開（calc_momentum 等）
  - factor_research.py — Momentum / Volatility / Value 等の計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク関数

---

## 開発・デバッグのヒント

- 自動環境変数読み込みを無効にしてテストしたい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してから import してください。

- OpenAI / J-Quants をテストでモックする:
  - モジュール内で API 呼び出しにラッパー関数を使っているため、unittest.mock.patch で差し替えが容易です（例: kabusys.ai.news_nlp._call_openai_api）。

- DuckDB の挙動（executemany の空リスト受け入れなど）に依存する箇所があるため、DuckDB バージョンに注意してください。

---

## ライセンス / 責務

この README はコードベースの説明を目的としています。実際の運用では API キーの管理、取引リスク、レギュレーション（金融商品取引法等）の遵守を必ず行ってください。発注機能を有効にする前にテスト環境（ペーパートレード）で十分な検証を行ってください。

---

必要があれば README にサンプル .env.example、requirements.txt、または CI / cron での実行例（systemd unit / GitHub Actions 等）を追加します。どの情報を優先して追記しますか？