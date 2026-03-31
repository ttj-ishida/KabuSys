# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。ETL（J-Quants からのデータ取り込み）、ニュースの NLP スコアリング、マーケットレジーム判定、リサーチ用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含むモジュール群を提供します。

主な設計方針は「バックテストでのルックアヘッドバイアス防止」「DuckDB を中心としたデータ永続化」「API 呼び出しの堅牢化（リトライ／レート制御）」「冪等性」です。

---

## 機能一覧

- data
  - J-Quants API クライアント（差分取得、ページネーション、トークン自動リフレッシュ、レート制御）
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - 市場カレンダー管理（営業日判定、next/prev trading day、calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策、raw_news 保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化・DB（signal_events / order_requests / executions テーブル）
  - 各種保存ロジック（DuckDB への冪等保存）
- ai
  - ニュース NLP（gpt-4o-mini を用いた銘柄別センチメントスコア: score_news）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースセンチメントの合成: score_regime）
- research
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
- config
  - 環境変数 / .env 自動ロード（プロジェクトルートの検出、.env / .env.local の優先度）
  - settings オブジェクト経由で設定値取得
- utils
  - 統計ユーティリティ（zscore 正規化 等）

---

## セットアップ手順

1. リポジトリをチェックアウト
   - 例: git clone <repo_url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate もしくは .venv\Scripts\activate (Windows)

3. 依存パッケージのインストール
   - 必須/主要依存（このコードベースで参照されている例）
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml があればそちらを利用してください）
   - 開発インストール（プロジェクトルートに setup.py/pyproject が存在する場合）:
     - pip install -e .

4. 環境変数 / .env 設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env`（および任意で `.env.local`）を配置すると自動でロードされます（デフォルト）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. 必要な環境変数（主要）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL / jquants_client）
   - OPENAI_API_KEY: OpenAI 呼び出しに使用（ai.news_nlp / ai.regime_detector）。score_news / score_regime の呼び出しに必要
   - KABU_API_PASSWORD: kabuステーション等の発注 API パスワード（execution モジュールで使用）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: モニタリング通知用
   - DUCKDB_PATH: デフォルト "data/kabusys.duckdb"（変更可）
   - SQLITE_PATH: デフォルト "data/monitoring.db"
   - KABUSYS_ENV: environment ("development", "paper_trading", "live") — settings.env で検証
   - LOG_LEVEL: "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（settings.log_level）

---

## 使い方

以下は典型的な利用例（Python スクリプト内での呼び出し）。

- DuckDB 接続を作成して日次 ETL を実行する

```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメントを取得して ai_scores に書き込む

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
written = score_news(conn, target_date=date(2026, 3, 20))
print(f"書き込み銘柄数: {written}")
```

- 市場レジーム判定を実行する

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログ（audit DB）の初期化

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# この conn を使って監査テーブルにアクセスできます
```

- .env 自動ロードについて
  - パッケージ import 時にプロジェクトルートを探索し、`.env` と `.env.local` を順にロードします。
  - OS 環境変数が優先され、`.env.local` は `.env` を上書きします（システム環境変数は保護される）。
  - 自動ロードを停止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

注意点:
- ai モジュールは OpenAI の Chat Completions（JSON Mode）を利用する前提です。API レスポンスが期待通りでない場合はフェイルセーフで 0.0 スコアにフォールバックします。
- ETL / jquants_client は API レート制御・リトライ・トークン自動更新を備えていますが、実行前に J-Quants トークンを正しく設定してください。
- DuckDB の executemany に関する互換性考慮がコード内にあります（空パラメータは避ける等）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 配下）

- __init__.py
  - パッケージバージョン等
- config.py
  - settings: 環境変数読み込み・検証・.env 自動ロードロジック
- ai/
  - __init__.py
  - news_nlp.py        — ニュースの銘柄別 NLP スコアリング（score_news）
  - regime_detector.py — ETF MA とマクロニュースで市場レジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント（fetch / save 関数）
  - pipeline.py           — ETL パイプライン（run_daily_etl 等）
  - etl.py                — ETLResult の再エクスポート
  - calendar_management.py— 市場カレンダー管理（is_trading_day 等）
  - news_collector.py     — RSS 取得・前処理・保存
  - quality.py            — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py              — 汎用統計ユーティリティ（z-score 等）
  - audit.py              — 監査ログテーブル定義・初期化（signal_events / order_requests / executions）
- research/
  - __init__.py
  - factor_research.py    — モメンタム / バリュー / ボラティリティ計算
  - feature_exploration.py— 将来リターン / IC / 統計サマリー 等

---

## 追加情報 / 注意事項

- テスト時の差し替えポイント:
  - ai モジュール内の OpenAI 呼び出しは `_call_openai_api` をモックして差し替え可能です（ユニットテストで利用）。
  - news_collector の `_urlopen` もモック可能です。
- 日時の扱い:
  - バックテストや指標計算での「ルックアヘッドバイアス」対策が随所に組み込まれています（date.today()/datetime.today() を直接参照しないなど）。
- ライセンス / 貢献:
  - この README ではライセンス情報は含めていません。リポジトリの LICENSE ファイルや開発ポリシーに従ってください。

---

この README はコードベースから読み取れる設計・使用法をまとめたものです。実際の環境で実行する際は各 API キーや環境変数、DuckDB のスキーマ（テーブル定義）が適切に作成されていることを確認してください。必要であれば、具体的な実行コマンドやスキーマ初期化スクリプトを追加で提供します。