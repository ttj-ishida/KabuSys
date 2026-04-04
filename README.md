# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群。ETL、ニュース収集・NLP、ファクター計算、監査ログなどを含むモジュール群で、J-Quants / kabuステーション / OpenAI と連携することを想定しています。

主な目的:
- J-Quants からのデータ取得と DuckDB への差分保存（ETL）
- RSS ニュース収集と LLM によるニュースセンチメント評価
- 日次ファクター計算やリサーチ用ユーティリティ
- 注文フローの監査ログスキーマ初期化

---

## 主な機能一覧

- 環境変数管理（.env 自動ロード、必須設定チェック）
- J-Quants API クライアント（株価・財務・マーケットカレンダー取得、保存）
- ETL パイプライン（日次 ETL の実行、品質チェック）
- ニュース収集モジュール（RSS 取得・前処理・raw_news 保存）
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価、ai_scores 書き込み）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを統合）
- リサーチ用ファクター計算（モメンタム / バリュー / ボラティリティ 等）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal / order_request / executions のテーブル定義・初期化）
- ユーティリティ（Zスコア正規化、カレンダー操作、DuckDB ヘルパー等）

---

## 動作要件（目安）

- Python 3.10+
- ライブラリ（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリのみで実装されている部分も多数あります）

開発環境によって追加パッケージが必要な場合があります。requirements.txt がある場合はそちらを使用してください。

---

## セットアップ手順

1. リポジトリをクローンする
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（最低限の例）
   ```
   pip install duckdb openai defusedxml
   ```

   プロジェクトに requirements.txt / pyproject.toml がある場合はそれらを使ってください。開発インストールは次のように行えます（パッケージ化されている場合）:
   ```
   pip install -e .
   ```

4. 環境変数を準備する
   - プロジェクトルートに `.env` または `.env.local` を作成してください。
   - パッケージは起動時に自動でプロジェクトルートの `.env` → `.env.local` をロードします（OS 環境変数が優先されます）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します（テスト時に便利）。

5. 主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須、発注系で使用）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
   - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知（任意）
   - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU/Memory/Disk 閾値 など（監視系）

   .env の例（抜粋）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（基本的な利用例）

以下は Python インタプリタやスクリプトからのサンプル呼び出し例です。

- DuckDB 接続を作る（設定からパスを取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュースのセンチメントをスコアリングして ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム（bull/neutral/bear）を判定して market_regime に書き込む
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

  OpenAI API キーを引数で渡すこともできます（デフォルトは環境変数 OPENAI_API_KEY を使用）。

- 監査ログスキーマを初期化する（別 DB に監査ログを作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- RSS フィードを取得する（ニュースコレクタ単体）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  ```

各関数の詳細な挙動や引数については、ライブラリ内の docstring を参照してください。多くの関数は Look-ahead bias を避けるために内部で date を明示的に扱っており、datetime.today() 等に依存しない設計です。

---

## よくある操作 / ヒント

- 自動 .env 読み込み:
  - 起動時にプロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` → `.env.local` が読み込まれます。
  - テストで自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

- OpenAI 呼び出し:
  - ニュース NLP / レジーム検出は GPT 系モデル（gpt-4o-mini 等）を使用する想定で JSON モードを利用します。
  - API エラーやレートリミットに対するリトライやフェイルセーフ（デフォルトスコア 0 で継続）を組み込んでいます。

- J-Quants API:
  - トークンは自動リフレッシュ対応、取得・キャッシュ処理とページネーション対応が実装されています。
  - レート制御（120 req/min）を守るための固定間隔スロットリングを実装しています。

- DuckDB のバージョン差分:
  - DuckDB の executemany の挙動や配列バインドに差異があるため、コード内では互換性を考慮した実装がされています。

---

## ディレクトリ構成（主要ファイル）

以下は主要なモジュールと説明です（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py             — ニュース NLP（銘柄別スコア付与）
    - regime_detector.py      — マーケットレジーム判定
  - data/
    - __init__.py
    - jquants_client.py       — J-Quants API クライアント（fetch / save）
    - pipeline.py             — ETL パイプライン（run_daily_etl 他）
    - calendar_management.py  — マーケットカレンダー管理
    - news_collector.py       — RSS ニュース収集
    - quality.py              — データ品質チェック
    - stats.py                — 統計ユーティリティ（z-score 等）
    - audit.py                — 監査ログスキーマ初期化
    - etl.py                  — ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py      — ファクター計算（momentum / value / volatility）
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等
  - research、execution、strategy、monitoring 等（パッケージ境界で公開されるモジュール群）

（実際のリポジトリには tests/ や scripts/、docs/ が存在する場合があります。）

---

## 開発・テスト上の注意

- 多くの関数は外部 API（J-Quants, OpenAI）とやり取りするため、ユニットテストでは API 呼び出し部分をモックすることを推奨します。コード内でもテスト置換を想定した設計（モジュール内呼び出しを差し替え可能）になっています。
- 自動 .env 読み込みでテストに影響が出る場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- DuckDB に対する一部処理はバージョン依存の回避コードを含むため、DuckDB のバージョンアップ時は挙動確認を行ってください。

---

## ライセンス・貢献

リポジトリの LICENSE を参照してください。バグ報告・機能要望・プルリクエストは issue/PR で歓迎します。

---

README は概要と典型的な利用パターンをまとめたものです。細かな API 仕様や追加の実行スクリプトが含まれている場合は、そのドキュメント（docs/ やモジュール docstring）を参照してください。必要であれば README の補足（実行スクリプト、デプロイ方法、運用手順など）を追加で作成します。