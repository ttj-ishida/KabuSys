# KabuSys

日本株向けの自動売買・データ基盤ライブラリ（KabuSys）。  
ETL（J-Quants からの市場データ取得）・ニュース収集・AI（ニュースセンチメント / 市場レジーム判定）・ファクター計算・データ品質チェック・監査ログ等のユーティリティを提供します。

---

## 概要

KabuSys は、J-Quants API を中心とした日本株データプラットフォームと、AI を活用したニュースセンチメント評価・市場レジーム判定、リサーチ用ファクター計算や品質チェック、監査ログ機能を備えたパッケージです。  
設計上のポイント：

- DuckDB をデータ層として採用（高速なローカル分析向け）
- J-Quants API の差分取得・レート制御・自動リフレッシュ対応
- OpenAI（gpt-4o-mini 等）を用いたニュース NLP（JSON Mode）／レジーム判定（フェイルセーフ、リトライ付き）
- Look-ahead bias を避ける設計（target_date を明示、内部で datetime.today() を参照しない）
- 冪等性を重視した DB 保存（ON CONFLICT / DELETE→INSERT パターン）
- データ品質チェック・監査ログ（シグナル→オーダー→約定のトレーサビリティ）

---

## 主な機能一覧

- データ取得・ETL
  - J-Quants からの株価（日足）、財務、上場銘柄情報、マーケットカレンダーの差分取得（ページネーション・レート制御・リトライ）
  - ETL の実行（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
- ニュース関連
  - RSS からのニュース収集（トラッキングパラメータ除去・SSRF 対策・XML セーフパース）
  - ニュースの AI センチメントスコアリング（score_news）
- AI（市場レジーム）
  - ETF（1321）200日 MA 乖離とマクロニュースセンチメントを合成した日次レジーム判定（score_regime）
- リサーチ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- データ品質チェック
  - 欠損値、重複、スパイク、非営業日／未来日付の検出
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル初期化・管理
- 設定管理
  - .env / .env.local / OS 環境変数からの自動読み込み（パッケージ起点でのプロジェクトルート探索）

---

## セットアップ手順（クイックスタート）

前提：Python 3.10 以上 を推奨（typing | 複合代入注釈などを利用しているため）

1. ソースコードをクローン / 取得し、パッケージをインストール（開発モード）
   ```bash
   git clone <repo-url>
   cd <repo-root>
   python -m pip install -e ".[dev]"  # setup.cfg/pyproject がある場合
   ```
   ※ リポジトリに pyproject.toml / setup がある前提。無い場合は必要最小限の依存を直接インストールしてください。

2. 必要な依存パッケージ（代表例）
   ```bash
   python -m pip install duckdb openai defusedxml
   ```
   実際のプロジェクトでは requirements.txt / pyproject の依存を参照してください。

3. 環境変数の設定
   プロジェクトルートに `.env`（と必要なら `.env.local`）を作り、必要な値を設定します。自動ロード順は OS 環境 > .env.local > .env です。自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   主要な環境変数（例）：
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 等で必要）
   - KABU_API_PASSWORD: kabu ステーション API パスワード（必要時）
   - KABU_API_BASE_URL: kabu API base URL（デフォルト: http://localhost:18080/kabusapi）
   - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 通知用（任意）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: development / paper_trading / live
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL

4. データディレクトリの作成（必要なら）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主な例）

以下はライブラリを Python から利用する最小例です。DuckDB 接続は文字列パス（settings.duckdb_path）を使うと便利です。

- 基本初期化と ETL 実行（日次 ETL）
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  # target_date を省略すると今日を基準に実行します（内部で trading_day に調整あり）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # API キーを引数で渡すか、OPENAI_API_KEY 環境変数を設定してください
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print("書き込んだ銘柄数:", written)
  ```

- 市場レジーム判定（score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))  # OPENAI_API_KEY を環境変数でセット
  ```

