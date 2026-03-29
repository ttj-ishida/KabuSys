# KabuSys

日本株向けの自動売買 / データプラットフォーム用 Python ライブラリ。  
ETL、ニュース収集・NLP、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）、J-Quants クライアント等を含むモジュール群を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株のデータ取得・品質管理・特徴量生成・AI（LLM）によるニュースセンチメント評価・市場レジーム判定・監査ログ管理までを一貫して実行できる内部ライブラリです。  
主な設計方針は次の通りです:

- ルックアヘッドバイアスを避ける：内部処理で `datetime.today()` 等で自動的に現在時刻を参照しない設計（呼び出し側が対象日を明示）。
- ETL と品質チェックを分離し、部分失敗でも他処理は継続する耐障害性。
- DuckDB をデータストアとして利用し、冪等保存（ON CONFLICT）を重視。
- OpenAI（gpt-4o-mini 等）を用いたニュース評価は JSON mode を使い、レスポンス検証とリトライを実装。
- ネットワーク周りや RSS 取得では SSRF / XML Bomb / 大容量レスポンス対策を実装。

---

## 機能一覧

- config: 環境変数 / .env 自動読み込み（プロジェクトルート検知）、必須項目チェック
- data:
  - jquants_client: J-Quants API との通信（株価・財務・マーケットカレンダー取得）、DuckDB への保存関数
  - pipeline: 日次 ETL（差分取得、保存、品質チェック）の統合
  - news_collector: RSS 取得・正規化・raw_news への保存（SSRF・XML 対策）
  - calendar_management: JPX カレンダー管理と営業日判定ユーティリティ
  - quality: データ品質チェック（欠損・重複・スパイク・日付不整合）
  - audit: 監査ログスキーマの初期化（signal/events/order_requests/executions）
  - stats: 汎用統計ユーティリティ（Zスコア正規化等）
- ai:
  - news_nlp.score_news: ニュース記事を銘柄ごとに LLM で評価して ai_scores テーブルに書き込む
  - regime_detector.score_regime: ETF (1321) の MA とマクロニュースセンチメントを合成して market_regime を算出・保存
- research:
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、統計サマリー

---

## セットアップ手順

1. Python 仮想環境の作成（推奨）
   - python >= 3.10 を想定
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（例）
   - pip install duckdb openai defusedxml
   - 必要に応じて HTTP/SSL 周りやテスト用ライブラリを追加

   （プロジェクトに requirements ファイルがあればそちらを利用してください）

3. プロジェクトの配置
   - 本 README は src/kabusys 配下のパッケージ構成を想定しています。
   - 開発用に editable インストール:
     - pip install -e .

4. 環境変数 / .env
   - プロジェクトルート（.git か pyproject.toml があるディレクトリ）に `.env` または `.env.local` を配置すると、自動で読み込まれます（ただしテスト時などは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可）。

   必須の環境変数（一部）:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD: kabuステーション API パスワード（本モジュールで使用）
   - SLACK_BOT_TOKEN: Slack 通知用トークン（必要な箇所のみ）
   - SLACK_CHANNEL_ID: Slack 送信先チャンネル ID
   - OPENAI_API_KEY: OpenAI 呼び出しで利用（ai モジュール内関数は引数 api_key を渡さない場合これを参照）

   例 `.env`（テンプレート）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（主要な呼び出し例）

以下は Python REPL やスクリプトからの利用例です。すべての呼び出しは DuckDB 接続を渡して行います。

1. DuckDB 接続を作る（ファイル DB）
   ```python
   import duckdb
   from kabusys.config import settings

   conn = duckdb.connect(str(settings.duckdb_path))
   ```

2. 日次 ETL を実行する
   ```python
   from kabusys.data.pipeline import run_daily_etl

   # target_date を指定しない場合は today が使われます（ETL 内で営業日に調整）
   result = run_daily_etl(conn)
   print(result.to_dict())
   ```

