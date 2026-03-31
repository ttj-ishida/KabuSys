# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ。  
ETL（J-Quants からのデータ取得）、ニュースセンチメント（OpenAI を使った NLP）、市場レジーム判定、研究用ファクター計算、監査ログ（オーダー→約定のトレーサビリティ）などの機能を提供します。

主な設計方針：
- DuckDB をデータレイヤに用いる（軽量・埋め込み型の分析 DB）
- 外部 API 呼び出し時はリトライ・バックオフ・レート制御など堅牢性を考慮
- バックテストでの Look‑ahead bias を防ぐ実装（内部で date.today() を盲目的に参照しない）
- 冪等保存（INSERT ... ON CONFLICT）や監査ログによるトレーサビリティ

---

## 機能一覧

- data
  - ETL パイプライン（daily ETL、個別 ETL ジョブ）
  - J-Quants クライアント（株価、財務、カレンダー、上場銘柄情報）
  - カレンダー管理（営業日判定、next/prev trading day、カレンダー更新ジョブ）
  - ニュース収集（RSS → raw_news 保存、SSRF 対策、トラッキングパラメータ除去）
  - データ品質チェック（欠損、スパイク、重複、日付不整合）
  - 監査ログスキーマ（signal / order_request / executions）と初期化ユーティリティ
  - 汎用統計ユーティリティ（Zスコア正規化）

- ai
  - ニュース NLP（銘柄ごとのニュースセンチメントを OpenAI に問い合わせ）
  - 市場レジーム判定（1321 ETF の MA200 乖離 + マクロニュースセンチメントを合成）

- research
  - ファクター計算（モメンタム、ボラティリティ、バリュー等）
  - 特徴量探索ユーティリティ（将来リターン計算、IC、統計サマリー、ランク処理）

- config
  - 環境変数管理（.env 自動読み込み、必須チェック、環境種別判定）

---

## 前提 / 必要要件

- Python 3.10+
- 主な依存パッケージ
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ多数使用）
- 外部サービスの資格情報
  - J-Quants リフレッシュトークン（JQUANTS_REFRESH_TOKEN）
  - OpenAI API キー（OPENAI_API_KEY） — ai モジュールで使用
  - kabu ステーション API 用パスワード（KABU_API_PASSWORD）
  - Slack Bot 用トークン・チャンネル（SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）

（実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください）

例（最小セットのインストール）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# 追加で必要なパッケージがあれば都度インストール
```

---

## 環境変数 / 設定

kabusys の設定は環境変数で行います（kabusys.config.Settings 経由で取得）。

主要な環境変数（必須は README 内で明示）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants 用リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu ステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack 通知先チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト development）
- LOG_LEVEL (任意) — DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト INFO）

自動 .env ロード:
- パッケージ初期化時にプロジェクトルート（.git または pyproject.toml を探索）から `.env` -> `.env.local` を読み込みます（OS 環境変数が優先）。  
- 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストなどで利用）。

.env ファイルを作る際は .env.example を参照してください（プロジェクトに存在する想定）。

---

## セットアップ手順（開発向けの一例）

1. リポジトリをクローン
```bash
git clone <repo-url>
cd <repo>
```

2. 仮想環境と依存関係のインストール
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"  # プロジェクトに pyproject.toml / extras があれば
# または最低限:
pip install duckdb openai defusedxml
```

3. 環境変数を設定
- プロジェクトルートに `.env` または `.env.local` を作成し、必要なキーを設定します（JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。

4. DuckDB ファイルの準備（初回はこのままでも作成されます）
- デフォルトパスは `data/kabusys.duckdb`（Settings.duckdb_path）

5. 監査 DB 初期化（監査専用 DB を作る例）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可能
```

---

## 使い方（主要ユースケース）

以下は Python API を直接呼び出す例です。スクリプトやジョブから利用してください。

- 設定と DuckDB 接続準備
```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
```

- 日次 ETL を実行（run_daily_etl）
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を明示することでルックアヘッドバイアスを避けられます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメントのスコアを付与（OpenAI を使用）
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（ETF 1321 の MA200 とマクロセンチメントを合成）
```python
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査スキーマを既存の DuckDB 接続に導入
```python
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 研究用: ファクター計算・IC・統計
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

target = date(2026, 3, 20)
mom = calc_momentum(conn, target)
fwd = calc_forward_returns(conn, target, horizons=[1,5,21])
ic = calc_ic(mom, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

- J-Quants API を直接使う（例: id_token 取得）
```python
from kabusys.data.jquants_client import get_id_token
token = get_id_token()  # 環境変数 JQUANTS_REFRESH_TOKEN を使用
```

注意点:
- OpenAI 呼び出しはモデルや API 仕様に依存します（ライブラリのバージョン差分に注意）。
- ETL や AI スコア処理は外部 API 呼び出しを伴うため、ネットワークや API レート制限を考慮してください。

---

## よく使う API の説明（補足）

- data.pipeline.run_daily_etl(...)
  - 市場カレンダー ETL → 株価 ETL → 財務 ETL → 品質チェック の順で実行し ETLResult を返す。

- ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 指定のタイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）に該当するニュースを銘柄ごとに集約し、OpenAI に一括評価を行い ai_scores テーブルへ保存する。

- ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF 1321 の 200 日 MA 乖離（重み 70%）＋マクロニュース LLM スコア（重み 30%）で市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ保存する。

- data.news_collector.fetch_rss(url, source, timeout=30)
  - RSS を取得して記事リストを返す。SSRF 防御・受信サイズ制限・gzip 対応あり。

- data.jquants_client.fetch_daily_quotes / save_daily_quotes
  - J-Quants から日足を取得し、raw_prices テーブルへ冪等的に保存する。get_id_token() による自動トークンリフレッシュと RateLimiter を備える。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソースツリー（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (ETL インターフェース再エクスポート)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - (その他: schema 初期化等)
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/（上記）
  - research/（上記）

各モジュールの詳細はファイル先頭の docstring（英日混在）で設計方針と処理フローが記載されています。実装を変更する際は docstring を参考にしてください。

---

## テスト・開発時の注意

- 環境変数自動ロードを無効化：KABUSYS_DISABLE_AUTO_ENV_LOAD=1（ユニットテストで外部環境への依存を断つ場合に有用）
- OpenAI コールは外部依存が大きいためユニットテスト時は該当関数（_call_openai_api 等）をモックしてください（コード内にその目的のコメントあり）。
- DuckDB の executemany の挙動（空リスト不可など）に注意（既に処理中に対策済みの箇所あり）。

---

必要であれば、この README をベースに「運用手順（Cron／Airflow ジョブの例）」「.env.example のテンプレート」「サンプル SQL スキーマ（raw_prices などの CREATE TABLE）」を追加します。どれを優先して作成しますか？