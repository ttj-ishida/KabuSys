# KabuSys

KabuSys は日本株のデータプラットフォーム、リサーチ、AI評価、監査ログ、ETL を統合した自動売買/研究向けライブラリです。J-Quants / OpenAI / kabuステーション 等の外部サービスと連携し、データ収集・品質チェック・ファクター計算・ニュースセンチメント・市場レジーム判定・監査ログを提供します。

主な設計方針は「ルックアヘッドバイアス防止」「冪等性」「フェイルセーフ（API障害時の安全なフォールバック）」「DuckDB を利用した軽量永続化」です。

---

プロジェクトの要点
- Language: Python（型ヒントあり、3.10+ 推奨）
- DB: DuckDB（ローカルファイルまたはメモリ）
- 外部API: J-Quants（株価/財務/カレンダー等）、OpenAI（ニュースのセンチメント/レジーム判定）
- セキュリティ/堅牢性: SSRF 対策、XML パース防御（defusedxml）、API リトライ・レート制御、環境変数管理

---

機能一覧
- 環境設定管理（.env の自動読み込み、必須環境変数取得）
- データ ETL
  - J-Quants から株価日足、財務データ、マーケットカレンダーを差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付整合性）
- ニュース収集（RSS から raw_news へ安全に取り込み）
- ニュース NLP（OpenAI を使った銘柄別ニュースセンチメントのスコアリング）
- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- 研究用ユーティリティ
  - モメンタム/バリュー/ボラティリティなどのファクター計算
  - 将来リターン計算、IC（Information Coefficient）、Z スコア正規化等
- 監査ログ（signal_events / order_requests / executions のスキーマ定義・初期化）
- J-Quants クライアント（レート制御・トークン自動更新・ページネーション対応）

---

セットアップ手順（開発環境向けの概要）
1. Python バージョン
   - Python 3.10 以降を推奨（typing の union 表記などを利用）

2. リポジトリをクローン
   - git clone <repo-url>
   - パッケージルートが .git または pyproject.toml によって自動認識されます

3. 依存パッケージをインストール
   - 主要依存: duckdb, openai, defusedxml
   - 例:
     pip install duckdb openai defusedxml

   - 開発用に pyproject.toml / requirements.txt がある場合はそちらを使用してください。

4. 環境変数の設定
   - プロジェクトルートに .env（および任意で .env.local）を作成すると、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必須例（.env に設定すべき主要キー）:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...（kabuステーション API）
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
   - 任意/デフォルト:
     - KABUSYS_ENV=development|paper_trading|live（デフォルト: development）
     - LOG_LEVEL=INFO
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PID_FILE_PATH=data/execution.pid

5. データディレクトリ作成（必要に応じて）
   - mkdir -p data

---

使い方（基本のコードスニペット）

- 共通: 設定と DuckDB 接続
  - settings = kabusys.config.settings
  - DB 接続例:
    import duckdb
    from kabusys.config import settings
    conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行（市場カレンダー・株価・財務・品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date=None)  # target_date を date オブジェクトで指定可能
  print(res.to_dict())

- ニュースセンチメントスコア（ai.news_nlp.score_news）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"書き込み銘柄数: {written}")

  注意: OpenAI API キーは OPENAI_API_KEY または api_key 引数で指定

- 市場レジーム判定（ai.regime_detector.score_regime）
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

- RSS フィード取得（ニュース収集の個別利用）
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES
  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])

  注: fetch_rss は SSRF 対策やレスポンスサイズ制限を行っています。HTTP/HTTPS のみ許可。

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  # conn_audit を使って監査テーブルへ書き込み/参照が可能

---

環境変数（主要）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY (必須 for AI functions) — OpenAI の API キー
- KABU_API_PASSWORD (必須 for execution module) — kabuステーション API のパスワード
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: デフォルト data/monitoring.db
- KABUSYS_ENV: development | paper_trading | live（挙動や安全チェックに影響）
- LOG_LEVEL: DEBUG|INFO|...（ログ出力レベル）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env 自動ロードを無効化できます（テスト用）

.env 読み込みルール
- 読み込み優先順位: OS 環境変数 > .env.local > .env
- export KEY=val フォーマットに対応
- クォートやインラインコメントの扱いに配慮したパーサ実装

---

ディレクトリ構成（主なファイル/モジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py             — ニュースのセンチメントスコアリング（OpenAI）
    - regime_detector.py      — 市場レジーム判定（ETF MA + マクロニュース）
  - data/
    - __init__.py
    - pipeline.py             — ETL パイプライン（run_daily_etl 等）
    - etl.py                  — ETLResult の再エクスポート
    - jquants_client.py       — J-Quants API クライアント（取得/保存/レート制御）
    - news_collector.py       — RSS 取得と前処理（SSRF 対策）
    - calendar_management.py  — 市場カレンダー管理（営業日判定等）
    - stats.py                — Zスコア等の統計ユーティリティ
    - quality.py              — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py                — 監査ログスキーマ定義と初期化
  - research/
    - __init__.py
    - factor_research.py      — Momentum/Value/Volatility の計算
    - feature_exploration.py  — 将来リターン、IC、統計サマリー等
  - ai/ (上記)
  - research/ (上記)
  - その他（strategy / execution / monitoring）パッケージは __all__ に宣言済み（実装は別ファイルに存在する想定）

---

注意事項 / 運用上のポイント
- ルックアヘッドバイアス防止:
  - 多くの機能（ETL / AI スコアリング / レジーム判定）は date パラメータを受け取り、内部で datetime.today() を参照しない設計です。バックテストや履歴再計算時に日付を明示してください。
- OpenAI 呼び出し:
  - レスポンスのパースや API エラーはフェイルセーフで処理され、可能な限り部分的な結果とログを残して継続します。
- DuckDB 互換性:
  - 一部の executemany の挙動やリストバインドの扱いに注意（コード内に互換性対策あり）。
- セキュリティ:
  - news_collector は SSRF 対策、XML パース防御、レスポンスサイズ制限を実装しています。
- 自動 .env ロード:
  - パッケージ import 時にプロジェクトルート（.git または pyproject.toml）を探索して .env を自動読み込みします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

トラブルシューティング（よくある質問）
- "OpenAI API キーが未設定です" エラー:
  - OPENAI_API_KEY を環境変数か api_key 引数で指定してください。
- "J-Quants API リクエスト失敗" や 401 エラー:
  - JQUANTS_REFRESH_TOKEN が正しいか、ネットワーク/認証状態を確認。get_id_token はトークン自動更新を試みます。
- DuckDB のテーブルやスキーマが存在しない:
  - 必要なスキーマは ETL 実行時や init_audit_db で初期化される想定です。監査スキーマは init_audit_db / init_audit_schema を呼んで作成してください。

---

貢献
- バグ報告、機能提案、プルリクエストは歓迎します。プロジェクトの方針に沿った設計（冪等性・フェイルセーフ・ルックアヘッド回避）を維持してください。

---

以上がこのコードベースの概要、セットアップ、使い方、ディレクトリ構成です。必要に応じて利用シナリオ（バッチ ETL スケジュール例、監視設定、発注実行フロー）を追補できますので、どの部分をドキュメント化したいか教えてください。