# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ集合です。  
ETL（J-Quants 経由）、ニュース収集・NLP スコアリング（OpenAI）、研究用ファクター計算、監査ログ（約定トレース）、マーケットカレンダー管理などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株のデータ収集・品質管理・特徴量生成・AI ベースのニュース評価・市場レジーム判定・監査ログ管理・ETL パイプラインなど、アルゴリズム取引基盤に必要な機能群をまとめた Python モジュール群です。

設計上のポイント:
- DuckDB を主要データストアとして使用（オンディスク / インメモリ対応）
- Look-ahead bias を避けるため日付参照を外部から注入する設計
- 外部 API（J-Quants / OpenAI）への堅牢なリトライ・レート制御を実装
- ETL / 品質チェックはフォールトトレラント（1ステップ失敗でも他を継続）
- 監査ログでシグナル→発注→約定のトレーサビリティを確保

---

## 主な機能一覧

- 環境変数 / .env 自動読み込み（config）
- J-Quants API クライアント（データ取得・保存・レートリミット・リフレッシュ）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄情報
- ETL パイプライン（差分取得・保存・品質チェック）
  - run_daily_etl を中心に prices / financials / calendar を差分更新
- データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集（RSS）と前処理（SSRF対策・トラッキング削除）
- ニュース NLP（OpenAI）による銘柄単位センチメントスコア化（news_nlp.score_news）
- 市場レジーム判定（ETF 1321 の MA200 とマクロ記事の LLM センチメント合成、regime_detector.score_regime）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリューなどのファクター算出
  - 将来リターン計算、IC（Spearman）など
  - Zスコア正規化ユーティリティ
- 監査ログ（audit）: signal_events, order_requests, executions テーブルと初期化ヘルパー
- カレンダー管理（market_calendar テーブルを参照／更新）と営業日ヘルパー

---

## 要件 (推奨)

- Python 3.10+（PEP 604 型記法を使用）
- 必須ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリに依存

実際のプロジェクトでは requirements.txt / pyproject.toml を用意して下さい。最低限は以下をインストールしてください（例）:

pip install duckdb openai defusedxml

※ 実行環境の要求は導入環境に合わせて調整してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd <repo>

2. Python 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - pip install -e .          # パッケージがセットアップ可能な場合
   - pip install duckdb openai defusedxml

4. 環境変数 / .env を用意
   - プロジェクトルートに `.env` または `.env.local` を配置すると自動読み込みされます。
   - 自動読み込みを無効化する場合: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須の環境変数（config.Settings により参照・必須とされるもの）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション（発注用）パスワード
- SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID      : Slack のチャネル ID

OpenAI を利用する機能を使う場合:
- OPENAI_API_KEY : OpenAI API キー（news_nlp.score_news / regime_detector.score_regime では引数で渡すこともできます）

その他の設定（省略時はデフォルト値を使用）:
- DUCKDB_PATH : data/kabusys.duckdb
- SQLITE_PATH : data/monitoring.db
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT, KABU_API_BASE_URL, LOG_LEVEL, KABUSYS_ENV など

例 (.env):
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb

---

## 使い方（簡易サンプル）

以下は Python REPL / スクリプトからの利用例です。DuckDB ファイルパスは Settings.duckdb_path を使うと便利です。

- ETL（日次更新）を実行する:
```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl
from kabusys.config import settings

conn = duckdb.connect(str(settings.duckdb_path))
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

- ニュースセンチメント (ai/news_nlp.score_news)
```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect(str(settings.duckdb_path))
# OPENAI_API_KEY を環境変数に設定しているか、api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20))
print("書き込み銘柄数:", n_written)
```

- 市場レジーム判定 (ai/regime_detector.score_regime)
```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect(str(settings.duckdb_path))
score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API キーは env か引数で
```

- 研究用ファクター計算
```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

conn = duckdb.connect("data/kabusys.duckdb")
mom = calc_momentum(conn, target_date=date(2026,3,20))
val = calc_value(conn, target_date=date(2026,3,20))
vol = calc_volatility(conn, target_date=date(2026,3,20))
```

- 監査ログDB 初期化
```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# conn を使って order_requests 等の操作が可能
```

- RSS フィード取得（ニュース収集）
```python
from kabusys.data.news_collector import fetch_rss
articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", "yahoo_finance")
# 取得した articles を DB に保存するロジックはプロジェクト側で実装します（モジュール内に保存ロジックあり）
```

注意:
- AI 呼び出し（OpenAI）は API エラー時にフォールバックする実装（0.0 で継続等）を採用していますが、API キーとレート制限の管理は利用者側で行ってください。
- DuckDB の executemany に空リストを渡すと問題になる箇所があるため、空チェックが行われています。直接 SQL 実行する際は注意してください。

---

## ディレクトリ構成

（リポジトリの主要なソースファイル群の例）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / .env 読み込みと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースの LLM スコアリング（score_news）
    - regime_detector.py            -- マーケットレジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント（fetch/save）
    - pipeline.py                   -- ETL パイプライン・run_daily_etl 等
    - etl.py                        -- ETLResult 再エクスポート
    - news_collector.py             -- RSS 収集・前処理
    - calendar_management.py        -- 市場カレンダー管理 / 営業日ヘルパー
    - quality.py                    -- 品質チェック（欠損/重複/スパイク等）
    - stats.py                      -- 共通統計ユーティリティ（zscore）
    - audit.py                      -- 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py            -- モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py        -- 将来リターン / IC / サマリー / ランク
  - ai/ (再掲) etc.

（上記はコードベースに含まれる主要モジュールを抜粋した構成です）

---

## 運用上の注意・ヒント

- .env 自動読み込み:
  - プロジェクトルート（.git または pyproject.toml）を起点に `.env` と `.env.local` を自動ロードします。
  - OS 環境変数が優先され、`.env.local` は `.env` の上書きに使用されます。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- テスト:
  - OpenAI やネットワーク依存部分はモックが差し替えられるよう設計されています（例: news_nlp._call_openai_api を patch してテスト可能）。
  - DuckDB は ":memory:" を指定してインメモリ DB としてテストできます。

- ロギング:
  - Settings.log_level や LOG_LEVEL 環境変数で制御できます。生産環境では INFO 〜 WARNING を推奨。

- セキュリティ:
  - news_collector は SSRF、XML Bomb、過大レスポンスなどへの対策（SSRF ブロックハンドラ、defusedxml、最大バイト数制限等）を導入しています。
  - API キーやトークンは安全な方法で保管してください（CI/CD のシークレット、Vault 等）。

---

## 連絡・貢献

バグ報告や機能改善要望は Issue を立ててください。Pull Request は歓迎します。README やドキュメントの追加も助かります。

---

README は簡潔化した抜粋です。実際の運用では pyproject.toml / setup.cfg / requirements.txt を整備し、CI テスト、型チェック、コードスタイル（Black/Flake）を導入することを推奨します。