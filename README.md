# KabuSys

KabuSys は日本株のデータ基盤・リサーチ・AI・監査・自動売買のためのライブラリ群です。  
DuckDB をデータ層に用い、J-Quants API / RSS / OpenAI を組み合わせてデータ収集（ETL）→品質チェック→特徴量計算→AI スコアリング→監査ログ保管までを一貫してサポートします。設計上、バックテスト時のルックアヘッドバイアスを避ける工夫や、API のリトライ/レート制御、冪等性（idempotency）を重視しています。

主な設計方針の要点
- Look-ahead バイアス回避（内部で date.today() を不用意に参照しない実装）
- DuckDB を中心にしたローカルデータパイプライン
- J-Quants / OpenAI / RSS への堅牢な接続（リトライ、レート制御、SSRF 防御 等）
- ETL / 品質チェック / 研究用ユーティリティ / 監査ログ機能をモジュール化

---

## 機能一覧
- データ収集（ETL）
  - J-Quants から株価日足（OHLCV）、財務指標、上場情報、マーケットカレンダーを差分取得・保存
  - RSS からニュース記事収集（前処理、URL 正規化、SSRF 対策）
- データ品質チェック
  - 欠損、重複、未来日付、スパイク（前日比）などの検出とレポート
- AI スコアリング（OpenAI利用）
  - ニュースベースで銘柄ごとのセンチメント ai_score を生成（gpt-4o-mini, JSON Mode）
  - マクロニュースと ETF の MA を組み合わせて市場レジーム（bull/neutral/bear）を判定
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計など
- 監査ログ（audit）
  - signal_events / order_requests / executions テーブルを作成し、トレース可能な監査ログを保持
- その他ユーティリティ
  - カレンダー管理（営業日判定、next/prev trading day）
  - 統計ユーティリティ（Zスコア正規化 等）

---

## セットアップ手順

1. Python 環境（推奨: 3.10+）を用意します。

2. 必要なパッケージをインストールします（プロジェクトに requirements ファイルがある想定）。最低限必要となるライブラリ例:
   - duckdb
   - openai
   - defusedxml
   - （その他: requests 等、実装に応じて追加）

   例:
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージのインストール（開発環境向け）:
   ```
   pip install -e .
   ```
   またはプロジェクトルートで pip install -r requirements.txt

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと、kabusys.config が自動で読み込みます（自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数（少なくとも以下を設定してください）:
     - JQUANTS_REFRESH_TOKEN：J-Quants の refresh token
     - KABU_API_PASSWORD：kabu API パスワード（注文実行をする場合）
     - SLACK_BOT_TOKEN：Slack 通知に使用する場合
     - SLACK_CHANNEL_ID：Slack 通知先チャンネルID
     - OPENAI_API_KEY：OpenAI を利用する場合（score_news / score_regime の api_key を省略する場合）
   - 任意:
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト development）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）

   簡単な .env 例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   DUCKDB_PATH=~/kabusys/data/kabusys.duckdb
   KABUS_API_PASSWORD=...
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   ```

5. DuckDB のスキーマ初期化（必要に応じて）
   - 監査ログ用 DB を初期化する例:
     ```python
     from kabusys.config import settings
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可
     ```
   - 他のシステム向けに必要なスキーマは実装上別途用意されている想定です（ETL 実行時に必要なテーブルがない場合はエラーになることがあります）。

---

## 使い方（基本例）

以下は主要なユースケースの簡単なサンプルコードです。各関数は duckdb の接続オブジェクト（kabusys.settings.duckdb_path で指定したパスに接続）を受け取ります。

- 共通準備:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースの AI スコアリング（score_news）
  - OpenAI API キーを環境変数 OPENAI_API_KEY で指定するか、api_key を渡します。
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  n_written = score_news(conn, target_date=date(2026, 3, 19))
  print(f"ai_scores に書き込んだ銘柄数: {n_written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 19))
  ```

- 監査 DB 初期化（監査向け専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  audit_conn = init_audit_db(settings.duckdb_path)  # 別パスでも可
  ```

- 研究用ファクター計算・分析
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, zscore_normalize

  momentum = calc_momentum(conn, target_date=date(2026, 3, 19))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 19))
  value = calc_value(conn, target_date=date(2026, 3, 19))
  normalized = zscore_normalize(momentum, ["mom_1m", "ma200_dev"])
  ```

注意点
- OpenAI 呼び出しはネットワーク/課金が関わるため、テスト時は各モジュールに用意された内部関数をモックしてテストすることを推奨します（例: kabusys.ai.news_nlp._call_openai_api のパッチ）。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動で .env ファイルを読み込まなくなります（テストで環境を完全に制御したい場合に便利）。

---

## 環境変数一覧（主要なもの）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須 for kabu API)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- OPENAI_API_KEY (score_news / score_regime を環境変数経由で使う場合)
- SLACK_BOT_TOKEN (Slack 通知)
- SLACK_CHANNEL_ID (Slack 通知先)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live) デフォルト development
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 (.env 自動読み込みを無効化)

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル・モジュール構成（src/kabusys 配下）:

- kabusys/
  - __init__.py
  - config.py                     # 環境変数 / 設定管理（.env 自動ロード等）
  - ai/
    - __init__.py
    - news_nlp.py                 # ニュースを OpenAI でスコアリング
    - regime_detector.py          # ETF MA とマクロニュースでレジーム判定
  - data/
    - __init__.py
    - jquants_client.py           # J-Quants API クライアント + DuckDB 保存
    - pipeline.py                 # ETL パイプライン実行ロジック
    - etl.py                      # ETL の公開インターフェース (ETLResult)
    - news_collector.py           # RSS 収集・前処理・保存
    - quality.py                  # データ品質チェック
    - stats.py                    # 統計ユーティリティ（zscore など）
    - calendar_management.py      # 市場カレンダー管理・営業日判定
    - audit.py                    # 監査テーブル初期化・監査DBユーティリティ
  - research/
    - __init__.py
    - factor_research.py          # モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py      # 将来リターン・IC・統計サマリー
  - research/ (その他)
  - （そのほか strategy / execution / monitoring 等のモジュールが想定されます）

詳細なファイルは src/kabusys 以下を参照してください。

---

## テスト・開発のヒント
- OpenAI / ネットワーク依存部分はユニットテストでモックする（モジュール内部に差し替えしやすいフックが用意されています）。
- .env の自動ロードはプロジェクトルート（.git または pyproject.toml がある場所）を基準に行われます。テストで自動ロードを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を使うことで高速にローカルで開発でき、":memory:" を使えばテスト用のインメモリ DB を使えます。

---

もし README に追加したい利用例（運用スクリプト、Docker 設定、CI／CD パイプラインの例など）があれば用途に合わせて追記します。必要な情報を教えてください。