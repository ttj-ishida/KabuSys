KabuSys — 日本株自動売買プラットフォーム（README 日本語版）
================================================

概要
----
KabuSys は日本株向けのデータプラットフォーム／自動売買基盤のライブラリ群です。  
主に以下の役割を想定しています。

- J-Quants API からのデータ取得（株価日足・財務・マーケットカレンダー）
- DuckDB を用いた時系列データ管理と ETL パイプライン
- ニュースを用いた NLP（OpenAI）による銘柄センチメント評価
- 市場レジーム判定（ETF MA とマクロ・ニュースの合成）
- 監査ログ（signal → order_request → execution）のスキーマ初期化と管理
- データ品質チェック / 研究用ファクター計算ユーティリティ

設計上の特徴：
- Look-ahead バイアス回避を意識した設計（内部で date.today() を不用意に参照しない）
- 冪等な DB 書き込み（ON CONFLICT / 個別 DELETE→INSERT による保護）
- API 呼び出しに対するリトライ、レートリミット、フェイルセーフの実装

主な機能一覧
-------------
- data/etl.py: 日次 ETL（市場カレンダー、株価、財務データ）、差分取得、品質チェック
- data/jquants_client.py: J-Quants API クライアント（fetch / save / 認証 / ページネーション）
- data/news_collector.py: RSS からのニュース収集・正規化・raw_news 保存
- data/quality.py: 欠損・スパイク・重複・日付不整合の検出
- data/calendar_management.py: 営業日判定・翌営業日/前営業日検索・カレンダー更新ジョブ
- data/audit.py: 監査テーブルの DDL / 初期化ユーティリティ
- ai/news_nlp.py: OpenAI を用いた銘柄別ニュースセンチメント（ai_scores へ書込）
- ai/regime_detector.py: ETF（1321）MA とマクロニュースで市場レジームを判定（market_regime へ書込）
- research/*: ファクター計算（モメンタム／ボラティリティ／バリュー）・特徴量解析ユーティリティ
- config.py: 環境変数 / .env 自動読み込みと Settings 抽象化

セットアップ手順
----------------

1. Python 環境を用意
   - Python 3.10 以上を推奨

2. 仮想環境の作成（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - requirements.txt が無い場合は少なくとも次をインストールしてください：
     - duckdb
     - openai
     - defusedxml
   例:
     - pip install duckdb openai defusedxml

   （プロジェクトに packaging がある場合は pip install -e . を使う想定）

4. 環境変数 / .env の準備
   - リポジトリルートの .env または .env.local に設定を置けます（config.py が自動ロード）。
   - 必須環境変数（Settings で require されるもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD — kabu ステーション API パスワード（発注関連を使う場合）
     - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を使う場合
   - 任意・デフォルト値が用意されているもの:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト development
     - LOG_LEVEL — DEBUG/INFO/...
     - KABU_API_BASE_URL — デフォルト http://localhost:18080/kabusapi
     - DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, 各種しきい値（CPU/MEM/DISK）

   .env の自動読み込みを無効にする:
     - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

使い方（短い例）
----------------

※ 以下は最小の呼び出し例です。実運用では例外処理やロギング設定、トランザクション管理を追加してください。

1) DuckDB 接続を作り日次 ETL を実行する
```python
import duckdb
from datetime import date
from kabusys.data.pipeline import run_daily_etl

conn = duckdb.connect("data/kabusys.duckdb")
result = run_daily_etl(conn, target_date=date(2026, 3, 20))
print(result.to_dict())
```

2) ニュースセンチメントを生成（OpenAI API キーが必要）
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
print(f"書き込み銘柄数: {written}")
```

3) 市場レジームを判定して書き込む
```python
import duckdb
from datetime import date
from kabusys.ai.regime_detector import score_regime

conn = duckdb.connect("data/kabusys.duckdb")
score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx")
```

4) 監査ログ DB を初期化する
```python
from kabusys.data.audit import init_audit_db

conn = init_audit_db("data/audit.duckdb")
# init_audit_db はテーブルとインデックスを作成し、UTC タイムゾーンを設定します
```

5) 研究用ユーティリティ例（ファクター計算）
```python
from kabusys.research.factor_research import calc_momentum
import duckdb
from datetime import date

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026, 3, 20))
# z-score 正規化
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])
```

主要な環境変数一覧（config.Settings で使用）
------------------------------------------
- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API ベース URL（省略時 http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須。Slack 連携を行う場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須。Slack 連携を行う場合）
- DUCKDB_PATH: DuckDB ファイルパス（省略時 data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（省略時 data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development | paper_trading | live（省略時 development）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）

ディレクトリ構成（主要ファイル）
-----------------------------
（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 自動ロードと Settings
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュース NLP（OpenAI） → ai_scores 書き込み
    - regime_detector.py            — 市場レジーム判定（ETF ma200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（fetch / save）
    - pipeline.py                   — ETL パイプライン（run_daily_etl 等）
    - etl.py                        — ETL の公開インターフェース（ETLResult 再エクスポート）
    - news_collector.py             — RSS 取得と raw_news 保存
    - quality.py                    — データ品質チェック
    - calendar_management.py        — 市場カレンダー管理 / 営業日判定
    - stats.py                      — zscore_normalize 等汎用統計
    - audit.py                      — 監査テーブル DDL / 初期化
  - research/
    - __init__.py
    - factor_research.py            — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py        — 将来リターン / IC / サマリー等

注意点・運用上のヒント
--------------------
- OpenAI 呼び出しには API キー (OPENAI_API_KEY) が必要です。score_news / score_regime では引数で渡すか環境変数を使用します。
- J-Quants API の認証は JQUANTS_REFRESH_TOKEN を用いて行われます。get_id_token が自動で更新を行います。
- DuckDB に保存する際は冪等性（ON CONFLICT）を意識しており、部分失敗時に既存データを不用意に上書きしないよう設計されています。
- Look-ahead バイアス対策のため、多くの関数は target_date を明示的に受け取り、内部で date.today() を不用意に参照しません。バックテスト時は target_date を適切に渡してください。
- テスト時には外部 API 呼び出し（OpenAI / J-Quants / RSS）の箇所をモックすると容易です。各モジュール（news_nlp, regime_detector, news_collector, jquants_client）には差し替えポイントが用意されています。

トラブルシューティング（よくあるエラー）
-----------------------------------------
- 環境変数が未設定 → settings が ValueError を投げます。必須変数を .env または環境に設定してください。
- DuckDB のテーブルが存在しない → ETL 実行前にスキーマ初期化手順（プロジェクト固有の schema 初期化関数）を実行してください（例: audit.init_audit_schema）。
- OpenAI からのパース失敗や API エラー → モジュールはフェイルセーフとしてスコア 0.0 を採用する箇所があります。ログを確認してください。

ライセンス・貢献
----------------
本 README はコードベースの説明に基づくドキュメントです。実際のライセンスや CONTRIBUTING 方針はリポジトリのトップレベルファイル（LICENSE, CONTRIBUTING.md 等）を参照してください。

付録: よく使う関数一覧（抜粋）
-----------------------------
- ETL:
  - kabusys.data.pipeline.run_daily_etl(...)
  - kabusys.data.pipeline.run_prices_etl(...)
  - kabusys.data.pipeline.run_financials_etl(...)
  - kabusys.data.pipeline.run_calendar_etl(...)
- AI:
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- Data:
  - kabusys.data.jquants_client.fetch_daily_quotes(...)
  - kabusys.data.jquants_client.save_daily_quotes(conn, records)
- Audit:
  - kabusys.data.audit.init_audit_db(path)
  - kabusys.data.audit.init_audit_schema(conn, transactional=False)

その他の詳細な実装やパラメータはソースコード内の docstring を参照してください。必要であれば README を拡張して CI / デプロイ手順、より詳細な設定例、運用手順を書き加えます。