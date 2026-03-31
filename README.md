# KabuSys

日本株向けのデータプラットフォームと自動売買基盤のためのライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を用いた銘柄センチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（トレーサビリティ）などを提供します。

注意: 本 README はリポジトリ内のソースコードを基に作成しています。

---

目次
- プロジェクト概要
- 主な機能
- 要件
- セットアップ手順
- 環境変数（.env）
- 使い方（基本例）
- ディレクトリ構成
- 開発・テスト時のヒント

---

プロジェクト概要
- KabuSys は日本株のデータ収集・品質管理・特徴量生成・AIによるニュース評価・市場レジーム判定・監査ログ管理を統合したライブラリ群です。
- DuckDB をデータストアとして利用し、J-Quants API から市場データ・財務データ・市場カレンダーを差分取得して保存します。
- OpenAI（gpt-4o-mini 等）を使ってニュースセンチメントやマクロセンチメントを評価し、ai_scores や market_regime テーブルへスコアを格納します。
- 監査（audit）機能により、シグナル → 発注要求 → 約定 のフローを UUID ベースでトレース可能にします。

---

主な機能
- データ取得 / ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl を提供
- データ品質
  - 欠損、スパイク（急騰/急落）、重複、日付不整合などのチェック（quality.run_all_checks）
- ニュース収集・前処理
  - RSS フィードの取得（SSRF 対策、gzip サイズ制限、URL 正規化、トラッキングパラメータ除去）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュースを集約し、LLM でセンチメントを算出して ai_scores に書き込み（ai.news_nlp.score_news）
  - マクロニュースを基に市場レジームを判定（ai.regime_detector.score_regime）
- リサーチ用ユーティリティ
  - ファクター（モメンタム、ボラティリティ、バリュー）計算（research.calc_*）
  - 将来リターン、IC（Information Coefficient）計算、統計サマリー
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを初期化・管理（data.audit.init_audit_db, init_audit_schema）

---

要件
- Python 3.10 以上（ソースが型アノテーションの union 表記などを使用）
- 主なライブラリ（少なくとも開発時に必要）:
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリを多用（urllib, json, datetime 等）

依存パッケージはプロジェクト配布方法に応じて requirements.txt や pyproject.toml にまとめてください。

---

セットアップ手順（ローカル開発向け）
1. Python（推奨 3.10+）を用意する
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要な依存をインストール
   - pip install duckdb openai defusedxml
   - 追加で logging 等を設定するためのライブラリがある場合は適宜追加してください
4. パッケージを開発インストール（リポジトリルートで）
   - pip install -e .
   （pyproject.toml / setup.cfg がある場合）
5. 環境変数 / .env を用意する（下記参照）
6. DuckDB データベースや監査用 DB を作成する（下記 使い方 参照）

自動 .env ロードについて:
- パッケージはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）にある .env および .env.local を自動で読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
- 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途など）。

---

環境変数（主なもの）
- 必須
  - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
  - KABU_API_PASSWORD     : kabuステーション API 用パスワード（発注周りの別モジュールで利用）
  - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（通知機能を使う場合）
  - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知先）
- 任意 / デフォルトあり
  - KABUSYS_ENV           : "development" | "paper_trading" | "live" （デフォルト development）
  - LOG_LEVEL             : "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" で .env 自動ロードを停止
  - OPENAI_API_KEY        : OpenAI API キー（score_news / score_regime では引数でも渡せます）
  - DUCKDB_PATH           : DuckDB ファイルのパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH           : SQLite 監視 DB（デフォルト data/monitoring.db）

簡易 .env 例（.env.example を用意することを推奨）
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567

---

使い方（主要 API 例）

1) DuckDB 接続と日次 ETL 実行
- ETL を実行して J-Quants からデータを取得・保存・品質チェックを行うサンプル:

```python
from datetime import date
import duckdb
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date.today())
print(result.to_dict())
```

2) ニュース NLP スコアリング（OpenAI を使用）
- 前提: raw_news / news_symbols テーブルにデータがあること

```python
from datetime import date
import duckdb
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# API キーは OPENAI_API_KEY 環境変数、もしくは api_key 引数で渡す
n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
print(f"書き込み銘柄数: {n_written}")
```

3) 市場レジーム判定（MA200 とマクロセンチメントの組合せ）
- ETF 1321 の MA200 乖離とマクロニュースの LLM スコアを合成して market_regime に書き込みます。

```python
from datetime import date
import duckdb
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
```

4) 監査ログの初期化 / 監査用 DB の作成

```python
from kabusys.data.audit import init_audit_db
conn = init_audit_db("data/audit.duckdb")
# これで signal_events, order_requests, executions テーブルが作成されます
```

5) 研究用ファクター計算（副作用なし、DB 読取のみ）

```python
from datetime import date
import duckdb
from kabusys.research.factor_research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
# 結果は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
```

注意点:
- score_news / score_regime は OpenAI API 呼び出しを行います。テストでは内部の _call_openai_api をモックして外部呼び出しを回避できます（ソースコード内に明記あり）。
- research モジュール（calc_momentum 等）は外部 API にアクセスしない設計です（ローカル DB の prices_daily 等のみ参照）。

---

ディレクトリ構成（主要ファイルのみ抜粋）
- src/kabusys/
  - __init__.py
  - config.py            # .env 自動読み込み・設定ラッパー (settings)
  - ai/
    - __init__.py
    - news_nlp.py        # ニュースセンチメントスコア算出、score_news
    - regime_detector.py # マクロ + MA200 合成による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py  # J-Quants API client + DuckDB 保存関数
    - pipeline.py        # ETL コントローラ（run_daily_etl 等）
    - etl.py             # ETL インターフェース（ETLResult の再エクスポート）
    - news_collector.py  # RSS 取得・前処理
    - quality.py         # データ品質チェック
    - stats.py           # z-score 正規化などユーティリティ
    - calendar_management.py
    - audit.py           # 監査ログテーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*           # ファクター調査系ユーティリティ
  - その他モジュール...

（上記は主要モジュールの一覧です。詳細は各ファイルの docstring を参照してください）

---

開発・テスト時のヒント
- 自動 .env ロードを無効化したいとき:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してからインポートしてください。
- OpenAI 呼び出しのユニットテスト:
  - news_nlp._call_openai_api / regime_detector._call_openai_api を unittest.mock.patch で差し替えることで外部 API 呼び出しを模擬できます。
- DuckDB の一時接続:
  - テストでは ":memory:" を使って in-memory DB を作成できます（init_audit_db などは ":memory:" を受け付けます）。
- ETL の id_token:
  - jquants_client.get_id_token() は settings.jquants_refresh_token を使いますが、run_* 関数に id_token を渡してテスト用のトークンを注入することもできます。

---

ライセンス・貢献
- 本 README はソースコードの docstring に基づいて作成しています。実際に配布する場合は LICENSE ファイル・コントリビューションガイドを追記してください。

---

フィードバックや追加してほしいサンプル（CLI 例、Docker 構成、CI 設定など）があれば教えてください。README を用途に合わせて拡張します。