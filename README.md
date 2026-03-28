# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集と LLM によるニュースセンチメント、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株向けの以下機能を提供する Python パッケージです。

- J-Quants API からの差分 ETL（株価日足 / 財務 / JPX カレンダー）
- RSS ニュース収集・前処理・raw_news への保存
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄別 ai_score）およびマクロセンチメントを組み合わせた市場レジーム判定
- 研究用途のファクター計算（モメンタム / ボラティリティ / バリュー 等）と統計ユーティリティ（Zスコア、IC 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal_events / order_requests / executions）の初期化と運用ヘルパー
- 設定は環境変数（.env）から読み込み、duckdb を主要なオンディスク DB として利用

設計上のポイント:
- ルックアヘッドバイアス対策（内部で date.today() を不用意に参照しない・DB クエリで排他条件を使用）
- 外部 API 呼び出しは再試行・バックオフ・フォールバック（失敗時に安全側へ）を実装
- DuckDB を用いた効率的な SQL 処理
- 冪等性を意識した保存ロジック（ON CONFLICT / DELETE→INSERT など）

---

## 主な機能一覧

- kabusys.data
  - ETL パイプライン: run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl
  - J-Quants クライアント（取得・保存関数）: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar / save_*
  - カレンダー管理（営業日判定 / next/prev / calendar_update_job）
  - ニュース収集: RSS → raw_news（SSRF 対策・サイズ制限・トラッキングパラメータ除去）
  - 品質チェック: check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
  - 監査ログ初期化: init_audit_schema / init_audit_db
  - 統計ユーティリティ: zscore_normalize

- kabusys.ai
  - ニュースセンチメント解析: score_news (銘柄別 ai_score)
  - マーケットレジーム判定: score_regime (ETF 1321 の MA200 とマクロニュースを合成)

- kabusys.research
  - ファクター計算: calc_momentum / calc_volatility / calc_value
  - 特徴量探索: calc_forward_returns / calc_ic / factor_summary / rank

- 設定管理
  - 環境変数ロード（.env/.env.local をプロジェクトルートから自動読み込み、優先度 OS > .env.local > .env）
  - 設定アクセス: kabusys.config.settings

---

## 必要条件 / 依存

- Python 3.10+
- 主要外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- （ネットワークアクセスを伴うため）J-Quants API アクセス情報、OpenAI API キー 等が必要

requirements.txt は本リポジトリに合わせて用意してください（本 README はコードベースからの要件を想定しています）。

---

## セットアップ手順

1. リポジトリをクローンしてインストール（開発モード推奨: src 配置を想定）
   - pip（プロジェクトルートで）
     ```
     python -m pip install -e .
     ```

2. 必要ライブラリのインストール（例）
   ```
   python -m pip install duckdb openai defusedxml
   ```

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml がある場所）から .env / .env.local を自動読み込みします。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   主要な環境変数（最低限必要なもの）
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx

   # OpenAI
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

   # kabuステーション（注文実行等）
   KABU_API_PASSWORD=your_kabu_password
   KABU_API_BASE_URL=http://localhost:18080/kabusapi  # 任意（デフォルトあり）

   # Slack (通知等)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567

   # システム設定（任意）
   KABUSYS_ENV=development  # 有効値: development, paper_trading, live
   LOG_LEVEL=INFO           # DEBUG/INFO/WARNING/ERROR/CRITICAL
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

   - 必須項目が欠けていると settings の該当プロパティで ValueError が発生します（例: settings.jquants_refresh_token）。

4. データベース用ディレクトリ・ファイルを用意
   - デフォルトは data/kabusys.duckdb（duckdb）と data/monitoring.db（sqlite）です。必要に応じてフォルダを作成してください（init 関数は親ディレクトリを自動作成します）。

---

## 使い方（簡単な例）

- DuckDB 接続を作成して日次 ETL を実行する例:

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
# ETL を実行（target_date を省略すると今日）
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニュースセンチメント解析（ai_scores への書き込み）:

```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- マーケットレジーム判定（market_regime への書き込み）:

```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ DB の初期化（専用ファイルに作成）:

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn は初期化済みの DuckDB 接続
```

注意点:
- OpenAI の呼び出しには OPENAI_API_KEY（あるいは score_* に api_key を直接渡す）が必要です。API 呼び出しはリトライを行いますが、テストでは _call_openai_api をモックすることが可能です。
- J-Quants の呼び出しは JQUANTS_REFRESH_TOKEN を用いて id_token を取得します。

---

## 環境変数 / 設定（要点）

- 自動 .env ロード
  - プロジェクトルート（.git または pyproject.toml を含むパス）から .env および .env.local を自動ロードします。
  - ロード優先度: OS 環境変数 > .env.local > .env
  - 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 重要なキー（Settings API 経由でアクセス可能）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - KABU_API_BASE_URL（任意、デフォルトあり）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - KABUSYS_ENV（development / paper_trading / live）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

---

## テスト / 開発ノート

- OpenAI 呼び出しのユニットテストでは各モジュール内の _call_openai_api を patch して外部呼び出しをモックできます（news_nlp と regime_detector はそれぞれ独立実装）。
- news_collector は SSRF 対策や gzip サイズチェックなど行っているため、テストでは _urlopen を差し替えることで制御できます。
- DuckDB バージョンにより executemany で空リストが拒否される実装上の考慮が一部にあるため、モジュールのテスト / 実行時は互換性に注意してください。

---

## ディレクトリ構成

（主要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py               - 環境変数 / 設定ロードロジック
  - ai/
    - __init__.py
    - news_nlp.py           - ニュースセンチメント解析（ai_scores 書き込み）
    - regime_detector.py    - マーケットレジーム判定（market_regime 書き込み）
  - data/
    - __init__.py
    - pipeline.py           - ETL パイプライン（run_daily_etl 他）
    - jquants_client.py     - J-Quants API クライアント（fetch / save）
    - calendar_management.py- マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py     - RSS ニュース収集・前処理
    - quality.py            - データ品質チェック
    - stats.py              - Zスコア等の統計ユーティリティ
    - audit.py              - 監査ログテーブル初期化 / init_audit_db
    - etl.py                - ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py    - ファクター計算（momentum / value / volatility）
    - feature_exploration.py- 将来リターン / IC / 統計サマリー

ソース全体は src 配下に配置されているため、pip install -e . などでパッケージ化して利用できます。

---

## ライセンス / 貢献

この README にはライセンス情報が含まれていません。実プロジェクトでは LICENSE ファイルを含め、コントリビューションガイド（CONTRIBUTING.md）を用意してください。

---

必要ならば README にサンプル .env.example、CI 実行手順、より詳しい API 使用例（kabu ステーション連携、order lifecycle）やデータスキーマ（テーブル定義）を追加します。どの情報を優先して追加しますか？