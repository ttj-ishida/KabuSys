# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ収集）、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株投資戦略のための以下機能群を提供します。

- J-Quants API を用いた株価・財務・カレンダー等の差分 ETL パイプライン
- RSS ベースのニュース収集と記事前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini）を利用したニュースセンチメント（銘柄別）スコアリング
- ETF とマクロニュースを組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算（Momentum / Value / Volatility 等）とリサーチ用ユーティリティ
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- 監査ログ用テーブルと初期化ユーティリティ（信頼性の高い発注トレーサビリティ）
- 環境設定は .env または環境変数で管理（プロジェクトルート自動検出）

設計上の重要点:
- ルックアヘッドバイアスを避けるために内部で date.today() 等の参照を最小化
- DuckDB をデータ保存基盤として使用（ローカルファイル / インメモリ）
- 冪等性を重視（DB 保存は基本 ON CONFLICT / DELETE→INSERT 等で上書き制御）
- ネットワーク/API 呼び出しはリトライ・バックオフ・レート制限を備える

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save のセット）
  - カレンダー管理（営業日判定、next/prev trading day）
  - ニュース収集（RSS 取得・前処理・raw_news への保存ロジック）
  - データ品質チェック（missing, spike, duplicates, date_consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計（zscore_normalize）
- ai/
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量評価ユーティリティ（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - Settings クラス（環境変数の読み込みと検証、自動 .env ロード）

---

## セットアップ手順

前提:
- Python 3.10 以上（ソースに 3.10 の型構文（`|`）を使用）
- DuckDB（Python パッケージ：duckdb）
- OpenAI SDK（openai）
- defusedxml（RSS パーサ保護）
- 標準ライブラリ外パッケージ例: duckdb, openai, defusedxml

推奨インストール例:

1. 仮想環境を作成・有効化
   - macOS / Linux:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows:
     ```
     python -m venv .venv
     .venv\Scripts\activate
     ```

2. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

   ※ プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください。

3. リポジトリルート（pyproject.toml がある階層）でパッケージを編集可能インストール:
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動ロードされます（config.py にて .git または pyproject.toml の存在するルートを探索）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

必要な主要環境変数（最低限）:
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン
- SLACK_BOT_TOKEN: Slack 通知に使用（必要に応じて）
- SLACK_CHANNEL_ID: Slack チャンネル ID
- KABU_API_PASSWORD: kabu API 用パスワード（発注関連を使う場合）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（score_news / score_regime にも関数引数で渡せます）
- DB パス（任意、デフォルトあり）:
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（オプション）

例 .env（実際の値は秘匿）:
```
JQUANTS_REFRESH_TOKEN=xxxx...
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方の例

以下は Python REPL もしくはスクリプトから呼ぶ基本的な例です。DuckDB の接続は `duckdb.connect(path)` で取得します。

1) ETL（デイリー ETL 実行）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定しない場合は today が使われます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API 必要）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定していれば api_key は省略可
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

3) 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB 初期化（監査専用 DB を作成）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db("data/audit.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions等) が作成されます
```

5) カレンダー操作の例
```python
from datetime import date
import duckdb
from kabusys.data.calendar_management import is_trading_day, next_trading_day

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
print(is_trading_day(conn, d))
print(next_trading_day(conn, d))
```

注意点:
- score_news / score_regime は OpenAI 呼び出しを伴うため API キーとコストを確認してください。関数の api_key 引数に文字列で渡すことも可能。
- ETL 実行時は J-Quants のリフレッシュトークンが必要です（settings.jquants_refresh_token）。

---

## 環境変数と設定（まとめ）

主要な設定は `kabusys.config.Settings` から取得されます。代表的なキー:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 if kabu 発注を利用)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (必須 for AI 処理; 関数引数でも指定可)
- SLACK_BOT_TOKEN (必須 if Slack 通知を使う)
- SLACK_CHANNEL_ID (必須 if Slack 通知を使う)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると .env 自動ロードを無効化

config.py はプロジェクトルート（.git または pyproject.toml）を探索して `.env`, `.env.local` を順に読み込みます。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要構成）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースセンチメント（銘柄別）と関連ユーティリティ
    - regime_detector.py     # ETF MA200 とマクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント + DuckDB 保存ロジック
    - pipeline.py            # ETL パイプライン (run_daily_etl 等)
    - etl.py                 # ETL インターフェース（ETLResult 再エクスポート）
    - calendar_management.py # 市場カレンダー管理（営業日判定等）
    - news_collector.py      # RSS 収集・前処理
    - quality.py             # データ品質チェック群
    - stats.py               # 汎用統計（zscore_normalize）
    - audit.py               # 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py     # ファクター計算（momentum/value/volatility）
    - feature_exploration.py # 将来リターン・IC・統計サマリー等

各モジュールは docstring に設計方針と使用法が記載されています。関数レベルでも入出力や副作用（DB 書き込み等）が明記されています。

---

## 運用上の注意 / ベストプラクティス

- DuckDB ファイルはバージョンやスキーマ互換を考慮してバックアップを取ってください。
- OpenAI 呼び出しはコストが発生します。バッチサイズやスリープ、エラーハンドリングが組み込まれていますが、運用時は API 使用状況を監視してください。
- ETL は J-Quants のレート制限を考慮して実装されていますが、複数プロセス同時実行は避けるか管理してください。
- 本ライブラリは発注ロジック・本番運用に用いる場合は十分なレビューとテストを行ってください（特に order_requests / executions 周りの監査・冪等性）。
- テスト用途や CI では環境変数自動読み込みを無効化するか、テスト専用 .env を使ってください。

---

必要があれば、README に実行コマンド例（systemd / cron ジョブ、Dockerfile、CI スクリプトなど）やより詳細な DB スキーマ説明、サンプル .env.example を追加できます。どの情報を優先して追加しますか？