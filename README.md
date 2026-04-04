# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL・ニュース収集・AIによるニュースセンチメント、ファクター計算、監査ログなど、バックテスト／運用に必要な主要機能をモジュール化して提供します。

---

## 主要な特徴（抜粋）

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、マーケットカレンダーを差分取得して DuckDB に保存（冪等）。
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行可能。
- ニュース収集 / NLP
  - RSS からニュースを収集して前処理し `raw_news` に保存。
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores）とマクロセンチメント（market_regime）判定。
  - API 呼び出しはリトライ・バッチ・JSON mode を用いた堅牢設計。
- リサーチ / ファクター
  - モメンタム / ボラティリティ / バリュー系ファクター計算（DuckDB クエリ＋Python）。
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Z スコア正規化。
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution までの監査テーブルを DuckDB に初期化・保存するユーティリティ。
- 運用ツール
  - プロセス監視用設定（PIDファイル、killフラグ等）、環境変数による挙動制御。
- 設計方針
  - ルックアヘッドバイアスを避ける設計（内部で date.today() / datetime.today() を無闇に参照しない等）。
  - 冪等性・フェイルセーフ（API失敗時のフォールバックなど）を重視。

---

## 依存パッケージ（代表）

- Python 3.10+
- duckdb
- openai (OpenAI の Python SDK)
- defusedxml
- （標準ライブラリ多数）

インストール時にプロジェクトの pyproject.toml / requirements.txt を参照して下さい。

---

## セットアップ手順（開発環境）

1. リポジトリをクローンしてプロジェクトルートへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成して有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストール
   - 例（pip）
     ```
     pip install -r requirements.txt
     ```
     または（編集可能インストール）
     ```
     pip install -e .
     ```

4. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動で読み込まれます（優先順位: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

5. 必須設定（例）
   - J-Quants 用トークン、OpenAI キー等を環境変数に設定します。例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_station_password
     ```

---

## 主要な環境変数（キーと既定値の例）

- JQUANTS_REFRESH_TOKEN ・・・（必須）J-Quants のリフレッシュトークン
- OPENAI_API_KEY ・・・ OpenAI API キー（AI モジュールで使用）
- KABU_API_PASSWORD ・・・ kabuステーション API パスワード
- KABU_API_BASE_URL ・・・ kabu API のベース URL（既定: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID ・・・（任意）LINE 通知用
- DUCKDB_PATH ・・・ DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH ・・・ 監視用 SQLite パス（既定: data/monitoring.db）
- PID_FILE_PATH / KILL_FLAG_PATH ・・・ 監視用フラグファイルのパス（既定あり）
- KILL_FLAG_CLEAR_ON_START ・・・ 1 にすると起動時に kill flag をクリア
- CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT ・・・ リソースしきい値
- KABUSYS_ENV ・・・ development / paper_trading / live（既定: development）
- LOG_LEVEL ・・・ DEBUG, INFO, WARNING, ERROR, CRITICAL（既定: INFO）

（`.env.example` を用意すると利用者にとってわかりやすくなります。）

---

## 使い方（簡単な利用例）

以下は最小限の利用例です。実行前に必要な環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続と日次 ETL 実行
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  # settings.duckdb_path は環境変数 DUCKDB_PATH の既定を考慮して Path を返します
  conn = duckdb.connect(str(settings.duckdb_path))

  # ETL を今日に対して実行
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）をスコアリング
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY を環境変数で設定していれば api_key 引数は不要
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

- マクロレジーム判定（market_regime）を計算
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ作成されます
  ```

注意点:
- AI 関連関数は OPENAI_API_KEY を参照します。引数で明示的に api_key を渡すことも可能です。
- 各関数は Look-ahead バイアス回避のため target_date パラメータを受け取り、内部で未来データを参照しない設計になっています。
- OpenAI 呼び出しや外部 API に対してはリトライ・フォールバックを備えていますが、API キーやレート制限に留意してください。

---

## ディレクトリ構成（抜粋）

リポジトリの主要ディレクトリと代表ファイル:

- src/kabusys/
  - __init__.py (パッケージ定義、バージョン)
  - config.py (環境変数 / 設定管理、自動 .env ロード)
  - ai/
    - __init__.py
    - news_nlp.py (ニュースセンチメント算出)
    - regime_detector.py (マクロ + ETF MA を合成した市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント、取得 + 保存ユーティリティ)
    - pipeline.py (ETL パイプライン: run_daily_etl 等)
    - etl.py (ETL 型の再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー / 営業日判定)
    - stats.py (zscore 正規化等)
    - quality.py (データ品質チェック)
    - audit.py (監査ログテーブルの初期化)
  - research/
    - __init__.py
    - factor_research.py (モメンタム / ボラティリティ / バリュー等)
    - feature_exploration.py (将来リターン・IC・統計サマリ)
  - ai/ (上記)
  - research/ (上記)
- pyproject.toml / requirements.txt 等（プロジェクトルート）

（実際のリポジトリにはさらに多くのファイル・テスト等が含まれる可能性があります。）

---

## 実運用上の注意・設計コメント

- 環境変数の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テストや CI で無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- J-Quants API 呼び出しはモジュール内で RateLimiter を用いてレート制御しています。大量の並列呼び出しは避けてください。
- AI 呼び出し（OpenAI）は JSON Mode を使い厳密な JSON を期待して処理していますが、万が一パースが失敗した場合はフォールバック（0.0 等）する設計です。モデルの挙動変化に注意してください。
- ETL / DB 操作は DuckDB を用いており、INSERT は冪等（ON CONFLICT DO UPDATE）で行います。DuckDB バージョンによる挙動差に注意して下さい（executemany の空リスト等の取り扱いがあるためコードで対処済み）。

---

## サポート / 貢献

- バグ報告や機能提案は Issue を立ててください。
- コードスタイルやテストはプロジェクトのガイドラインに従ってプルリクエストをお願いします。

---

この README はコードベースの概要と主要な利用方法を示すものです。詳細な API 使用法やスキーマ定義、運用手順は個別のドキュメント（DataPlatform.md / StrategyModel.md 等）を参照してください。