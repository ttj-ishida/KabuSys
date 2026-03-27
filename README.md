# KabuSys

日本株向けの自動売買 / データプラットフォーム基盤（部分実装）。  
ETL（J-Quants）→ データ品質チェック → ニュース収集 → LLM によるニュース/マクロ評価 → リサーチ / ファクター計算 → 監査ログ のワークフローを提供します。

主な目的は「ルックアヘッドバイアスを避けた時系列データ取得と解析」「ETL / 品質チェックの自動化」「LLM を用いたニュースセンチメント評価」「監査可能な発注ライフサイクルの保存」です。

バージョン: 0.1.0

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード（プロジェクトルート検出、.env / .env.local）
  - 必須環境変数の取得ユーティリティ
- データプラットフォーム（DuckDB ベース）
  - J-Quants からの差分 ETL（株価日足 / 財務 / JPX カレンダー）
  - ETL の集約エントリポイント（日次 ETL）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - ニュース収集（RSS、SSRF 対策、トラッキングパラメータ除去）
  - 監査ログ（signal / order_request / executions テーブル、冪等設計）
- AI（OpenAI）連携
  - ニュースを銘柄別に集約してセンチメントを算出（gpt-4o-mini, JSON mode）
  - マクロニュースと ETF MA乖離から市場レジーム判定（bull/neutral/bear）
  - リトライ / フェイルセーフ設計（API 失敗時は中立扱い等）
- リサーチ / ファクター
  - モメンタム / バリュー / ボラティリティ等のファクター計算
  - 将来リターン（forward returns）や IC（Information Coefficient）計算
  - Zスコア正規化など統計ユーティリティ

---

## 動作要件（推奨）

- Python 3.10 以上
- 必要外部ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス: J-Quants API, RSS ソース, OpenAI API（必要に応じて）
- 推奨: 仮想環境（venv / pyenv）

（requirements.txt はリポジトリに合わせて作成してください。例: duckdb, openai, defusedxml）

---

## セットアップ手順

1. リポジトリをクローンして仮想環境を作る
```bash
git clone <repo-url>
cd <repo-root>
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
# 追加の依存パッケージがあればここで pip install してください
```

2. 環境変数設定 (.env)
プロジェクトルートに `.env`（または `.env.local`）を配置します。自動読み込みはデフォルトで有効です（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

必要な環境変数（config.Settings 参照）:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants の refresh token
- KABU_API_PASSWORD (必須) — kabu ステーション API 用パスワード
- SLACK_BOT_TOKEN (必須) — Slack 通知（任意だが設定がある想定）
- SLACK_CHANNEL_ID (必須) — Slack チャネル ID
- OPENAI_API_KEY (AI モジュール利用時必須)
- KABUSYS_ENV (任意) — development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — DEBUG, INFO, WARNING, ERROR, CRITICAL（デフォルト: INFO）
- DUCKDB_PATH (任意) — デフォルト "data/kabusys.duckdb"
- SQLITE_PATH (任意) — 監視用 sqlite データベースパス（デフォルト "data/monitoring.db"）

例（.env）:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

3. DuckDB の準備（監査用 DB 初期化例）
Python REPL かスクリプトで監査テーブルを初期化します。`kabusys.data.audit.init_audit_db` を利用できます。

```python
from kabusys.config import settings
from kabusys.data.audit import init_audit_db

conn = init_audit_db(settings.duckdb_path)
# conn は duckdb 接続。以降 ETL 等で同じ DB を使ってください。
```

---

## 使い方（主要 API/ワークフロー例）

基本的に Python から関数を呼ぶ形で利用します。以下は主要な利用例です。

1. 日次 ETL 実行（株価 / 財務 / カレンダーの差分取得 → 品質チェック）
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(settings.duckdb_path)
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2. ニュースセンチメント（銘柄別）スコア化
```python
from datetime import date
import duckdb
from kabusys.config import settings
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(settings.duckdb_path)
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("wrote", n_written, "scores")
```
- OpenAI API キーを引数で渡すことも可: score_news(conn, target_date, api_key="sk-...")

3. 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM スコア合成）
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(settings.duckdb_path)
score_regime(conn, target_date=date(2026, 3, 20))
```

4. ファクター計算 / リサーチ
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect(settings.duckdb_path)
momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

5. ニュース収集（RSS） → raw_news 保存は news_collector を使用（関数 fetch_rss 等）

---

## 設計上の注意点 / ポイント

- ルックアヘッドバイアス防止:
  - モジュール内で datetime.today() / date.today() を直接参照しない設計が施されています（target_date を明示的に渡す）。
  - DB クエリで date < target_date 等の排他条件により未来データ参照を防止。
- 冪等性:
  - ETL の保存処理は ON CONFLICT DO UPDATE 等を使い再実行可能に設計。
  - 発注ログ（order_requests）に冪等キー order_request_id を用意。
- フェイルセーフ:
  - LLM や外部 API の失敗時は例外を投げず中立値で続行する箇所がある（一部はログ出力）。
  - ETL の各ステップは独立してエラーハンドリングされ、他ステップの継続を保証。
- API 呼び出し:
  - J-Quants には固定間隔レートリミッタとリトライロジックを実装。
  - OpenAI 呼び出しは retry/backoff の仕組みを実装（429/5xx/タイムアウト等に対応）。

---

## ディレクトリ構成

（主要ファイル・モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースを銘柄別に集約してLLMでスコア化
    - regime_detector.py     — ETF MA とマクロ LLM を合成した市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント & DuckDB 保存ロジック
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult エクスポート
    - news_collector.py      — RSS ニュース収集（SSRF 対策等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - quality.py             — データ品質チェック
    - stats.py               — 統計ユーティリティ（zscore 等）
    - audit.py               — 監査ログ（signal/order/execution テーブル）
  - research/
    - __init__.py
    - factor_research.py     — Momentum / Value / Volatility 等
    - feature_exploration.py — forward returns, IC, factor_summary, rank
  - monitoring/               — 監視関連（実装があればここに配置）
  - execution/                — 発注・ブローカー連携（将来的なモジュール）
  - strategy/                 — 戦略定義（将来的なモジュール）
  - monitoring/               — （プレースホルダ）

この README は主要なモジュールをカバーした案内であり、各関数の詳細な仕様や DB スキーマ定義についてはソースコード内の docstring を参照してください。

---

## 開発 / テスト

- 環境変数読み込みの自動化はテスト時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- OpenAI 呼び出しなどはユニットテストでモック化（unittest.mock.patch）することを想定しています（ソース内に差し替えポイントあり）。
- DuckDB を ":memory:" で使えばテスト用のインメモリ DB を作成できます（例: init_audit_db(":memory:")）。

---

必要な追加ドキュメントやサンプル（requirements.txt、.env.example、DB スキーマ定義の SQL export、デモスクリプト等）があれば作成できます。どのドキュメントを優先して出力しましょうか？