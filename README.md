# KabuSys — 日本株自動売買システム

簡潔な概要
- KabuSys は日本株向けのデータ基盤・リサーチ・簡易自動売買（監査／発注連携を想定）を目的とした Python パッケージです。
- 主な機能はデータ ETL（J-Quants 経由）、ニュース収集と LLM を用いたニュースセンチメント、マーケットレジーム判定、ファクター計算、データ品質チェック、監査ログ用スキーマ（DuckDB）などです。
- モジュール群はデータ取得/保存（duckdb）、研究用ユーティリティ（ファクター計算）、AI（OpenAI）によるニュース評価を分離して提供します。

主な機能一覧
- データ ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、マーケットカレンダーを差分取得・保存
  - 差分更新・バックフィル・ページネーション対応
  - レート制御（120 req/min）、リトライ、トークン自動リフレッシュ対応
- ニュース収集
  - RSS フィードを安全に取得（SSRF対策、サイズ上限、トラッキングパラメータ削除）
  - raw_news / news_symbols への冪等保存ロジック
- AI（LLM）解析
  - ニュースを銘柄ごとにまとめて OpenAI（gpt-4o-mini）でセンチメント評価（news_nlp.score_news）
  - マクロニュースと ETF（1321）の MA200 乖離を合成して市場レジーム判定（regime_detector.score_regime）
  - API 呼び出しのリトライ、レスポンス検証やフェイルセーフを実装
- 研究系ユーティリティ
  - Momentum / Volatility / Value ファクター計算（research.factor_research）
  - 将来リターン、IC 計算、統計サマリー（research.feature_exploration）
  - z-score 正規化（data.stats）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合の検出（data.quality）
- 監査ログ（Audit）
  - signal_events / order_requests / executions の DDL とインデックス
  - init_audit_schema / init_audit_db による冪等初期化
- 設定管理
  - .env / .env.local 自動ロード（プロジェクトルート検出）
  - 必須環境変数チェックと settings API（kabusys.config）

動作環境・前提
- Python 3.10 以上（型ヒントの | 演算子等を使用）
- 必要なパッケージ（主なもの）:
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外を追加する場合は requirements.txt を用意してください）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローンし仮想環境を作成
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （開発用に editable install をする場合）pip install -e .

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に .env を置くと自動で読み込まれます。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

   例（.env, 必須項目のみの最小例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=your_openai_api_key
   SLACK_BOT_TOKEN=your_slack_bot_token
   SLACK_CHANNEL_ID=your_slack_channel_id
   KABUSYS_ENV=development
   ```

4. DuckDB ファイル格納先の確認（デフォルト）
   - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH（監視等のための SQLite、デフォルト: data/monitoring.db）

使い方（基本的な呼び出し例）
- DuckDB コネクション作成（例）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（pipeline）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  res = run_daily_etl(conn, target_date=date(2026,3,20))
  print(res.to_dict())
  ```

- ニューススコア生成（LLM による銘柄センチメント）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  written = score_news(conn, target_date=date(2026,3,20), api_key=None)  # 環境変数 OPENAI_API_KEY を使う
  print("written codes:", written)
  ```

- 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査 DB 初期化（監査専用 DB を作る）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 設定値の参照（settings）
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path, settings.is_live)
  ```

主要ディレクトリ / ファイル構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義、公開モジュール一覧
  - config.py — 環境変数 / .env の自動読み込み、Settings API
  - ai/
    - news_nlp.py — ニュースを銘柄別に集約し OpenAI でセンチメント評価
    - regime_detector.py — MA200 とマクロニュースを合成して市場レジーム判定
  - data/
    - jquants_client.py — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py — ETL のエントリポイント（run_daily_etl 等）
    - news_collector.py — RSS 収集と前処理（SSRF 対策など）
    - calendar_management.py — 市場カレンダー管理・営業日計算
    - quality.py — データ品質チェック
    - stats.py — zscore 正規化などの統計ユーティリティ
    - audit.py — 監査ログ（DDL / 初期化）
    - etl.py — ETLResult の再エクスポート
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - research/__init__.py, data/__init__.py, ai/__init__.py — API エクスポート

注意事項 / 運用上のポイント
- OpenAI / J-Quants の API キーはそれぞれ環境変数（OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN 等）で管理してください。
- LLM 呼び出しはコストとレート制限に注意してください。news_nlp / regime_detector はリトライとフェイルセーフ（失敗時はスコア0にフォールバック）を備えていますが、運用設定は考慮する必要があります。
- DuckDB による ON CONFLICT アップサートやトランザクション管理を用いているため、データの冪等性はある程度担保されています。
- テストや CI で自動的な .env 読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発 / 貢献
- 新しい機能追加や修正は module 単位で行い、ユニットテスト（モックを多用）を追加してください。
- LLM 呼び出しやネットワーク I/O 部分は差し替えやモックがしやすい設計になっています（例: _call_openai_api の差し替え、_urlopen のモック）。

以上がコードベースの概要と基本的な利用方法です。必要であれば、デプロイ手順（コンテナ化 / systemd ジョブ化）、より詳細な API リファレンス、.env.example の完全版なども作成します。どの情報を優先して追加しますか？