# KabuSys

日本株向けのデータ基盤・研究・自動売買補助ライブラリ群です。  
J-Quants / RSS / OpenAI 等の外部ソースからデータを取得・整備し、ファクタ計算・ニュースNLP・市場レジーム判定・ETL処理・監査ログ管理などを提供します。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易サンプル）
- 環境変数一覧（主なもの）
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は日本株のデータ収集（J-Quants、RSS）、品質チェック、特徴量（ファクター）計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、ETL パイプライン、監査ログ（発注/約定のトレース）などを提供する Python モジュール群です。
- DuckDB を主なローカルデータベースとして使用し、ETL は冪等性や品質チェック、Look-ahead バイアス回避を意識して設計されています。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント評価やレジーム判定機能を備えています（APIキー必要）。

---

機能一覧（抜粋）
- data.jquants_client:
  - J-Quants API からの株価・財務・市場カレンダー取得（ページネーション、再試行、レート制御）
  - DuckDB への冪等保存（raw_prices / raw_financials / market_calendar 等）
- data.pipeline:
  - 日次 ETL の統合エントリ（run_daily_etl）と個別 ETL（run_prices_etl / run_financials_etl / run_calendar_etl）
  - ETL 実行結果を ETLResult で返却
- data.quality:
  - 欠損・スパイク・重複・日付不整合などの品質チェック（run_all_checks）
- data.calendar_management:
  - 営業日判定 / 前後営業日取得 / 期間内営業日列挙 / カレンダーバッチ更新ジョブ
- data.news_collector:
  - RSS 取得・前処理・raw_news への保存（SSRF 対策、URL 正規化、圧縮対策等）
- data.audit:
  - 発注／約定などの監査用テーブル定義・初期化（init_audit_schema / init_audit_db）
- ai.news_nlp:
  - raw_news + news_symbols を元に銘柄ごとのニュースセンチメントを OpenAI に投げて ai_scores に書込む（score_news）
- ai.regime_detector:
  - ETF 1321 の 200 日 MA 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を日次判定（score_regime）
- research:
  - ファクター計算（モメンタム / ボラティリティ / バリュー）、将来リターン計算、IC（情報係数）、統計サマリーなど
- 共通ユーティリティ:
  - 設定管理（kabusys.config: .env 自動ロード, Settings オブジェクト）
  - 統計関数（zscore 正規化 など）

---

セットアップ手順（開発 / 実行環境）
1. リポジトリをクローン
   - 例: git clone <repo_url>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 必要最低限の依存例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml

   （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数 / .env を用意
   - プロジェクトルートの .env または .env.local を使用できます（読み込み順: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 主な必須環境変数は README 下部の「環境変数一覧」を参照してください。

5. DuckDB データベースファイルの準備
   - デフォルトパスは data/kabusys.duckdb（settings.duckdb_path）
   - 監査ログ専用 DB を初期化する場合:
     - Python 上で: from kabusys.data.audit import init_audit_db; conn = init_audit_db("data/audit.duckdb")

---

使い方（簡易サンプル）
- 共通: Settings と DuckDB 接続
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する（例: 今日分）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース NLP スコア（OpenAI API キーが環境変数 OPENAI_API_KEY に設定されていること）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026,3,20))
  print(f"written: {written} codes")
  ```

- 市場レジーム判定（OpenAI API キーを引数で渡すことも可能）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import os

  api_key = os.environ.get("OPENAI_API_KEY")  # 省略可能（関数内で環境変数を参照）
  score_regime(conn, target_date=date(2026,3,20), api_key=api_key)
  ```

- 研究用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  date0 = date(2026,3,20)
  mom = calc_momentum(conn, date0)
  vol = calc_volatility(conn, date0)
  val = calc_value(conn, date0)
  ```

- 監査ログテーブルの初期化（監査用 DB を新規に作る）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/monitoring.db")
  ```

注意点（運用上）
- AI 呼び出し（news_nlp / regime_detector）は OpenAI API への課金・レート制限の対象です。APIキーは適切に管理してください。
- ETL は外部 API（J-Quants）に依存します。トークンやレートに注意してください。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）から行われます。テスト時などに自動ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

主な環境変数
- 必須
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（jquants_client.get_id_token 用）
  - SLACK_BOT_TOKEN: Slack 通知に使用する Bot token（プロジェクトの一部で必要）
  - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
  - KABU_API_PASSWORD: kabu API（kabuステーション）パスワード（発注等を行う場合）
- 任意 / デフォルトあり
  - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると自動 .env 読み込みを無効化
  - OPENAI_API_KEY: OpenAI API キー（ai モジュールで使用。score_* 関数に api_key 引数を渡すことも可能）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 sqlite パス（デフォルト data/monitoring.db）

例 (.env)
  ```
  JQUANTS_REFRESH_TOKEN=xxxx
  OPENAI_API_KEY=sk-...
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567
  DUCKDB_PATH=data/kabusys.duckdb
  KABUSYS_ENV=development
  LOG_LEVEL=INFO
  ```

---

ディレクトリ構成（主要ファイルと説明）
- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の自動読み込み、Settings クラス（各種設定値取得）
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースの NLP スコアリング（score_news）
    - regime_detector.py  — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得・保存関数）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETLResult 再エクスポート
    - quality.py          — データ品質チェック
    - stats.py            — 汎用統計（zscore_normalize 等）
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - news_collector.py   — RSS 収集・前処理
    - audit.py            — 監査ログスキーマ初期化（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — 将来リターン計算・IC・統計サマリー
  - monitoring/ (※コードベースによっては別ディレクトリ)
    - （監視・通知関連の実装が入る想定）
- README.md (本ファイル)
- .env, .env.local (任意)

---

開発・テスト向けの補足
- モジュール内に多くの外部 I/O（ネットワーク・ファイル・DB）呼び出しがあるため、ユニットテスト時は該当関数をモックする設計が想定されています（例: news_nlp._call_openai_api, news_collector._urlopen 等を patch）。
- 設計上、datetime.today() や date.today() を直接参照しないよう配慮された関数が多く（ルックアヘッドバイアス対策）、テスト時に date を指定可能です。

---

ライセンス / コントリビューション
- （本リポジトリのライセンス情報があればここに記載してください）

---

問題や質問
- 実行時に依存関係や環境変数で不明な点があれば、ソース内 docstring（各モジュール冒頭）を参照してください。必要であれば README を補足します。

以上。README の追加修正やサンプルの充実（Dockerfile / GitHub Actions ワークフロー例 / requirements.txt 追加）などご希望があれば教えてください。