# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ群。  
ETL（J-Quants）による市場データ収集、ニュース収集・NLP、ファクター計算、監査ログ（発注・約定）といった基盤機能を提供します。

---

## プロジェクト概要

KabuSys は以下の主要機能を持つ Python パッケージです。

- J-Quants API からの株価・財務・カレンダー取得（差分取得・ページネーション・レート制御・リトライ付き）
- DuckDB を用いた永続化（冪等保存）
- ニュース収集（RSS）とニュースの前処理、銘柄紐付け
- OpenAI を使ったニュースセンチメント / マクロセンチメント評価（JSON mode + 再試行ロジック）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 市場カレンダー管理（営業日判定、next/prev/trading days）
- 監査ログ（signal / order_request / executions）のスキーマ初期化と DB 操作ユーティリティ
- 環境変数・設定管理（.env 自動読み込み機能あり）

設計方針として、バックテストにおけるルックアヘッドバイアスを避けるため、日付取得に datetime.today()/date.today() の直接参照を最小限にし、ETL/解析は受け取った target_date に基づいて処理します。

---

## 主な機能一覧

- data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - レートリミット制御、401 の自動トークンリフレッシュ、リトライバックオフ
- data.pipeline
  - run_daily_etl（市場カレンダー → 株価 → 財務 → 品質チェック を順に実行）
  - run_prices_etl / run_financials_etl / run_calendar_etl（個別 ETL）
  - ETLResult（実行結果の構造）
- data.news_collector
  - RSS フィード取得、前処理（URL除去・正規化）、raw_news 保存
  - SSRF 対策、gzip 上限チェック、トラッキングパラメータ除去
- ai.news_nlp
  - score_news（指定ウィンドウ内のニュースを集約して OpenAI に投げ、銘柄ごとにスコアを ai_scores に保存）
- ai.regime_detector
  - score_regime（ETF 1321 の MA200 乖離とマクロニュース LLM スコアを合成して market_regime を書き込み）
- research
  - calc_momentum / calc_value / calc_volatility（ファクター計算）
  - calc_forward_returns / calc_ic / factor_summary / rank（研究用統計）
- data.quality
  - check_missing_data / check_spike / check_duplicates / check_date_consistency / run_all_checks
- data.audit
  - init_audit_schema / init_audit_db（監査ログ用スキーマ作成、インデックス含む）
- config
  - Settings（環境変数からの設定取得）
  - 自動でプロジェクトルートの .env / .env.local を読み込む仕組み（無効化可）

---

## セットアップ手順

前提
- Python 3.10 以上（コードは | 型アノテーションなどを利用）
- システムに `duckdb` がインストールされること（pip からインストールします）

1. リポジトリをクローン（またはパッケージ配置）
2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate.bat  # Windows
   ```
3. 必要な依存パッケージをインストール
   ```
   pip install duckdb openai defusedxml
   ```
   - プロジェクトを開発インストールする場合（プロジェクトルートに pyproject.toml / setup.cfg がある想定）
   ```
   pip install -e .
   ```
   （必要に応じて追加パッケージを requirements にまとめてください）

4. 環境変数設定 (.env)
   プロジェクトルートに `.env` を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   必須の環境変数（少なくともこれらを設定してください）:

   - JQUANTS_REFRESH_TOKEN=（J-Quants のリフレッシュトークン）
   - KABU_API_PASSWORD=（kabuステーション API パスワード）
   - SLACK_BOT_TOKEN=（Slack Bot Token）
   - SLACK_CHANNEL_ID=（通知先 Slack チャンネル ID）
   - OPENAI_API_KEY=（OpenAI API キー。AI 機能を使う場合必須）

   任意 / デフォルトあり:
   - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト: data/monitoring.db）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト development）
   - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト INFO）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

※ 以下の例では DuckDB を利用します。DuckDB のファイルは `DUCKDB_PATH`（settings.duckdb_path）で指定できます。

1) DuckDB 接続の作成と ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")  # ファイルがなければ作成されます
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニューススコアリング（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
num_scored = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {num_scored} tickers")
```

3) 市場レジーム判定
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査DB初期化（監査用 DuckDB を別ファイルに作る例）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit_duckdb.duckdb")
# これで監査用テーブル(signal_events, order_requests, executions) とインデックスが作成されます
```

5) ファクター計算（研究用途）
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
d = date(2026, 3, 20)
mom = calc_momentum(conn, d)
val = calc_value(conn, d)
vol = calc_volatility(conn, d)
```

---

## 自動 .env 読み込みについて

- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` と `.env.local` を自動で読み込みます。
- 読み込み優先度: OS 環境変数 > .env.local > .env
- 自動読み込みを無効にするには環境変数を設定しておきます:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

---

## ディレクトリ構成

以下は主要ファイル／モジュールの一覧（src/kabusys 配下）。実際のリポジトリでは pyproject.toml 等がプロジェクトルートに存在する想定です。

- src/
  - kabusys/
    - __init__.py
    - config.py                         # 環境変数 / 設定管理（.env 自動読み込み含む）
    - ai/
      - __init__.py
      - news_nlp.py                      # ニュース NLP スコアリング（score_news）
      - regime_detector.py               # 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py                # J-Quants API クライアント（fetch/save 等）
      - pipeline.py                      # ETL パイプライン（run_daily_etl 等）
      - etl.py                           # ETLResult エクスポート
      - news_collector.py                # RSS ニュース収集（fetch_rss 等）
      - calendar_management.py           # 市場カレンダー管理（is_trading_day 等）
      - stats.py                         # 共通統計ユーティリティ（zscore_normalize）
      - quality.py                       # データ品質チェック
      - audit.py                         # 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py               # ファクター計算（momentum, value, volatility）
      - feature_exploration.py           # 将来リターン・IC・統計サマリー
    - monitoring/ (パッケージ名は __all__ に含まれていますが実装ファイルは省略)
    - strategy/ (戦略関連は別モジュールで追加想定)
    - execution/ (発注・broker integration 想定)

---

## 注意点 / 運用メモ

- OpenAI（gpt-4o-mini）を利用する機能は API キー（OPENAI_API_KEY）を必須とします。API 呼び出しは再試行や 5xx/429 対応を行いますが、課金やレートに注意してください。
- ETL は差分取得を基本とし、backfill 機能で直近数日を再取得して API の後出し修正を吸収します。
- ニュース収集は SSRF 対策や応答サイズ上限、XML の安全パーサ (defusedxml) を利用しています。
- DuckDB の SQL はオンメモリ・ファイルの両方に対応します。複数プロセスや同時実行時のロックに注意してください。
- 監査ログ（data.audit）は削除せず蓄積する前提で設計されています。order_request_id は冪等キーとして機能します。

---

## 連絡先 / Contributing

この README はコードベースの現状実装に基づく概要ドキュメントです。バグ報告や改善提案は Issue を立ててください。Pull Request 歓迎します。

---

以上。必要であればサンプル .env.example や docker-compose, CI 用の起動手順、より詳細な API リファレンス（関数毎の入力/出力例）を追加で作成します。どの部分のドキュメントを拡張しますか？