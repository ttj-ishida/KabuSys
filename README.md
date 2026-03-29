# KabuSys

KabuSys は日本株向けの自動売買プラットフォーム用ライブラリ群です。本リポジトリはデータ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マクロレジーム判定、監査ログ用スキーマなどを含むモジュール群を提供します。

主な設計方針：
- ルックアヘッドバイアスを避ける（日時取得やクエリで未来データを参照しない）
- DuckDB をデータ基盤として使用（ETL／分析／監査ログ）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価（JSON Mode, 再試行・フォールバックあり）
- J-Quants API からの差分取得を想定した安全なレート制御とリトライロジック

---

## 機能一覧

- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務データ、JPX マーケットカレンダー、上場銘柄一覧
  - Rate limiter、401 自動リフレッシュ、ページネーション対応
- ETL パイプライン
  - 差分取得、保存（冪等）、品質チェック（欠損・スパイク・重複・日付不整合）
  - 日次パイプライン（run_daily_etl）
- ニュース収集 & 前処理
  - RSS フィード取得（SSRF 対策、gzip 対応、トラッキングパラメータ除去）
  - raw_news / news_symbols への保存フローを想定
- ニュース NLP（AI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - マクロニュースと ETF（1321）200日MA乖離の組合せによる市場レジーム判定（score_regime）
  - OpenAI 呼び出しは厳密な JSON 出力を期待、失敗時はフェイルセーフで継続
- 研究用ユーティリティ（Research）
  - ファクター算出（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（スピアマン）計算、ファクター統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events, order_requests, executions テーブルの DDL / インデックス
  - init_audit_schema / init_audit_db による初期化

---

## 必要条件（主な依存パッケージ）

- Python 3.10+
- duckdb
- openai（OpenAI Python SDK）
- defusedxml
- その他標準ライブラリ

（プロジェクトの pyproject.toml / requirements.txt を参照してください）

---

## セットアップ手順

1. リポジトリをクローンして、開発環境を作成します。

   ```
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストールします（例: pip）。

   ```
   pip install -U pip
   pip install duckdb openai defusedxml
   # またはプロジェクトがパッケージ化されていれば:
   pip install -e .
   ```

3. 環境変数（.env）を用意します。リポジトリルートに `.env` / `.env.local` を置くと、自動で読み込まれます（パッケージの config モジュールが .env を探索して読み込みます）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   必須（主なもの）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID
   - OPENAI_API_KEY（score_news / score_regime を呼ぶ場合）

   任意（既定値あり）:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
   - LOG_LEVEL (DEBUG|INFO|...) — デフォルト: INFO
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視用 DB のパス）

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-xxxx
   SLACK_BOT_TOKEN=xoxb-xxxx
   SLACK_CHANNEL_ID=C01234567
   KABUSYS_ENV=development
   DUCKDB_PATH=data/kabusys.duckdb
   ```

4. DuckDB 用のスキーマや監査 DB を初期化する場合（監査ログ専用 DB を作る例）:

   Python から:
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_db

   conn = init_audit_db("data/audit.duckdb")  # :memory: も可
   ```

   既存の DuckDB 接続にスキーマのみ追加する場合:
   ```python
   from kabusys.data.audit import init_audit_schema
   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要な API 例）

以下は代表的な呼び出し例です。実運用ではエラーハンドリングやログ設定を行ってください。

1. DuckDB 接続の作成

   ```python
   import duckdb
   conn = duckdb.connect("data/kabusys.duckdb")
   ```

2. 日次 ETL の実行

   ```python
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   res = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(res.to_dict())
   ```

3. ニュース NLP スコアリング（OpenAI API キーは環境変数 OPENAI_API_KEY で設定）

   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   n = score_news(conn, target_date=date(2026, 3, 20))
   print(f"Wrote {n} ai_scores")
   ```

4. 市場レジーム判定（ETF 1321 MA200 とマクロニュースの組合せ）

   ```python
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 研究用ファクター計算例

   ```python
   from datetime import date
   from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

   mom = calc_momentum(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   ```

6. 監査ログの利用（発注フローなど）  
   - init_audit_schema / init_audit_db でテーブルを用意し、アプリ側で signal_events / order_requests / executions を INSERT/UPDATE してください。

---

## 実装上の注意・運用ポイント

- .env 自動読み込み:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を基準に .env を自動読み込みします。
  - .env.local は .env を上書きする形で読み込まれます（OS 環境変数より低優先）。
  - 自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出し:
  - API の失敗時は最大 retry を行い、それでも失敗した場合は安全側のデフォルト（0.0）にフォールバックします。テスト時は _call_openai_api をモックしてください。
- J-Quants クライアント:
  - RateLimiter がレート管理を行います。大量のページネーションがある処理では遅延が発生します。
  - get_id_token() は自動でリフレッシュを試みます（401 を検出すると1回リフレッシュして再試行）。
- DuckDB 実行:
  - 一部の executemany は空リストを渡すと問題となるバージョンがあるため、空チェックを行っています。
- ルックアヘッドバイアス:
  - モジュール設計上、多くの関数は内部で date.today() や datetime.today() を直接参照せず、引数で target_date を受け取ります。バックテスト運用時は注意してください。

---

## ディレクトリ構成（主なファイル）

（抜粋。実際のリポジトリには追加ファイルがあります）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py (re-export)
    - calendar_management.py
    - news_collector.py
    - quality.py
    - stats.py
    - audit.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/*（ファクター・探索用ユーティリティ群）

各モジュールの役割：
- config.py: 環境変数読み込み、Settings クラス（必須変数の取得・検証）
- data/jquants_client.py: J-Quants API 通信・保存ロジック（fetch_*, save_*）
- data/pipeline.py: ETL の上位制御（run_daily_etl 等）
- data/quality.py: データ品質チェック（欠損・重複・スパイク・日付不整合）
- data/news_collector.py: RSS 収集および前処理
- ai/news_nlp.py: ニュースの銘柄別センチメント算出（OpenAI）
- ai/regime_detector.py: マクロセンチメント + ETF MA による市場レジーム判定
- research/*: 研究・因子計算・統計ユーティリティ

---

## テスト / モックに関するヒント

- OpenAI API 呼び出しは各モジュール内の _call_openai_api を unittest.mock.patch で差し替えてテストすることを想定しています（score_news / score_regime で特に有用）。
- network IO（RSS fetch / J-Quants）もモック可能です。news_collector._urlopen や jquants_client._request を差し替えることで外部依存を切れます。
- DuckDB は ":memory:" を渡すとインメモリ DB になるため単体テストで便利です。

---

## ライセンス・貢献

各ファイルへ実装上のコメントや設計指針が含まれています。バグ報告、改善提案、テストケースの追加はプルリクエストで歓迎します。ライセンスはリポジトリルートの LICENSE を参照してください。

---

この README はコードベースの概要と使い方の導入を目的としています。個別 API の詳細やパラメータは該当モジュールの docstring（ソース内コメント）を参照してください。