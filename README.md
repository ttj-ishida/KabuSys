# KabuSys

日本株向け自動売買 / データパイプライン / リサーチ基盤用の Python ライブラリセットです。  
データ収集（J-Quants）、ニュース収集・NLP（OpenAI）、ETL、マーケットカレンダー管理、ファクター計算、監査ログ（監査DB）などを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータプラットフォームと研究 (research) / 戦略 (strategy) 層のための共通ユーティリティ群を提供します。主な目的は次のとおりです。

- J-Quants API から株価・財務・カレンダー等を差分取得し DuckDB に保存する ETL パイプライン
- RSS ニュース収集と前処理、OpenAI を用いたニュースセンチメント付与（銘柄別 ai_scores）
- 市場レジーム判定（ETF の MA とマクロニュースのセンチメントを合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ
- 監査ログ（signal → order → execution を辿るテーブル群）を DuckDB に初期化する機能
- データ品質チェック機能（欠損・重複・スパイク・日付不整合検出）

設計上の特徴:
- DuckDB を中心とした SQL ベースの処理（外部依存を最小化）
- Look-ahead バイアス対策（date 引数ベース、datetime.today() を直接参照しない設計）
- API 呼び出しはリトライ・バックオフ・レート制限など現実運用向けロジックを実装
- 冪等性（ETL 保存は ON CONFLICT / DO UPDATE 等で対処）

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl 等）
  - J-Quants クライアント（fetch / save / token refresh / rate limit）
  - カレンダー管理（is_trading_day, next_trading_day, calendar_update_job）
  - ニュース収集（RSS フィード取得、前処理、raw_news 保存）
  - データ品質チェック（missing / duplicate / spike / date consistency）
  - 監査ログ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - ニュース NLP（score_news：銘柄ごとの ai_score を生成して ai_scores テーブルへ格納）
  - 市場レジーム判定（score_regime：ETF MA とマクロニュースを統合して market_regime に書込）
- research/
  - ファクター計算（calc_momentum, calc_value, calc_volatility）
  - 特徴量解析（calc_forward_returns, calc_ic, factor_summary, rank）
- config.py
  - 環境変数の自動読み込み（.env, .env.local）、設定のラップ（settings）

---

## セットアップ手順

前提
- Python 3.10+（typing の union | 等を利用しているため）を推奨
- DuckDB を利用（ローカルファイルまたは :memory:）

1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml
   - その他プロジェクトに合わせて requirements を用意してください

4. 環境変数の設定
   - プロジェクトルートに `.env`（および環境固有の `.env.local`）を置くと、kabusys.config が自動で読み込みます。
   - 自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン
- SLACK_BOT_TOKEN        — Slack 連携（通知等を使う場合）
- SLACK_CHANNEL_ID       — Slack チャンネル ID
- KABU_API_PASSWORD      — kabuステーション API パスワード（実運用時）
- OPENAI_API_KEY         — OpenAI API キー（score_news / score_regime 実行時に必要）

任意 / デフォルト
- KABUSYS_ENV            — development / paper_trading / live（デフォルト development）
- LOG_LEVEL              — ログレベル（DEBUG, INFO, ...、デフォルト INFO）
- DUCKDB_PATH            — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH            — 監視系 SQLite（デフォルト data/monitoring.db）

.env の例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=secret
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## 使い方（主要な API と実行例）

以下は Python からの実行例です。すべての関数は DuckDB 接続（duckdb.connect() で得られる接続オブジェクト）を受け取ります。

共通準備:
```python
import duckdb
from kabusys.config import settings

# settings.duckdb_path は Path オブジェクト
conn = duckdb.connect(str(settings.duckdb_path))
```

1) 日次 ETL を実行する
```python
from datetime import date
from kabusys.data.pipeline import run_daily_etl

# ETL を今日実行
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースの NLP スコアを生成して ai_scores に書き込む
```python
from datetime import date
from kabusys.ai.news_nlp import score_news

# target_date に対するニュースウィンドウを対象にスコア付与
count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
print(f"scored {count} tickers")
```

3) 市場レジーム判定を実行して market_regime に書き込む
```python
from datetime import date
from kabusys.ai.regime_detector import score_regime

score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
```

4) 監査ログ用 DuckDB を初期化する（注文監査テーブル群を作成）
```python
from kabusys.data.audit import init_audit_db

audit_conn = init_audit_db("data/audit.duckdb")
# audit_conn を使って監査ログを操作できます
```

5) ファクター計算 / リサーチ
```python
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
from datetime import date

momentum = calc_momentum(conn, date(2026, 3, 20))
vol = calc_volatility(conn, date(2026, 3, 20))
value = calc_value(conn, date(2026, 3, 20))
```

6) 設定参照例
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- score_news / score_regime は OpenAI の API を利用します。api_key を引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL / 保存関数は冪等設計になっていますが、実行前にスキーマ（raw_prices 等）が存在していることを確認してください（プロジェクト側でスキーマ初期化が用意されている想定）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys の主要なファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py                — パッケージ定義（バージョン）
  - config.py                  — 環境変数 / 設定管理（.env 自動ロード・Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント付与（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch/save/認証/レート制御）
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - etl.py                   — ETL 結果の公開（ETLResult）
    - calendar_management.py   — マーケットカレンダー管理（is_trading_day 等）
    - news_collector.py        — RSS ニュース取得 & 前処理
    - quality.py               — データ品質チェック（missing/spike/duplicates/date）
    - stats.py                 — 汎用統計ユーティリティ（zscore_normalize）
    - audit.py                 — 監査ログテーブルの初期化・管理（init_audit_schema/init_audit_db）
  - research/
    - __init__.py
    - factor_research.py       — ファクター計算（momentum / value / volatility）
    - feature_exploration.py   — 将来リターン / IC / summary / rank
  - research/*                  — リサーチ支援モジュール群

README に載せきれない内部実装の詳細（SQL クエリ設計、エラーハンドリング方針など）は各モジュールのドキュメンテーション文字列（docstring）を参照してください。

---

## 実運用上の注意

- API キーやパスワードは必ず安全に管理してください（.env は gitignore 推奨）。
- 本ライブラリは実証済みの取引を保証するものではありません。実口座での注文送信機能を使う際には十分な検証とリスク管理を行ってください。
- OpenAI / J-Quants へのリクエストはコスト・レート制限があります。ロギングとレート制御の設定を確認してから大量実行してください。
- DuckDB のバージョン依存（executemany の挙動等）に注意してください。コード中に互換性を考慮した記述がありますが、使用する環境での動作確認を推奨します。

---

もし README に追加したい「インストール用 requirements.txt」「開発・テストの手順」「運用スクリプトの例」などがあれば、リポジトリ構成や利用ケースに合わせて追記します。