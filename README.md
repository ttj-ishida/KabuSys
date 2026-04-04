# KabuSys — 日本株自動売買システム

KabuSys は日本株向けのデータパイプライン、リサーチ、AI/NLP、監査ログ、および発注監視を組み合わせた自動売買基盤のライブラリ群です。DuckDB をデータレイクとして用い、J-Quants API からのデータ取得、ニュースの NLP スコアリング、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ（オーダー → 約定トレース）といった主要コンポーネントを提供します。

主な対象
- データETL（株価・財務・マーケットカレンダー）
- ニュースのセンチメント分析（OpenAI を利用）
- 市場レジーム判定（ETF + マクロニュース）
- ファクター生成・探索・IC 計算（リサーチ向け）
- 監査ログ（シグナル → 発注 → 約定のトレーサビリティ）
- データ品質チェック、カレンダー管理、ニュース収集

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（認証・ページネーション・レートリミット・保存関数）
  - 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）
  - ニュース収集（RSS 取得、前処理、SSRF 対策）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - 汎用統計ユーティリティ（zscore_normalize）
- ai
  - ニュース NLP スコアリング（score_news）
  - 市場レジーム判定（score_regime; ETF 1321 の MA200 乖離 + マクロセンチメント合成）
- research
  - ファクター計算（calc_momentum / calc_value / calc_volatility）
  - 特徴量探索・IC・統計サマリー（calc_forward_returns / calc_ic / factor_summary / rank）
- config
  - .env 自動ロード（プロジェクトルート検出）と Settings API
  - 必須設定の取得（例: settings.jquants_refresh_token）
- audit / execution / monitoring（発注・監視用インターフェースの基盤）

設計上の特徴:
- ルックアヘッドバイアスを防ぐ（target_date に基づいた過去データ参照）
- 冪等な DB 保存（ON CONFLICT / DELETE→INSERT の設計）
- API 呼び出しはリトライ / バックオフ / レート制御を実装
- 外部ライブラリは最小限（依存: duckdb, openai, defusedxml 等）

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに | 記法を使用）
- システムにネットワークアクセスがあること（J-Quants / OpenAI / RSS）

1. リポジトリをクローン／チェックアウト
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   ※ プロジェクトに pyproject.toml/requirements.txt があればそちらを使ってください。最低限の依存例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   実運用では logging 設定や HTTP 周りのライブラリが追加される場合があります。

4. 環境変数 / .env を設定
   プロジェクトルートに `.env` または `.env.local` を作成します。自動ロードは既定で有効（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。主なキー:
   - JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
   - OPENAI_API_KEY (AI 機能を使う場合、または関数呼び出しで直接渡しても可)
   - KABU_API_PASSWORD (実取引で kabu API を使う場合)
   - KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB 用デフォルト: data/monitoring.db)
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用途)
   - KABUSYS_ENV (development / paper_trading / live)
   - LOG_LEVEL (DEBUG/INFO/...)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=eyJ...your_refresh_token...
   OPENAI_API_KEY=sk-...your_openai_key...
   DUCKDB_PATH=data/kabusys.duckdb
   ```

5. （任意）自動 .env ロードを無効化（テスト時）
   ```bash
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   ```

---

## 使い方

以下は主要な利用例（Python REPL またはスクリプト）です。DuckDB 接続は `duckdb.connect(path)` で取得します。

1. Settings を通じて設定値を取得
   ```python
   from kabusys.config import settings
   print(settings.duckdb_path)  # Path オブジェクト
   ```

2. 日次 ETL を実行（J-Quants トークンが必要）
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(settings.duckdb_path))
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

3. ニュース NLP スコア（AI）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect(str(settings.duckdb_path))
   # OPENAI_API_KEY が環境変数にあるか、api_key を渡す
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"wrote {written} scores")
   ```

4. 市場レジーム判定（AI）
   ```python
   from datetime import date
   import duckdb
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect(str(settings.duckdb_path))
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. ファクター計算 / リサーチ
   ```python
   from datetime import date
   import duckdb
   from kabusys.research import calc_momentum, calc_value, calc_volatility

   conn = duckdb.connect(str(settings.duckdb_path))
   d = date(2026, 3, 20)
   mom = calc_momentum(conn, d)
   val = calc_value(conn, d)
   vol = calc_volatility(conn, d)
   ```

6. 監査ログデータベース初期化（監査用 DB を別途作る場合）
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   # これで監査用テーブル群が作成されます
   ```

注意点
- AI モジュール（news_nlp, regime_detector）は OpenAI API を呼び出します。OPENAI_API_KEY を環境変数に設定するか、関数の api_key 引数で渡してください。
- J-Quants データ取得には JQUANTS_REFRESH_TOKEN が必須です。get_id_token は自動的にトークンをリフレッシュします。
- ETL・AI 処理は DB のスキーマ前提で動作します。必要に応じてスキーマ作成スクリプトを実行してください（本リポジトリに schema 初期化用の関数や DDL が含まれています）。

---

## ディレクトリ構成

（主要なファイル／モジュールの抜粋）

- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - ai/
    - __init__.py
    - news_nlp.py                     — ニュース NLP スコアリング（score_news）
    - regime_detector.py              — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py               — J-Quants API クライアント（fetch / save）
    - pipeline.py                     — ETL パイプライン（run_daily_etl など）
    - etl.py                          — ETLResult の再エクスポート
    - news_collector.py               — RSS 収集・前処理
    - calendar_management.py          — 市場カレンダー管理
    - quality.py                      — データ品質チェック
    - stats.py                        — zscore_normalize 等の統計ユーティリティ
    - audit.py                        — 監査ログテーブル定義 / 初期化
  - research/
    - __init__.py
    - factor_research.py              — calc_momentum / calc_value / calc_volatility
    - feature_exploration.py          — calc_forward_returns / calc_ic / factor_summary / rank
  - research/（その他のリサーチモジュール）
  - ai/（上記）
  - monitoring/, execution/, strategy/（発注・監視・戦略層の基盤ファイルはここに配置想定）

各モジュールは docstring に処理フロー・設計方針・フェイルセーフを明示しています。大規模処理は DuckDB 接続を外部から注入する設計で、テストがしやすくなっています。

---

## 追加メモ / 運用上の注意

- .env 自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在する場所）から `.env` / `.env.local` を自動読み込みします。
  - 優先順位: OS 環境変数 > .env.local > .env
  - テストや明示的に環境管理する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ログレベルと稼働モード:
  - KABUSYS_ENV = development | paper_trading | live により is_live/is_paper/is_dev が切り替わります。
  - LOG_LEVEL でログ出力レベルを制御します。
- セキュリティ:
  - news_collector は SSRF 対策、受信サイズ制限、defusedxml を使用した XML パースを実施しています。
  - jquants_client はレート制御とトークン自動リフレッシュ、リトライを実装しています。
- テスト:
  - AI 呼び出し等は内部関数をモックすることでテスト可能（コード内に patch 指示あり）。
  - DuckDB のインメモリ接続(":memory:") を用いて単体テストが可能です。

---

もし README に追加したいサンプルスクリプト、CI/デプロイ手順、スキーマ定義ファイル（CREATE TABLE）や pyproject の依存情報があれば、それに合わせて追記します。必要な出力例や運用チェックリストも作成できます。どの部分をより詳しく載せたいか教えてください。