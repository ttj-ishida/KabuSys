# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants）、データ品質チェック、ニュース収集・NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（発注トレーサビリティ）などを含みます。

## 概要
KabuSys は次のような機能を提供するモジュール群で構成されています。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存（ETL）
- ニュース収集（RSS）と記事前処理、銘柄紐付け
- OpenAI を用いたニュースセンチメント（銘柄毎）とマクロセンチメント評価
- ETF（1321）の MA 乖離とマクロセンチメントの合成による市場レジーム判定
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損、重複、スパイク、日付不整合）
- 監査ログ（signal -> order_request -> execution をトレースする監査テーブル）
- 環境変数 / .env の自動読み込みと設定管理

設計上、バックテスト等でルックアヘッドバイアスが入らないように日付参照を慎重に扱う実装が多く含まれます。

## 主な機能一覧
- data/
  - ETL（daily ETL, prices/financials/calendar の差分取得）
  - J-Quants クライアント（認証・レート制御・リトライ・保存）
  - news_collector（RSS 収集、SSRF 防止、前処理、DB 保存）
  - quality（品質チェック：欠損・スパイク・重複・日付不整合）
  - calendar_management（営業日判定／次営業日・前営業日取得等）
  - audit（監査テーブル定義・初期化）
  - stats（zscore 正規化等）
- ai/
  - news_nlp.score_news（銘柄別ニュースセンチメント算出・ai_scores 書き込み）
  - regime_detector.score_regime（ETF MA とマクロセンチメント合成による market_regime 更新）
- research/
  - factor_research（モメンタム、バリュー、ボラティリティ）
  - feature_exploration（将来リターン計算、IC、統計サマリー）
- config.py
  - .env の自動読み込み（.env / .env.local）と Settings オブジェクトによる環境設定取得

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化（例）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 必須（主に本コードで使用されるもの）:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージ管理ファイルがある場合はそれに従ってください（requirements.txt / pyproject.toml 等）。

4. 環境変数の設定
   - プロジェクトルートの .env またはシステム環境変数に必要な設定を追加します。
   - 自動読み込みは config.py がプロジェクトルート（.git または pyproject.toml を基準）を検出できる場合に行われます。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数例（必須のものがいくつかあります）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=xxxxx

   # kabuステーション（発注等を行う場合）
   KABU_API_PASSWORD=xxxxx
   # 任意: KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI
   OPENAI_API_KEY=sk-...

   # Slack (通知等で使用する場合)
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C...

   # データベースパス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 実行環境 / ログ
   KABUSYS_ENV=development        # development | paper_trading | live
   LOG_LEVEL=INFO                # DEBUG | INFO | WARNING | ERROR | CRITICAL
   ```

## 使い方（基本例）

- DuckDB に接続して日次 ETL を実行する例:
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI）を実行する例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY を環境変数にセットしておくか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム判定の実行例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB を初期化する例:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/kabusys_audit.duckdb")
  ```

- ファクター計算（研究用）例:
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from kabusys.data.stats import zscore_normalize

  conn = duckdb.connect("data/kabusys.duckdb")
  target = date(2026,3,20)
  moment = calc_momentum(conn, target)
  value = calc_value(conn, target)
  vol = calc_volatility(conn, target)

  normed = zscore_normalize(moment, ["mom_1m", "mom_3m"])
  ```

注意:
- OpenAI 呼び出しを行う関数は API キーを環境変数 `OPENAI_API_KEY` から取得しますが、関数引数で明示的に渡すことも可能です。
- ETL・API 呼び出しはネットワーク・API レート・認証を伴うため、適切な環境（トークン設定やネットワーク）で実行してください。

## 環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 if using kabu API) — kabu API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector で使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル

## ディレクトリ構成（抜粋）
プロジェクトは src/kabusys 以下に主要モジュールを持ちます。主なファイル・ディレクトリ:

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数・.env 読み込み設定
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュースの NLP スコアリング（ai_scores）
    - regime_detector.py              — 市場レジーム判定（market_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント、保存ロジック
    - pipeline.py                     — ETL パイプライン（run_daily_etl 等）
    - etl.py                          — ETL 結果クラスの再エクスポート
    - news_collector.py               — RSS 収集・前処理・保存
    - quality.py                      — データ品質チェック
    - calendar_management.py          — マーケットカレンダー管理・営業日判定
    - stats.py                         — 統計ユーティリティ（zscore_normalize）
    - audit.py                         — 監査スキーマ初期化
  - research/
    - __init__.py
    - factor_research.py              — モメンタム / バリュー / ボラティリティ
    - feature_exploration.py          — 将来リターン・IC・統計サマリー
  - research/*（その他研究用ユーティリティ）

（上記は主要ファイルの抜粋です。実際のツリーはリポジトリの内容に従ってください。）

## 注意事項 / ベストプラクティス
- 本プロジェクトは実取引系のロジックを含むため、本番環境（live）で動かす際は十分な検証・権限管理を行ってください。
- OpenAI の利用には API コストが発生します。テスト時はモック（unittest.mock.patch）して API 呼び出しを差し替えることを推奨します。
- .env ファイルは機密情報を含むためソース管理に含めないでください（.gitignore 等で除外してください）。
- DuckDB のバージョンや SQL 方言差異により挙動が変わることがあるため、運用環境での検証を行ってください。
- news_collector は SSRF / XML Bomb 等の対策を実装していますが、RSS ソースの安全性確認は運用側でも行ってください。

---

この README はコードベースの主要機能・使い方の概略を示すものです。より詳しい設計ドキュメント（DataPlatform.md / StrategyModel.md 等）がある場合はそちらを参照してください。質問や補足が必要であれば教えてください。