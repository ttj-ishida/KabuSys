# KabuSys — 日本株自動売買基盤（README）

KabuSys は日本株向けのデータプラットフォーム・研究・AI スコアリング・監査ログを備えた自動売買基盤のライブラリです。本リポジトリは ETL、データ品質チェック、ニュース収集と NLP スコアリング、ファクター計算、監査テーブル等を提供します。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数（設定）
- 使い方（簡単なコード例）
- ディレクトリ構成（抜粋）
- 注意点 / 運用メモ

---

## プロジェクト概要

このパッケージは以下を目的としています。

- J-Quants API から株価・財務・カレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ベースのニュース収集と記事前処理、銘柄紐付け
- OpenAI（gpt-4o-mini）を使ったニュースセンチメントと市場レジーム判定
- ファクター計算（モメンタム / ボラティリティ / バリュー 等）と特徴量探索ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を保持するスキーマ作成ユーティリティ

設計上のポイント:
- ルックアヘッドバイアスを避けるため、内部処理で date.today() 等を不用意に参照しない実装方針
- DuckDB を中心としたローカルデータベース設計（ETL の冪等保存）
- API 呼び出しはリトライ・レート制御を備えた堅牢な実装

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（差分取得、バックフィル、品質チェック）
  - J-Quants API クライアント（取得・保存ロジック、トークン自動リフレッシュ、レートリミット）
- データ
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - ニュース収集（RSS 取得・前処理・SSRF 対策）
  - データ品質チェック（missing / spike / duplicates / date consistency）
  - 監査ログスキーマ生成（init_audit_schema / init_audit_db）
- AI
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント（ai_scores テーブルへの書き込み）
  - regime_detector.score_regime: ETF(1321) の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定（market_regime へ書込）
- Research
  - calc_momentum / calc_volatility / calc_value（ファクター群）
  - calc_forward_returns, calc_ic, factor_summary, rank（特徴量探索・統計）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 の `|` 型注釈などを使用）
- ネットワーク接続（J-Quants / OpenAI を利用する場合）

1. 仮想環境を作成してアクティブ化（任意だが推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. 必要パッケージをインストール（例）
   ```bash
   pip install duckdb openai defusedxml
   ```
   実運用では requirements.txt を用意して:
   ```bash
   pip install -r requirements.txt
   ```
   （本 README はコードベースから依存ライブラリを推測しています。実際のプロジェクトでは requirements.txt を参照してください。）

3. 開発インストール（ソースルートで）
   ```bash
   pip install -e .
   ```

4. 設定ファイル
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（os 環境変数よりも下位にロードされ、.env.local は .env を上書きします）。
   - 自動ロードを無効にするには環境変数を設定:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

---

## 環境変数（主要）

（設定は kubusys.config.Settings で参照されます）

必須（ETL / API 利用時）:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD — kabu ステーション（実行系を使う場合）

OpenAI / 通知:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime が利用）
- LINE_CHANNEL_ACCESS_TOKEN — LINE 通知（任意）
- LINE_USER_ID — LINE 通知先（任意）

データベース / ファイルパス（デフォルトを持つもの）:
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — プロセス停止フラグファイル（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill flag を消すか（"1" で有効）

動作モード / ログ:
- KABUSYS_ENV — environment ("development" / "paper_trading" / "live"), デフォルト "development"
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL"), デフォルト "INFO"

その他:
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロード無効化（"1"）

.env の例は .env.example（存在する場合）を参照してください。

---

## 使い方（簡単なコード例）

以下は各主要機能の利用例です。DuckDB 接続は duckdb.connect(settings.duckdb_path) を想定します。

- ETL（日次パイプラインを実行）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI が必要）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key は環境変数 OPENAI_API_KEY を使う
print("written:", written)
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY 必須（env または引数）
```

- RSS フィード取得（news_collector 内部ユーティリティ）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
for a in articles:
    print(a["id"], a["title"])
```

- 監査ログ DB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# 以降 order_requests / signal_events / executions テーブルが利用可能
```

- 研究用ユーティリティ（ファクター計算）
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum, calc_volatility, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

注意: 上記は直接モジュールを呼ぶ例です。実運用ではログ設定、例外ハンドリング、バックグラウンドジョブ管理を追加してください。

---

## ディレクトリ構成（主要ファイル抜粋）

src/kabusys/
- __init__.py
- config.py                            -- 環境変数・設定読み込みロジック
- ai/
  - __init__.py
  - news_nlp.py                         -- ニュース NLP スコアリング
  - regime_detector.py                  -- 市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py                   -- J-Quants API クライアント（取得・保存）
  - pipeline.py                         -- ETL パイプライン / run_daily_etl
  - etl.py (再エクスポート)
  - calendar_management.py              -- 市場カレンダー管理
  - news_collector.py                   -- RSS 収集・前処理
  - quality.py                          -- データ品質チェック
  - stats.py                            -- 共通統計ユーティリティ
  - audit.py                            -- 監査ログスキーマ初期化
- research/
  - __init__.py
  - factor_research.py                  -- モメンタム/ボラティリティ/バリュー
  - feature_exploration.py              -- 将来リターン / IC / 統計要約
- research/（その他ユーティリティ）
- その他: strategy, execution, monitoring（パッケージ設計に応じて追加）

（注）上記は提供されたコード抜粋に基づく構成です。実際のリポジトリにはさらにモジュールやスクリプトがある可能性があります。

---

## 注意点 / 運用メモ

- OpenAI 呼び出しについて
  - news_nlp と regime_detector は JSON Mode（response_format）を利用します。OpenAI のレスポンスが壊れている場合はフォールバックやログ出力により安全に処理を継続する設計です。
  - APIキー漏洩に注意し、環境変数かシークレットマネージャで管理してください。

- J-Quants API
  - レートリミット（120 req/min）を守るため内部でスロットリングがあります。長期間の全銘柄取得では時間がかかる可能性があります。
  - get_id_token はリフレッシュトークンを使用して id_token を取得します。refresh token は安全に保管してください。

- データベース（DuckDB）
  - ETL は冪等（ON CONFLICT DO UPDATE）を前提にしています。直接 DB を操作する場合はスキーマと制約に注意してください。
  - audit.init_audit_db は UTC タイムゾーン固定やトランザクションオプションを提供します。

- テスト / 開発
  - 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化できます。テストで環境を強制したい場合に便利です。
  - OpenAI 呼び出し関数やネットワーク I/O 部分は unittest.mock で差し替えてユニットテスト可能な設計になっています。

---

この README はコードベースの概要と利用方法を簡潔にまとめたものです。より詳細な設計ドキュメント（StrategyModel.md, DataPlatform.md 等）がある場合はそちらを参照してください。もし README の翻訳や追加セクション（例: CI / デプロイ手順、具体的なスキーマ定義の抜粋）を希望される場合はお知らせください。