- 監査ログ DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等のテーブルが作成されます
  ```

- ファクター計算・リサーチ例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  date0 = date(2026, 3, 20)
  momentum = calc_momentum(conn, date0)
  value = calc_value(conn, date0)
  volatility = calc_volatility(conn, date0)
  ```

注意点：
- OpenAI 呼び出し時は API のエラーに備えてフェイルセーフ（失敗時は 0.0 等にフォールバック）やリトライが組まれていますが、必ず API キーを環境変数に設定するか関数引数で渡してください。
- ETL・AI 関数は target_date を明示することでルックアヘッドバイアスを避ける設計です。バッチ処理やバックテストでは target_date を適切に指定してください。

---

## 環境変数（主な一覧と説明）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必要）
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH — 実行監視用ファイルパス
- KILL_FLAG_CLEAR_ON_START — 起動時にキルフラグをクリアするか（"1" で有効）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値
- KABUSYS_ENV — 実行環境: development / paper_trading / live
- LOG_LEVEL — ログレベル: DEBUG/INFO/...

自動 .env 読み込み：
- パッケージはプロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を自動で読み込みます。
- 読み込み順: OS 環境変数 > .env.local > .env
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主なファイル）

以下は src/kabusys 以下の主なモジュール構成です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                  — 環境変数・設定読み込みロジック
  - ai/
    - __init__.py
    - news_nlp.py              — ニュースセンチメント（score_news）
    - regime_detector.py       — 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - jquants_client.py        — J-Quants API クライアント（fetch / save）
    - pipeline.py              — ETL パイプライン（run_daily_etl など）
    - etl.py                   — ETL ユーティリティ公開（ETLResult）
    - stats.py                 — 統計ユーティリティ（zscore_normalize）
    - quality.py               — データ品質チェック
    - news_collector.py        — RSS ニュース収集
    - calendar_management.py   — マーケットカレンダー、営業日ロジック
    - audit.py                 — 監査ログテーブル初期化
  - research/
    - __init__.py
    - factor_research.py       — モメンタム / バリュー / ボラティリティ等
    - feature_exploration.py   — 将来リターン / IC / 統計サマリー
  - research/... (その他の研究系ユーティリティ)

（上記は抜粋です。実際のリポジトリでは他ファイルも含まれます）

---

## 設計上の注意・ベストプラクティス

- API キー／トークンは基本的に環境変数で管理し、.env はローカル開発用に用いること（.env は機密情報を含むため VCS 管理対象外にしてください）。
- AI モジュールは外部 API 呼び出しに依存するため、テスト時は該当関数をモックしてください（コード中にモックしやすい内部呼び出しが設計されています）。
- DuckDB のスキーマやテーブルは ETL 前に準備しておく必要があります（schema 初期化用ユーティリティが別途ある想定）。
- ルックアヘッドバイアス対策として関数群は target_date を明示する設計です。バックテスト用には target_date を正しく固定して使用してください。

---

## トラブルシューティング

- J-Quants の 401（Unauthorized）が発生する場合：
  - settings.jquants_refresh_token が正しいか確認。jquants_client は 401 を検出すると自動でリフレッシュを試みます。
- OpenAI の呼び出しが失敗しても関数は例外を投げずに安全側の値（0.0 等）で継続する箇所があります。ログ（LOG_LEVEL=DEBUG/INFO）で詳細を確認してください。
- DuckDB の executemany に空リストを渡すと失敗するバージョン依存の挙動を回避するため、コード中でも空リストチェックを行っていますが、念のため使用中の duckdb バージョンが推奨バージョンか確認してください。

---

以上が KabuSys の README（概要・セットアップ・使い方・構成）です。実際の運用や拡張に際しては、各モジュールのドキュメンテーション（関数 docstring）を参照してください。必要であれば README に以下を追加できます：詳細な .env.example、スキーマ初期化手順、systemd / supervisor 用の実行例、テストの手順など。どのドキュメントを追加希望か教えてください。