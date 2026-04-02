# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI 経由）、ファクター計算・リサーチ、監査ログ（発注トレース）など、自動売買プラットフォームのコア機能を提供します。

バージョン: 0.1.0

---

## 主な概要

KabuSys は次の目的を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダー等の差分取得と DuckDB への保存（ETL）
- RSS ベースのニュース収集（raw_news）と前処理 / SSRF 安全対策
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析（銘柄毎の ai_score）とマクロセンチメントを用いた市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量探索（IC, forward returns 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用スキーマ生成・初期化
- 環境変数 / .env の取り扱い支援（自動ロード機能）

多くのモジュールは DuckDB 接続を受け取り、外部取引所への発注等を含まないため、研究（バックテスト）用途や運用 ETL に利用できます。

---

## 機能一覧

- data/
  - ETL（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（ページネーション・リトライ・トークン自動リフレッシュ対応）
  - 市場カレンダー管理（営業日判定、次/前営業日取得）
  - ニュース収集（RSS、URL 正規化、SSRF 対策、前処理）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマの初期化（監査テーブル・インデックス作成）
  - 汎用統計ユーティリティ（Zスコア正規化）
- ai/
  - news_nlp.score_news: ニュースをまとめて OpenAI に送り、銘柄ごとのスコアを書き込み
  - regime_detector.score_regime: ETF（1321）MA200 乖離とマクロニュース LLM スコアを合成して市場レジームを算出
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込み（.env/.env.local の自動ロード、必要変数チェック）
- audit
  - 監査ログ用 DuckDB 初期化ユーティリティ

設計上のポイント:
- ルックアヘッドバイアス対策（内部で date.today()/datetime.today() を直接参照しない設計や、DB クエリで排他条件を採用）
- フェイルセーフ（API 失敗時のデフォルト値やスキップ）
- セキュリティ考慮（SSRF ブロック、defusedxml、HTTP レスポンスサイズ制限 等）
- 冪等性（DB 保存は ON CONFLICT DO UPDATE / DO NOTHING を活用）

---

## 必要条件

- Python 3.10+（型注釈に union 型 | を使用）
- 主要依存パッケージ（プロジェクトに合わせて requirements を用意してください）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の追加がある場合は requirements.txt を用意してください）

---

## セットアップ手順

1. リポジトリをクローンします。

   git clone <repo-url>
   cd <repo-root>

2. 仮想環境を作成して有効化（例: venv）。

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. パッケージをインストール（開発インストールなど）。

   pip install -e src
   pip install duckdb openai defusedxml

   ※ 実際の requirements.txt / pyproject.toml がある場合はそちらを利用してください。

4. 環境変数を設定します。開発ではプロジェクトルートに `.env` / `.env.local` を作成しても良いです（config.py により自動ロードされます）。

   自動ロードはデフォルトで有効です。自動ロードを抑止する場合は:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## 必要な環境変数

config.Settings で参照される代表的な環境変数:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン。jquants_client.get_id_token で使用。
- KABU_API_PASSWORD (必須)
  - kabuステーション API 用パスワード（発注系を組む場合）
- KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- DUCKDB_PATH (任意, デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (任意, デフォルト: data/monitoring.db)
- PID_FILE_PATH (任意, デフォルト: data/execution.pid)
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT (監視閾値)
- KABUSYS_ENV (任意, 有効値: development, paper_trading, live) デフォルト: development
- LOG_LEVEL (任意: DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト: INFO
- OPENAI_API_KEY (ai モジュールを使う場合は必須。関数引数で渡すことも可能)

config.py の自動 .env ロードの挙動:
- プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を基準に `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化します。

---

## 使い方（クイックスタート）

以下は主要機能の簡単な使用例です。各関数は DuckDB の接続オブジェクト（duckdb.connect(...) の返り値）を受け取ります。

1) 日次 ETL の実行（市場カレンダー→株価→財務→品質チェック）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # 実ファイルまたは ":memory:"
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコア（ai/news_nlp）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY は環境変数か、第二引数に直接渡せます
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written: {n_written}")
```

3) 市場レジーム判定（ai/regime_detector）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
# market_regime テーブルに書き込まれます
```

4) 監査ログ DB 初期化:

```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")  # ファイルがなければ作成
# テーブル / インデックスが作成されます
```

5) ファクター計算 / リサーチ:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
moms = calc_momentum(conn, target_date=date(2026, 3, 20))
vals = calc_value(conn, target_date=date(2026, 3, 20))
vols = calc_volatility(conn, target_date=date(2026, 3, 20))
```

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py
  - regime_detector.py
- data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（取得/保存ロジック）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py   — 市場カレンダー管理（営業日判定等）
  - news_collector.py        — RSS ニュース収集（SSRF 保護）
  - quality.py               — データ品質チェック
  - stats.py                 — 汎用統計（zscore_normalize）
  - audit.py                 — 監査ログスキーマ初期化
  - etl.py                   — ETLResult の再エクスポート
- research/
  - __init__.py
  - factor_research.py       — ファクター計算（momentum/value/volatility）
  - feature_exploration.py   — 将来リターン / IC / 統計サマリー 等
- monitoring/ （実装とファイルがある場合）
- execution/  （発注周りの実装がある場合）
- その他モジュール（将来的に追加）

（注）プロジェクトルートに .env, .env.local を置くと config.py が自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。

---

## 注意事項 / 実運用上のポイント

- OpenAI 呼び出しは外部 API のため、API キーや呼び出し回数に注意してください。news_nlp / regime_detector はリトライとフェイルセーフを備えていますが、コスト管理が必要です。
- J-Quants API はレート制限（120 req/min）に合わせた RateLimiter を実装しています。大量取得を行う場合はカスタムの待ち時間やオフピークのスケジューリングを検討してください。
- ETL や research 関数は DuckDB 接続を直接操作します。スキーマが期待通りでない場合はエラーになります。初期スキーマ生成やサンプルデータ準備を事前に行ってください。
- セキュリティ: news_collector は SSRF 対策や受信サイズ制限を実装していますが、追加のネットワーク制限やプロキシの設定は運用環境に応じて行ってください。
- ルックアヘッドバイアス防止: 多くの処理は外部に現在日時を参照する実装を避けており、target_date を明示的に渡すことで過去シミュレーション（バックテスト）でも再現性の高い処理が行えます。

---

## さらに詳しく / 貢献

- 各モジュールの docstring に詳細な設計方針・処理フローが含まれています。実装の理解や拡張時は該当ファイルのドキュメントコメントを参照してください。
- バグ報告・機能要望は Issue を立ててください。プルリクエスト歓迎です。

---

必要であれば README に含める具体的なコマンド（データベース初期化スクリプト、cron 設定例、Dockerfile サンプルなど）を追加できます。どの情報を優先して追記しますか？