# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュースの NLP による銘柄スコアリング、ファクター計算、監査ログ（発注→約定トレーサビリティ）、マーケットカレンダー管理などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python パッケージです：

- J-Quants API から株価・財務・カレンダーデータを安全に取得・差分保存する ETL パイプライン
- RSS ニュース収集と OpenAI を用いたニュースセンチメント解析（銘柄別 ai_score の算出）
- 市場レジーム判定（ETF の MA200 乖離 + マクロニュースセンチメントの合成）
- 研究用途のファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック、カレンダー管理、監査ログ用スキーマ／初期化ユーティリティ

設計上の特徴：
- Look-ahead bias を防ぐため、内部で date.today() 等の暗黙参照を避け、明示的な target_date を多用
- DuckDB を主なストレージ（デフォルト path: data/kabusys.duckdb）
- 冪等性を考慮した保存ロジック（ON CONFLICT / INSERT ... DO UPDATE）や監査トレース
- 外部 API 呼び出しは適切なリトライ／レート制御を実装

---

## 主な機能一覧

- データ取得 / ETL
  - run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl（kabusys.data.pipeline）
  - J-Quants クライアント（kabusys.data.jquants_client）: fetch_* / save_* 関数、id_token 取得、レートリミットとリトライ実装
- ニュース収集 / NLP
  - fetch_rss, news 前処理、raw_news への保存ロジック（kabusys.data.news_collector）
  - score_news（kabusys.ai.news_nlp）: OpenAI（gpt-4o-mini）を用いた銘柄別センチメント（ai_scores）生成
- 市場レジーム判定
  - score_regime（kabusys.ai.regime_detector）: ETF（1321）の MA200 乖離とマクロニュースを合成して daily market_regime を算出
- 研究・ファクター
  - calc_momentum, calc_value, calc_volatility（kabusys.research.factor_research）
  - calc_forward_returns, calc_ic, factor_summary, rank（kabusys.research.feature_exploration）
  - zscore_normalize（kabusys.data.stats）
- データ品質チェック
  - check_missing_data, check_spike, check_duplicates, check_date_consistency, run_all_checks（kabusys.data.quality）
- マーケットカレンダー管理
  - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, calendar_update_job（kabusys.data.calendar_management）
- 監査ログ
  - init_audit_schema / init_audit_db（kabusys.data.audit）: 発注・約定トレース用テーブル定義と初期化

---

## 前提・依存関係

- Python 3.10+
- 必要となる外部ライブラリ（代表）
  - duckdb
  - openai
  - defusedxml
（プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してインストールしてください。）

---

## セットアップ手順

1. リポジトリをクローン／取得
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

4. パッケージのインストール（編集可能に）
   - pip install -e .

5. 環境変数 / .env ファイル
   - パッケージはプロジェクトルート（.git または pyproject.toml）を探索して自動的に `.env` と `.env.local` を読み込みます。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

6. 必要な環境変数（最低限）
   - JQUANTS_REFRESH_TOKEN : J-Quants の refresh token（jquants API 用）
   - KABU_API_PASSWORD : kabuステーション API パスワード（本パッケージ内の一部機能で利用）
   - SLACK_BOT_TOKEN : Slack 通知用（monitoring 等で利用）
   - SLACK_CHANNEL_ID : Slack 通知先チャンネル ID
   - OPENAI_API_KEY : OpenAI API キー（news_nlp / regime_detector 用）
   - その他:
     - DUCKDB_PATH (省略時: data/kabusys.duckdb)
     - SQLITE_PATH (省略時: data/monitoring.db)
     - KABUSYS_ENV (development|paper_trading|live)（省略時 development）
     - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL)

例 (.env):
    JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
    OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
    KABU_API_PASSWORD=your_kabu_password
    SLACK_BOT_TOKEN=xoxb-...
    SLACK_CHANNEL_ID=C0123456789
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

---

## 使い方（基本的なサンプル）

以下は Python REPL / スクリプトでの基本的な使い方例です。

1) DuckDB 接続と日次 ETL 実行
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニューススコアの生成（OpenAI API キーが環境変数に設定されている前提）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
n_written = score_news(conn, target_date=date(2026, 3, 20))
print(f"written scores: {n_written}")
```

3) 市場レジームスコアの算出
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

4) 監査ログ DB の初期化（監査専用 DB を分けたい場合）
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# テーブルが作成された接続が返る
```

5) 研究用途のファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026, 3, 20))
val = calc_value(conn, target_date=date(2026, 3, 20))
# zscore 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
```

注意点：
- OpenAI 呼び出しはレイテンシ・コストが発生します。API キー、モデル選定（コードでは gpt-4o-mini）を運用ポリシーに合わせて設定してください。
- J-Quants API の認証は refresh token を与え、jquants_client.get_id_token が id_token を取得して使用します。レート制限（120 req/min）を内部で制御します。

---

## 環境変数 / 設定の説明（kabusys.config.Settings）

主な設定項目（Settings クラスのプロパティ）：

- jquants_refresh_token: J-Quants リフレッシュトークン（必須）
- kabu_api_password: kabu API パスワード（必須）
- kabu_api_base_url: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- slack_bot_token, slack_channel_id: Slack 通知用（必須）
- duckdb_path: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- sqlite_path: 監視用 SQLite パス（デフォルト data/monitoring.db）
- env: KABUSYS_ENV (development|paper_trading|live) — 環境モード
- log_level: LOG_LEVEL（INFO 等）
- is_live / is_paper / is_dev: 環境判定ヘルパー

.env 自動ロード:
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` と `.env.local` を自動読み込みします。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
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
    - etl.py (公開エイリアス)
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - etl.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/ (パッケージ内に監視関連のコードが入る想定)
  - execution/ (発注・ブローカー連携の実装想定)
  - strategy/ (戦略ロジックを置く場所)

重要な公開 API：
- kabusys.data.pipeline.ETLResult / run_daily_etl
- kabusys.ai.news_nlp.score_news
- kabusys.ai.regime_detector.score_regime
- kabusys.data.audit.init_audit_schema / init_audit_db
- kabusys.research.* のファクター計算関数

---

## 運用上の注意

- API キーやシークレットは適切に管理してください（.env は gitignore に追加推奨）。
- OpenAI 呼び出しはコストがかかるためバッチサイズや実行頻度を運用ポリシーに合わせて調整してください（news_nlp は銘柄 20 件ごとにバッチ送信）。
- ETL は外部 API 依存のためネットワーク障害時にリトライ・部分失敗が生じる設計です。ETLResult の errors / quality_issues を監視して運用してください。
- DuckDB の接続はシングルスレッドで扱う場面もあるためマルチプロセス・マルチスレッド利用時は注意してください。

---

## コントリビュート / テスト

- 新しい機能追加やバグ修正の際は、ユニットテストを追加してください（特に ETL の境界ケース、AI レスポンスの不整合、ニュースパース部分）。
- OpenAI 呼び出しや HTTP 周りはモック可能な設計（内部の _call_openai_api、_urlopen 等）になっているため、それらを差し替えてテストしてください。

---

以上。必要であれば README にサンプルの .env.example や具体的なコマンド（cron での ETL 実行例、監視ジョブの設定例）を追加します。どの部分を詳しく載せたいか教えてください。