# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、ニュースセンチメント（OpenAI），市場レジーム判定、ファクター計算、監査ログなどを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下を目的とした Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得と DuckDB への ETL
- RSS ベースのニュース収集と前処理、OpenAI を用いたニュースセンチメント解析
- 市場レジーム判定（MA と マクロニュースセンチメントの合成）
- 研究用途のファクター計算・検証ユーティリティ（モメンタム / ボラティリティ / バリュー 等）
- 監査ログ（シグナル→発注→約定のトレーサビリティ）用スキーマと初期化ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付整合性）

設計上の重要点:
- ルックアヘッドバイアスを避けるため、現在時刻を直接参照しない関数設計（target_date 引数を利用）
- DuckDB を主要なローカル分析 DB として使用
- OpenAI 呼び出しは JSON mode を利用（厳密な JSON 出力を期待）
- API 呼び出しにはリトライ / バックオフ / レート制御を備える

---

## 主な機能一覧

- data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント: fetch_* / save_*（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar, save_*）
  - ニュース収集: RSS 取得・前処理・raw_news への保存
  - カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
  - データ品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db

- ai
  - ニュース NLP スコアリング: score_news（ai_scores への書き込み）
  - 市場レジーム判定: score_regime（market_regime への書き込み）

- research
  - ファクター計算: calc_momentum, calc_volatility, calc_value
  - 特徴量解析: calc_forward_returns, calc_ic, factor_summary, rank
  - 統計ユーティリティ（data.stats.zscore_normalize）

- config
  - 環境変数の自動読み込み（.env, .env.local）と Settings オブジェクト経由の設定取得

- audit
  - signal_events / order_requests / executions テーブル DDL とインデックス、インメモリ/ファイル DB 初期化

---

## 前提条件

- Python 3.10+
  - 型注釈（| 表記など）を使用しているため Python 3.10 以上を推奨
- 必要な外部ライブラリ（代表例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API、OpenAI API、RSS ソース などにアクセス可能であること

（プロジェクトには requirements.txt/pyproject.toml がある想定です。適切に依存をインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存ライブラリをインストール
   - pip install -r requirements.txt
   - または最低限: pip install duckdb openai defusedxml
4. 環境変数 / .env を用意する（下に例を示します）
5. DuckDB や監査 DB の初期化を行う（必要に応じて）

.env の例 (.env.example)
```
# J-Quants
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here

# OpenAI（score_news / regime で使用）
OPENAI_API_KEY=sk-...

# kabuステーション API（発注等を行う場合）
KABU_API_PASSWORD=your_kabu_password
# optional override
# KABU_API_BASE_URL=http://localhost:18080/kabusapi

# Slack 通知（任意）
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

# DB パス
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db

# 実行環境
KABUSYS_ENV=development
LOG_LEVEL=INFO

# テスト時に自動 .env 読み込みを無効にする場合
# KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

備考:
- パッケージの config モジュールはプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、.env/.env.local を自動読み込みします。テストで自動読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## 使い方（主要な例）

以下はパッケージの代表的な利用例です。実行はプロジェクトのルートで行ってください。

1) ETL（日次パイプライン）の呼び出し例
```py
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成して ai_scores に保存
```py
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"written: {n_written}")
```

3) 市場レジーム判定の実行
```py
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DuckDB 初期化
```py
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_kabusys.duckdb")
# conn を使って order_requests / signal_events / executions にアクセスできます
```

5) 研究用ファクター計算
```py
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

6) J-Quants API を直接使う（取得のみ）
```py
from kabusys.data.jquants_client import fetch_daily_quotes

records = fetch_daily_quotes(date_from=date(2026, 3, 1), date_to=date(2026,3,20))
```

---

## ディレクトリ構成

主要なファイル/モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数/設定管理（.env 自動読み込み）
  - ai/
    - __init__.py
    - news_nlp.py               — ニュースセンチメント生成（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py   — 市場カレンダー管理（is_trading_day 等）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult 再エクスポート
    - jquants_client.py        — J-Quants API クライアント & DuckDB 保存ロジック
    - news_collector.py        — RSS ニュース収集
    - quality.py               — データ品質チェック
    - stats.py                 — zscore_normalize 等ユーティリティ
    - audit.py                 — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py       — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py   — calc_forward_returns / calc_ic / factor_summary / rank
  - monitoring/                — （モニタリング関連モジュール想定、今回抜粋なし）
  - execution/                 — （発注/ブローカー統合関連想定）
  - strategy/                  — （戦略定義・シグナル生成想定）
  - data/                      — データ層関連（上記）

---

## 環境変数一覧（主な必須/任意変数）

必須（少なくとも開発で必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
- OPENAI_API_KEY — OpenAI 呼び出しに使用（score_news / regime）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知先チャンネル

発注や実稼働で必要
- KABU_API_PASSWORD — kabuステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

データベース / 実行制御
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用途の SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — development / paper_trading / live
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 を設定すると .env の自動読み込みを無効化

---

## テスト / モック化のポイント

- OpenAI 呼び出しは各モジュール内の _call_openai_api を経由しているため、ユニットテストではこの関数を patch して外部呼び出しを模擬できます。
  - 例: unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api", return_value=mocked_resp)
- news_collector のネットワーク呼び出しは _urlopen をモック可能（SSRF 検査やレスポンス制御をテスト可能）。
- J-Quants クライアントの _request は HTTP 層の振る舞いを含むため、get_id_token / fetch_* をモックして ETL の DB 書き込み挙動をテストしてください。

---

## 注意事項 / 運用メモ

- DuckDB の executemany で空リストを渡すとエラーになるバージョンがあります（コード中でガード済み）。DB 保存関数呼び出し時は注意してください。
- OpenAI の API 呼び出しは JSON モードで厳密な JSON を期待しますが、モデル出力に外部ノイズが入る想定で耐性（JSON 抽出・復元ロジック）を組み込んでいます。
- J-Quants API のレート制限（120 req/min）を尊重するため内部で固定間隔スロットリングを行います。
- 監査ログは削除しない設計です。テーブルを初期化する際は既存データの扱いを注意してください。
- 本リポジトリは自動売買システムの一部を提供します。実際の売買を行う場合は十分なレビュー・バックテスト・リスク管理を行ってください。

---

必要であれば、README に以下を追加できます:
- インストール手順（pyproject.toml / setup.py を使った pip install -e . の例）
- CI / テストの実行方法
- 開発用の .env.example ファイルをリポジトリに含めるサンプル

ご希望があれば README をより具体的なコマンドや pyproject.toml に合わせて調整します。