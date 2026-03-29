# KabuSys

日本株向け自動売買・データプラットフォーム／リサーチ基盤ライブラリ

概要
- KabuSys は日本株のデータ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP、研究用ファクター計算、監査ログ（トレーサビリティ）、および市場レジーム推定を目的とした Python コード群です。
- DuckDB を使ったローカルデータベースでデータを保持し、OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント評価やレジーム判定の機能を備えます。
- バックテストや本番運用での Look-ahead バイアス対策や冪等性（idempotency）に配慮した設計になっています。

主な機能一覧
- データ取得・ETL
  - J-Quants API から株価（日足）・財務データ・市場カレンダーを差分取得（ページネーション対応、レート制御、リトライ、トークン自動更新）
  - ETL パイプライン（run_daily_etl）によるまとめ実行、結果は ETLResult オブジェクトで取得
- データ品質チェック
  - 欠損データ、スパイク（急騰/急落）、重複、日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS フィードの安全な取得（SSRF対策、サイズ上限、XML攻撃対策）と raw_news への冪等保存設計（記事ID は正規化 URL のハッシュ）
- ニュースNLP（AI）
  - OpenAI を用いた銘柄別ニュースのセンチメント評価（score_news）
  - レート制限・リトライ・レスポンス検証を組み込んだ安全な実装
- 市場レジーム判定（AI + 指標）
  - ETF（1321）200日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で 'bull' / 'neutral' / 'bear' を判定（score_regime）
- 研究用モジュール
  - モメンタム、ボラティリティ、バリュー等のファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー、Zスコア正規化等
- 監査ログ（Audit）
  - signal_events / order_requests / executions などの監査テーブルを DuckDB に初期化するユーティリティ（init_audit_schema / init_audit_db）

セットアップ手順（ローカル開発用）
1. Python 環境（推奨: 3.10+）を用意
   - 仮想環境の作成と有効化（例）
     - python -m venv .venv
     - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必須パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合は最低限以下を入れてください：
     - pip install duckdb openai defusedxml
   - （必要に応じて）他の依存（requests 等）を追加してください。

3. 環境変数設定
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（config.py による自動ロード）。
   - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
   - 必須の環境変数（Settings が参照）:
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（必須）
     - SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
     - OPENAI_API_KEY — OpenAI API キー（score_news / score_regime に使用）
   - 任意 / デフォルト:
     - KABUSYS_ENV — 開発環境: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）

   例 (.env)
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

4. DuckDB スキーマや監査テーブルの初期化
   - 監査用 DB を初期化する例:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```
   - その他スキーマは利用側で作成する（本 README では省略）。

基本的な使い方（コード例）
- ETL（日次）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")
  print(f"scored {count} securities")
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")
  ```

- 研究用ファクター計算
  ```python
  import duckdb
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  # records は [{"date": ..., "code": "...", "mom_1m": ..., ...}, ...]
  ```

注意事項（設計上のポイント）
- Look-ahead バイアス回避: モジュールの多くは date 引数や DuckDB のクエリ上で「target_date 未満」や明示的なウィンドウを使い、実行時の現在時刻参照（date.today() の乱用）を避けています。
- 冪等性: ETL・保存関数は ON CONFLICT DO UPDATE / INSERT ... DO UPDATE などで冪等性を確保しています。
- AI 呼び出し: OpenAI 呼び出しは JSON mode を使い、レスポンスの検証・リトライを実装しています。APIキーは引数経由で注入可能、テスト時は内部の呼び出し関数をモック可能です。
- セキュリティ: RSS 取得は SSRF／XML攻撃対策（スキームチェック、ホストのプライベート判定、defusedxml、レスポンスサイズ制限）を行っています。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                        — 環境変数 / 設定管理（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py                    — ニュースによる銘柄別スコアリング（OpenAI）
    - regime_detector.py             — ETF MA + マクロニュースで市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py              — J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py                    — ETL パイプライン（run_daily_etl 等）
    - etl.py                         — ETL インターフェース再エクスポート
    - news_collector.py              — RSS 収集と前処理（SSRF 対策等）
    - calendar_management.py         — 市場カレンダー管理（営業日判定等）
    - stats.py                       — 共通統計ユーティリティ（Zスコア等）
    - quality.py                     — データ品質チェック
    - audit.py                       — 監査ログ（テーブル初期化、init_audit_db）
  - research/
    - __init__.py
    - factor_research.py             — Momentum/Value/Volatility 等の計算
    - feature_exploration.py         — 将来リターン/IC/統計サマリー等
  - research/...（その他ユーティリティ）
- その他: packaging に合わせて pyproject.toml 等がプロジェクトルートにある想定

追加メモ
- ログ: Settings.log_level によってログレベルを制御できます。KABUSYS_ENV に応じて挙動（本番/ペーパー）を切り替えられます。
- テスト: OpenAI やネットワーク呼び出し部分は内部関数をモックしてユニットテスト可能な構成です（_call_openai_api など）。
- 実運用: 発注（execution）や kabuステーション連携は設定・認証を正しく行い、まず paper_trading 環境で十分に検証してください。

問い合わせ / 貢献
- 本リポジトリに Issue / PR を立ててください。設計方針（Look-ahead の回避、冪等性、トレーサビリティ）を尊重した実装を歓迎します。

以上。README を元に環境構築・初期化・ETL 実行を行ってください。必要であればサンプル .env.example や requirements.txt、スキーマ初期化スクリプトのテンプレートも作成できます。必要であれば次に作成します。