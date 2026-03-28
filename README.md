# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリ。  
ETL（J-Quants からのデータ収集）、データ品質チェック、ニュース収集・NLP による銘柄スコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（オーダー／約定追跡）などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ基盤とリサーチ／売買ロジックの共通実装群を収めたパッケージです。主な目的は以下です。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- RSS ベースのニュース収集と LLM による銘柄センチメント分析
- マーケットレジーム判定（ETF + マクロニュースの組合せ）
- ファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ、IC など）
- 発注〜約定まで追跡可能な監査ログスキーマ（DuckDB ベース）

設計上の特徴：
- Look-ahead バイアスを避ける（内部で date.today() を不用意に参照しない実装）
- DuckDB を用いたローカル DB 管理（ETL・監査ログ用）
- J-Quants / OpenAI 呼び出しに対するリトライ・レート制御・フェイルセーフ実装
- 冪等（idempotent）でのデータ保存

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数、認証トークン管理、レート制御、リトライ）
  - カレンダー管理（営業日判定、next/prev_trading_day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news への保存）
  - データ品質チェック（欠損、スパイク、重複、未来日付/非営業日検査）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news: 銘柄ごとのセンチメントを ai_scores テーブルへ書込）
  - マーケットレジーム判定（score_regime: ETF の MA + マクロニュースセンチメント合成）
  - OpenAI 呼び出しは gpt-4o-mini（JSON mode）を想定。テスト時に内部呼出しをモック可能
- research
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数の読み込み（.env/.env.local 自動ロード）と settings オブジェクトを提供

---

## セットアップ手順

想定: Python 3.9+（型記法に応じた環境）。必要なパッケージはプロジェクトで使用するライブラリ（duckdb, openai, defusedxml など）です。以下は一例です。

1. リポジトリをクローン／チェックアウト

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール（例）

   ```bash
   pip install duckdb openai defusedxml
   # その他に必要なパッケージがあれば追加でインストールしてください
   ```

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを使用してください）

4. 環境変数の設定

   プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと、kabusys.config が自動で読み込みます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必要な主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: 通知用
   - DUCKDB_PATH (任意): デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH (任意): デフォルト `data/monitoring.db`
   - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
   - LOG_LEVEL: DEBUG / INFO / ...（デフォルト INFO）

   .env 例（短縮）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=xxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C012345
   ```

---

## 使い方（主要なユースケース）

以下は Python REPL やスクリプトからの利用例です。DuckDB 接続は `duckdb.connect(settings.duckdb_path)` のように取得します。

- 設定オブジェクトにアクセス

```python
from kabusys.config import settings
print(settings.duckdb_path)  # Path オブジェクト
```

- 日次 ETL の実行（例: 今日分を ETL）

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュース NLP を実行して ai_scores に書き込む

```python
from datetime import date
from kabusys.ai.news_nlp import score_news
import duckdb

conn = duckdb.connect(str(settings.duckdb_path))
count = score_news(conn, target_date=date(2026, 3, 20))  # 例
print(f"scored {count} codes")
```

- マーケットレジーム判定

```python
from kabusys.ai.regime_detector import score_regime
import duckdb
from datetime import date

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB 初期化（専用 DB を作る / in-memory も可）

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")   # ディレクトリ自動作成
# または
conn = init_audit_db(":memory:")
```

- OpenAI 呼び出しをテストでモックする  
  テスト時は ai.news_nlp._call_openai_api や ai.regime_detector._call_openai_api を unittest.mock.patch して差し替え可能です。

---

## 簡単なワークフロー例

1. `.env` を用意して J-Quants / OpenAI キーを設定
2. DuckDB 接続を作成（settings.duckdb_path）
3. run_daily_etl を実行して prices / financials / calendar を更新
4. news_collector を回して raw_news を追加（外部ジョブ）
5. score_news を実行して ai_scores を更新
6. score_regime を実行して market_regime を更新
7. research モジュールでファクター計算や IC 評価を行う
8. 監査ログを初期化し、実稼働時は signal → order_request → executions を記録

---

## ディレクトリ構成（主要ファイル）

概略（src/kabusys 以下）:

- kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py           — ニュース NLP（score_news）
    - regime_detector.py    — マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py
    - etl.py                 — ETL 結果型再エクスポート
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - stats.py               — zscore_normalize 等
    - quality.py             — データ品質チェック
    - audit.py               — 監査ログスキーマ初期化
    - jquants_client.py      — J-Quants API クライアント（fetch / save）
    - news_collector.py      — RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py     — calc_momentum, calc_value, calc_volatility
    - feature_exploration.py — calc_forward_returns, calc_ic, factor_summary, rank

各ファイルには詳細な docstring と実装上の設計方針・フェイルセーフが記載されています。コード中の docstring を参照すると内部ロジックや注意点が分かります。

---

## 注意点 / 運用時のポイント

- 環境変数管理: config.Settings は環境変数を参照します。必須変数は未設定だと例外を投げます（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）。
- .env 自動ロード: プロジェクトルートを .git または pyproject.toml から探索し `.env` と `.env.local` を読み込みます。テストでは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化できます。
- Look-ahead バイアス対策: 多くの関数は target_date 未満 / 以前のデータのみ参照するなどの措置を取っています。バックテスト実行時は取得済みデータの時点管理に注意してください。
- OpenAI / J-Quants のレート制御とリトライ実装あり。API 呼び出し失敗時はフェイルセーフ（0.0 返却やスキップ）する設計の箇所がありますが、運用ポリシーに応じたエラーハンドリングが必要です。
- DuckDB の executemany に空リストを渡すと失敗するバージョンがあるため、コード内で空チェックを行っています。DuckDB のバージョンに注意してください。

---

## 開発・テスト

- OpenAI 呼び出しのモック: ai モジュール内の `_call_openai_api` を patch してテスト可能。
- J-Quants 呼び出しのモック: `kabusys.data.jquants_client._request` や `fetch_*` をモック（get_id_token も含む）。
- DuckDB を用いたユニットテストでは `:memory:` を指定してインメモリ DB を使うと高速に回せます。
- ログレベルは `LOG_LEVEL` 環境変数で調整可能。

---

この README はパッケージの利用開始および主要なワークフローに焦点を当てた概要です。詳細な挙動や引数の説明は各モジュールの docstring（ソース内コメント）を参照してください。README に不足があれば、追加したいセクション（例: API リファレンス、運用チェックリスト、例外ハンドリング方針等）を指定してください。