# KabuSys

日本株向けの自動売買／データ基盤ライブラリです。  
ETL（J-Quants からの時系列・財務データ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント付与）、ファクター算出・研究ユーティリティ、監査ログ（発注トレーサビリティ）など、アルゴリズム取引システムのバックエンド処理を提供します。

---

## 主な機能（機能一覧）

- データ取得・ETL
  - J-Quants API クライアント（株価日足、財務データ、上場銘柄、JPX カレンダー）
  - 差分更新／バックフィル／ページネーション対応
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL パイプライン（日次 ETL 実行）
- データ品質管理
  - 欠損、重複、スパイク、日付不整合検査（品質チェック）
- ニュース収集・前処理
  - RSS フィード取得（SSRF 対策、サイズ制限、トラッキングパラメータ除去）
  - 記事ID の冪等生成（URL 正規化 + SHA-256）
- ニュース NLP（OpenAI）
  - 銘柄単位のニュースセンチメント付与（JSON Mode、チャンク/リトライ）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM を組合せ）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value などの定量ファクター算出
  - 将来リターン計算、IC（スピアマン）計算、統計サマリ
  - Z-score 正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化
  - UUID ベースのトレーサビリティ
- 設定管理
  - .env / .env.local / OS 環境変数の自動読み込み（プロジェクトルート検出）
  - 各種環境変数の検証メソッドを提供

---

## 前提・必須環境

- Python 3.10+
- duckdb（Python パッケージ）
- OpenAI API（news_nlp / regime_detector で使用）
- J-Quants API（ETL で使用）
- そのほかのネットワークアクセス（RSS, J-Quants API）

必要な環境変数（主なもの）:
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（news_nlp, regime_detector で使用）
- KABU_API_PASSWORD — kabu API パスワード（発注連携時）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境（development / paper_trading / live）、デフォルト development
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）、デフォルト INFO

自動 .env ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml）から .env を自動読み込みします。
- 読み込み順: OS 環境 > .env.local > .env
- 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## セットアップ手順

1. リポジトリをクローンしてワークディレクトリへ移動
   - （プロジェクトルートに .git または pyproject.toml が必要です）

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトで配布されている requirements.txt があればそれを使ってください）
   - 開発時は pip install -e . （パッケージを編集可能モードでインストール）

4. 環境変数の用意
   - プロジェクトルートに .env または .env.local を作成し、必要なキーを設定
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     KABU_API_PASSWORD=...
     DUCKDB_PATH=data/kabusys.duckdb

5. DuckDB ファイルの親ディレクトリを作成（自動作成されることが多いですが手動で準備しても可）
   - mkdir -p data

---

## 使い方（基本例）

以下は Python スクリプト内での利用例です。適宜ロガーやエラーハンドリングを追加してください。

- DuckDB 接続を用意して日次 ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

db_path = str(settings.duckdb_path)
conn = duckdb.connect(db_path)

# target_date を省略すると today が対象になります
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- OpenAI を使ったニューススコア付与（ai.news_nlp.score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# 環境変数 OPENAI_API_KEY が未設定なら api_key を渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定（ai.regime_detector.score_regime）:

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB を初期化する（独立した監査用 DB を作る場合）:

```python
from pathlib import Path
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db(Path("data/audit.duckdb"))
# audit_conn を使って発注ログを操作できます
```

- リサーチ系関数の使用例:

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
conn = duckdb.connect(str(settings.duckdb_path))
moms = calc_momentum(conn, date(2026, 3, 20))
vols = calc_volatility(conn, date(2026, 3, 20))
vals = calc_value(conn, date(2026, 3, 20))
```

- RSS フィード取得（news_collector.fetch_rss）:

```python
from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

src = DEFAULT_RSS_SOURCES["yahoo_finance"]
articles = fetch_rss(src, source="yahoo_finance")
# 取得した articles は raw_news に格納する処理を実装して保存します
```

注意:
- AI 関連関数は OpenAI API を呼び出します。テスト環境では kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api をモックしてテストしてください。
- J-Quants クライアントにはレートリミッタとリトライが組み込まれています（120 req/min、リトライ、401 の自動リフレッシュ等）。

---

## 環境変数一覧（代表）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）（必須で利用する場合）
- KABU_API_PASSWORD: kabu API パスワード（発注連携）
- KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン
- SLACK_CHANNEL_ID: Slack チャンネル ID
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: SQLite ファイルパス（デフォルト data/monitoring.db）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する（1 を設定）

---

## 開発 / テスト上の注意

- 自動 .env 読み込みはパッケージが配置された場所（__file__ の親）から .git または pyproject.toml を探索して行われます。CI や一時的なテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしてください。
- OpenAI 呼び出しは外部依存のためユニットテストでは _call_openai_api のモックを使って応答を差し替えてください。
- news_collector は SSRF や XML 攻撃防止のため defusedxml、SSRF 検査、コンテンツサイズ制限等を実装しています。外部 URL を取り扱う際はその設計を尊重してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、コード上では空チェックが行われています（互換性注意）。

---

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 配下の主要モジュールと簡単な説明です。

- kabusys/
  - __init__.py           — パッケージ初期化（バージョン情報）
  - config.py             — 環境変数・設定管理（.env 自動読み込み、Settings クラス）
  - ai/
    - __init__.py         — ai パッケージ公開 API
    - news_nlp.py         — ニュースセンチメント付与（OpenAI 連携）
    - regime_detector.py  — マクロ + MA200 合成で市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py — JPX カレンダー管理、営業日判定
    - etl.py               — ETL インターフェース再エクスポート
    - pipeline.py          — ETL パイプライン実装（run_daily_etl 等）
    - stats.py             — 統計ユーティリティ（zscore_normalize）
    - quality.py           — データ品質チェック
    - audit.py             — 監査ログスキーマ初期化（signal/order/execution）
    - jquants_client.py    — J-Quants API クライアント（取得 + 保存）
    - news_collector.py    — RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py   — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリー、ランク関数
  - research/ (他モジュール)
  - monitoring, strategy, execution などは将来的な拡張箇所（パッケージ公開時に含める）

（リポジトリ内のファイルに基づく要約です。実際のプロジェクトルートには pyproject.toml / .env.example 等がある想定です。）

---

## 運用上の留意点

- OpenAI コールはコストとレイテンシーを伴うため、バッチ設計（チャンク、最大銘柄数）やリトライ/フォールバック（API 失敗時に 0 にフォールバック）を実装しています。
- J-Quants API はレート制限が厳格なので、jquants_client の RateLimiter を介して呼び出してください（モジュールは既に利用を想定しています）。
- ETL はデータ品質チェックの結果を収集します。重大な品質問題（error）が検出された場合は運用側でアラートを設定してください。
- 監査ログは削除しない前提です。監査テーブルの設計（created_at, updated_at, UUID）に従い、トレーサビリティを保ってください。

---

必要であれば README を拡張して以下を追加できます：
- 各 API の引数詳細・戻り値サンプル
- CLI スクリプト例（cron / Airflow での実行例）
- データベーススキーマ（CREATE TABLE）全文
- 運用チェックリスト（死活監視・アラート設定例）

ご希望があれば、特定の使い方（ETL の定期実行、発注フロー例、Slack 通知実装例など）に合わせてサンプルを追加します。