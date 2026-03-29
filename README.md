# KabuSys

日本株向けの自動売買／データパイプライン基盤ライブラリです。  
市場データの ETL、ニュースの収集・NLP スコアリング、ファクター計算、監査ログ／発注トレーサビリティ、マーケットカレンダー管理、LLM を使った市場レジーム判定など、投資システムの基盤機能を提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ」で、安全にデータを蓄積・解析できるように実装されています。

---

目次
- プロジェクト概要
- 機能一覧
- 必要環境・依存パッケージ
- セットアップ手順
- 環境変数（.env）設定例
- 使い方（主要 API の利用例）
- ディレクトリ構成
- 補足（設計上の注意点）

---

## プロジェクト概要

KabuSys は日本株の自動売買システムやリサーチ基盤で共通して必要となる機能群をモジュール化したパッケージです。  
主な用途は次の通りです。

- J-Quants API からのデータ取得（株価、財務、マーケットカレンダー）
- DuckDB を用いたデータ保存（冪等な保存ロジック）
- データ品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース RSS の収集と前処理（SSRF 対策・トラッキング除去）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント分析・市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログ（signal -> order_request -> execution のトレーサビリティ）
- マーケットカレンダー管理（営業日判定、next/prev_trading_day 等）

---

## 機能一覧

- data パッケージ
  - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save / token 管理、レートリミット・リトライ実装）
  - ニュース収集（RSS の取得・正規化・保存・SSRF 対策）
  - カレンダー管理（is_trading_day, next_trading_day, get_trading_days）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai パッケージ
  - ニュース NLP（score_news: ニュースを銘柄ごとに LLM でスコアリング）
  - レジーム判定（score_regime: ETF の MA とマクロニュースを合成して市場レジームを判定）
- research パッケージ
  - ファクター計算（calc_momentum, calc_volatility, calc_value）
  - 特徴量探索（calc_forward_returns, calc_ic, factor_summary, rank）
- config
  - 環境変数読み込みと設定管理（自動 .env ロード、必須チェック、環境判定）

---

## 必要環境・依存パッケージ

- Python 3.10 以上（モダンな型記法（|）等を使用）
- 必要パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

インストール例:
```bash
pip install duckdb openai defusedxml
```

プロジェクト固有に追加の依存があれば requirements.txt を用意して管理してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境であれば editable install:
     ```bash
     git clone <repo-url>
     cd <repo-root>
     pip install -e .
     ```
   - もしくは必要パッケージを pip で直接インストール（上記参照）。

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（デフォルト）。
   - 自動ロードを無効にしたい場合:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

3. DuckDB データベースやディレクトリを準備
   - デフォルトでは `data/kabusys.duckdb` を使います（設定で変更可能）。
   - 監査ログ専用 DB を初期化する場合は data ディレクトリを作成しておくと便利です。

---

## 環境変数（.env）例

主要な環境変数（必須・任意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必須 for AI 機能) — OpenAI API キー
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — 監視用 sqlite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

例 (.env):
```
JQUANTS_REFRESH_TOKEN=xxxx
OPENAI_API_KEY=sk-xxxx
KABU_API_PASSWORD=secret
SLACK_BOT_TOKEN=xoxb-xxxx
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

注意: config モジュールはプロジェクトルート（.git または pyproject.toml が基準）を探索して `.env` / `.env.local` を自動読み込みします。

---

## 使い方（主要 API の例）

以下は代表的な関数の使い方例です。すべて DuckDB の接続オブジェクト（duckdb.connect(...)）を渡して利用します。

1) DuckDB に接続して日次 ETL を実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアを計算して ai_scores に書き込む
```python
from kabusys.ai.news_nlp import score_news
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境に設定しておく
print("written:", n_written)
```

3) 市場レジームを判定して market_regime テーブルに書き込む
```python
from kabusys.ai.regime_detector import score_regime
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
rc = score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境に設定
print("rc:", rc)
```

4) ファクター計算（研究用途）
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date
import duckdb

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
vol = calc_volatility(conn, target_date=date(2026, 3, 20))
value = calc_value(conn, target_date=date(2026, 3, 20))
```

5) 監査ログ（テーブル）を初期化する
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")  # DB ファイルを作成し、テーブルを初期化します
```

---

## ディレクトリ構成（抜粋）

以下は package 内のおもなファイル／モジュール構成です（src/kabusys 以下）。

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
  - (その他補助モジュール)
- research/
  - __init__.py
  - factor_research.py
  - feature_exploration.py
- monitoring/, strategy/, execution/ 等（パッケージ初期化時に __all__ で公開予定）

（コードベースの各モジュールは README 作成時点の実装概要を先頭 docstring に記載しています。詳細は各ソースファイルをご参照ください。）

---

## 補足（設計上の注意点）

- ルックアヘッドバイアス防止:
  - 多くの処理は target_date を明示的に受け取り、datetime.today()/date.today() を直接参照しない設計です。バックテスト等では明示的な日付注入が推奨されます。
- 冪等性:
  - DB への保存は ON CONFLICT / DELETE+INSERT 等で冪等性を保つ実装が多用されています。
- フェイルセーフ:
  - LLM/API が失敗した場合でも処理を継続する（デフォルトでスコアに 0 を割り当てる等）設計です。
- セキュリティ:
  - news_collector は SSRF 対策、XML 攻撃対策（defusedxml）、レスポンスサイズ制限等を実装しています。
- 環境変数の自動ロード:
  - config.py はプロジェクトルートの `.env` / `.env.local` を自動で読み込みますが、テスト等で無効化するために KABUSYS_DISABLE_AUTO_ENV_LOAD を使えます。

---

README に書ききれない実装の詳細や API の細かい挙動は各モジュールの docstring を参照してください。必要であれば、各機能のサンプルスクリプトやユニットテストの雛形も提供できます。どの機能のサンプルが欲しいか教えてください。