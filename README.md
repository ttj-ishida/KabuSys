# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、ニュース NLP（OpenAI）、市場レジーム判定、ファクター研究、監査ログなどを含むモジュール群を提供します。

---

## 主要な特徴

- J-Quants API 経由で株価／財務／カレンダーを差分取得・保存（レートリミット・リトライ実装）
- DuckDB を用いたローカルデータベース格納・冪等保存（ON CONFLICT / upsert）
- ニュース収集（RSS）・前処理と OpenAI を使ったニュースセンチメント解析（バッチ / JSON mode）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- ファクター計算（モメンタム・バリュー・ボラティリティ等）と研究用ユーティリティ（forward returns, IC, summary）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査（audit）テーブル群の初期化ユーティリティ（signal → order → execution のトレーサビリティ）
- 環境変数管理と .env 自動ロード（プロジェクトルート検出）

---

## 必要環境

- Python 3.10+
- 主な依存パッケージ（抜粋）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ中心に書かれているため最小限の外部依存で動作します）

プロジェクトに requirements.txt / pyproject.toml があればそちらを参照してください。

---

## セットアップ手順

1. 仮想環境を作成して有効化（例: venv / poetry）
   - venv の例:
     ```
     python -m venv .venv
     source .venv/bin/activate  # macOS / Linux
     .venv\Scripts\activate     # Windows
     ```

2. パッケージをインストール
   - ローカル開発インストール:
     ```
     pip install -e .
     ```
   - または必要な依存を個別にインストール:
     ```
     pip install duckdb openai defusedxml
     ```

3. 環境変数を設定
   - プロジェクトルートの `.env` / `.env.local` を作成すると自動で読み込まれます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY: OpenAI API キー（score_news / regime で使用）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注系で使用）
     - SLACK_BOT_TOKEN: Slack 通知トークン（通知機能がある場合）
     - SLACK_CHANNEL_ID: Slack 送信先チャンネルID
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 動作環境（development / paper_trading / live）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）

   - 例 `.env`:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     ```

4. データベース用ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単なサンプル）

以下はライブラリの代表的な使用例です。すべて Python スクリプト / REPL から実行できます。

- DuckDB 接続の作成（監査 DB 初期化例）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_db

  # 監査専用 DB を初期化して接続を取得
  conn = init_audit_db("data/audit.duckdb")
  ```

- 日次 ETL の実行（J-Quants から差分取得して保存）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（OpenAI）でスコアを付与
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数にある場合は api_key を省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("ai_scores written:", n_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026, 3, 20))
  val = calc_value(conn, date(2026, 3, 20))
  vol = calc_volatility(conn, date(2026, 3, 20))
  ```

- Zスコア正規化（ユーティリティ）
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "mom_6m"])
  ```

注意点:
- OpenAI を呼ぶ関数は API の失敗をフェイルセーフで扱う設計が多く、API失敗時はスコアを 0 にフォールバックする等の動作をします。
- ルックアヘッドバイアス防止のため、内部実装は target_date を明示的に受け取り、datetime.today() を直接参照しない設計です。バックテストで利用する際は target_date を適切に設定してください。

---

## よく使うモジュール（API）

- kabusys.config
  - settings: 環境変数から設定を取得（例: settings.jquants_refresh_token）
- kabusys.data.jquants_client
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
  - save_daily_quotes / save_financial_statements / save_market_calendar
  - get_id_token
- kabusys.data.pipeline
  - run_daily_etl(conn, target_date, ...)
  - run_prices_etl / run_financials_etl / run_calendar_etl
- kabusys.data.news_collector
  - fetch_rss / preprocess utilities
- kabusys.ai.news_nlp
  - score_news(conn, target_date, api_key=None)
- kabusys.ai.regime_detector
  - score_regime(conn, target_date, api_key=None)
- kabusys.research
  - calc_momentum, calc_value, calc_volatility, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.data.quality
  - run_all_checks(conn, target_date, ...), 各チェック関数
- kabusys.data.audit
  - init_audit_schema / init_audit_db

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境設定 / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                   -- ニュースセンチメント解析、score_news
    - regime_detector.py            -- 市場レジーム判定、score_regime
  - data/
    - __init__.py
    - jquants_client.py             -- J-Quants API クライアント + 保存関数
    - pipeline.py                   -- ETL パイプライン（run_daily_etl 等）
    - calendar_management.py        -- 市場カレンダーの操作ユーティリティ
    - stats.py                      -- 統計ユーティリティ（zscore_normalize）
    - quality.py                    -- データ品質チェック
    - news_collector.py             -- RSS 収集・前処理
    - audit.py                      -- 監査ログスキーマ初期化
    - etl.py                        -- ETLResult の再エクスポート
  - research/
    - __init__.py
    - factor_research.py            -- Momentum / Value / Volatility の計算
    - feature_exploration.py        -- forward returns, IC, factor summary

---

## 設計方針・注意事項（要点）

- Look-ahead bias 防止:
  - 多くの処理は target_date を受け取り、過去データのみ参照する（datetime.today() を直接参照しない）。
- フェイルセーフ:
  - 外部 API（OpenAI / J-Quants）が一時エラーを返しても、部分的に処理を継続する設計（スコアを 0 にする、失敗コードをスキップ等）。
- 冪等性:
  - DuckDB への保存は基本的に ON CONFLICT / upsert を使って冪等になるよう実装。
- セキュリティ:
  - news_collector は SSRF 対策（スキーム検証、プライベートホスト拒否、リダイレクトチェック）と XML パーサ保護（defusedxml）を備えています。

---

## トラブルシューティング

- .env が読み込まれない場合:
  - プロジェクトルートの検出は __file__ を基準に .git または pyproject.toml を探します。環境によってルートが見つからない場合は自動ロードがスキップされます。自動ロードを無効化している場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を確認してください。
- OpenAI / J-Quants の認証エラー:
  - 環境変数に正しいキーが設定されているか確認してください。J-Quants の場合は JQUANTS_REFRESH_TOKEN、OpenAI は OPENAI_API_KEY。
- DuckDB の接続先:
  - settings.duckdb_path（デフォルト data/kabusys.duckdb）を利用するか、明示的に duckdb.connect(...) で接続してください。

---

必要であれば README にサンプル .env.example や詳細な API リファレンス、開発フロー（テスト・CI）のセクションを追加します。どの情報を追加したいか教えてください。