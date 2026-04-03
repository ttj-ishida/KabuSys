# KabuSys

日本株向け自動売買 / データプラットフォーム用ライブラリ (KabuSys)

> 小要約：DuckDB を中心に据えた市場データ ETL、ニュースの NLP スコアリング、レジーム判定、監査ログ等のユーティリティ群を提供する Python パッケージです。J-Quants / OpenAI / kabuステーション 等と連携する想定のモジュール群が含まれます。

## 主要機能
- データ ETL（J-Quants からの株価・財務・市場カレンダー取得）
- データ品質チェック（欠損・重複・スパイク・日付整合性）
- ニュース収集（RSS）と前処理（SSRF 対策・トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄ごとのセンチメントスコア算出）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- DuckDB ベースの冪等保存 / バッチ処理 / トランザクション管理

## 動作環境（推奨）
- Python 3.10+
- 必要パッケージ（代表例）
  - duckdb
  - openai
  - defusedxml
  - （その他: 標準ライブラリのみで多くの処理を実装していますが、実行環境で必要な依存を適宜インストールしてください）

※パッケージ化された pyproject.toml / requirements.txt がある場合はそちらを参照してください。

## セットアップ手順

1. リポジトリをクローン / コピーして仮想環境を作成・有効化
   ```
   git clone <repo-url>
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 依存パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   ```

3. パッケージを開発モードでインストール（任意）
   ```
   pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートの `.env` / `.env.local` を用いる仕組みが自動で読み込まれます（ただし自動読み込みを無効にする環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定可能）。
   - 必須環境変数（一例）:
     - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD     : kabuステーション API のパスワード（発注連携等）
     - OPENAI_API_KEY        : OpenAI API キー（news_nlp / regime_detector 実行時に使用。関数引数で注入も可）
   - 任意・設定例:
     - KABUSYS_ENV (development | paper_trading | live) — 動作モード
     - LOG_LEVEL (DEBUG | INFO | ...)
     - DUCKDB_PATH / SQLITE_PATH / PID_FILE_PATH / など：デフォルトパスは config.Settings に定義

   例: `.env`
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   ```

## 使い方（主要なワークフロー）

以下は Python から直接利用する例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() が返す接続）を受け取ります。

1. DuckDB 接続の例
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL 実行（株価・財務・カレンダー取得と品質チェック）
   ```python
   from kabusys.data.pipeline import run_daily_etl

   # target_date を省略すると今日（settings により営業日に調整される）
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. ニュースのセンチメントスコア算出（前日15:00〜当日08:30 JST のウィンドウ）
   ```python
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   # target_date: スコア生成対象日（date オブジェクト）
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"scored {written} codes")
   ```

   - OpenAI API キーを明示的に渡すこともできます: score_news(conn, date(2026,3,20), api_key="sk-...")

4. 市場レジーム判定（ETF 1321 の MA とマクロニュースを合成）
   ```python
   from kabusys.ai.regime_detector import score_regime

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査ログ DB 初期化（監査専用 DB を作る）
   ```python
   from pathlib import Path
   from kabusys.data.audit import init_audit_db

   audit_db = init_audit_db(Path("data/audit.duckdb"))
   # audit_db は duckdb 接続
   ```

6. 研究用ファクター計算等
   ```python
   from kabusys.research.factor_research import calc_momentum
   from datetime import date

   momentum = calc_momentum(conn, date(2026, 3, 20))
   ```

## 設定（環境変数のポイント）
- 自動 .env ロード順序: OS 環境 > .env.local > .env
- 自動ロードを無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- 主要な環境変数（config.Settings で参照）
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - OPENAI_API_KEY（news / regime モジュールで必要）
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PID_FILE_PATH, KILL_FLAG_PATH（監視用）
  - KABUSYS_ENV (development | paper_trading | live)
  - LOG_LEVEL (DEBUG | INFO | ...)

## 注意点 / 設計上のポイント
- ルックアヘッドバイアス防止: 多くの関数は datetime.today() や date.today() を直接参照せず、明示的な target_date を受け取るか、DB の既存データに基づいて処理するよう設計されています。
- 冪等性: J-Quants から取得したデータは DuckDB に対して ON CONFLICT DO UPDATE 等で冪等保存されます。
- フェイルセーフ: OpenAI API 等の外部呼び出しが失敗した場合、多くの場所でスコアを中立値（0.0）にフォールバックする等、処理全体が停止しない設計です。
- セキュリティ: news_collector は SSRF 対策、defusedxml による XML パーサ保護、トラッキングパラメータ除去などを実装しています。
- トランザクション: 重要な書き込みは BEGIN / DELETE / INSERT / COMMIT のように冪等かつ原子性を意識して実行します。

## 主要モジュールの説明（簡易）

- kabusys.config
  - 環境変数と .env ファイルの読み込み、Settings クラスによる設定アクセス

- kabusys.data
  - jquants_client: J-Quants API ラッパ（取得・保存・レートリミット・リトライ）
  - pipeline: ETL の高レベル実行（run_daily_etl など）
  - quality: データ品質チェック
  - news_collector: RSS 収集と前処理
  - calendar_management: 市場カレンダーの判定や更新ジョブ
  - stats: zscore_normalize 等の共通統計ユーティリティ
  - audit: 監査ログスキーマの初期化ユーティリティ

- kabusys.ai
  - news_nlp: ニュースを LLM でスコアリングして ai_scores へ書き込む
  - regime_detector: ETF MA とマクロニュースを合わせて market_regime を生成

- kabusys.research
  - factor_research / feature_exploration: ファクター計算・IC 計算等の研究ツール

## ディレクトリ構成（主要ファイルのみ抜粋）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ quality.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ stats.py
│  └─ audit.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/（他研究ユーティリティ）
```

（全ソースは src/kabusys 以下に配置されています。上は主要モジュールの抜粋です。）

## 開発 / テストに関するヒント
- 自動 .env のロードを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（ユニットテストなどで利用）。
- OpenAI 呼び出しは内部でラップされています。ユニットテストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch / モックする設計です。
- DuckDB はインメモリ（":memory:"）でテスト可能です。監査 DB 初期化関数 init_audit_db は ":memory:" を受け取れます。

## 貢献・ライセンス
- プロジェクトの貢献フロー、コントリビュート規約、ライセンス情報はリポジトリのトップレベルにある CONTRIBUTING.md / LICENSE ファイル（存在する場合）を参照してください。

---

以上がこのコードベースの概要・セットアップ・基本的な使い方です。特定の機能のサンプルや CLI スクリプトの追加が必要であれば、どの操作（ETL、ニュース収集、監査初期化、シミュレーション等）を優先してドキュメント化するか教えてください。