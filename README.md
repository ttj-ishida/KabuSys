# KabuSys

日本株向けの自動売買・データ基盤ライブラリ群です。  
ETL（J-Quants 経由）、ニュース収集・NLP、マーケットカレンダー管理、ファクター研究、監査ログ（オーディット）など、アルゴリズムトレーディングに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを支える内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API を用いたデータ取得（株価日足、財務、マーケットカレンダー）
- DuckDB を用いたローカルデータベースの ETL と品質チェック
- RSS ベースのニュース収集と前処理（SSRF 対策、トラッキングパラメータ除去等）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント解析と市場レジーム判定
- ファクター計算・特徴量探索（モメンタム、ボラティリティ、バリュー等）
- 監査ログスキーマ（signal → order_request → execution のトレーサビリティ）
- 軽量な設定管理と .env 自動読み込み

設計上、ルックアヘッドバイアスを避けるために内部で現在日時を直接参照しない関数設計がなされています（target_date を明示する方式）。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（取得・保存の冪等処理、リトライ、レートリミット）
  - pipeline: 日次 ETL パイプライン（run_daily_etl 等）
  - quality: データ品質チェック（欠損、重複、スパイク、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定・カレンダー更新ジョブ
  - news_collector: RSS フィード収集・前処理・raw_news 保存（SSRF 対策・サイズ制限）
  - audit: 監査ログ（監査テーブル DDL / 初期化・インデックス）
  - stats: 汎用統計（Zスコア正規化など）
- ai
  - news_nlp.score_news: 銘柄ごとのニュースセンチメントを ai_scores に書込
  - regime_detector.score_regime: ETF(1321) の MA 乖離 + マクロニュースで市場レジーム判定
- research
  - factor_research: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー
- config: 環境変数管理（.env 自動読み込み、必須値チェック、各種パス/閾値設定）
- その他: audit 初期化や DuckDB 初期化ユーティリティなど

---

## セットアップ手順

前提:
- Python 3.9+（より新しいバージョン推奨）
- ネットワークアクセス（J-Quants / OpenAI / RSS ソース）

推奨インストール手順（ローカル開発環境）:

1. リポジトリをクローン
   ```
   git clone <repository-url>
   cd <repository-root>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - 主要な依存想定パッケージ:
     - duckdb
     - openai
     - defusedxml
   例:
   ```
   pip install duckdb openai defusedxml
   ```
   ※ pyproject.toml / requirements.txt がある場合はそれを利用してください:
   ```
   pip install -e .
   ```

4. 環境変数 (.env) を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` または `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須の環境変数（Settings に基づく）:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API のパスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID
     - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime 実行時に必要）
   - オプション / デフォルト値:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

   例 .env:
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
   OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABU_API_PASSWORD=your_password
   ```

5. データベース（DuckDB）の親ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡易ガイド）

以下は代表的な操作例です。各関数は target_date を明示することでルックアヘッドバイアスを避ける設計になっています。

- DuckDB 接続を作成して日次 ETL を実行する
  ```python
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=None)  # target_date None → 今日
  print(result.to_dict())
  ```

- ニュースの NLP スコアを作成する
  - 事前に OpenAI API キーが環境変数 OPENAI_API_KEY に設定されている必要があります。
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # 例: 2026-03-20 のニュースウィンドウを対象
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジームを判定して market_regime テーブルへ書き込む
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（audit）スキーマを初期化する
  ```python
  from kabusys.data.audit import init_audit_db
  from kabusys.config import settings

  conn = init_audit_db(settings.duckdb_path)
  # または既存 conn がある場合:
  # from kabusys.data.audit import init_audit_schema
  # init_audit_schema(conn, transactional=True)
  ```

- ファクター計算（例: モメンタム）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records), records[:3])
  ```

注意:
- score_news / score_regime は OpenAI API を呼ぶため API キー・利用コスト・レスポンス形式に注意してください。
- jquants_client を使う ETL（fetch / save）には J-Quants のトークンが必要です。
- ETL 中の DB 書き込みは冪等性（ON CONFLICT DO UPDATE 等）を考慮していますが、バックテスト用途では過去のデータ取得タイミングに注意を払ってください。

---

## 環境変数と設定（主なもの）

- JQUANTS_REFRESH_TOKEN (必須) : J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須) : kabu API のパスワード
- KABU_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY : OpenAI API キー（score_news, score_regime 等で使用）
- SLACK_BOT_TOKEN (必須) : Slack 通知用ボットトークン
- SLACK_CHANNEL_ID (必須) : Slack 通知先チャンネル
- DUCKDB_PATH : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH : SQLite 用監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV : development / paper_trading / live（デフォルト: development）
- LOG_LEVEL : ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD : "1" にすると .env 自動読み込みを無効化

設定は kabusys.config.settings オブジェクト経由で取得できます。

---

## 開発・テストに関する注意点

- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml がある場所）から行われます。テスト時に自動ロードを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI API 呼び出しや外部ネットワーク呼び出しはテストでモック可能なよう設計されています（例: kabusys.ai.news_nlp._call_openai_api をモック）。
- news_collector は SSRF/サイズ制限/XML パースに対する安全対策を行っていますが、外部フィードの扱いは慎重に行ってください。
- DuckDB の executemany に対する空パラメータの扱い等、バージョン差に配慮した実装が含まれます。ローカルで動作しない場合は duckdb のバージョンを確認してください。

---

## ディレクトリ構成（主要ファイルと役割）

- src/kabusys/
  - __init__.py: パッケージ公開（data, strategy, execution, monitoring）
  - config.py: 環境変数 / 設定管理（.env 自動読み込み、Settings）
  - ai/
    - __init__.py
    - news_nlp.py: ニュースセンチメント解析（score_news）
    - regime_detector.py: 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py: マーケットカレンダー管理・営業日判定・更新ジョブ
    - etl.py: ETL 結果型再エクスポート（ETLResult）
    - pipeline.py: ETL パイプライン（run_daily_etl 等）
    - stats.py: 統計ユーティリティ（zscore_normalize）
    - quality.py: 品質チェック（欠損・重複・スパイク・日付不整合）
    - audit.py: 監査ログスキーマ定義と初期化ユーティリティ
    - jquants_client.py: J-Quants API クライアント（fetch / save）
    - news_collector.py: RSS 収集と前処理
  - research/
    - __init__.py
    - factor_research.py: ファクター計算（momentum, value, volatility）
    - feature_exploration.py: 将来リターン・IC・統計サマリー
  - ai/regime_detector.py, ai/news_nlp.py: OpenAI を用いた NLP ロジック

（README にはここにない細部モジュールも含まれる可能性があります。実際のリポジトリで確認してください）

---

## 運用上の注意

- 本プロジェクトは実際の資金運用に用いる場合、十分な検証（バックテスト / シミュレーション / ペーパー取引）を行ってください。
- 外部 API（J-Quants / OpenAI）利用には API キーと利用契約が必要です。利用制限・コストに注意してください。
- データ取得時のレート制限・リトライ挙動は組み込まれていますが、大量同時実行や誤設定による過剰な API 呼び出しは避けてください。
- ログや監査データは運用観点から削除しない設計です（トレーサビリティ保持）。

---

必要なら、README に追加したいサンプルスクリプトや詳細な API リファレンス、依存関係ファイル（requirements.txt / pyproject.toml）を出力します。どの部分を詳述しましょうか？