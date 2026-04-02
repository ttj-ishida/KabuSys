# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README です。  
このリポジトリはデータ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ファクター/リサーチ、監査ログ・発注監視などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けのアルゴリズム取引プラットフォーム／データ基盤のコンポーネント群です。主な目的は以下です。

- J-Quants API を用いた株価・財務・マーケットカレンダーの差分ETL
- ニュースRSSの収集と前処理、OpenAI を用いた記事ベースのセンチメント算出
- 市場レジーム判定（MA とマクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量探索
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（シグナル→発注→約定のトレース）用のスキーマ初期化ユーティリティ
- DuckDB を用いたローカル DB 保存

設計上の特徴として、ルックアヘッドバイアス回避や API のリトライ／レートリミット、冪等保存（ON CONFLICT）等を重視しています。

---

## 主な機能一覧

- data
  - ETL：run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl
  - J-Quants クライアント（fetch_* / save_*）
  - カレンダ管理（is_trading_day / next_trading_day / prev_trading_day / get_trading_days）
  - ニュース収集（RSS 取得・前処理・raw_news 挿入補助）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI API 呼び出しはリトライや JSON モードを想定した実装
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー
- monitoring / execution / strategy
  - パッケージ公開インターフェースに含まれる（コードベースから将来的な発注/監視機能を想定）
- config
  - .env 自動ロード（プロジェクトルートを .git / pyproject.toml で検出）
  - 環境変数の取得ラッパー（settings）

---

## 必要な環境変数（主なもの）

以下は本ライブラリの主要機能で使用される環境変数例です。`.env` または `.env.local` に設定してください。

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL — kabu API のベース URL（省略可、デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack 通知先チャンネル ID（必須）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス（デフォルト data/execution.pid）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 等で使用）
- KABUSYS_ENV — environment (development / paper_trading / live)。不正値はエラー
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

テスト等で自動で .env を読み込ませたくない場合:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## セットアップ手順

1. リポジトリをチェックアウトし、開発用の Python 仮想環境を作成・有効化します。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 必要なパッケージをインストールします（例: pip）。

   pip install duckdb openai defusedxml

   ※ 実行環境に応じて追加でインストールが必要になる場合があります（例: slack SDK 等）。  
   プロジェクトの packaging/requirements が別にある場合はそちらを参照してください。

3. .env ファイルを作成します（プロジェクトルート）。最低限必要なキー例:

   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=CHXXXXXXX
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO

   ※ .env.local を用いれば OS 環境変数より優先して上書きできます。

4. データ保存先ディレクトリを作成（必要なら）:

   mkdir -p data

---

## 使い方（主なユーティリティの例）

以下は主要関数の呼び出し例です。DuckDB 接続は duckdb.connect() で生成して渡します。

- 日次 ETL（株価・財務・カレンダー・品質チェック）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースの NLP スコアリング（OpenAI を使用）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key=None で動作
n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n}")
```

- 市場レジーム判定

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（監査専用 DB を作る場合）

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# conn に対してアプリ側で order_requests 等を書き込めます
```

- カレンダー判定

```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026,3,20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意:
- 各処理はルックアヘッドバイアスを避けるため内部で date.today() を不用意に参照しない設計です（target_date を明示することを推奨します）。
- OpenAI 呼び出し部分は API エラー時にフォールバック／リトライを行いますが、APIキーの設定は必須です。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 内の主要モジュールと役割です（抜粋）。

- src/kabusys/__init__.py
- src/kabusys/config.py
  - 環境変数・.env 自動ロード、settings オブジェクト
- src/kabusys/ai/
  - news_nlp.py — ニュースの集合的センチメント算出と ai_scores テーブルへの書き込み
  - regime_detector.py — ETF 1321 の MA とマクロセンチメントを合成した市場レジーム判定
- src/kabusys/data/
  - pipeline.py — 日次 ETL のメインロジック（run_daily_etl 等）
  - jquants_client.py — J-Quants API の fetch/save 実装（ページネーション・リトライ・レート制御）
  - news_collector.py — RSS 取得、前処理、raw_news への保存補助
  - calendar_management.py — JPX カレンダー管理・営業日判定
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログ（signal_events / order_requests / executions）の DDL と初期化
  - stats.py — zscore_normalize 等の汎用統計ユーティリティ
  - etl.py — ETLResult の再エクスポート
- src/kabusys/research/
  - factor_research.py — モメンタム / バリュー / ボラティリティの計算
  - feature_exploration.py — 将来リターン、IC 計算、統計サマリー
  - __init__.py — 研究向け API の公開

---

## テスト・開発時のポイント

- 環境変数の自動ロードは config.py 内でプロジェクトルート (.git / pyproject.toml) を探索して .env / .env.local を読み込みます。テスト中に自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI 呼び出しや RSS 取得はネットワーク IO を伴うため、ユニットテスト時は該当関数（_call_openai_api, _urlopen 等）をモックしてください。ソース内に注入しやすい設計（モジュール内関数をパッチ）になっています。
- DuckDB の executemany は空リストを渡せないバージョンがあるため、実装は空チェックを行っています。DuckDB のバージョン差異に注意してください。

---

## ライセンス / 免責

本 README はコードベースの説明を目的としています。実運用（特に live モード）は十分なテストと運用上の安全対策（資金管理、レート制限、例外処理、監査）を行った上で実行してください。KabuSys 自体には取引の責任や法的助言は含まれません。

---

必要であれば、README に実際の .env.example、requirements.txt、実行スクリプト例（cron / systemd ユニット）や運用チェックリストを追加できます。どの情報を優先して追加しますか？