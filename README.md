# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。ETL、ニュース収集・NLP評価、ファクター計算、監査ログ、J-Quants / kabu ステーション連携などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムのコアコンポーネントを集約した Python パッケージです。主に次を目的とします。

- J-Quants API を使った株価・財務・カレンダーの差分 ETL
- RSS ベースのニュース収集と OpenAI を使ったニュースセンチメント評価（銘柄別 ai_score）
- 市場レジーム判定（ETF ベースの MA とマクロニュースの LLM 評価の合成）
- ファクター計算（モメンタム、ボラティリティ、バリュー等）と研究用ユーティリティ
- データ品質チェックと監査ログ（発注→約定トレーサビリティ）
- kabu ステーション等発注系は別モジュール（execution 等）として構成可能

設計上の特徴:
- DuckDB を中心にローカル DB で高速に集計・保存
- Look-ahead バイアス対策（バックテスト用に日付参照を明示）
- 外部 API はリトライ・レートリミット制御・フェイルセーフ実装
- 冪等操作（ON CONFLICT / transaction）を重視

---

## 主な機能一覧

- data/
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save / token 管理・レート制御）
  - market_calendar 管理（営業日計算・next/prev/is_trading_day 等）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - ニュース収集（RSS 取得、URL 正規化、SSRF 対策）
  - 監査ログ初期化・DB（signal_events / order_requests / executions）
  - 統計ユーティリティ（zscore_normalize）
- ai/
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを OpenAI で評価して ai_scores に保存
  - regime_detector.score_regime: ETF MA とマクロニュース LLM を合成して market_regime を算出
- research/
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索（forward returns, IC, factor summary 等）
- config
  - 環境変数の自動読み込み (.env/.env.local) と Settings クラス

---

## 必要条件 / 依存

（最低限の主要依存ライブラリ例。実際の requirements.txt がない場合は適宜追加してください）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK v1 系想定)
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb openai defusedxml
# またはプロジェクトの requirements.txt があれば:
# pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン・作業ディレクトリへ移動
   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成 / 有効化、依存インストール（上記参照）

3. 環境変数を設定
   - .env または環境変数で下記を設定します。パッケージはプロジェクトルート（.git または pyproject.toml）を探索して .env 自動読み込みを行います（無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

   必須:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_station_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - OPENAI_API_KEY=<openai_api_key>  # ai モジュール実行時に必要

   任意 / デフォルトあり:
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (デフォルト: data/monitoring.db)
   - KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL, デフォルト: INFO)

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxx
   OPENAI_API_KEY=sk-xxxx
   KABU_API_PASSWORD=secret
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   ```

4. DuckDB 初期スキーマ（必要に応じて）や監査 DB 初期化
   - 監査ログ用 DB を初期化する場合:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - メインのデータ DB へは duckdb.connect(settings.duckdb_path) で接続してスキーマ初期化等を行ってください（本 README には全DDLを列挙していませんが、プロジェクト内の schema 初期化関数を使う想定です）。

---

## 使い方（簡単なコード例）

- DuckDB 接続を作成:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリングして ai_scores に保存:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY を環境変数に設定済みであれば api_key 引数は不要
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジームを算出して market_regime に保存:
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化（別 DB 推奨）:
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/monitoring_audit.duckdb")
  ```

- ファクター計算（例: momentum）:
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  recs = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(recs), recs[:3])
  ```

- データ品質チェック:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i)
  ```

注意:
- OpenAI 呼び出しを行う関数は api_key を引数で注入できます（テストや切り替えに便利）。
- DuckDB への書き込みはトランザクション管理やエラーハンドリングが内部で実装されていますが、呼び出し側で接続の管理（ファイルパス、排他など）に注意してください。

---

## ディレクトリ構成（主なファイル）

以下は package の主要構成です（src/kabusys 配下を抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境変数/Settings 管理（.env 自動読込）
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースセンチメント評価 / score_news
    - regime_detector.py             -- 市場レジーム判定 / score_regime
  - data/
    - __init__.py
    - calendar_management.py         -- 市場カレンダー管理（is_trading_day 等）
    - etl.py                         -- ETL 公開インターフェース（ETLResult）
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - stats.py                       -- 統計ユーティリティ（zscore_normalize）
    - quality.py                     -- データ品質チェック
    - audit.py                       -- 監査ログスキーマ初期化 / init_audit_db
    - jquants_client.py              -- J-Quants API クライアント + save_* 関数
    - news_collector.py              -- RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py             -- ファクター計算（momentum/value/volatility）
    - feature_exploration.py         -- 将来リターン / IC / サマリー等
  - research/（その他モジュール）
  - (その他: strategy, execution, monitoring 等のサブパッケージは __all__ で公開)

---

## 運用上の注意点

- 環境分離: KABUSYS_ENV により development / paper_trading / live を切り替えます。live 環境での実行は十分な安全対策（リスク管理、二重チェック）を行ってください。
- OpenAI の呼び出しはコスト・レート制限があります。バッチ・リトライロジックは実装済みですが、API キー管理とコスト監視を怠らないでください。
- J-Quants の API レート制御・トークン自動更新を実装していますが、ID トークンの漏洩防止とリフレッシュトークンの管理は厳格に行ってください。
- RSS 取得では SSRF や XML 脆弱性に対して対策（_SSRFBlockRedirectHandler, defusedxml, レスポンスサイズ制限）を入れています。外部フィードの追加時も信頼性を確認してください。
- DuckDB のバージョンによる挙動差（executemany の空リストなど）に注意し、アップグレード時はテストを行ってください。

---

## 貢献・拡張

- 追加したい機能例:
  - strategy / execution モジュールの実装（注文ルールとブローカー統合）
  - モニタリング用 UI / Slack 通知ラッパー
  - バックテスト用モジュール（時系列シミュレーション）
- コード規約・テスト:
  - モジュールごとにユニットテストを追加してください。外部 API 呼び出しはモック推奨です（例: news_nlp._call_openai_api の patch）。
  - CI による静的解析・テスト実行を推奨します。

---

必要があれば README に「実行例の詳細」「schema 初期化サンプル」「requirements.txt の候補」などを追記します。どの情報を追加したいか教えてください。