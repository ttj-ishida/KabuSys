# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株のデータ取得・品質管理・特徴量計算・AI ニュース分析・市場レジーム判定・監査ログなどを含む自動売買プラットフォームのライブラリ群です。本リポジトリは ETL、データ品質、研究（リサーチ）、ニュース NLP、レジーム判定、監査ログ用スキーマなどのモジュールを提供します。

バージョン: 0.1.0

---

## 目次

- プロジェクト概要
- 機能一覧
- 前提条件
- セットアップ手順
- 環境変数（.env）
- 使い方（主要なユースケースとサンプルコード）
  - DuckDB 初期化（監査DB）
  - 日次 ETL 実行
  - ニューススコアリング（score_news）
  - 市場レジーム判定（score_regime）
  - ファクター計算・リサーチ API
- ディレクトリ構成
- 設計上の注意と運用上のポイント

---

## プロジェクト概要

KabuSys は主に以下を目的とする Python パッケージです。

- J-Quants API を利用した株価 / 財務 / カレンダーの差分 ETL
- DuckDB を用いたローカルデータベース管理
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュースの収集・前処理・OpenAI を使った銘柄別センチメント算出
- 市場全体のレジーム（bull/neutral/bear）判定（ETF と LLM の組合せ）
- 監査ログ（signal → order_request → execution のトレース）用スキーマの初期化
- 研究用途のファクター / フィーチャー探索ユーティリティ

設計方針として、ルックアヘッドバイアスを避けるために内部で datetime.today() 等を不用意に参照しないこと、DB 操作は冪等 (idempotent) に行うこと、外部 API 呼び出しはリトライやレート制御を持つこと、などが採用されています。

---

## 機能一覧

- data
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save）
  - ニュース収集（RSS の安全取得・正規化・raw_news への保存ロジック）
  - カレンダー管理（営業日判定、next/prev/get_trading_days）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP による銘柄センチメント（score_news）
  - 市場レジーム判定（score_regime）
  - OpenAI（gpt-4o-mini）を JSON mode で利用（バックオフ、検証含む）
- research
  - ファクター計算（momentum, value, volatility）
  - 将来リターン計算（forward returns）
  - IC 計算、統計サマリー、ランク変換など

---

## 前提条件

- Python 3.10+
- ネットワークアクセス（J-Quants API、OpenAI、RSS フィード など）
- 推奨パッケージ（主要な依存、実際の requirements はプロジェクトに合わせて管理してください）:
  - duckdb
  - openai (および openai SDK に合わせた import 構成)
  - defusedxml
  - その他標準ライブラリ（urllib, json, logging, datetime 等）

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください。

---

## セットアップ手順

1. リポジトリをクローン / 取得

2. 仮想環境の作成・有効化（例: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

5. 環境変数設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（設定は下記参照）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 環境変数 (.env)

config.py で参照される主要な環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabu ステーション API のパスワード（使用する場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合の Bot トークン
- SLACK_CHANNEL_ID — 通知先チャンネル ID

OpenAI 関連:
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime のデフォルト参照先）

オプション（デフォルト値あり）:
- KABU_API_BASE_URL — kabuAPI のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 実行監視用 PID ファイルパス（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

注意:
- .env.local は .env の上書き（優先）として読み込まれます。
- 自動ロードはプロジェクトルート（.git または pyproject.toml を基準）から行われます。

---

## 使い方（主要ユースケース）

以下はライブラリを直接インポートして使うサンプルです。実運用ではジョブスケジューラ（cron / systemd / Airflow など）から呼び出すことを想定しています。

※ 以下サンプルは Python スクリプト内での呼び出し例です。

- DuckDB 接続と監査DB初期化

```python
from kabusys.data.audit import init_audit_db

# 監査専用 DuckDB を作成してスキーマを初期化
conn = init_audit_db("data/audit.duckdb")
# conn は duckdb.DuckDBPyConnection オブジェクト
```

- 日次 ETL を実行する（J-Quants からの差分取得、品質チェック含む）

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path と合わせる
result = run_daily_etl(conn, target_date=date.today())  # target_date を明示してもよい
print(result.to_dict())
```

- ニュースセンチメントを生成（OpenAI API キーが必要）

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定するか api_key パラメータで渡す
n = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {n} codes")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの合成）

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数に
```

- ファクター / リサーチ API 例

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic, factor_summary
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)

forward = calc_forward_returns(conn, d, horizons=[1,5,21])
ic = calc_ic(mom, forward, "mom_1m", "fwd_1d")
summary = factor_summary(mom, ["mom_1m","mom_3m","ma200_dev"])
normed = zscore_normalize(mom, ["mom_1m","mom_3m","mom_6m"])
```

---

## 運用上の注意 / 設計ノート

- Look-ahead bias 回避
  - 多くの関数は target_date を明示して使用し、内部で datetime.today() を不用意に参照しない設計です。バックテストやスコアリング時は target_date を必ず指定するか、外部で取得した trading_day を渡してください。
- OpenAI / J-Quants 呼び出し
  - OpenAI（gpt-4o-mini）は JSON Mode を使って厳密な JSON を期待します。レスポンスの検証やリトライが実装済みです。
  - J-Quants クライアントは RateLimiter（120 req/min）および 401 リフレッシュハンドリングを備えています。
- データベース
  - DuckDB をローカルに置き、ETL を通して raw_prices / raw_financials / market_calendar / ai_scores / market_regime / audit テーブル等にデータを保存します。
  - 監査ログ初期化時は TIMEZONE を UTC に固定します（init_audit_schema 内で SET TimeZone='UTC' を実行）。
- セキュリティ
  - news_collector では SSRF 対策や受信サイズ制限、XML パーサーの hardening（defusedxml）などを行っています。
- エラーハンドリング
  - ETL は個別ステップごとにエラーハンドリングされ、1 ステップ失敗でも他ステップは継続します（結果に errors を蓄積）。

---

## ディレクトリ構成（抜粋）

下記は主要モジュールの配置（src/kabusys 以下）です。コメントは各モジュールの役割。

- src/kabusys/
  - __init__.py
  - config.py              — 環境変数 / .env 管理
  - ai/
    - __init__.py
    - news_nlp.py          — ニュースセンチメント算出（score_news）
    - regime_detector.py   — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント + 保存ロジック
    - pipeline.py          — ETL の orchestrator（run_daily_etl 等）
    - etl.py               — ETL 入口型定義の再エクスポート
    - news_collector.py    — RSS 収集 / 前処理 / 保存
    - calendar_management.py — 市場カレンダーの判定・更新
    - quality.py           — データ品質チェック
    - stats.py             — 汎用統計関数（zscore_normalize）
    - audit.py             — 監査ログスキーマ初期化（init_audit_schema, init_audit_db）
  - research/
    - __init__.py
    - factor_research.py   — momentum, value, volatility の計算
    - feature_exploration.py — forward returns, IC, summaries, rank

---

## 最後に

本 README はコードベースの主要機能と使い方の概要を示すものであり、実際の導入・運用時には以下を推奨します。

- pyproject.toml / requirements.txt に基づく依存関係の固定
- 実運用用のログ・監視設定（SLACK 通知等）の整備
- 秘密情報（API トークン等）は安全に管理（シークレットマネージャ / Vault 等を推奨）
- DuckDB のバックアップ・運用ポリシーの策定

追加で README に載せたい具体的なスクリプト例（cron / systemd unit / Dockerfile / CI のセットアップ等）があれば教えてください。必要に応じて追記・改善します。