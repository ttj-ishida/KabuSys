# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、ニュース収集と LLM によるセンチメント解析、特徴量／ファクター計算、監査ログ（発注トレース）などのモジュールを備え、DuckDB を中心としたワークフローでバックテストおよび運用支援を行います。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API 経由で株価日足（OHLCV）・財務データ・上場情報・マーケットカレンダーを差分取得
  - 差分取得・バックフィル・冪等保存（ON CONFLICT DO UPDATE）
  - ETL の品質チェック（欠損、スパイク、重複、日付不整合）

- ニュース収集・NLP
  - RSS からニュース記事を収集して raw_news テーブルに保存
  - URL 正規化、SSRF 対策、gzip 上限など堅牢な取得実装
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores）解析
  - マクロニュース + ETF の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）

- 研究（Research）
  - モメンタム／ボラティリティ／バリュー等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - z-score 正規化などの統計ユーティリティ

- カレンダー管理
  - JPX カレンダーの取得／保存／営業日判定・前後営業日探索
  - カレンダー未取得時は曜日ベースでフォールバック

- 監査ログ（Audit）
  - signal_events / order_requests / executions を含む監査スキーマ定義と初期化ユーティリティ
  - 発注トレースのために UUID ベースで階層的にログ保存

- 外部統合
  - J-Quants API クライアント（レートリミット、リトライ、401 自動リフレッシュ対応）
  - OpenAI クライアント利用（API 呼び出しは適切にリトライ／フェイルセーフ化）
  - Slack 等の通知（設定は環境変数で管理）

---

## 必要条件（Prerequisites）

- Python 3.10+
- DuckDB
- OpenAI SDK（openai）
- defusedxml
- その他依存パッケージ（urllib/標準ライブラリ中心ですが、requirements がある場合はそちらを参照してください）

例（最低限の pip パッケージ）:
- duckdb
- openai
- defusedxml

（プロジェクト配布方法により pyproject.toml / requirements.txt が付属する想定です。なければ上記パッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローン／チェックアウト
   - git clone ...（省略）

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - もし requirements.txt があれば: pip install -r requirements.txt
   - 開発インストール: pip install -e .

4. 環境変数（.env ファイル）を用意
   - プロジェクトルートに `.env`（および必要なら .env.local）を作成すると自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須（Settings が必須で参照するもの）
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
     - KABU_API_PASSWORD=<kabu_station_password>
     - SLACK_BOT_TOKEN=<slack_bot_token>
     - SLACK_CHANNEL_ID=<slack_channel_id>
   - 推奨 / 任意
     - OPENAI_API_KEY=<openai_api_key>  # news_nlp / regime_detector で使用
     - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
     - LOG_LEVEL=INFO|DEBUG|... (デフォルト: INFO)
     - DUCKDB_PATH=data/kabusys.duckdb (デフォルト)
     - SQLITE_PATH=data/monitoring.db (監視用)
   - .env のフォーマットは一般的な KEY=VALUE、export KEY=VALUE、クォートを含む値にも対応します。

5. データディレクトリ（例）
   - DuckDB ファイルを保存するディレクトリが必要なら作成します:
     - mkdir -p data

---

## 使い方（主要なユースケース）

以下は Python モジュールを直接呼び出す例です。プロジェクトに CLI があればそちらを利用してください。

- DuckDB に接続して日次 ETL を実行（株価・財務・カレンダー取得 + 品質チェック）

  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコアを計算して ai_scores に書き込む

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を .env に設定しておけば None で可
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジームスコアを計算して market_regime に書き込む

  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマを初期化（監査用 DuckDB）

  ```
  import duckdb
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # または
  # conn = duckdb.connect("data/kabusys.duckdb")
  # init_audit_schema(conn)
  ```

- カレンダー関連ユーティリティ（営業日判定など）

  ```
  from datetime import date
  import duckdb
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  conn = duckdb.connect("data/kabusys.duckdb")
  d = date(2026, 1, 1)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

注意点:
- OpenAI 呼び出しを行う関数は API キーが必要です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- 自動ロードされる環境変数の優先順位: OS 環境 > .env.local > .env（プロジェクトルート検出は .git または pyproject.toml を基準）
- テスト時に自動 env ロードを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

---

## ディレクトリ構成（主要ファイルと概要）

（src/kabusys 以下の主なモジュール構成）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py
      - ニュースセンチメント解析（OpenAI を用いた銘柄別スコアリング）
    - regime_detector.py
      - ETF（1321）MA200 とマクロニュースの LLM センチメントを合成して市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py
      - J-Quants API クライアント（取得・保存ユーティリティ、リトライ・レート制御）
    - pipeline.py
      - ETL パイプライン（run_daily_etl, run_prices_etl, run_financials_etl, run_calendar_etl）
    - etl.py
      - ETLResult の再エクスポート
    - news_collector.py
      - RSS 取得・正規化・raw_news 保存
    - calendar_management.py
      - 市場カレンダー管理・営業日判定・カレンダージョブ
    - quality.py
      - データ品質チェック（欠損、スパイク、重複、日付不整合）
    - stats.py
      - 汎用統計ユーティリティ（zscore_normalize 等）
    - audit.py
      - 監査ログ（監査スキーマ DDL / 初期化ユーティリティ）
  - research/
    - __init__.py
    - factor_research.py
      - momentum, value, volatility 等のファクター計算
    - feature_exploration.py
      - forward returns, IC, factor summary, rank 等
  - ai/*, research/*, data/* の相互参照は最小化され、テストしやすい設計

---

## 開発・運用上の注意

- Look-ahead バイアス回避
  - 多くの関数は date.today()/datetime.today() を直接参照せず、明示的な target_date を受け取る設計です。バックテストや再現性を保つために target_date を明示してください。

- フェイルセーフ
  - 外部 API（OpenAI / J-Quants）呼び出しの失敗は基本的に例外を上位へ投げず（もしくはフォールバック値で継続）する設計箇所が多いです。運用で監視ログを確認してください。

- テスト容易性
  - OpenAI 呼び出しなどは内部関数（_call_openai_api 等）を patch して差し替えテスト可能です。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して環境依存を切り離せます。

---

## 例: .env のサンプル

.env.example（例）

```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_station_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

---

README に書かれている通り、まずは依存パッケージを揃え、.env を整え、DuckDB を用意して ETL を一回実行してみることを推奨します。運用やバックテスト用途に合わせて KABUSYS_ENV を切り替え、監視・ロギング設定を整えてください。質問や追加で README に入れたい内容があれば教えてください。