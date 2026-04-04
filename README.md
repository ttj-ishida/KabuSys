# KabuSys

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。  
データ収集（J-Quants）、データ品質チェック、ETL、ニュース収集、LLM によるニュースセンチメント、ファクター計算、監査ログ（トレーサビリティ）、マーケットカレンダーなど、バックテスト・研究・運用に必要な基盤機能を提供します。

---

## 主な機能（Overview / Features）

- 環境変数ベースの設定読み込み（.env / .env.local、自動ロード）
- J-Quants API クライアント
  - 株価日足（OHLCV）、財務データ、上場銘柄情報、JPX カレンダー取得
  - レートリミット制御・リトライ・トークン自動リフレッシュ対応
- ETL パイプライン
  - 差分取得 / バックフィル / 品質チェック（欠損・重複・スパイク・日付整合性）
  - DuckDB へ冪等保存（ON CONFLICT）
- ニュース収集（RSS）
  - URL 正規化・SSRF 対策・XML セーフパーサ（defusedxml）・前処理
  - raw_news / news_symbols テーブルへの冪等保存
- ニュース NLP（OpenAI）
  - 銘柄別ニュースセンチメントの生成（gpt-4o-mini を想定）
  - チャンク／バッチ処理、リトライ、レスポンス検証、スコアクリップ
- 市場レジーム判定
  - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュースセンチメント（30%）を合成して `bull` / `neutral` / `bear` を判定
- 研究用モジュール
  - モメンタム、バリュー、ボラティリティなどのファクター計算
  - 将来リターン、IC（情報係数）、統計サマリー、Zスコア正規化ユーティリティ
- マーケットカレンダー管理
  - JPX カレンダーを取り込み、営業日判定 / next/prev_trading_day / get_trading_days 等を提供
- 監査ログ（Audit）
  - signal → order_request → execution まで UUID を使って完全トレース可能なスキーマ生成・初期化
- データ品質チェックモジュール
  - ETL 後の品質検査を統合的に実行

---

## 必要条件 / 依存ライブラリ

- Python 3.9+（型ヒント表記を利用）
- 必須パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

具体的なバージョンはプロジェクト側で requirements.txt / pyproject.toml を参照してください。

---

## セットアップ手順（Setup）

1. リポジトリをクローン、作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - もし `pyproject.toml` / `requirements.txt` があればそれを使用してください。例:
     ```
     pip install -r requirements.txt
     ```
   - あるいは最低限:
     ```
     pip install duckdb openai defusedxml
     ```

4. 開発インストール（パッケージ化されている場合）
   ```
   pip install -e .
   ```

5. 環境変数 / .env の準備
   - プロジェクトルートに `.env` として必要な環境変数を配置すると、自動で読み込まれます（優先度: OS 環境変数 > .env.local > .env）。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   例（.env）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 設定項目（主な環境変数）

- JQUANTS_REFRESH_TOKEN — J-Quants の refresh token（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須 for execution）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START — 実行監視設定
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — environment: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL

設定モジュールは `kabusys.config.settings` 経由でアクセスできます。

---

## 使い方（Usage）

以下は代表的な利用例です。各関数は DuckDB 接続（duckdb.connect(...) が返す接続オブジェクト）を受け取ります。

- DuckDB に接続する例:
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（市場カレンダー／株価／財務／品質チェックを一括実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄単位）を計算して ai_scores に保存
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY は環境変数または引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored: {count} codes")
  ```

- 市場レジーム判定（ma200 + マクロニュース）を実行
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化（専用 DuckDB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成される
  ```

- カレンダー更新バッチを手動で実行
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  from datetime import date

  saved = calendar_update_job(conn)
  print(f"calendar saved: {saved}")
  ```

注意:
- AI 関連関数（news_nlp.score_news, regime_detector.score_regime）は OpenAI API キーが必要です。引数で明示的に渡すこともできます。
- ETL / 保存系は DuckDB のスキーマ依存です。事前にスキーマ初期化（スクリプトや migration）が必要になります（本 README ではスキーマ作成手順は別途用意されている想定です）。

---

## 開発・デバッグのヒント

- .env の自動読み込みはパッケージ初期化時に行われます。テスト時にこれを無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部でリトライや JSON 検証を行いますが、ユニットテストでは `_call_openai_api` をモックして外部依存を切り離す設計です（kabusys.ai.news_nlp._call_openai_api 等）。
- J-Quants API 呼び出しは内部でレートリミット・リトライを行います。大量ページネーション時は id_token のキャッシュが使われます。

---

## ディレクトリ構成（Directory structure）

プロジェクトの重要ファイル / モジュールの構成（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理（.env 自動ロード含む）
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュースセンチメント（銘柄別 ai_scores 生成）
    - regime_detector.py           — 市場レジーム判定（ma200 + マクロ）
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント & DuckDB 保存
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL の公開インターフェース（ETLResult 再エクスポート）
    - stats.py                     — 汎用統計ユーティリティ（Zスコア等）
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS ニュース収集（SSRF 対策・正規化）
    - calendar_management.py       — マーケットカレンダー管理 / 営業日ロジック
    - audit.py                     — 監査ログスキーマ初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算（momentum / value / volatility）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー
  - ai/                           — AI 関連
  - research/                     — 研究用ユーティリティ群
  - monitoring/                   — 監視・プロセスマネジメント（実装ファイル想定）
  - execution/                    — 発注周り（kabu API 連携等、実装ファイル想定）
  - strategy/                     — 戦略ロジック（実装ファイル想定）
- pyproject.toml / setup.cfg / requirements.txt（プロジェクトルートに存在する想定）
- .env / .env.local               — 環境変数（プロジェクトルートに配置）

---

## 最後に / 注意点

- 本ライブラリには実際の発注（ブローカー API）を行うモジュールを含む想定です。live 環境での実行時は十分な安全策（テスト、dry-run、ポジション制限、監査ログ）を行ってください。
- データの「ルックアヘッドバイアス」回避に注意した設計（target_date 未満のデータのみを参照する等）がなされています。バックテストや研究ではこの挙動を尊重して使用してください。
- OpenAI / J-Quants の利用は各サービスの利用規約・料金体系に従ってください。

必要であれば、README にインストール済みパッケージの具体的なバージョン情報、スキーマ初期化スクリプト、サンプル .env.example を追記します。どの情報を優先的に追加しますか？