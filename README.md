# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からのデータ取得）・データ品質チェック・ニュース収集・LLM を使ったニュースセンチメント評価・市場レジーム判定・研究用ファクター計算・監査ログ（発注→約定のトレーサビリティ）などを提供します。

## 主要な特徴
- J-Quants API を用いた差分 ETL（株価・財務・市場カレンダー）
  - レート制限・リトライ・トークン自動リフレッシュを内蔵
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ニュース収集（RSS）と前処理（URL 正規化・SSRF 対策）
- OpenAI（gpt-4o-mini）を用いたニュース NLP（銘柄ごとのセンチメント）と市場レジーム判定
  - JSON Mode を使った堅牢なレスポンス検証・リトライ処理
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- 研究モジュール（モメンタム、バリュー、ボラティリティ、将来リターン、IC、統計サマリー）
- 監査ログ（signal_events / order_requests / executions）スキーマ生成ユーティリティ
- 設定は環境変数またはルートの `.env` / `.env.local` から自動読み込み（必要に応じて無効化可能）

---

## 機能一覧（モジュール別）
- kabusys.config
  - 環境変数読み込み・設定アクセス（自動 `.env` ロード、必須キーチェック）
- kabusys.data
  - jquants_client: J-Quants API クライアント（取得/保存関数）
  - pipeline / etl: 日次 ETL パイプライン（差分取得・品質チェック）
  - news_collector: RSS 収集・前処理・raw_news 保存
  - calendar_management: 市場カレンダー管理・営業日判定ユーティリティ
  - quality: データ品質チェック（QualityIssue）
  - stats: 汎用統計（Zスコア正規化等）
  - audit: 監査ログスキーマの初期化・監査用 DB 作成ユーティリティ
- kabusys.ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメント算出 → ai_scores に書き込み
  - regime_detector.score_regime: ETF(1321) MA200 乖離とマクロニュースの LLM 評価から市場レジーム判定 → market_regime に書き込み
- kabusys.research
  - factor_research: calc_momentum, calc_value, calc_volatility
  - feature_exploration: calc_forward_returns, calc_ic, factor_summary, rank

---

## 必須環境変数
主に以下を利用します。README 例の .env を参照して設定してください。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- SLACK_BOT_TOKEN: 通知用 Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリング系で必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: environment（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

自動ロードを無効化する:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

プロジェクトルートの `.env` / `.env.local` は自動で読み込まれます（.git または pyproject.toml を基準に探索）。

簡易の .env.example:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 環境を作成（推奨: Python 3.10 以上）
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   ```

3. 必要なパッケージをインストール  
   （プロジェクトに requirements.txt / pyproject.toml がある想定。無い場合は主要依存をインストール）
   ```
   pip install duckdb openai defusedxml
   # さらに必要に応じて: pip install -e .
   ```

4. 環境変数を設定  
   プロジェクトルートに `.env` を作成するか、環境変数をエクスポートします。

5. データディレクトリ作成（例）
   ```
   mkdir -p data
   ```

---

## 初期化 / 基本的な使い方（サンプル）
以下はライブラリ API を直接呼ぶ最小例です。詳細は各モジュールの docstring を参照してください。

- DuckDB 接続を作成して監査 DB の初期化:
```python
import duckdb
from kabusys.data.audit import init_audit_db

# ファイル DB を初期化（親ディレクトリを自動作成）
conn = init_audit_db("data/kabusys_audit.duckdb")
# すでに存在する DB に接続して init_audit_schema を呼ぶ場合は
# conn = duckdb.connect("data/kabusys.duckdb")
# from kabusys.data.audit import init_audit_schema
# init_audit_schema(conn, transactional=True)
```

- 日次 ETL の実行（run_daily_etl）
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026,3,20))
print(result.to_dict())
```

- ニュースセンチメントスコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
print(f"scored {n} codes")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
```

- 研究系ユーティリティ（例: モメンタム計算）
```python
from kabusys.research.factor_research import calc_momentum
records = calc_momentum(conn, target_date=date(2026,3,20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

---

## よくある運用ポイント / 注意事項
- Look-ahead バイアス回避: 多くの関数は内部で date.today() を使わず、呼び出し側で target_date を渡す設計です。バックテスト等で必ず適切な date を渡してください。
- OpenAI 呼び出し: レスポンスの JSON バリデーションやリトライ処理をしていますが、API キーの割当やコストに注意してください。レスポンスの形式が崩れた場合は安全側にフォールバック（0.0）します。
- J-Quants API: レート制限（120 req/min）に対応する RateLimiter を内蔵しています。トークンの自動リフレッシュにも対応。
- .env 自動ロード: プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動で読み込みます。テスト時などに無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB executemany の注意: DuckDB のバージョンによっては空リストの executemany が許容されないため、空チェックを行ってから実行しています。

---

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境設定・.env 自動読み込み
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（銘柄別）と AI 呼び出し処理
    - regime_detector.py — 市場レジーム判定（MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py — ETL の主処理（run_daily_etl 等）
    - etl.py — ETLResult のエクスポート
    - news_collector.py — RSS 取得 / 前処理 / raw_news 保存
    - calendar_management.py — 市場カレンダー管理・営業日判定
    - quality.py — データ品質チェック群
    - stats.py — 統計ユーティリティ（zscore_normalize 等）
    - audit.py — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py — 将来リターン / IC / 統計サマリー

---

## 開発 / テストに関するヒント
- 外部 API を叩く箇所（J-Quants / OpenAI / RSS）にはモック差し替え対象のヘルパー関数を用意しているので、ユニットテストでは patch して外部通信を抑制してください（例: kabusys.ai.news_nlp._call_openai_api のモックなど）。
- 自動 .env ロードがテストによって副作用を与える場合は KABUSYS_DISABLE_AUTO_ENV_LOAD をセットしてください。
- DuckDB のスキーマや初期化処理は audit.init_audit_schema 等の関数で実行できます。監査 DB を別ファイルで運用することを推奨します（データの分離）。

---

以上が本リポジトリの概要と基本的な使い方です。各モジュールの docstring（コード内コメント）に設計方針や詳細が細かく記載されていますので、実装や拡張を行う際はそちらも参照してください。必要であれば README に入れる追加サンプルや運用手順（CI / デプロイ / cron ジョブ例）を作成します。どの情報を追記しますか？