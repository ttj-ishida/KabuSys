# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、監査ログ用スキーマなど、運用・研究に必要な機能群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ基盤向けに設計された Python モジュール群です。主な機能は以下です。

- J-Quants API からの差分 ETL（株価、財務、マーケットカレンダー）
- RSS によるニュース収集と前処理（SSRF 対策・サイズ制限）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価（銘柄単位 / マクロ）
- 市場レジーム判定（ETF 1321 の MA とマクロセンチメントの合成）
- ファクター計算（モメンタム、バリュー、ボラティリティ等）と特徴量解析ユーティリティ
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログ（信号→発注→約定 のトレーサビリティ）用 DuckDB スキーマ初期化ユーティリティ
- 環境変数 / .env の自動ロードと設定管理

設計方針として、ルックアヘッドバイアス防止、冪等保存、外部呼び出しの堅牢なリトライ制御、テスト容易性を重視しています。

---

## 主な機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants クライアント（fetch / save 系）
  - カレンダー管理（営業日判定・next/prev_trading_day）
  - ニュース収集（RSS fetch_rss / 前処理）
  - データ品質チェック（run_all_checks）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP（score_news） — 銘柄別ニュースセンチメント
  - 市場レジーム判定（score_regime） — ETF MA とマクロセンチメントの合成
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 将来リターン / IC / 統計サマリー（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - 環境変数読み込み・設定アクセス（Settings）

---

## セットアップ手順

前提
- Python 3.10+（型ヒントに union 型表記を含むため少なくとも 3.10 以上を推奨）
- ネットワークアクセス（J-Quants / OpenAI 等）

1. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

2. リポジトリルートでインストール（編集可能インストールを想定）
   ```
   pip install -e .
   ```

3. 依存ライブラリ（開発環境に応じて追加）
   - duckdb
   - openai
   - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```

4. 環境変数 / .env の用意  
   リポジトリルートの `.env`（または `.env.local`）に必要なキーを設定します。自動ロードはデフォルトで有効です（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。

   最小例（.env）:
   ```
   # J-Quants
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

   # kabu ステーション API（使用する場合）
   KABU_API_PASSWORD=your_kabu_api_password
   # KABU_API_BASE_URL=http://localhost:18080/kabusapi

   # OpenAI（ai.score_news, ai.regime_detector 実行時に必要）
   OPENAI_API_KEY=sk-...

   # Slack（通知等を使う場合）
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789

   # DB パス（任意）
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   # 環境
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単な例）

以下は Python REPL / スクリプトから主要な機能を呼び出す例です。

- DuckDB 接続準備（設定からパス取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL 実行
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # 今日を対象に ETL 実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # score_news は ai_scores テーブルへスコアを書き込みます
  written = score_news(conn, target_date=date(2026, 3, 20))
  print("written:", written)
  ```

- 市場レジーム判定（OpenAI API キーが必要）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査ログ用）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- ニュース RSS 取得（news_collector.fetch_rss）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles[:5]:
      print(a["datetime"], a["title"])
  ```

注意点
- OpenAI を呼ぶ関数（score_news / score_regime）では環境変数 OPENAI_API_KEY か `api_key` 引数が必要です。未設定時は ValueError を投げます。
- ETL / 保存関数は DuckDB に対して冪等操作（ON CONFLICT）を行う設計です。
- 日付の扱いはルックアヘッドバイアスを避けるため、内部で date.today() を不用意に参照しないよう設計されています（呼び出し側で対象日を明示することを推奨）。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須 if kabu API を使用)
- KABU_API_BASE_URL (任意, default: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (ai モジュールを使う場合必須)
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (Slack 通知用)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化

---

## ディレクトリ構成

主要ファイル・モジュールの概要（src/kabusys 以下）

- __init__.py
  - パッケージ公開 API（version など）

- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス

- ai/
  - news_nlp.py : 銘柄毎ニュースセンチメント評価（score_news）
  - regime_detector.py : 市場レジーム判定（score_regime）
  - __init__.py

- data/
  - jquants_client.py : J-Quants API クライアント（fetch / save / get_id_token）
  - pipeline.py : ETL パイプライン（run_daily_etl 等） + ETLResult
  - etl.py : ETLResult の再エクスポート
  - calendar_management.py : 市場カレンダー管理（is_trading_day 等）
  - news_collector.py : RSS 取得・前処理
  - quality.py : データ品質チェック
  - stats.py : 統計ユーティリティ（zscore_normalize）
  - audit.py : 監査ログスキーマ初期化 / init_audit_db
  - __init__.py

- research/
  - factor_research.py : ファクター計算（momentum / value / volatility）
  - feature_exploration.py : 将来リターン、IC、統計サマリー
  - __init__.py

その他: テスト・ドキュメント・設定ファイルがリポジトリルートに存在する想定

---

## 開発・運用に関する注意事項

- API キーやトークンは秘匿情報のため .env を用いて管理し、リポジトリに含めないでください。
- OpenAI 呼び出しはコストが発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください。コード内にテストフック（モックしやすい関数分割）が用意されています。
- J-Quants API にはレート制限があるため、jquants_client は内部でスロットリング・リトライ制御を行います。
- DuckDB の executemany にはバージョン依存の制約があるため、空リストでの executemany を回避する実装になっています。
- 監査ログスキーマは冪等で初期化できますが、トランザクションの扱いに注意（DuckDB はネストトランザクション非対応）。

---

## よくある操作（コマンド例）

- パッケージをローカルで編集しながら使う
  ```
  pip install -e .
  ```

- DuckDB ファイルを指定して監査 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  init_audit_db("data/audit.duckdb")
  ```

- ETL を cron / Airflow 等から定期実行する際は、環境変数・DB パス設定を確実に行い、ログ出力レベルを適切に設定してください。

---

必要であれば README に CI 設定、テスト実行方法、より詳細な API リファレンス（各関数の引数詳細）や .env.example ファイルのテンプレートも追加できます。どの情報を優先して追加しましょうか？