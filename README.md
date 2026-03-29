# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J‑Quants からのデータ取得）、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログなどの機能を提供します。

---

## 特徴（概要）

- J‑Quants API からの株価・財務・カレンダーの差分取得 + DuckDB への冪等保存
- RSS ベースのニュース収集（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 / マクロ）
- レジーム判定（ETF 1321 の MA 乖離 と マクロセンチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化 等）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- 監査ログ（signal → order_request → execution のトレーサビリティ）を DuckDB に初期化・管理
- 環境変数 / .env 自動読み込み（プロジェクトルート検出）と設定ラッパー

設計上の注力点：
- ルックアヘッドバイアスを防ぐ（関数は date 引数を受け、date.today() に依存しない等）
- 冪等性（ON CONFLICT / 主キー設計）と堅牢なエラーハンドリング
- 外部 API 呼び出しはリトライ・バックオフ・レート制限を実装

---

## 主な機能一覧

- data
  - ETL: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J‑Quants クライアント（fetch/save daily_quotes / financials / market_calendar / listed info）
  - market_calendar（営業日判定、next/prev_trading_day、calendar_update_job）
  - news_collector: RSS 取得・正規化・raw_news 保存
  - quality: 欠損 / スパイク / 重複 / 日付不整合チェック
  - audit: 監査スキーマ初期化（init_audit_schema / init_audit_db）
  - stats: zscore_normalize 等
- ai
  - news_nlp.score_news: 銘柄別ニュースセンチメント算出 → ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF 1321 の MA 乖離 + マクロセンチメント → market_regime に書込
- research
  - ファクター計算: calc_momentum / calc_value / calc_volatility
  - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank
- config
  - Settings クラス: 環境変数管理（.env の自動ロード、必須チェック、パス設定）

---

## 動作環境・依存

- Python 3.10+
- 主なパッケージ（例）:
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセスが必要（J‑Quants API, RSS フィード, OpenAI API）

（実際の導入では requirements.txt / poetry / pyproject.toml を用意してください）

---

## 環境変数

主要な環境変数（必須・推奨）:

- JQUANTS_REFRESH_TOKEN — J‑Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime のデフォルト）
- KABU_API_PASSWORD — kabuステーション API のパスワード（本プロジェクトで使用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack チャンネル ID
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")
- LOG_LEVEL — ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")

自動でプロジェクトルートの `.env` と `.env.local` を読み込む仕様です。自動ロードを無効にするには:
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

.env の解析は Bash 風の export やクォート・コメントに対応しています。

---

## セットアップ手順（簡易）

1. Python の準備（3.10+ を推奨）
2. リポジトリをクローン / ソース配置
3. 必要なパッケージをインストール
   - 例:
     pip install duckdb openai defusedxml
   - 実際は requirements.txt / pyproject.toml に合わせてインストールしてください
4. .env をプロジェクトルートに作成（例は下記）
5. DuckDB 用ディレクトリを作成（必要なら）
   mkdir -p data

.env の最小例:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=CXXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 初期化例・使い方

以下はライブラリを直接使う際の簡単な例です。実行はプロジェクトルートで行ってください。

- DuckDB 接続の作成（ファイル DB）
```python
import duckdb
conn = duckdb.connect('data/kabusys.duckdb')
```

- 監査ログ用 DB を初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn_audit = init_audit_db('data/kabusys_audit.duckdb')
# または既存 conn に対してスキーマを追加
from kabusys.data.audit import init_audit_schema
init_audit_schema(conn, transactional=True)
```

- 日次 ETL 実行（J‑Quants からデータを取得して DuckDB に保存）
```python
from kabusys.data.pipeline import run_daily_etl
from datetime import date

result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント算出（OpenAI API キーは環境変数または引数で渡す）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date

written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
print(f"書込銘柄数: {written}")
```

- 市場レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date

score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

- 研究用ファクター計算例
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

mom = calc_momentum(conn, date(2026, 3, 20))
val = calc_value(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
```

- データ品質チェック
```python
from kabusys.data.quality import run_all_checks
issues = run_all_checks(conn, target_date=date(2026, 3, 20))
for i in issues:
    print(i)
```

注意点:
- OpenAI 呼び出しは料金発生するため、テスト時はモック化を推奨します（モジュール関数を patch 可能）。
- ETL / API 呼び出しはネットワーク・レート制限・リトライロジックがあります。大量バッチは注意してください。
- 関数は多くが date 引数を受け取り、バックテストでのルックアヘッドバイアスを避ける設計です。

---

## 主要モジュール（説明）

- kabusys.config
  - Settings: 環境変数取得・必須チェック・.env 自動読み込み
- kabusys.data.jquants_client
  - J‑Quants API の取得・保存処理（fetch_*/save_*）
  - rate limiter、id_token 自動リフレッシュ、ページネーション対応
- kabusys.data.pipeline
  - run_daily_etl を含む ETL パイプライン
- kabusys.data.news_collector
  - RSS 取得、前処理、raw_news への冪等保存（SSRF 対策・サイズ制限等）
- kabusys.ai.news_nlp / regime_detector
  - OpenAI を用いたセンチメント評価（銘柄別 / マクロ）とテーブル書込
- kabusys.research
  - ファクター計算・探索用ユーティリティ
- kabusys.data.quality
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
- kabusys.data.audit
  - 監査ログスキーマ定義・初期化（signal_events / order_requests / executions）

---

## ディレクトリ構成

プロジェクトの主要ファイル配置（抜粋）:

- src/
  - kabusys/
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
      - etl.py
      - news_collector.py
      - calendar_management.py
      - quality.py
      - stats.py
      - audit.py
      - audit.py
      - etc...
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/
    - monitoring/ (監視系モジュール、コードベースに応じて存在)
    - execution/ (注文実行系モジュール等)
    - strategy/ (戦略定義モジュール等)

上記はリポジトリ内の実装ファイルを抜粋したものです。各モジュールの docstring に詳細な設計方針と処理フローが記載されています。

---

## テスト・開発時のヒント

- AI / 外部 API を使う部分はユニットテストでモック化することを推奨します。
  - news_nlp._call_openai_api / regime_detector._call_openai_api などを patch 可能。
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、テスト用に環境値を明示的に注入してください。
- DuckDB はインメモリ（":memory:"）での利用やファイル DB が選べます。テストでは :memory: を利用すると簡単です。

---

## ライセンス・貢献

（ここにプロジェクトのライセンスや貢献ルールを記載してください）

---

README の内容は実装ドキュメント（各モジュールの docstring）を要約しています。詳細な API 仕様や運用手順は該当モジュールの docstring を参照してください。必要であれば、サンプルスクリプトや CLI、CI 設定ファイルのテンプレートも追加できます。