# KabuSys

日本株向けのデータプラットフォーム＋自動売買フレームワーク（KabuSys）。  
J-Quants / DuckDB を用いたデータ ETL、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注〜約定のトレーサビリティ）などを含むモジュール群を提供します。

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質検査・ファクター計算・ニュース NLP・市場レジーム判定・監査ログ生成までを想定したライブラリ群です。  
主な目的は以下です。

- J-Quants API からの差分取得（株価・財務・マーケットカレンダー）
- DuckDB を用いたローカル永続化（ETL：取得→保存→品質チェック）
- ニュース記事の収集と OpenAI による銘柄別センチメントスコア化
- ETF（1321）を使った市場レジーム判定（MA + マクロニュース）
- 研究用にファクター計算・将来リターン・IC 計測ツールを提供
- 発注／約定の監査ログ（監査テーブル／スキーマ初期化ユーティリティ）

---

## 主な機能一覧

- data/
  - ETL（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
  - J-Quants クライアント（fetch / save 関数）
  - News Collector（RSS 取得 + 前処理 + DB 保存）
  - Market calendar ヘルパー（営業日判定、next/prev_trading_day）
  - 品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news(): 銘柄ごとのニュースセンチメントを ai_scores に書き込む（OpenAI）
  - regime_detector.score_regime(): ETF + マクロニュースを合成して market_regime に書き込む（OpenAI）
- research/
  - ファクター計算（momentum / volatility / value）
  - 特徴量解析（forward returns / IC / summary / rank）
- 設定:
  - kabusys.config.Settings: 環境変数ベースの設定管理（.env の自動読み込みあり）
  - 自動 .env ロードはプロジェクトルート（.git / pyproject.toml）を基準に行う

---

## 必要条件 / 依存パッケージ（例）

- Python 3.10+
- 必要パッケージ（代表例）:
  - duckdb
  - openai
  - defusedxml
- （ネットワーク/API を使う場合）J-Quants アカウント、OpenAI API キー、kabu API のパスワードなど

用途に応じて pyproject.toml / requirements.txt を用意してください。

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込みます。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。

必須（使用する機能に依存）：
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（ETL）
- SLACK_BOT_TOKEN — Slack 通知用トークン（必要な場合）
- SLACK_CHANNEL_ID — Slack チャンネル ID
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携を行う場合）
- OPENAI_API_KEY — OpenAI 呼び出しを行う場合（news_nlp / regime_detector）

任意/デフォルト値あり：
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）

例（.env）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABU_API_PASSWORD=your_password
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - ローカル開発:
     - pip install -e . などで依存をインストールしてください（pyproject.toml がある前提）。

2. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成するか、環境変数を直接設定します。
   - 自動ロードは project root（.git または pyproject.toml）を探索して行われます。テスト等で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

3. DuckDB 等のデータベース準備
   - デフォルトでは data/kabusys.duckdb を使用します（設定で変更可）。
   - 監査ログ専用 DB を作る場合: data/audit.duckdb などを用意して init_audit_db を呼んで初期化できます。

4. 必要な外部 API キー（J-Quants / OpenAI）を用意

---

## 使い方（代表的な呼び出し例）

基本的には Python から各関数を呼んで使用します。以下はサンプル。

- ETL を日次で実行（DuckDB 接続を渡す例）
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

- ニューススコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY を利用）
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
count = score_news(conn, target_date=date(2026, 3, 20))
print(f"scored {count} codes")
```

- 市場レジーム判定
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20))
```

- 監査ログスキーマの初期化（監査専用 DB を作る）
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで監査テーブルが作成されます
```

- 設定参照
```python
from kabusys.config import settings
print(settings.duckdb_path)
print(settings.is_live)
```

注意点:
- news_nlp / regime_detector は OpenAI を呼び出します。API キーと通信環境を用意してください。
- 各関数はルックアヘッドバイアスを避けるために内部で date.today() 等を安易に参照しない設計です。target_date を明示して呼ぶことを推奨します。
- OpenAI 呼び出しはリトライ・フォールバックを持ちますが、API 制限に注意してください。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py                       - 環境変数 / .env 自動読み込み / Settings
  - ai/
    - __init__.py
    - news_nlp.py                    - ニュース NLP スコアリング（score_news）
    - regime_detector.py             - 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py              - J-Quants API client（fetch / save）
    - pipeline.py                    - ETL パイプライン（run_daily_etl 等）
    - etl.py                         - ETLResult 再エクスポート
    - news_collector.py              - RSS 収集・前処理
    - calendar_management.py         - 市場カレンダー管理（is_trading_day 等）
    - quality.py                     - データ品質チェック
    - audit.py                       - 監査ログスキーマ初期化 / init_audit_db
    - stats.py                       - 汎用統計ユーティリティ（zscore_normalize）
  - research/
    - __init__.py
    - factor_research.py             - ファクター計算（momentum/value/volatility）
    - feature_exploration.py         - 将来リターン / IC / summary / rank

その他の補助モジュールやテスト用のユーティリティが含まれています。

---

## 運用上の注意 / ベストプラクティス

- 各 ETL / Scoring の呼び出しは cron / Airflow 等でスケジュールすることを想定しています。
- OpenAI 呼び出しはコストとレート制限があるためバッチ化やレート管理を行ってください（本実装はリトライ・バッチ処理ロジックを含みます）。
- ETL の品質チェック（quality.run_all_checks）結果は ETLResult に含まれます。重大な品質問題が検出された場合はアラートを上げる運用設計を推奨します。
- KABUSYS_ENV を `live` にすると実運用モード判定に使えます。paper_trading などの運用モードを分けて管理してください。
- .env の自動読み込みはプロジェクトルート探索に依存します。CI 環境やテストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して外部から環境を注入してください。

---

## ライセンス / 貢献

（該当リポジトリのライセンス情報をここに記載してください。）

---

不明点や README に追加したい利用例があれば教えてください。README をプロジェクトの実際の README.md フォーマットに合わせて微調整します。