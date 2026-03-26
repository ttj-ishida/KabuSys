# KabuSys

日本株向けの自動売買・データ基盤ライブラリ。J-Quants や RSS / OpenAI（LLM）を組み合わせ、データ ETL、ニュースセンチメント解析、因子研究、監査ログ、カレンダー管理、発注監査などの基盤機能を提供します。

主な設計方針：Look-ahead バイアス回避、DuckDB を中心とした冪等保存、API リトライ & レート制御、セキュリティ対策（SSRF 等）、LLM 呼び出しのフェイルセーフ処理。

---

## 機能一覧

- データ取得 / ETL
  - J-Quants からの株価日足・財務データ・上場情報取得（ページネーション対応）
  - 市場カレンダー取得・更新（JPX）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
  - DuckDB への冪等保存（ON CONFLICT を利用）

- データ品質管理
  - 欠損チェック、重複チェック、スパイク検出、日付整合性チェック
  - 品質問題の集約（QualityIssue）

- ニュース収集と NLP（LLM）
  - RSS フィード取得・前処理（URL 正規化・トラッキング除去・SSRF 防御）
  - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI に JSON モードで送信
  - ai_scores テーブルへの書き込み（最大バッチ処理・リトライ・レスポンス検証）
  - 市場レジーム判定（ETF 1321 の MA200 乖離 + マクロニュースセンチメントの合成）

- リサーチ / ファクタ計算
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials）
  - 将来リターン計算、IC（Spearman）の計算、ファクター統計要約
  - Z スコア正規化ユーティリティ

- 監査（トレーサビリティ）
  - signal_events, order_requests, executions の監査テーブル定義・初期化
  - order_request_id を冪等キーとして二重発注を防止
  - 監査 DB 初期化ユーティリティ

- ユーティリティ
  - J-Quants クライアント（レートリミット・401 自動リフレッシュ・リトライ）
  - カレンダー関連ヘルパー（is_trading_day, next_trading_day, prev_trading_day, get_trading_days）
  - 設定管理（.env 自動読み込み、必須 env の取得）

---

## 要件

- Python 3.10+
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じて他に `urllib3` など標準外の HTTP 依存が必要になる場合があります。パッケージを requirements.txt にまとめてください。）

---

## インストール

開発環境での例:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb openai defusedxml

3. パッケージを editable インストール（プロジェクト直下で）
   - pip install -e .

（プロジェクトに requirements.txt を用意する場合は pip install -r requirements.txt を使用してください）

---

## 環境変数（設定）

settings（kabusys.config.Settings）が参照する主要な環境変数：

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- KABUSYS_ENV (任意) — "development" | "paper_trading" | "live"（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env ロード:
- プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` → `.env.local` の順で自動読み込みします。
- テスト等で自動ロードを無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

例: .env（最低限必要な項目）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
KABU_API_PASSWORD=your_kabu_password_here
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ（初期化例）

DuckDB 監査 DB を初期化する例:

```python
from kabusys.data.audit import init_audit_db

# 監査用 DuckDB を初期化（ファイル DB または ":memory:"）
conn = init_audit_db("data/audit_duckdb.db")
# conn を使って監査テーブルにアクセスできます
```

DuckDB のメイン DB（データプラットフォーム）接続例:

```python
import duckdb
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
# ここにスキーマ作成用ユーティリティ（プロジェクトで提供されていれば）を呼び出す
```

---

## 使い方（代表的な呼び出し例）

- 日次 ETL 実行（run_daily_etl）:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースのセンチメントスコアリング（score_news）:

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を利用
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（score_regime）:

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算・解析（research）:

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.data.stats import zscore_normalize

conn = duckdb.connect(str(settings.duckdb_path))
momentums = calc_momentum(conn, date(2026, 3, 20))
normed = zscore_normalize(momentums, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
```

各関数は DuckDB 接続オブジェクトと日付を受け取り、副作用は主に DuckDB テーブルへの書き込み（score_news など）です。

---

## セキュリティ・運用上の注意

- Look-ahead bias を避ける設計：多くの処理は内部で date.today() を直接参照せず、呼び出し側が target_date を明示する設計です。バックテスト等では適切な過去データだけを利用してください。
- OpenAI 呼び出しは JSON mode を使い、レスポンスのバリデーションを行っていますが、LLM の出力が不正な場合はフェイルセーフとしてスコアを 0 にフォールバックします。
- J-Quants API はレート制限が厳守されます（固定間隔スロットリング）。ID トークン自動リフレッシュとリトライ処理を備えています。
- RSS 取得は SSRF 防御（ホストのプライベート判定・リダイレクト検査）、受信サイズ制限、defusedxml を使用した XML 安全化を行っています。
- DuckDB への保存は基本的に ON CONFLICT DO UPDATE で冪等性が担保されています。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py — ニュースの LLM スコアリングと ai_scores 書き込み
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - jquants_client.py — J-Quants API クライアント（取得/保存ユーティリティ）
  - news_collector.py — RSS 収集・前処理・raw_news へ保存
  - calendar_management.py — market_calendar 管理 / 営業日ヘルパー
  - stats.py — zscore_normalize 等ユーティリティ
  - quality.py — データ品質チェック
  - audit.py — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等
  - feature_exploration.py — 将来リターン / IC / 統計サマリー

（実コードは src/kabusys 以下の各モジュールに分割されています）

---

## 追加情報・運用ヒント

- テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして .env 自動ロードを無効化できます。
- OpenAI の API キーは環境変数 OPENAI_API_KEY または関数引数で注入できます（テストは引数注入が便利）。
- DuckDB ファイルの配置（settings.duckdb_path）や sqlite パスは環境変数で変更可能です。
- ETLResult は品質チェックの結果やエラーを集約して返すため、運用モニタリングやアラートトリガーに利用できます。

---

必要であれば、README に含める具体的な requirements.txt の候補や初期スキーマ作成スクリプト、運用ワークフロー（cron / Airflow / GitHub Actions）例も作成します。どの情報を追加しますか？