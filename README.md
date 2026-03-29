# KabuSys

日本株向け自動売買・データプラットフォームライブラリ KabuSys の README（日本語）。

このリポジトリは、データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集・NLP（OpenAI を利用したセンチメント解析）、ファクター算出、監査ログ（発注トレーサビリティ）などを包含するコンポーネント群を提供します。バックテストや自動売買戦略の基盤として使えるよう設計されています。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（簡易例）
- ディレクトリ構成
- 追加情報 / 注意点

---

プロジェクト概要
- 名称: KabuSys
- 目的: 日本株向けのデータプラットフォームと自動売買支援ライブラリ。J-Quants API からのデータ取得、DuckDB による保存・クエリ、ニュース収集と LLM によるニュースセンチメント判定、ファクター計算、データ品質チェック、監査ログ（シグナル→発注→約定のトレーサビリティ）を提供します。
- 設計方針: ルックアヘッドバイアス回避、冪等性、堅牢なリトライ／レート制御、DB トランザクション保護、外部 API エラーに対するフェイルセーフ。

---

機能一覧
- 環境設定管理
  - .env / .env.local 自動ロード（プロジェクトルート判定）
  - 必須環境変数の取得 (Settings)
  - 自動 env ロードを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD
- データ取得 (J-Quants)
  - 株価日足（OHLCV）取得・ページネーション対応
  - 財務データ（四半期 BS/PL）取得
  - JPX マーケットカレンダー取得
  - レートリミッタ & 再試行ロジック、401 時のトークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT）
- ETL パイプライン
  - 日次 ETL（calendar → prices → financials、品質チェック）
  - 個別 ETL ジョブ（run_prices_etl, run_financials_etl, run_calendar_etl）
  - ETL 実行結果を ETLResult で集約
- データ品質チェック
  - 欠損、主キー重複、スパイク（急騰/急落）、日付不整合（未来日付、非営業日）など
  - QualityIssue オブジェクトで出力
- ニュース収集 & 前処理
  - RSS の取得（SSRF 対策、リダイレクト検査、サイズ制限、トラッキング除去）
  - URL 正規化 → 記事 ID 生成（SHA-256 の先頭）
  - raw_news / news_symbols への冪等保存フロー（実装参照）
- ニュース NLP（OpenAI）
  - news_nlp.score_news: 銘柄ごとに記事を集約 → LLM に投げてセンチメントを取得 → ai_scores へ書き込み
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定・保存
  - gpt-4o-mini を利用（JSON モード）、リトライ・バックオフ実装、レスポンス検証・クリッピング
- 研究用ユーティリティ
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
  - 外部ライブラリに依存しない純 Python 実装
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブル定義と初期化ヘルパー
  - UUID ベースのトレーサビリティ、UTC タイムスタンプ保持、冪等キー（order_request_id）設計

---

セットアップ手順（開発用・最小セット）
前提
- Python 3.10 以上（Union 型記法や型ヒントを使用）
- システムに internet 接続（J-Quants / OpenAI API へアクセスする場合）

1) 仮想環境を作成・有効化（推奨）
- Unix/macOS:
  python -m venv .venv
  source .venv/bin/activate
- Windows (PowerShell):
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1

2) 必要なパッケージをインストール
- 必要最低限の依存（参考）:
  pip install duckdb openai defusedxml

  （プロジェクトに setup.py / pyproject.toml がある場合は pip install -e . を推奨）

3) 環境変数 (.env)
- プロジェクトルートに .env / .env.local を配置すると自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化可能）。
- 必要な環境変数（主に Settings で必須とされるもの）:
  - JQUANTS_REFRESH_TOKEN    ← J-Quants のリフレッシュトークン（必須）
  - KABU_API_PASSWORD        ← kabuステーション API パスワード（必須）
  - SLACK_BOT_TOKEN          ← Slack 通知用（必須）
  - SLACK_CHANNEL_ID         ← Slack チャンネル ID（必須）
  - OPENAI_API_KEY           ← OpenAI API キー（news_nlp / regime_detector で使用）
  - DUCKDB_PATH              ← DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH              ← 監視用 SQLite（デフォルト: data/monitoring.db）
  - KABUSYS_ENV              ← development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL                ← DEBUG / INFO / ...（デフォルト: INFO）

  .env の例（.env.example がある場合はそちらを参照してください）:
  JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=secret
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567

