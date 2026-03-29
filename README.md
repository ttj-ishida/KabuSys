# KabuSys

日本株向けの自動売買／データプラットフォームライブラリです。  
市場データ取得（J-Quants）、ETL、ニュース収集・NLP、ファクター計算、監査ログ（トレーサビリティ）など、運用とリサーチの両面を想定したモジュール群を提供します。

主な設計方針
- ルックアヘッドバイアスを避ける（内部で date.today() を不用意に参照しない等）
- DuckDB をデータ格納基盤として利用（軽量かつ高速な分析向け）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（冪等／リトライ／フォールバック実装）
- J-Quants API からの差分ETL（レート制限／トークン自動リフレッシュ／リトライ）
- 監査ログ（signal → order_request → execution）を DuckDB に保持してトレーサビリティを担保

---

## 機能一覧

- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 等
- データ取得・ETL（kabusys.data）
  - J-Quants クライアント（fetch / save 関数）
  - 日次 ETL パイプライン（run_daily_etl）
  - マーケットカレンダー管理（is_trading_day / next_trading_day 等）
  - ニュース収集（RSS → raw_news、SSRF/サイズ制限対策付き）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ（audit）テーブルの初期化・管理
- AI（kabusys.ai）
  - ニュース NLP（score_news: 銘柄ごとのセンチメントを ai_scores に保存）
  - 市場レジーム判定（score_regime: ETF 1321 の MA とマクロニュースで bull/neutral/bear を判定）
  - LLM 呼び出しに対するリトライ・フォールバックロジック
- Research（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- ユーティリティ
  - 汎用統計（zscore_normalize）
  - DuckDB へ保存するためのユーティリティ群

---

## 動作環境と依存関係

- Python 3.10+
  - 型表記に PEP 604 の `|` を使用しているため 3.10 以上が必要です。
- 主要依存パッケージ（最低限）
  - duckdb
  - openai
  - defusedxml

（実行環境に応じてその他の標準ライブラリを利用します。必要に応じて追加のライブラリをインストールしてください。）

例（開発環境セットアップ）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリに入る
   - プロジェクトルートに `.git` または `pyproject.toml` があることを想定しています（config の自動 .env 読み込みに使用）。

2. 仮想環境を作成し依存パッケージをインストール
   - 例: pip で `duckdb`, `openai`, `defusedxml` をインストール。

3. 環境変数を設定
   - プロジェクトルートに `.env`（もしくは `.env.local`）を置くと自動読み込みされます（読み込みは config モジュールが .git / pyproject.toml を親に探索して実行）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

4. 必須の環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL で使用）
   - KABU_API_PASSWORD: kabuステーション連携時のパスワード
   - SLACK_BOT_TOKEN: Slack 通知用トークン（該当機能使用時）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しに用いる API キー（AI 関連機能で利用）
   - その他（任意）:
     - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live）
     - LOG_LEVEL（DEBUG/INFO/...）

例: .env（プロジェクトルート）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## 使い方（基本例）

下記は Python スクリプトや REPL から呼び出す基本的な操作例です。

- DuckDB へ接続して日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

# settings.duckdb_path で指定されたパスを使用
conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())  # ETLResult の要約
```

- ニュースの NLP スコアを計算して ai_scores に保存する
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str("data/kabusys.duckdb"))
# OPENAI_API_KEY は環境変数か api_key 引数で指定
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {n_written}")
```

- 市場レジーム判定（market_regime テーブルへ書き込み）
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ用 DB を初期化する（別 DB 推奨）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログへの書き込み/検索を行う
```

- リサーチ用のファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

注意点
- AI モジュールは OpenAI API を呼び出します。API キーを設定し、利用料・レートに注意してください。エラー時はフォールバック（スコア=0 等）する実装ですが、呼び出し量に応じたコスト管理が必要です。
- J-Quants の API 呼び出しはレート制限を守る実装がありますが、利用には J-Quants 側のアカウント・トークンが必要です。

---

## ディレクトリ構成（主要ファイル）

（リポジトリの src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                  — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py       — 市場レジーム判定（ETF 1321 MA + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save / auth / rate limit）
    - pipeline.py              — 日次 ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETLResult 再エクスポート
    - calendar_management.py   — マーケットカレンダー管理（営業日判定等）
    - news_collector.py        — RSS 収集（SSRF対策・サイズ制限等）
    - quality.py               — データ品質チェック
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py                 — 監査ログテーブル初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py       — Momentum/Value/Volatility 等
    - feature_exploration.py   — 将来リターン, IC, 統計サマリ等
  - research モジュールは data.stats を参照する設計です

主要な想定 DB テーブル（コード中で参照）
- raw_prices（または raw_prices テーブル群）
- raw_financials
- market_calendar
- raw_news / news_symbols
- ai_scores
- market_regime
- signal_events / order_requests / executions（監査ログ）

（ETL 実行前にスキーマの初期化や監査ログ用の init_audit_schema を実行してください）

---

## 補足と運用注意

- 環境変数の自動読み込み:
  - プロジェクトルート（.git もしくは pyproject.toml を基準）に `.env` / `.env.local` があると config モジュールが自動で読み込みます。
  - テスト時や明示的に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- AI 呼び出し:
  - ニュースとレジーム判定は OpenAI を利用します。API エラー発生時は安全側のデフォルト（スコア 0 や処理スキップ）にフォールバックする設計です。
- ETL と品質チェック:
  - run_daily_etl は複数のステップ（カレンダー → 株価 → 財務 → 品質チェック）を実行しますが、個別ステップはエラーを捕捉して続行するため、結果の ETLResult を確認して異常を検出してください。
- 監査ログ:
  - order_request_id を冪等キーとして扱うことで二重発注の防止を想定しています。実運用では order_request_id の生成・管理ルールを厳密にする必要があります。
- テスト:
  - AI 呼び出しや HTTP 通信部分はテストで差し替え（モック）できるよう設計されています（モジュール内の _call_openai_api や _urlopen など）。

---

もし README の例に CLI の追加、セットアップ用スクリプト、あるいは pyproject.toml / requirements.txt の雛形を追加したい場合は、その内容を教えてください。必要に応じて具体的な手順（システムd タイマー設定、Dockerfile、CI 用のテスト例など）も作成できます。