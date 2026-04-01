# KabuSys

日本株向けの自動売買・データパイプライン基盤ライブラリです。  
ETL（J-Quants）→ データ品質チェック → ファクター計算 → AI（ニュースセンチメント / レジーム判定） → 監査ログ の一連処理を想定したモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today()/datetime.today() を使わない箇所が多い）
- DuckDB を中心としたローカル DB ベースの ETL / 解析
- OpenAI（gpt-4o-mini）を用いたニュース NLP & マクロセンチメント評価（JSON Mode）
- J-Quants API との差分取得・保存（レート制限、トークン自動リフレッシュ、冪等保存）
- 監査ログ（signal → order_request → execution）のスキーマ初期化ユーティリティ

---

## 機能一覧

- 環境設定読み込み / Settings API（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルートを自動検出）
  - 必須値チェック・型変換ユーティリティ
- データ取得・ETL（kabusys.data.jquants_client, pipeline）
  - J-Quants API からの日足・財務・市場カレンダー取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - 日次 ETL 実行（run_daily_etl）と個別 ETL ジョブ（prices / financials / calendar）
  - データ品質チェック（missing / duplicates / spike / date consistency）
- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・前処理（URL 正規化・トラッキング除去・SSRF 対策）
- AI（kabusys.ai）
  - news_nlp.score_news：銘柄別ニュースをまとめて LLM に送り ai_scores に書き込む
  - regime_detector.score_regime：ETF（1321）MA200 とマクロセンチメントを合成して market_regime に書き込む
- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算・IC 計算・統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events, order_requests, executions のスキーマ初期化関数（init_audit_schema / init_audit_db）

---

## 必要要件（概略）

- Python 3.10+
- duckdb
- openai
- defusedxml
- （標準ライブラリのみで動く部分が多いですが、OpenAI クライアントや DuckDB は必須）

インストール用依存例（pip）
```
pip install duckdb openai defusedxml
```

プロジェクト配布の方式によっては `pip install -e .` などでインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存パッケージをインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -U pip
   pip install duckdb openai defusedxml
   pip install -e .
   ```
3. 環境変数の準備
   - プロジェクトルートに `.env`（およびローカル設定用に `.env.local`）を配置すると、`kabusys.config` が自動で読み込みます（CWD に依存せず、パッケージルートを検出）。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 環境変数 (.env の例)

最低限必要な環境変数（例）:

```
# J-Quants
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx

# OpenAI
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxx

# kabuステーション（注文系）
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack (モニタリング通知等)
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0123456789

# DB / その他
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PID_FILE_PATH=data/execution.pid

# 実行環境とログ
KABUSYS_ENV=development   # development | paper_trading | live
LOG_LEVEL=INFO
```

- Settings API（kabusys.config.settings）経由でこれらの値にアクセスできます。必須のキーが未設定の場合は ValueError が発生します。

---

## 使い方（主要な例）

以下は基本的な Python スニペット例です。各処理は DuckDB 接続（kabusys.config.settings.duckdb_path を推奨）を受け取る設計です。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュース NLP スコアリング（AI）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数で設定しているなら api_key=None で良い
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("written:", n_written)
```

3) 市場レジーム判定（MA200 + マクロセンチメント合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査 DB を初期化（監査ログ専用 DB）
```python
from kabusys.data.audit import init_audit_db
from kabusys.config import settings

# settings.duckdb_path を使う or 別のファイルを指定してもよい
audit_conn = init_audit_db(settings.duckdb_path)
```

5) RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

articles = fetch_rss(DEFAULT_RSS_SOURCES['yahoo_finance'], source='yahoo_finance')
# articles は list[NewsArticle]
```
（raw_news への保存ロジックは ETL ワークフローや別モジュールで制御する想定です。fetch_rss は記事抽出を提供します。）

---

## 注意点 / 実装上のポイント

- OpenAI 呼び出しは JSON Mode を使い、レスポンスを厳密にパースしているため、API キーやモデルの利用方法に注意してください。
- J-Quants API との通信では固定間隔レートリミッタとリトライ（指数バックオフ）、401 時のトークン自動リフレッシュを実装しています。
- ETL の各ステップは独立してエラーハンドリングされ、部分失敗しても可能な範囲で処理を続け、結果を ETLResult に格納します。
- news_nlp / regime_detector はルックアヘッドバイアスに注意して実装されています（target_date に対して過去のウィンドウのみ参照）。

---

## ディレクトリ構成（主要ファイル）

（ソースは `src/kabusys/` 以下に配置）

- kabusys/
  - __init__.py  (パッケージメタ情報: __version__)
  - config.py  (環境変数 / Settings)
  - ai/
    - __init__.py
    - news_nlp.py         (ニュースセンチメント、score_news)
    - regime_detector.py  (市場レジーム判定、score_regime)
  - data/
    - __init__.py
    - jquants_client.py   (J-Quants API クライアント、fetch / save 関数)
    - pipeline.py         (ETL パイプライン、run_daily_etl 等)
    - etl.py              (ETL 型の再エクスポート)
    - stats.py            (zscore_normalize 等の統計ユーティリティ)
    - quality.py          (データ品質チェック)
    - calendar_management.py (市場カレンダー管理 / next/prev_trading_day 等)
    - news_collector.py   (RSS 取得・前処理)
    - audit.py            (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py  (momentum/value/volatility)
    - feature_exploration.py (forward returns / IC / summary / rank)
  - monitoring/  (パッケージ公開対象に含まれる想定 - 実装ファイルはここに存在)
  - strategy/   (戦略・シグナル生成用モジュール群 - 実装は別途)
  - execution/  (発注・ブローカーインターフェース - 実装は別途)

---

## 補足

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を基準に行われます。テストなどで自動読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB のバージョンや OpenAI SDK のバージョン差分により例外型や挙動が変わる点に注意してください（コード中で互換性対策の記述あり）。
- 実運用（ライブ発注）を行う場合はログ出力、監視、バックアップ、二重化、十分なテストを行ってください。特に order/execution 周りは冪等性と監査証跡が重要です。

---

この README はコードベース（src/kabusys）からの注釈ベースの概要です。詳細な実行手順や追加の CLI、ユニットテスト、デプロイ手順は別ドキュメントで管理することを推奨します。質問や特定の使い方（例: ETL の定期実行、監査スキーマ拡張、モデル変更）についてあれば具体的に教えてください。