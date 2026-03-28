# KabuSys — 日本株自動売買システム

短い概要
- KabuSys は日本株のデータ取得（J-Quants）、データ品質チェック、特徴量計算、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ管理などを含む自動売買プラットフォーム向けのユーティリティ群です。
- コアは DuckDB を用いたデータプラットフォームと、OpenAI（gpt-4o-mini）を使ったニュースセンチメント評価を組み合わせた研究・実行補助モジュール群で構成されています。

主な機能一覧
- データ取得・ETL
  - J-Quants からの日次株価（OHLCV）取得 / 保存（差分更新・ページネーション対応）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
- データ品質チェック
  - 欠損データ、スパイク（前日比）、重複、日付不整合チェック
- ニュース収集・NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI を用いた銘柄別ニュースセンチメント（ai_scores テーブルへ書き込み）
- 市場レジーム判定
  - ETF 1321 の 200 日 MA とマクロニュースの LLM スコアを合成してレジーム判定（bull/neutral/bear）
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions の監査テーブル定義と初期化ユーティリティ
- 設定管理
  - .env / .env.local / OS 環境変数から設定を読み込み。自動ロードは環境変数で無効化可能

環境要件
- Python 3.10+
- 必要パッケージ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで HTTP は urllib を使用（外部 HTTP ライブラリは不要）

セットアップ手順（ローカル開発向け）
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成・有効化（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # Unix/macOS
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   - もし requirements.txt / pyproject.toml があればそれに従ってください。基本的には次をインストールします:
   ```
   pip install duckdb openai defusedxml
   ```
   - 開発パッケージや追加の依存がある場合はプロジェクト固有の指示に従ってください。

4. 環境変数設定
   - 簡単にはプロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。config モジュールはプロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` を読み込みます。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

   必須となる代表的な環境変数（実行する機能に応じて変わります）:
   - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（ETL）
   - OPENAI_API_KEY — OpenAI 呼び出し（news_nlp / regime_detector）
   - KABU_API_PASSWORD — kabuステーション API パスワード（注文連携を行う場合）
   - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID — Slack 通知を行う場合
   - 任意: KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
   - データベースパス（任意、デフォルトあり）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）

   例 .env（テンプレート）:
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

使い方 — 主要な操作例
- DuckDB 接続の作成（例: スクリプト内）
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（指定日）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026,3,20))
  print(f"書き込んだ銘柄数: {written}")
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  import duckdb

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ DB 初期化（監査専用 DB を作る場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # 親ディレクトリは自動作成される
  ```

- 監査スキーマのみ既存接続へ適用
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

設定管理の挙動メモ
- config モジュールはプロジェクトルート（.git / pyproject.toml）を起点に `.env` と `.env.local` を自動で読み込みます（OS 環境変数が優先）。テストや特別な用途で自動読み込みを停止する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- Settings クラス経由でアクセスします。必須項目が未設定の場合は ValueError が発生します。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージのエントリ（version など）
  - config.py — 環境変数 / 設定読み込みユーティリティ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI 使用）
    - regime_detector.py — マクロ + MA による市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（取得 / 保存）
    - pipeline.py — ETL パイプライン（run_daily_etl など）
    - etl.py — ETLResult の再エクスポート
    - calendar_management.py — 市場カレンダー操作ユーティリティ
    - news_collector.py — RSS 取得 / raw_news 保存（SSRF 対策等）
    - quality.py — データ品質チェック群
    - stats.py — 汎用統計ユーティリティ（zscore_normalize など）
    - audit.py — 監査ログテーブル定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility 等のファクター計算
    - feature_exploration.py — 将来リターン / IC / summary / ranking 等
  - ai/（上記）
  - research/（上記）
- その他
  - data/ (デフォルトの DuckDB 等の格納先)
  - .env.example（プロジェクトルートに置く想定の雛形; 作成推奨）

開発・テストに関する注意
- DuckDB のバージョンに依存する SQL の振る舞い（executemany の空リスト扱いなど）があるため、CI やローカルで使用する DuckDB のバージョンを固定することを推奨します。
- OpenAI への呼び出しはネットワーク / レート制限 / JSON 形式のパース不備に対してフォールバックやリトライを組み込んでいます。テスト時は各モジュール内の _call_openai_api をモックしてください。
- RSS 取得周りは defusedxml や SSRF チェック等の安全対策を組み込んでいます。外部ソースやネットワーク周りのエラーは適切にハンドリングしてください。

よくある運用フロー（例）
1. 毎夜 ETL（run_daily_etl）を走らせデータを更新
2. 朝に news_nlp.score_news を走らせ ai_scores を更新
3. morning のバッチで regime_detector.score_regime を実行し取引方針を決定
4. 戦略層で signal を生成 → order_requests に記録 → 約定を executions に格納（監査ログ）

補足
- セキュリティ: API キーやパスワードは `.env` にハードコーディングしない・アクセス管理を行ってください。
- Look-ahead バイアス対策: 多くの関数は datetime.today() を直接参照せず、明示的な target_date 引数を使う設計です。バックテスト時は必ず過去のデータ状態に基づくようにしてください。

フィードバック・貢献
- バグ報告や改善提案は Issue を作成してください。外部 API 呼び出しまわり（リトライ・エラーハンドリング等）や SQL の互換性に関する改善は歓迎します。

以上がこのコードベースの README.md 相当の内容です。必要であれば、利用例（スクリプト）や .env.example のテンプレートを補足で作成します。どの情報を優先して追加しますか？