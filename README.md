# KabuSys

日本株向け自動売買・データ基盤ライブラリ（KabuSys）

簡潔な説明:
KabuSys は日本株のデータ取得（J-Quants）、ETL、品質チェック、ニュース NLP（LLM を用いたセンチメント）、市場レジーム判定、ファクター計算・リサーチ、監査ログ/発注トレーサビリティなどを統合した内部ライブラリ群です。DuckDB をデータ層に用い、OpenAI（gpt-4o-mini）をニュース解析に利用します。バックテストや本番オペレーションを支えるユーティリティ群を提供します。

---

## 主な機能

- データ取得・ETL
  - J-Quants API からの日次株価・財務データ・カレンダー取得（差分取得・ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL の統合実行（run_daily_etl）と ETL 結果オブジェクト（ETLResult）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などのチェック（quality モジュール）
- マーケットカレンダー管理
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / calendar_update_job
- ニュース収集
  - RSS フィード取得・前処理・raw_news への冪等保存（news_collector）
  - SSRF 対策、レスポンスサイズ制限、URL 正規化など安全設計
- ニュース NLP（LLM）
  - 銘柄ごとのニュースセンチメントを OpenAI へバッチ送信して ai_scores に保存（news_nlp.score_news）
  - マクロニュースを用いた市場レジーム判定（regime_detector.score_regime）
  - JSON Mode / 再試行・バックオフ・フェイルセーフ設計
- リサーチ / ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算（research モジュール）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env 自動読み込み（プロジェクトルート検出）、環境変数ラッパー（kabusys.config.settings）

---

## 要件

- Python 3.10+（typing の union 表記などを利用）
- 主要依存パッケージ（一例）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリの urllib、json、logging 等

（実プロジェクトでは pyproject.toml / requirements.txt を参照して必要パッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン、またはパッケージをチェックアウト

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements / pyproject があればそれを使用）

4. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須環境変数（少なくとも開発で必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu API のパスワード（発注等で使用）
     - SLACK_BOT_TOKEN — Slack 通知用トークン（オプションだが設定されていることを想定する箇所あり）
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI を直接使う場合（score_news / regime_detector の呼び出しで使用）
   - 任意（デフォルト有り）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/...、デフォルト INFO）

5. データベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（クイックスタート）

以下の例は各主要機能を簡単に呼び出す例です。実際にはロギング設定や例外ハンドリングを追加してください。

- DuckDB 接続の用意例

```python
import duckdb
from pathlib import Path
from kabusys.config import settings

db_path = settings.duckdb_path  # デフォルト data/kabusys.duckdb
conn = duckdb.connect(str(db_path))
```

- ETL（日次）実行

```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# target_date を指定しないと today を使用しますが、バックテスト時は明示すること
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（AI）

```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# OPENAI_API_KEY が環境変数に設定されている前提
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored codes: {count}")
```

- 市場レジーム判定（AI + MA）

```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査 DB 初期化（監査ログ用の専用 DB）

```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査テーブルへアクセス可能
```

- J-Quants API 直接利用例（データ取得のみ）

```python
from kabusys.data.jquants_client import fetch_daily_quotes, fetch_financial_statements

quotes = fetch_daily_quotes(date_from=date(2026,3,1), date_to=date(2026,3,20))
financials = fetch_financial_statements(date_from=date(2025,1,1), date_to=date(2026,3,20))
```

- リサーチ / ファクター計算

```python
from datetime import date
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

momentum = calc_momentum(conn, date(2026,3,20))
value = calc_value(conn, date(2026,3,20))
volatility = calc_volatility(conn, date(2026,3,20))
```

- データ品質チェック

```python
from kabusys.data.quality import run_all_checks

issues = run_all_checks(conn, target_date=date(2026,3,20))
for i in issues:
    print(i)
```

注意点:
- score_news / score_regime は OpenAI API を呼ぶため、API キーと使用料に注意してください。API 呼び出しは再試行・バックオフ・フェイルセーフ（失敗時は 0.0 等で継続）の実装があります。
- J-Quants API 呼び出しはレート制限とトークン自動リフレッシュを組み込んでいます。

---

## 設定（環境変数）

主要な設定は環境変数で行います。kabusys.config.Settings からアクセス可能です（settings = Settings()）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabu API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 経由で使用）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV — one of {development, paper_trading, live}（デフォルト development）
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）

.env 自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索し、`.env` と `.env.local` を自動で読み込みます。
- 読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュール一覧）

- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/ai/
  - __init__.py
  - news_nlp.py              — ニュースセンチメント（OpenAI）と score_news
  - regime_detector.py       — マクロ + MA を用いた市場レジーム判定
- src/kabusys/data/
  - __init__.py
  - jquants_client.py        — J-Quants API クライアント（fetch / save）
  - pipeline.py              — ETL パイプライン（run_daily_etl 等）と ETLResult
  - etl.py                   — ETL の公開インターフェース（ETLResult 再エクスポート）
  - calendar_management.py   — 市場カレンダーヘルパー・更新ジョブ
  - news_collector.py        — RSS ニュース収集・前処理・安全対策
  - quality.py               — データ品質チェック
  - stats.py                 — zscore_normalize 等の統計ユーティリティ
  - audit.py                 — 監査ログ（テーブル DDL, init_audit_schema/init_audit_db）
- src/kabusys/research/
  - __init__.py
  - factor_research.py       — Momentum / Value / Volatility 等
  - feature_exploration.py   — 将来リターン, IC, factor_summary, rank
- src/kabusys/research/* (その他ファイル)
- そのほか、strategy / execution / monitoring 等のパッケージ名が __all__ に含まれますが、実装は拡張対象です。

---

## 実運用上の注意

- API キーやトークンは機密情報です。`.env` を VCS にコミットしないでください。
- OpenAI の呼び出しはコストが発生します。バッチサイズやモデル（gpt-4o-mini）を適宜調整してコスト管理してください。
- J-Quants のレート制限やエラーハンドリングは実装済みですが、長時間バッチや大規模ページネーション時は運用監視を行ってください。
- DuckDB の executemany における空リスト制約など、バージョン互換の注意があります（コード内にワークアラウンドあり）。

---

## 貢献 / 開発者向け

- プロジェクトルートの pyproject.toml / .git によって .env 自動読み込みが働きます。
- テストを書く場合、外部 API 呼び出し（OpenAI / J-Quants / HTTP）をモックすることを推奨します（コード中に差し替えフックやモック対象の関数名が明記されています）。
- ローカルでの開発時は KABUSYS_ENV を `development` に設定してください。paper_trading/live モードは発注周りの挙動に影響する可能性があります。

---

README はここまでです。必要であれば以下を追加で作成します:
- .env.example のテンプレート
- 起動スクリプト（systemd / cron / GitHub Actions 用のサンプル）
- 詳細な API リファレンス（各関数の引数と返り値の一覧）
希望があればお知らせください。