4) DuckDB の初期化（監査ログなど）
- 監査 DB を初期化する例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで監査用テーブルが作成されます

---

使い方（簡易サンプル）
- ETL（日次パイプライン）を実行する（Python REPL 等）:

  from datetime import date
  import duckdb
  from kabusys.config import settings
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントを算出して ai_scores に書き込む:

  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key=None の場合は環境変数 OPENAI_API_KEY を使う
  print(f"書き込み銘柄数: {written}")

- 市場レジーム判定：

  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- ファクター計算（例: モメンタム）:

  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(records))

- 監査 DB 初期化（別 DB を用いる場合）:

  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリは自動作成されます

注意: 上記の API 呼び出しは外部サービス（J-Quants / OpenAI）にアクセスします。API キーやネットワークの設定を適切に行ってください。

---

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py                (パッケージ情報: __version__ = "0.1.0")
  - config.py                  (環境変数 / Settings 自動読み込み)
  - ai/
    - __init__.py              (score_news のエクスポート)
    - news_nlp.py              (ニュースセンチメント → ai_scores)
    - regime_detector.py       (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py        (J-Quants API クライアント & DuckDB 保存)
    - pipeline.py              (ETL パイプライン & run_daily_etl)
    - etl.py                   (ETLResult の再エクスポート)
    - calendar_management.py   (市場カレンダー管理・営業日判定)
    - news_collector.py        (RSS 取得・前処理・SSRF 対策)
    - quality.py               (データ品質チェック)
    - stats.py                 (zscore_normalize 等の統計ユーティリティ)
    - audit.py                 (監査ログテーブル定義・初期化)
  - research/
    - __init__.py
    - factor_research.py       (momentum/value/volatility 等)
    - feature_exploration.py   (forward returns, IC, summary, rank)
  - ai, research, data 以下にさらに細かな実装多数（ETL、保存、検証など）

（README に書かれている以外にも execution / monitoring 等のサブパッケージが想定されていますが、このコードベースには一部モジュールのみが含まれています）

---

追加情報 / 注意点
- Python バージョン: 型注釈や構文から Python 3.10+ を想定しています。可能であれば 3.11 を推奨します。
- OpenAI: news_nlp と regime_detector は gpt-4o-mini を呼び出し、JSON モードで厳密な JSON を取得する想定です。API レートやコストに注意してください。
- J-Quants: レート制限（120 req/min）を尊重する RateLimiter を実装しています。id_token の自動リフレッシュやページネーションに対応。
- DuckDB: executemany に空リストを渡せない制約を考慮した実装があります（空時は呼ばない）。
- セキュリティ:
  - news_collector は SSRF 防止（ホストのプライベートチェック、リダイレクト検査）や XML の安全パーサ（defusedxml）を利用。
  - .env の取り扱いや API キーの管理は十分に注意してください。
- 自動環境読み込み: config.py はプロジェクトルート（.git または pyproject.toml を探索）を検出して .env/.env.local を読み込みます。テスト時や特別な状況では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- ロギング: Settings.log_level でログレベルを指定可能。 production 環境では適切に設定してください。
- エラー処理: 多くの API 呼び出し・ETL では一部失敗を許容して処理を継続するデザイン（フェイルセーフ）になっています。運用上は ETLResult の errors / quality_issues を確認して運用判断を行ってください。

---

貢献・拡張
- execution（ブローカー接続/約定）や monitoring（監視/アラート）などの実装を追加して自動売買ループへ組み込むことが可能です。
- news_collector のソース追加、AI モデル切替、より厳密な品質チェックの追加などが想定されます。

---

以上がこのコードベースの概要と主要な使い方です。さらに具体的な使い方や拡張のサンプルが必要であれば、どの機能についての実例（ETL 実行スクリプト、ニュース収集の運用、監査 DB 運用、AI レスポンス検証など）を出力すれば良いか教えてください。