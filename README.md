# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）などの機能を提供します。

主な設計方針
- バックテストにおけるルックアヘッドバイアス回避（date/target_date ベースの処理、現在時刻参照を極力排除）
- DuckDB を用いたローカルデータストア
- J-Quants API や OpenAI を利用する処理には堅牢なリトライ・フェイルセーフを実装
- ETL/品質チェックは失敗時も他処理を継続する（問題を収集して呼び出し元で判断）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を探索）
  - 必須環境変数のラッパー（kabusys.config.settings）

- データ取得 / ETL（kabusys.data.jquants_client / pipeline）
  - J-Quants API から株価日足・財務データ・JPXカレンダーを差分取得・保存
  - レートリミット制御、トークン自動リフレッシュ、ページネーション対応
  - ETL パイプライン（run_daily_etl）＋個別 ETL（prices/financials/calendar）
  - 保存は冪等（ON CONFLICT DO UPDATE）

- ニュース収集 / NLP（kabusys.data.news_collector, kabusys.ai.news_nlp）
  - RSS 取得（SSRF 対策、サイズ制限、URL 正規化）
  - OpenAI を用いた銘柄別ニュースセンチメント解析（gpt-4o-mini, JSON mode）
  - スコアを ai_scores テーブルへ保存

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321 の 200 日移動平均乖離（70%）とマクロニュースセンチメント（30%）を合成
  - LLM（OpenAI）呼び出しは冗長対策あり（リトライ、フェイルセーフ）

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（急騰/急落）、主キー重複、日付不整合を検出
  - QualityIssue オブジェクトのリストを返す（severity による分類）

- 研究用ユーティリティ（kabusys.research）
  - モメンタム、バリュー、ボラティリティ等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - zscore_normalize 等の共通統計ユーティリティ

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - audit DB 初期化関数（init_audit_db / init_audit_schema）

---

## セットアップ手順

1. Python 環境
   - Python 3.10+ を推奨（typing 機能や型注釈を利用）
2. 仮想環境を作成して有効化
   - 例（Unix / macOS）:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
3. 依存パッケージをインストール
   - 必要最低限:
     - duckdb
     - openai
     - defusedxml
   - 例:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発用にパッケージ化されている場合:
     ```
     pip install -e .
     ```
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）を基準に自動で `.env` / `.env.local` を読み込みます。
   - 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
   - 代表的な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN (必須)
     - SLACK_CHANNEL_ID (必須)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
     - KABUSYS_ENV (development | paper_trading | live)
     - LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
     - OPENAI_API_KEY (AI モジュールで未指定時に使用)

   - 注意: 必須変数が不足すると `kabusys.config.settings` のプロパティで ValueError が発生します。

5. データベースディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易例）

以下は代表的な使用例です。各関数は DuckDB 接続（duckdb.connect(...) の返り値）を受け取り動作します。

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- ETL を日次で実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのスコアリング（OpenAI API キー必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されている前提
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み件数: {written}")
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB を初期化
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- カレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  ```

- 研究用ファクター計算
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  momentum = calc_momentum(conn, date(2026, 3, 20))
  ```

- J-Quants から直接データ取得（テスト・ETL 以外は推奨しない）
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # JQUANTS_REFRESH_TOKEN が必要
  quotes = fetch_daily_quotes(id_token=token, date_from=date(2026,3,1), date_to=date(2026,3,20))
  ```

---

## 重要な注意点 / 設計に関するメモ

- ルックアヘッドバイアス防止
  - 多くのモジュールは内部で date.today() を参照せず、関数引数として target_date を受け取ります。バックテストや再現性のため、この設計に従ってください。

- OpenAI 呼び出し
  - news_nlp、regime_detector は gpt-4o-mini を想定しており、JSON mode を使って厳密な JSON 出力を期待します。API 失敗時はフェイルセーフで中立スコア（0.0）などにフォールバックします。

- 環境ファイルの自動読み込み
  - プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込みます。`.env.local` は `.env` を上書きします。OS 環境変数が優先され、上書き保護されています。
  - 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- DuckDB 互換性
  - DuckDB のバージョンによって executemany の空リストなどの挙動差異があるため、コード内で空チェックを行っています。DuckDB のメジャーアップデート時は注意してください。

---

## ディレクトリ構成（主要ファイルと説明）

src/kabusys/
- __init__.py
  - パッケージ定義 / バージョン情報
- config.py
  - 環境変数管理、settings オブジェクトを提供（J-Quants / kabu / Slack / DB パス 等）
- ai/
  - __init__.py
  - news_nlp.py
    - ニュースを銘柄別に集約して LLM へ送り、ai_scores に書き込む
  - regime_detector.py
    - ETF 1321 の MA 乖離とマクロセンチメントを合成して市場レジームを判定
- data/
  - __init__.py
  - calendar_management.py
    - 市場カレンダー管理・営業日判定・夜間更新ジョブ
  - pipeline.py
    - ETL パイプライン（run_daily_etl 等）、ETLResult データクラス
  - etl.py
    - pipeline.ETLResult の再エクスポート
  - stats.py
    - zscore_normalize などの統計ユーティリティ
  - quality.py
    - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py
    - 監査ログ（signal_events / order_requests / executions）の DDL と初期化関数
  - jquants_client.py
    - J-Quants API クライアント（取得・保存ユーティリティ）
  - news_collector.py
    - RSS 収集・正規化・保存ユーティリティ（SSRF/サイズ制限等の防御あり）
- research/
  - __init__.py
  - factor_research.py
    - momentum / value / volatility 等のファクター計算
  - feature_exploration.py
    - 将来リターン計算、IC、統計サマリー、ランク変換

その他
- data/
  - デフォルトのローカル DB 保存先（例: data/kabusys.duckdb, data/monitoring.db）

---

## ライセンス / 責務

この README はコードベースからの情報を基に生成しています。商用利用・本番運用前には十分なレビュー・テストを行ってください。外部 API（J-Quants / OpenAI）を利用する箇所では API 利用規約に従ってください。

---

README に不足している具体的な環境 (Python バージョン、追加の依存関係、テスト実行方法など) があれば教えてください。必要に応じてサンプル .env.example の雛形や docker-compose / systemd ユニット例も作成できます。