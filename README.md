# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ群。  
ETL（J-Quants からのデータ取得）、データ品質チェック、ニュースの NLP 評価、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定トレース）などを提供します。

---

## 概要

KabuSys は日本株向けのデータ基盤および研究・自動売買のためのユーティリティ群です。主な目的は以下です。

- J-Quants API からの差分 ETL（株価、財務、取引カレンダー）
- DuckDB を利用したデータ保存・クエリ
- ニュース収集・NLP による銘柄単位センチメントスコア算出（OpenAI）
- 市場レジーム判定（ETF MA とマクロニュースの組合せ）
- ファクター計算・特徴量解析（研究用）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（シグナル→発注→約定のトレーサビリティ）
- kabuステーション等への発注連携や Slack 通知のための設定管理

設計上のポイント:
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない）
- 冪等性（DB への保存は ON CONFLICT 等で上書き）
- フェイルセーフ：外部 API 失敗時は適切にフォールバックし処理継続
- テスト可能性：API 呼び出しや時間依存処理の差し替えを考慮

---

## 機能一覧

- 設定管理
  - .env / 環境変数の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で各種設定にアクセス（J-Quants / kabu / Slack / DB パス等）

- Data（data/）
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - 市場カレンダー管理（is_trading_day, next_trading_day, get_trading_days 等）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - ニュース収集（RSS → raw_news、SSRF 対策・トラッキング除去）
  - 監査ログ初期化（init_audit_schema / init_audit_db）

- AI（ai/）
  - ニュース NLP：銘柄ごとのセンチメントを OpenAI で評価して ai_scores に書き込み（score_news）
  - レジーム判定：ETF (1321) の MA200 乖離とマクロニュースの LLM 評価を合成して market_regime に保存（score_regime）

- Research（research/）
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリー

- utils
  - 統計ユーティリティ（zscore_normalize）
  - 各種 API のリトライ/レート制御・フェイルセーフ実装

---

## 必要条件（目安）

- Python 3.10+
  - コード中に「X | Y」型注釈や型ヒントを使用しているため 3.10 以上を推奨します。
- 必要パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリで実装されている部分が多いですが、上記は必須/実運用向け）
- ネットワークアクセス（J-Quants API / RSS / OpenAI）

pip 等でインストールする場合の例:
pip install duckdb openai defusedxml

（プロジェクトをパッケージとして使う場合は setup / pyproject の依存に従ってください）

---

## 環境変数 / .env

自動的にプロジェクトルート（.git または pyproject.toml があるディレクトリ）から `.env` と `.env.local` をロードします。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（必須を含む）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API 用パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack ボットトークン
- SLACK_CHANNEL_ID (必須) — Slack 通知のチャンネル ID
- OPENAI_API_KEY — OpenAI API キー（score_news / score_regime 実行時に参照される）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視設定
- KABUSYS_ENV — 実行環境 (development / paper_trading / live)
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）

設定はコードから `from kabusys.config import settings` で取得できます。
例: settings.jquants_refresh_token, settings.duckdb_path

---

## セットアップ手順（ローカル向け）

1. リポジトリをクローン
   git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   python -m venv .venv
   source .venv/bin/activate

3. 依存パッケージをインストール
   pip install -U pip
   pip install duckdb openai defusedxml

   （プロジェクトに pyproject.toml/requirements.txt があればそちらを使用してください）

4. 環境変数設定
   - リポジトリルートに `.env`（および必要なら `.env.local`）を作成し、必要なキーを設定してください。
   - 例（.env）:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     KABU_API_PASSWORD=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
     DUCKDB_PATH=data/kabusys.duckdb

   - 自動ロードを無効化したい場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

5. データベース用ディレクトリ作成（必要に応じて）
   mkdir -p data

---

## 使い方（主要な操作例）

以下は Python REPL / スクリプトからの利用例です。適宜 import して関数を呼び出します。

- DuckDB 接続の準備:
```python
import duckdb
from datetime import date
conn = duckdb.connect(str("data/kabusys.duckdb"))
```

- 日次 ETL 実行（カレンダー・株価・財務取得 + 品質チェック）
```python
from kabusys.data.pipeline import run_daily_etl
res = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(res.to_dict())
```

- ニュース NLP スコア生成（OpenAI API キーは環境変数 OPENAI_API_KEY でも指定可）
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
count = score_news(conn, target_date=date(2026, 3, 20))
print("scored:", count)
```

- 市場レジーム判定（1321 MA200 とマクロニュース）
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
score_regime(conn, target_date=date(2026, 3, 20))
```

- ファクター計算 / 研究ユーティリティ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from kabusys.research.feature_exploration import calc_forward_returns, calc_ic

moms = calc_momentum(conn, date(2026,3,20))
vols = calc_volatility(conn, date(2026,3,20))
vals = calc_value(conn, date(2026,3,20))
```

- 監査ログスキーマ初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
audit_conn = init_audit_db("data/audit.duckdb")
# 以降 audit_conn に対して監査ログを挿入していく
```

- J-Quants クライアントを直接使う（テストやカスタム ETL のため）
```python
from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
token = get_id_token()  # settings.jquants_refresh_token が必要
records = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
```

---

## 注意点・運用上のポイント

- OpenAI 呼び出し時は API エラーやレート制限を考慮したリトライ/フォールバックが組み込まれていますが、API キーやコスト管理に注意してください。
- J-Quants API はレート制限が厳しいため、jquants_client は固定間隔スロットリングを実装しています。大量リクエスト時は運用設計を検討してください。
- ETL の差分取得は「最終取得日から backfill 日数分を再取得」する仕様になっており、API の「後出し修正」を吸収する設計です。
- データ品質チェックは Fail-Fast しない設計です。品質問題は検出されても ETL は継続し、呼び出し元で decide できます。
- .env の自動ロードはプロジェクトルート検出を行います。テスト環境で明示的に環境をセットしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- DuckDB executemany は空リストを受け付けない制約を考慮した実装がされています（空パラメータは挿入処理をスキップ）。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの NLP スコアリング（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - etl.py              — ETL インターフェース再エクスポート
    - pipeline.py         — ETL パイプライン実装（run_daily_etl 等）
    - jquants_client.py   — J-Quants API クライアント（fetch/save）
    - news_collector.py   — RSS ニュース収集
    - calendar_management.py — マーケットカレンダー管理
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン / IC / サマリー
  - ai, data, research 以下にさらに細分化された内部関数やヘルパーあり

---

## 開発 / テスト

- 外部 API 呼び出し（OpenAI / J-Quants / RSS）をモックすることでユニットテストが容易に書けます。実装内でもテスト差替え用に関数を分離している箇所が多くあります（例: _call_openai_api, _urlopen 等）。
- 環境依存の自動 .env 読み込みはテスト時に `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます。
- DuckDB のインメモリ接続(":memory:") を使って DB を用意すれば外部ファイルを汚さずにテスト可能です。

---

必要であれば以下を追加で作成できます：
- .env.example（必須環境変数のテンプレート）
- 起動スクリプト / systemd ユニット例 / cron ジョブ例
- 運用ドキュメント（バックテスト・本番切替・リトライポリシー詳細）

ご希望があれば README に .env.example のテンプレートや具体的な systemd / cron の例、より詳細な API 使用例（SQL スキーマやサンプルクエリ）を追加します。どの項目が必要か教えてください。