3. ニュースセンチメントを生成して ai_scores に書き込む
   - OpenAI API キーを環境変数 `OPENAI_API_KEY` に設定しておくか、関数に渡す
   ```python
   from kabusys.ai.news_nlp import score_news
   from datetime import date

   written = score_news(conn, target_date=date(2026, 3, 20))
   print("written:", written)
   ```

4. 市場レジーム判定（regime score）を計算して market_regime に保存
   ```python
   from kabusys.ai.regime_detector import score_regime
   from datetime import date

   score_regime(conn, target_date=date(2026, 3, 20))
   ```

5. 監査ログ DB の初期化（監査用別 DB）
   ```python
   from kabusys.data.audit import init_audit_db

   audit_conn = init_audit_db("data/audit.duckdb")
   # audit_conn を使って監査テーブルに書き込み可能
   ```

6. ファクター計算・研究用ユーティリティ
   ```python
   from kabusys.research.factor_research import calc_momentum, calc_value
   from datetime import date

   momentum = calc_momentum(conn, date(2026, 3, 20))
   value = calc_value(conn, date(2026, 3, 20))
   ```

注意点:
- ai モジュール（news_nlp, regime_detector）は OpenAI API を呼び出すため API キーを設定してください。関数引数 `api_key` に直接キーを渡すこともできます（テストでの差し替えに便利）。
- 多くの関数は「対象日（target_date）」を明示的に受け取り、内部で現在日時を参照しない設計です（バックテスト時の Look-ahead バイアス回避）。

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール用）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development / paper_trading / live（デフォルト development）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

自動 .env ロードはプロジェクトルート（.git または pyproject.toml）から `.env` / `.env.local` を読み込みます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

---

## ディレクトリ構成

以下は src/kabusys 配下の主要ファイル・モジュールの概要です（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                : 環境変数 / .env 読み込み・設定クラス
    - ai/
      - __init__.py
      - news_nlp.py           : ニュースの LLM によるスコアリング（score_news）
      - regime_detector.py    : 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py     : J-Quants API クライアント（fetch / save 系）
      - pipeline.py           : ETL パイプライン（run_daily_etl 等）
      - news_collector.py     : RSS 収集・前処理
      - calendar_management.py: 市場カレンダー管理・営業日判定
      - quality.py            : データ品質チェック
      - stats.py              : 統計ユーティリティ（zscore_normalize）
      - audit.py              : 監査ログスキーマ初期化
      - etl.py                : ETLResult エクスポート
    - research/
      - __init__.py
      - factor_research.py    : ファクター計算（momentum / volatility / value）
      - feature_exploration.py: 将来リターン / IC / 統計サマリー
    - (その他)                 : strategy / execution / monitoring を想定するトップレベルパッケージ構成

各モジュールは docstring に処理フローと設計方針が詳細に記載されています。まずは `kabusys.data.pipeline` と `kabusys.data.jquants_client`、`kabusys.ai.news_nlp` を触ることで全体のデータフローを理解できます。

---

## 開発・テストに関する注意

- 自動 .env ロードはプロジェクトルート検出に基づくため、テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存を切ることを推奨します。
- OpenAI 呼び出し部分は `_call_openai_api` をモックしやすい設計になっています（ユニットテストで差し替え可能）。
- ネットワーク依存の部分（J-Quants / RSS / OpenAI）はエラー時のフェイルセーフ（スキップして継続）を多く実装していますが、本番運用時はログと監視を適切に行ってください。

---

## ライセンス / 責任範囲

本 README はコードベースの説明です。実際の商用運用における法的責任や各 API の利用規約、資金の投入に関するリスク管理は利用者の責任で行ってください。

---

必要であれば、README に実際の .env.example やスキーマ定義、簡単な CLI スクリプト例（ETL cron 実行や監査 DB 初期化スクリプト）も追加します。追加希望があれば教えてください。