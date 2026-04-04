# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。  
ETL（J-Quantsからの株価・財務・カレンダー取得）、ニュース収集・AIによるニュースセンチメント、リサーチ用ファクター計算、監査ログ（オーダー/約定追跡）などを提供します。

主な設計思想：
- DuckDB をデータ層に利用しローカルで高速に集計可能
- API 呼び出しはリトライ・レート制御・フェイルセーフ実装
- ルックアヘッドバイアス（バックテスト用不整合）対策を重視
- 冪等性（ON CONFLICT / idempotent）を意識した ETL / 保存処理

---

## 機能一覧

- データ取得・ETL
  - J-Quants からの株価日足、財務データ、JPX マーケットカレンダー取得（jquants_client）
  - 差分取得／バックフィル対応の日次 ETL（data.pipeline.run_daily_etl）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）

- ニュース収集・NLP
  - RSS からニュース収集（news_collector）
  - OpenAI を用いたニュースセンチメント（gpt-4o-mini）で銘柄毎の ai_score 生成（ai.news_nlp.score_news）
  - マクロニュースと ETF 移動平均を合成した市場レジーム判定（ai.regime_detector.score_regime）

- リサーチ・ファクター
  - Momentum / Volatility / Value 等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー等（research.feature_exploration）
  - Zスコア正規化ユーティリティ（data.stats.zscore_normalize）

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化（data.audit）
  - 監査用 DuckDB データベース初期化ユーティリティ

- 設定管理
  - .env / 環境変数から設定を自動ロード（config）
  - 自動ロード無効化や .env.local を上書き読み込みする仕組み

---

## セットアップ手順

前提：Python 3.10+（typing の Union 表記などを想定）、ネットワークアクセス（J-Quants / OpenAI 等）

1. リポジトリをクローン（既にコードが手元にある場合は不要）
   git clone <your-repo-url>

2. 仮想環境作成・有効化（任意）
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows

3. 必要パッケージのインストール
   pip install -e .              # パッケージとしてインストール（setup がある場合）
   pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を推奨）

4. 環境変数 / .env を用意する  
   プロジェクトルート（pyproject.toml または .git がある場所）に `.env` を置くと自動で読み込まれます。
   自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   主な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で未指定時に使用）
   - KABU_API_PASSWORD: kabuステーション API パスワード（実行/発注機能を使う場合）
   - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知を使う場合
   - DUCKDB_PATH: DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
   - PID_FILE_PATH / KILL_FLAG_PATH: 実行監視用ファイルパス
   - KABUSYS_ENV: 実行環境（development / paper_trading / live）
   - LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）

   サンプル .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（代表的な例）

以下は簡単な利用例です。すべての関数は DuckDB 接続を受け取る実装になっているため、まず接続を作ります。

- DuckDB 接続準備例
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())

- ニュースセンチメント（銘柄別 ai_score）を生成する
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))  # OpenAI キーは env または api_key 引数指定

- 市場レジームを判定して DB に書き込む
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- ファクター（モメンタム等）を計算する
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

- 監査ログ用 DB を初期化する
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db(settings.duckdb_path)  # ":memory:" も可

- テスト／モックのヒント
  - OpenAI 呼び出しは関数単位で抽象化されているため unittest.mock.patch で差し替え可能（例: kabusys.ai.news_nlp._call_openai_api）。
  - 自動 .env 読込を無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主なファイルと簡単な説明）

src/kabusys/
- __init__.py — パッケージ定義、バージョン
- config.py — 環境変数/.env の自動読み込みと Settings クラス

src/kabusys/ai/
- __init__.py
- news_nlp.py — ニュースを銘柄別に集約して OpenAI でスコア化、ai_scores へ保存
- regime_detector.py — ETF（1321）MA とマクロニュースを合成して市場レジーム判定

src/kabusys/data/
- __init__.py
- jquants_client.py — J-Quants API クライアント（認証・レート制御・保存関数）
- pipeline.py — ETL パイプラインと run_daily_etl の実装、ETLResult
- etl.py — ETLResult の公開エクスポート
- news_collector.py — RSS 取得・記事正規化・raw_news への保存
- calendar_management.py — 市場カレンダー（is_trading_day 等）と calendar_update_job
- stats.py — zscore_normalize 等の統計ユーティリティ
- quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
- audit.py — 監査ログ（テーブル DDL / init_audit_schema / init_audit_db）

src/kabusys/research/
- __init__.py
- factor_research.py — Momentum/Value/Volatility などのファクター計算
- feature_exploration.py — 将来リターン計算、IC、統計サマリー等

その他:
- data/ (デフォルトのデータ格納先; settings.duckdb_path が指す先に DB ファイルが作成されます)
- .env / .env.local — 環境変数ファイル（プロジェクトルートに置く）

---

## 運用上の注意

- 機密情報（API キー等）は .env/local に置き、リポジトリにコミットしないでください。
- OpenAI の呼び出しは課金対象です。バッチ実行前に料金・トークン使用量に注意してください。
- J-Quants API はレート制限があるため jquants_client の RateLimiter に従ってください。
- 本コードベースは実戦運用（特に発注・約定）を行う際は十分なテストと安全対策（注文二重防止、ポジション制御、監視）を行ってください。
- KABUSYS_ENV を `live` にすると本番挙動（発注等）を想定した動作・チェックが有効になる箇所があります。まずは `development` / `paper_trading` で検証してください。

---

必要があれば README に以下を追加できます：
- 具体的な SQL スキーマ（テーブル一覧）
- さらに詳しい運用手順（cron / systemd ユニット例）
- テスト実行方法（pytest 等）
- 依存パッケージの pinned requirements.txt

追加で盛り込みたい情報があれば教えてください。