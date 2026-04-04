# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、マーケットレジーム判定、ファクター計算、監査ログ（注文→約定トレーサビリティ）など、トレーディングシステムの基盤機能を提供します。

---

## 主要機能

- データ ETL（J-Quants API からの株価・財務・カレンダー取得）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュースの LLM によるセンチメント分析（gpt-4o-mini を想定）
  - 銘柄別ニューススコア（ai_scores）
  - マクロセンチメント + ETF MA による市場レジーム判定（bull / neutral / bear）
- 監査ログ（signal_events / order_requests / executions）スキーマ生成・初期化
- 研究用ユーティリティ（ファクター計算、将来リターン、IC 計算、Z スコア正規化）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 環境変数管理（.env 自動ロード）と設定ラッパー

---

## 必要条件

- Python 3.10+
- 推奨パッケージ（最低限）:
  - duckdb
  - openai
  - defusedxml

（実際のインストールにはプロジェクトの requirements.txt / pyproject.toml を使用してください。例: pip install -r requirements.txt または pip install -e .）

---

## セットアップ手順

1. リポジトリをクローン:
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成（任意）:
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存関係インストール:
   - 例:
     ```
     pip install duckdb openai defusedxml
     pip install -e .
     ```

4. 環境変数の設定:
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（CWD に依存しません）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（LLM 呼び出しに必須）
     - KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 関連
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: 通知用（任意）
     - DUCKDB_PATH: デフォルトの DuckDB ファイルパス（例: data/kabusys.duckdb）
     - SQLITE_PATH: 監視データ用 SQLite（任意）
     - KABUSYS_ENV: 動作環境 (development | paper_trading | live)
     - LOG_LEVEL: ログレベル (DEBUG | INFO | WARNING | ERROR | CRITICAL)
     - 監視閾値など: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

   - .env の書き方の例（コメント可、export 形式も可）:
     ```
     JQUANTS_REFRESH_TOKEN=xxxxx
     OPENAI_API_KEY=sk-xxxx
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

5. データディレクトリ作成（必要に応じて）:
   ```
   mkdir -p data
   ```

---

## 使い方（抜粋・サンプル）

以下はライブラリの主要機能を呼ぶ際の例です。実運用ではログ設定・エラーハンドリングを追加してください。

- 共通設定の取得:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

- DuckDB 接続を作成:
  ```python
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（カレンダー、株価、財務、品質チェック）:
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメント（銘柄別スコア）を算出して ai_scores に書き込む:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数に設定しておくか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- マーケットレジーム判定（ETF 1321 の MA200 とマクロ記事センチメントを合成）:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログスキーマの初期化（監査専用 DB もしくは既存の DuckDB に追加）:
  ```python
  from kabusys.data.audit import init_audit_schema, init_audit_db
  # 既存 conn に追加:
  init_audit_schema(conn, transactional=True)
  # または専用 DB を作る:
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))
  ```

- データ品質チェックの実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026, 3, 20))
  for i in issues:
      print(i)
  ```

- ニュース RSS フェッチ（低レベルユーティリティ）:
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], "yahoo_finance")
  ```

注意:
- AI モジュール（news_nlp, regime_detector）は OpenAI の API を使います。API キーは環境変数 OPENAI_API_KEY へ設定するか、各関数の api_key 引数で明示的に渡してください。
- 自動環境変数読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py — パッケージ初期化（version, export）
- config.py — 環境変数 / 設定管理（.env 自動読み込み、Settings）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（銘柄別スコア算出、OpenAI 呼び出し、バッチ処理）
  - regime_detector.py — マーケットレジーム判定（ETF MA + マクロセンチメント合成）
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 & DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - calendar_management.py — 市場カレンダー管理、営業日判定ユーティリティ
  - news_collector.py — RSS 取得と前処理（SSRF 対策等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 共通統計ユーティリティ（Z スコア正規化）
  - audit.py — 監査ログスキーマの DDL と初期化
  - etl.py — ETLResult の公開
- research/
  - __init__.py
  - factor_research.py — モメンタム / バリュー / ボラティリティ等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等
- research, execution, monitoring ...（その他実行 / 監視用モジュール群が想定）

---

## 運用上の注意・設計方針のポイント

- Look-ahead バイアス対策:
  - 日時計算で datetime.today() / date.today() を直接参照しない設計（多くの関数は target_date を引数で受けます）。
  - ETL / 取得関数は fetched_at を UTC で記録し、「いつデータを知り得たか」をトレース可能にしています。
- 冪等性:
  - J-Quants から取得したデータの DB 保存は ON CONFLICT DO UPDATE や UPSERT により冪等化しています。
  - 監査ログの order_request_id / broker_execution_id は冪等キーとして設計されています。
- フェイルセーフ:
  - LLM 呼び出し失敗時はゼロ・中立値にフォールバックするなど、致命的でない場合は処理を継続します（ログを必ず残す）。
- セキュリティ:
  - news_collector は SSRF 回避（リダイレクト検査 / プライベート IP チェック）や XML パースの安全化（defusedxml）を行います。
- レート制限:
  - J-Quants クライアントは固定間隔スロットリングでレート制限を遵守します（120 req/min）。

---

## テスト・開発ヒント

- 自動 .env ロードを無効化したい単体テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出しはネットワーク依存なので unit test では kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を unittest.mock.patch で差し替えてください。
- DuckDB を :memory: で使えばファイル I/O を伴わずに高速にテストできます。例:
  ```python
  import duckdb
  conn = duckdb.connect(":memory:")
  ```

---

## ライセンス・貢献

（ここにライセンス表記・Contributing ガイド等を追加してください）

---

README に記載の API 名や環境変数はソースコードの docstring / config クラスに基づく要約です。実際の利用やデプロイではログ設定、例外監視、シークレット管理（Vault 等）を適切に行ってください。