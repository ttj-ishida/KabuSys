# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定のトレーサビリティ）、カレンダー管理などを提供します。

主な目的：
- 日次 ETL による株価・財務・カレンダーの差分取得と品質チェック
- ニュースの収集・LLM による銘柄センチメント算出（ai_scores）
- 市場レジーム判定（MA と マクロニュースの合成）
- 研究用途のファクター計算・特徴量解析
- 発注〜約定に関する監査ログスキーマ（DuckDB）

---

## 機能一覧

- データ取得 & ETL
  - J-Quants API 経由で株価日足（OHLCV）、財務データ、JPX カレンダーを差分取得・保存
  - 差分更新 / バックフィル / ページネーション対応
  - データ保存は DuckDB に対して冪等（ON CONFLICT DO UPDATE）
  - 品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集 & NLP
  - RSS からニュース収集（SSRF 防止、トラッキングパラメータ除去、本文前処理）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（batch, JSON mode）
  - レスポンス検証とスコア ±1.0 クリップ、エラーはフェイルセーフで継続

- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して
    日次で市場レジーム（bull / neutral / bear）を算出して保存

- 研究（research）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、z-score 正規化

- 監査ログ（audit）
  - signal_events / order_requests / executions のスキーマ定義・初期化
  - 発注フローのトレーサビリティを UUID 階層で保持

- ユーティリティ
  - 市場カレンダー管理（営業日判定、next/prev_trading_day 等）
  - 環境変数と設定管理（自動 .env ロード・保護など）

---

## 必要条件

- Python 3.10+（型注釈で `|` を使用しているため推奨）
- 主な依存パッケージ（例）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリで HTTP は urllib を使用（requests 非必須）

実際のプロジェクトでは requirements.txt / pyproject.toml を用意してください。

---

## セットアップ手順

1. リポジトリをクローンして開発環境に配置

   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール

   例（pip）:

   ```bash
   pip install duckdb openai defusedxml
   ```

   開発時はソースを editable install:

   ```bash
   pip install -e .
   ```

4. 環境変数設定

   プロジェクトルートに `.env`（または `.env.local`）を置くと、自動で読み込まれます（既存の OS 環境変数は上書きされません）。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   重要な環境変数（代表例）：
   - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
   - KABU_API_PASSWORD — kabu ステーション API パスワード
   - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime などで参照）
   - KABUSYS_ENV — `development` / `paper_trading` / `live`（デフォルト: development）
   - LOG_LEVEL — `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`
   - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - その他（LINE トークンや監視用ファイルパス等）: KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID, SQLITE_PATH, PID_FILE_PATH, KILL_FLAG_PATH

   `.env` のフォーマットは一般的な KEY=VALUE 形式に対応し、export KEY=... もサポートします。クォート・コメントにも対応しています。

---

## 使い方（代表的な例）

以下の例は Python REPL / スクリプトからの利用例です。DuckDB のパスは環境変数 DUCKDB_PATH または明示的に指定してください。

- 日次 ETL を実行する（Pipeline）

  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコア（銘柄センチメント）を作成する

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # api_key を渡さない場合は環境変数 OPENAI_API_KEY を参照
  n_written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("written:", n_written)
  ```

- 市場レジームスコアを算出する

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査ログ用データベースの初期化（audit）

  ```python
  from kabusys.data.audit import init_audit_db

  # 新規ファイルまたは :memory:
  conn = init_audit_db("data/audit.duckdb")
  ```

- OpenAI 呼び出しのテスト時には、モジュール側の _call_openai_api をモックすることが想定されています（ユニットテスト容易化）。

---

## 設定・挙動メモ

- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在する親ディレクトリ）から `.env` → `.env.local` の順で読み込みます。
  - 既存の OS 環境変数は保護され、`.env` の内容が上書きされない設計です（`.env.local` は override=True なので `.env.local` は上書きしますが OS 環境変数は保護されます）。
  - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

- Look-ahead バイアス対策:
  - LLM 呼び出しや ETL の各関数は内部で `datetime.today()` / `date.today()` に依存しないよう設計されています（引数の target_date を基準に動作）。
  - DB クエリは常に target_date 未満・以下などルックアヘッドにならない形になっています。

- フェイルセーフ:
  - OpenAI API 呼び出しや外部 API 呼び出しはリトライやフォールバック（例: マクロセンチメントが取得できない場合は 0.0 とする）を備え、部分的失敗が全体を停止させない設計です。

---

## ディレクトリ構成（概要）

主要なファイルおよびモジュールを抜粋します：

- src/kabusys/
  - __init__.py
  - config.py                     -- 環境変数 / 設定管理（自動 .env ロード）
  - ai/
    - __init__.py
    - news_nlp.py                  -- ニュースの LLM スコアリング
    - regime_detector.py           -- 市場レジーム判定（MA200 + マクロニュース）
  - data/
    - __init__.py
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - etl.py                       -- ETLResult 再エクスポート
    - news_collector.py            -- RSS 収集・前処理・保存
    - calendar_management.py       -- 市場カレンダー管理（営業日判定等）
    - quality.py                   -- データ品質チェック
    - stats.py                     -- 統計ユーティリティ（zscore_normalize 等）
    - audit.py                     -- 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py           -- モメンタム / ボラティリティ / バリュー等
    - feature_exploration.py       -- forward returns / IC / summary
  - monitoring, execution, strategy, etc.
    - （README の元コードベースには戦略・実行・監視に関するパッケージ名が示唆されていますが、上記が主要実装ファイル）

（注）実際のリポジトリではさらに細かなモジュールやテスト、CLI スクリプトなどが存在する可能性があります。ここでは提供されたソースに基づく主要モジュール構成を示しています。

---

## テスト / モックについて（簡単な指針）

- OpenAI 呼び出しは内部で `_call_openai_api` を呼ぶ実装です。ユニットテストではこの関数をパッチして返り値を制御できます（例: `unittest.mock.patch("kabusys.ai.news_nlp._call_openai_api")`）。
- ネットワークやファイルシステムに依存する部分（RSS 取得・J-Quants API）は、それぞれの HTTP/urllib 関数をモックしてテストを行うと良いです。
- DuckDB を ":memory:" で初期化するとテストが容易です（`init_audit_db(":memory:")` など）。

---

もし README に追加したい「CLI の使い方」「具体的な .env.example のテンプレート」「デプロイ手順（systemd / supervisor）」「サンプル SQL スキーマ」などがあれば、その情報を教えてください。README をその内容に合わせて拡張します。