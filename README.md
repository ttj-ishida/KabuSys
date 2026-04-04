# KabuSys

日本株の自動売買 / データプラットフォームライブラリ (KabuSys)

---

目次
- プロジェクト概要
- 主な機能
- 動作環境 / 依存関係
- セットアップ手順
- 環境変数（.env）
- 使い方（簡単なコード例）
- ディレクトリ構成
- 補足（設計方針・注意点）

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・研究（ファクター計算）・AI によるニュースセンチメント分析・市場レジーム判定・監査ログのためのユーティリティ群を提供する Python パッケージ群です。J-Quants API や RSS ニュース、OpenAI（gpt-4o-mini）を活用し、DuckDB を用いたローカルデータベースでデータの永続化・ETL・解析を行います。

主な利用シナリオ：
- データパイプライン（株価・財務・カレンダー）の差分取得（ETL）と品質チェック
- ニュースの収集・NLP による銘柄別スコアリング（ai_scores）
- マクロニュース + ETF MA に基づく市場レジーム判定
- リサーチ（モメンタム・バリュー・ボラティリティ等のファクター計算）
- 発注フローの監査ログ（order_requests / executions 等）の初期化・管理

---

## 主な機能

- data
  - J-Quants API クライアント（レートリミット・リトライ・ID トークン自動更新）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS -> raw_news、SSRF 対策・トラッキングパラメータ除去）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ作成（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（z-score 正規化）

- ai
  - ニュース NLP による銘柄別センチメントスコア（score_news）
  - マクロニュース + ETF 200日MA の合成による市場レジーム判定（score_regime）
  - OpenAI 呼び出しはリトライやフォールバックを備える（API エラー時はフェイルセーフで継続）

- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）
  - data.stats.zscore_normalize の再利用

---

## 動作環境 / 依存関係

- Python 3.10+
- 主要依存パッケージ（例）:
  - duckdb
  - openai  (OpenAI の v1 SDK を想定)
  - defusedxml
- ネットワークアクセス:
  - J-Quants API（データ取得）
  - OpenAI API（モデル呼び出し）
  - RSS フィードの HTTP(S) アクセス

パッケージのインストール例:
```bash
python -m pip install duckdb openai defusedxml
# （パッケージをローカル開発でインストールする場合）
python -m pip install -e .
```

---

## セットアップ手順

1. リポジトリをクローン / 取得
2. Python 環境を用意（3.10+ 推奨）
3. 依存パッケージをインストール（上記参照）
4. 環境変数を設定
   - プロジェクトルートに `.env` を作成することで自動読み込みされます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます）。
5. データディレクトリを準備（デフォルトでは `data/` 以下に DuckDB ファイルなどを作成します）
   - 必要なら `mkdir -p data` を作成してください

---

## 環境変数（主な項目）

（.env ファイルに記載する想定。`.env.example` を参照してください）

必須（実行する機能により必要）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.score_news / regime の呼び出しで使用）

その他（デフォルトあり / 任意）:
- KABU_API_PASSWORD: kabuステーション API 用パスワード
- KABU_API_BASE_URL: kabu API のエンドポイント（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH: 監視制御ファイルパス
- KILL_FLAG_CLEAR_ON_START: "1" にすると開始時に kill flag をクリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT: 監視閾値
- KABUSYS_ENV: one of {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL: one of {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）

自動 .env ロードの挙動:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` -> `.env.local` の順で読み込みます。
- OS 環境変数が優先され、`.env.local` は上書き（override）可能です。
- テストなどで自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（コード例）

以下は典型的な使用例です。DuckDB 接続を作成して ETL / AI / 研究機能を呼び出します。

- ETL（日次パイプライン）の実行例:
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

# デフォルトの DuckDB ファイルパスは settings.duckdb_path
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）:
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key を None にすると OPENAI_API_KEY を使用
print(f"written scores: {written}")
```

- 市場レジーム判定:
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
ok = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
assert ok == 1
```

- 監査ログ DB の初期化:
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も指定可能
```

- ファクター計算（研究）:
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(str(settings.duckdb_path))
d = date(2026, 3, 20)
momentum = calc_momentum(conn, d)
value = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主なモジュールと役割の一覧です（src/kabusys 配下）。実際のリポジトリはこれを基本に拡張されます。

- src/kabusys/
  - __init__.py
  - config.py             — 環境変数・設定の管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの NLP スコアリング（score_news）
    - regime_detector.py  — マクロ + ETF MA による市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py    — J-Quants API クライアント・保存関数（fetch_*/save_*）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - calendar_management.py — 市場カレンダー管理 / calendar_update_job
    - news_collector.py   — RSS ニュース収集（SSRF 対策・正規化）
    - quality.py          — データ品質チェック（欠損・重複・スパイク等）
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
    - etl.py              — ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
  - research/...（上記参照）

---

## 補足（設計方針・注意点）

- Look-ahead バイアス対策:
  - 多くの処理は target_date を明示的に受け取り、内部で datetime.today() 等を用いない設計です。バックテスト用途の際は target_date を適切に供給してください。
  - J-Quants から取得したデータは fetched_at を記録し、「いつそのデータが入手可能になったか」をトレース可能にしています。

- フォールバック / フェイルセーフ:
  - OpenAI API の失敗やネットワーク障害時は、AI 系処理はゼロスコアやスキップで継続する実装になっています（例: macro_sentiment = 0.0）。
  - ETL はステップ毎に例外を捕捉し他ステップを継続する（全体が一度に停止しない）設計です。ただし、重大なエラーはログに残ります。

- セキュリティ:
  - RSS 取得部分では SSRF 対策（リダイレクト検査・プライベート IP ブロック）や XML 攻撃対策（defusedxml）を実装しています。
  - J-Quants API 呼び出しではレート制御・リトライ・401 リフレッシュを実装しています。

---

何か追加したい項目（例: CI 設定、テストの実行方法、.env.example のテンプレート、実運用向けのデプロイ手順など）があれば教えてください。README をそれに合わせて拡張します。