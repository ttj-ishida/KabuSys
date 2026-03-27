# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース収集・NLP（LLM）によるセンチメントスコアリング、ファクター計算、マーケットカレンダー管理、監査ログ（トレーサビリティ）など、バックテスト／運用で必要な機能群を含みます。

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 環境変数と設定
- 使い方（簡単な例）
- ディレクトリ構成
- 補足・注意事項

---

プロジェクト概要
- KabuSys は日本株を対象としたデータパイプライン・リサーチ・運用支援ライブラリです。
- J-Quants API を用いたデータ取得（株価、財務、取引カレンダー）・DuckDB への格納、ニュースの収集と LLM によるセンチメント評価、ファクター計算、データ品質チェック、監査ログ（シグナル→注文→約定のトレース）などを提供します。
- LLM 呼び出しには OpenAI（gpt-4o-mini 等）を想定しています。OpenAI SDK（openai パッケージ）を使用する実装です。

---

主な機能一覧
- data (ETL / pipeline)
  - 日次 ETL（株価・財務・カレンダー差分取得、保存、品質チェック）
  - J-Quants API クライアント（ページネーション / レート制限 / トークン自動リフレッシュ / 冪等保存）
  - マーケットカレンダー管理（営業日判定・next/prev/get_trading_days）
  - ニュース収集（RSS → raw_news、SSRF/サイズ/トラッキング除去対策）
  - データ品質チェック（欠損・スパイク・重複・日付整合性）
  - 監査ログ（signal_events / order_requests / executions テーブル、初期化ユーティリティ）
  - 統計ユーティリティ（Zスコア正規化など）
- ai
  - ニュース NLP（news_nlp.score_news）: ニュース記事を銘柄毎にまとめて LLM に投げ、ai_scores に書き込む
  - 市場レジーム判定（regime_detector.score_regime）: ETF 1321 の MA200 乖離とマクロニュースの LLM センチメントを合成して市場レジームを判定
- research
  - ファクター計算（momentum / value / volatility 等）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー等
- config
  - .env / 環境変数からの設定読み込み（自動ロード機能あり）
- audit / monitoring / execution
  - 監査ログ初期化、実行系・監視系モジュール（基盤は準備済み）

---

セットアップ手順（開発環境向け、例）
1. Python 環境の準備
   - 推奨: Python 3.10 以上（コードは型ヒントと最新構文を一部使用）
   - 仮想環境を作成・有効化
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（最低限）
   - pip install duckdb openai defusedxml
   - 実際には setup.py / pyproject.toml があれば pip install -e . を推奨

3. ソースを編集している場合（開発インストール）
   - repo ルートで: pip install -e .

4. 環境変数の設定
   - 本 README の「環境変数と設定」を参照して .env をプロジェクトルートに配置するか、OS 環境変数で設定してください。

5. DuckDB ファイル等のディレクトリ作成
   - デフォルトでは data/kabusys.duckdb を使用するので必要ならディレクトリを作成してください（コード側でも自動作成する処理がある箇所があります）。

---

環境変数と設定
- 自動 .env ロード
  - パッケージ起動時にプロジェクトルート（.git または pyproject.toml を探索）を探し、以下の順で読み込みます:
    1. OS 環境変数（優先）
    2. .env.local（存在する場合、OS を除き上書き）
    3. .env（.env.local が無ければ参照）
  - 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時などに便利）。
- 主な環境変数
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須: data.jquants_client.get_id_token / ETL）
  - KABU_API_PASSWORD: kabuステーション API のパスワード（実行モジュールで使用）
  - KABU_API_BASE_URL: kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
  - SLACK_BOT_TOKEN: Slack 通知で使用する Bot トークン（必須に設定されている箇所あり）
  - SLACK_CHANNEL_ID: 通知先 channel ID
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
  - KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
  - LOG_LEVEL: ログレベル ("DEBUG","INFO","WARNING","ERROR","CRITICAL")
  - OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- .env フォーマット
  - export KEY=VALUE 形式や KEY="quoted value" などをサポートしています。詳細は config._parse_env_line の挙動に従います。

---

使い方（簡単なコード例）

1) DuckDB に接続して日次 ETL を走らせる
- 例:
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

2) ニューススコア（LLM）を実行して ai_scores に保存
- 必要: OPENAI_API_KEY を環境変数で設定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} scores")

3) レジーム判定（MA200 + マクロニュース）
- 必要: OPENAI_API_KEY を環境変数で設定
- 例:
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  conn = duckdb.connect("data/kabusys.duckdb")
  ret = score_regime(conn, target_date=date(2026, 3, 20))
  print("done", ret)

4) 監査ログ（audit）DB の初期化
- 例:
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済み DuckDB 接続

5) リサーチ関数の利用（ファクター計算）
- 例:
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum
  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, date(2026, 3, 20))
  # records は各銘柄ごとの辞書リスト

注:
- AI 関連関数は OpenAI API を呼び出すため通信料・API 料金が発生します。テスト時は _call_openai_api をモックするよう設計されています。
- ETL / 保存処理は冪等性（ON CONFLICT 等）を考慮して実装されていますが、実行前にバックアップを推奨します。

---

ディレクトリ構成（主要ファイル・概要）
- src/kabusys/
  - __init__.py — パッケージ定義・バージョン
  - config.py — 環境変数 / .env 自動読み込み、Settings クラス
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメントの集約・OpenAI 呼び出し・ai_scores への書込
    - regime_detector.py — 市場レジーム判定（ETF 1321 の MA200 + マクロニュース LLM）
  - data/
    - __init__.py
    - jquants_client.py — J-Quants API クライアント（fetch/save 系）
    - pipeline.py — ETL パイプライン（run_daily_etl, run_prices_etl 等）
    - etl.py — ETLResult の再公開インターフェース
    - news_collector.py — RSS 収集・前処理・raw_news 保存
    - calendar_management.py — market_calendar 管理・営業日判定・calendar_update_job
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
    - audit.py — 監査ログスキーマ定義・初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py — Momentum / Value / Volatility 等のファクター計算
    - feature_exploration.py — 将来リターン・IC・統計サマリー等
  - (その他)
    - strategy/, execution/, monitoring/ は __all__ に含まれています（実行周りのモジュール等）

---

補足・注意事項
- Look-ahead bias 対策に設計上注意が払われています。多くの関数は date や target_date を引数で受け、内部で date.today() に依存しない設計です。
- OpenAI 呼び出しはリトライ・バックオフの制御や JSON mode（厳格な JSON 出力）の利用等を取り入れていますが、実運用時は料金やレイテンシーに注意してください。
- J-Quants API はレート制限（120 req/min）に合わせたスロットリングとリトライを実装しています。API キー（リフレッシュトークン）を必ず安全に管理してください。
- news_collector には SSRF や XML インジェクション対策が組み込まれていますが、外部フィードを扱う際は追加の監視や制約を検討してください。
- テスト: ai モジュールの OpenAI 呼び出し部分はモック差し替えを想定しているため、ユニットテストでは _call_openai_api を patch することが推奨されます。

---

貢献・ライセンス
- 本リポジトリの運用ルールやコントリビュート方法、ライセンスはプロジェクトルートの該当ファイル（LICENSE / CONTRIBUTING.md 等）を参照してください（存在する場合）。

---

質問や追加したいドキュメント（例: API 使用例、デプロイ手順、CI 設定など）があれば教えてください。README をそれに合わせて拡張します。