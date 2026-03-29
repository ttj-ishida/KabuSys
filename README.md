# KabuSys

日本株向けのデータプラットフォームおよび自動売買リサーチ/監査基盤ライブラリです。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を利用したセンチメント評価）、ファクター計算、品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）など、トレーディングシステムの基盤機能を提供します。

バージョン: 0.1.0

---

## 主な機能

- データ取得・ETL
  - J-Quants API から株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（DuckDB）
  - 差分更新、バックフィル、ページネーション、トークン自動リフレッシュ、レート制御、リトライ実装

- ニュース収集・NLP
  - RSS フィードからニュースを収集し raw_news に保存（SSRF / GZIP / XML の安全対策）
  - OpenAI（gpt-4o-mini）を使った銘柄別ニュースセンチメント（score_news）
  - マクロニュース + ETF（1321）200日移動平均乖離を合成した市場レジーム判定（score_regime）

- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算、IC（Information Coefficient）算出、統計サマリ、Zスコア正規化

- データ品質チェック
  - 欠損（OHLC 欠落）、重複、スパイク（前日比閾値）、日付不整合（未来日付／非営業日）検出
  - 問題は QualityIssue オブジェクトとして収集

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査スキーマの初期化・管理
  - order_request_id を冪等キーとして二重発注防止をサポート
  - UTC タイムゾーン固定や各種制約を含む堅牢な DDL

- ユーティリティ
  - マーケットカレンダー管理（営業日判定、next/prev trading day）
  - DuckDB 用ユーティリティ、統計ユーティリティ（zscore_normalize）

---

## セットアップ手順（開発環境向け）

前提
- Python 3.10 以上（型注釈で X | Y を使用）
- Git

1. リポジトリのクローン
   ```bash
   git clone <REPO_URL>
   cd <REPO_DIR>
   ```

2. 仮想環境の作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows (PowerShell 等)
   ```

3. 必要パッケージのインストール（例）
   - requirements.txt が無ければ下記パッケージをインストールしてください。
   ```bash
   pip install duckdb openai defusedxml
   ```
   （プロジェクトで他の依存がある場合は requirements.txt を参照してインストールしてください）

4. 環境変数（.env）を用意
   - プロジェクトルート（.git もしくは pyproject.toml があるディレクトリ）に `.env` / `.env.local` を置くと自動で読み込まれます（自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 最低限必要な環境変数（例）:
     ```
     JQUANTS_REFRESH_TOKEN=あなたの_jquants_refresh_token
     OPENAI_API_KEY=あなたの_openai_api_key
     KABU_API_PASSWORD=（kabu ステーション API のパスワード）
     SLACK_BOT_TOKEN=（Slack 通知用）
     SLACK_CHANNEL_ID=（Slack 通知先チャンネル）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development / paper_trading / live
     LOG_LEVEL=INFO
     ```
   - `.env` のパースはシェル風の単純な形式に対応しています（`export KEY=val` も可、クォート内のエスケープ等も扱います）。

---

## 使い方（代表的な API と実行例）

ここでは Python インタプリタやスクリプトからの呼び出し例を示します。DuckDB 接続は `duckdb.connect()` を使用します。

1. DuckDB に接続して ETL を実行（日次 ETL）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニュースセンチメントのスコア付け（OpenAI API 必須）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key None の場合は OPENAI_API_KEY を参照
   print("書き込み銘柄数:", written)
   ```

3. 市場レジーム判定（ETF 1321 とマクロニュースを合成）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. 監査ログ用 DB 初期化
   ```python
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # conn は初期化済み DuckDB 接続
   ```

5. ファクター計算例
   ```python
   from datetime import date
   import duckdb
   from kabusys.research.factor_research import calc_momentum, calc_volatility, calc_value

   conn = duckdb.connect("data/kabusys.duckdb")
   mom = calc_momentum(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

6. データ品質チェック
   ```python
   import duckdb
   from kabusys.data.quality import run_all_checks

   conn = duckdb.connect("data/kabusys.duckdb")
   issues = run_all_checks(conn, target_date=None)
   for i in issues:
       print(i)
   ```

注意:
- OpenAI / J-Quants の API キーは `.env` か引数で指定してください。
- 堅牢性のため、API 呼び出しはリトライ・バックオフ・フェイルセーフ（失敗時はスキップして続行）などが組み込まれていますが、本番運用ではログ・通知・監視を併用してください。

---

## 重要な設計上の注意点（概要）

- ルックアヘッドバイアス防止: 各モジュールは内部で `datetime.today()` や `date.today()` を不用意に参照せず、必ず外部から `target_date` を渡して判定/計算を行うよう設計されています。
- 冪等性: ETL 保存処理は可能な限り ON CONFLICT（または同等の手法）で上書き（冪等）処理を実装。
- フェイルセーフ: LLM / 外部 API エラーは基本的に例外放出ではなくフォールバック値を返すか、処理をスキップして続行する設計です（ログは残ります）。
- セキュリティ: RSS フェッチは SSRF 対策、XML の defusedxml 使用、リダイレクト先の検査、受信サイズ制限などの対策を講じています。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（settings オブジェクト）
  - ai/
    - __init__.py
    - news_nlp.py         - ニュースの LLM を用いたセンチメントスコアリング
    - regime_detector.py  - マクロニュース + ETF MA200 による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py   - J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py         - ETL パイプライン（run_daily_etl 等）
    - etl.py              - ETLResult のエクスポート
    - news_collector.py   - RSS フィード収集（SSRF 対策・前処理）
    - calendar_management.py - マーケットカレンダー管理（営業日判定等）
    - stats.py            - 汎用統計ユーティリティ（zscore_normalize）
    - quality.py          - データ品質チェック（欠損・重複・スパイク等）
    - audit.py            - 監査ログスキーマ初期化・監査 DB ユーティリティ
  - research/
    - __init__.py
    - factor_research.py  - Momentum/Volatility/Value の計算
    - feature_exploration.py - 将来リターン / IC / 統計サマリ 等
  - research/ .. other research utilities
  - ai/ .. LLM 関連
  - その他: strategy, execution, monitoring（パッケージエクスポートに含まれるが今回の抜粋では各実装の一部が省略されています）

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（LLM 呼び出しに必要）
- KABU_API_PASSWORD — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知用
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB 等に使う SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env 読み込みを抑制する（値が存在すれば無効化）

---

## 開発・テスト時のヒント

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探す）基準で行われます。ユニットテストで環境分離したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し部やネットワーク I/O 部分はモック可能（コメント中にもテスト差替えポイントが明記されています）。ユニットテストでは外部 API を直接叩かないようにしてください。
- DuckDB は軽量で単一ファイル DB のため、テストでは `:memory:` を指定してインメモリ DB を利用できます（audit.init_audit_db でも対応）。

---

## ライセンス / 貢献

- この README 生成時点ではリポジトリ自体のライセンスや貢献ガイドは明示されていません。実際のリポジトリに LICENSE / CONTRIBUTING.md を追加してください。

---

不明点や README に追加したい項目（例: CI 手順、詳細な .env.example、実運用時の監視設計や Slack 通知の実装例など）があれば指示ください。README を拡張してサンプル .env.example や推奨 requirements.txt の内容も追加できます。