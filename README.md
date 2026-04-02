# KabuSys

日本株向けの自動売買／データ基盤ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、ファクター計算・研究ユーティリティ、監査ログスキーマなどを提供します。

主な設計方針:
- DuckDB をデータ保存・クエリ基盤に利用
- Look‑ahead バイアス（未来情報参照）を避ける設計
- 外部 API 呼び出しはリトライ・レート制御・フォールバックを実装
- LLM（OpenAI）呼び出しは JSON Mode を用い、レスポンスを厳密にバリデート

バージョン: 0.1.0

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方（主要 API 例）
- 環境変数 / 設定
- ディレクトリ構成

---

プロジェクト概要
- KabuSys は、J-Quants API 等からデータを取得し DuckDB に格納する ETL、ニュース収集と OpenAI による記事センチメント評価、ファクター計算・研究用ユーティリティ、取引監査ログ（監査テーブル）の初期化・管理等をまとめたライブラリです。
- バックテストや本番の自動売買基盤の一部（データ基盤・分析・監査）を担います。実際の発注・取引実行や戦略実行のためのモジュールは別途組み合わせて利用します。

機能一覧
- 設定管理
  - .env / 環境変数を自動読み込み（プロジェクトルート判定; .env → .env.local）
  - 必須設定チェック（settings オブジェクト）
- データ ETL（kabusys.data.pipeline）
  - 日次 ETL（株価 / 財務 / 市場カレンダー）
  - 差分取得・バックフィル・品質チェック（欠損・スパイク・重複・日付整合性）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
- ニュース収集（kabusys.data.news_collector）
  - RSS 取得、URL 正規化、トラッキングパラメータ除去、SSRF 対策、前処理、raw_news への冪等保存想定
- ニュース NLP（kabusys.ai.news_nlp）
  - 指定ウィンドウ内のニュースを銘柄別にまとめ、OpenAI（gpt-4o-mini）でセンチメントを取得
  - レスポンス検証、バッチ処理、リトライ、スコアクリッピング、ai_scores への書き込み
- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF（1321）の MA200 乖離とマクロ記事の LLM センチメントを合成して market_regime に書き込む
- リサーチ（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー 等）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計サマリー
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等のテーブル DDL と初期化ユーティリティ（DuckDB 用）
  - init_audit_db / init_audit_schema を提供
- 汎用統計（kabusys.data.stats）
  - Zスコア正規化ユーティリティ など

セットアップ手順（開発向け）
1. Python バージョン
   - Python 3.10+ を推奨（型ヒントで | 演算子等を使用）。
2. 必要パッケージ（例）
   - duckdb
   - openai
   - defusedxml
   - （標準ライブラリで賄えるもの以外は上記を用意）
   例:
   ```
   pip install duckdb openai defusedxml
   ```
3. リポジトリルートで環境変数設定
   - プロジェクトルート（.git または pyproject.toml のある場所）を基準に .env/.env.local が自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数は下記「環境変数 / 設定」を参照。
4. DuckDB ファイル格納先のディレクトリ作成はコード側で自動作成される箇所もありますが、必要に応じて data/ を作成してください。

環境変数 / 設定
- 自動読み込み順序: OS 環境変数 > .env.local > .env
- 自動ロード無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

必須（Settings._require を介して参照される）
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API のパスワード（発注系を使う場合）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン（監視等で使用）
- SLACK_CHANNEL_ID — Slack チャンネル ID（監視等で使用）

任意（デフォルトあり）
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 用パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH — 監視 PID ファイル（デフォルト: data/execution.pid）
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT — 監視閾値（%）
- KABUSYS_ENV — 環境: development / paper_trading / live（デフォルト development）
- LOG_LEVEL — ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト INFO）

注意: OpenAI API のキーは各 AI モジュールの引数として渡すか、環境変数 OPENAI_API_KEY を設定してください（OpenAI呼び出し関数は api_key 引数 or 環境変数を参照します）。

使い方（代表的な例）
- 基本的な準備
  ```
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行する
  ```
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算して ai_scores に保存する
  ```
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("書き込み銘柄数:", n_written)
  ```

- 市場レジーム判定を行う
  ```
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログスキーマを初期化する（DuckDB 接続内にテーブルを作成）
  ```
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 監査専用 DB を作成して接続取得
  ```
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用関数（ファクター計算等）
  ```
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  res = calc_momentum(conn, target_date=date(2026,3,20))
  ```

ディレクトリ構成（主なモジュール）
- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定読み込み（.env 自動ロード）
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースの LLM スコアリングと ai_scores 書込み
    - regime_detector.py     — マクロセンチメント＋ETF MA200 から市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得・保存・認証）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - etl.py                 — ETLResult のエクスポート
    - news_collector.py      — RSS 取得・前処理・記事保存ロジック
    - calendar_management.py — マーケットカレンダー管理／営業日判定
    - stats.py               — zscore_normalize 等の統計ユーティリティ
    - quality.py             — データ品質チェック（欠損・スパイク等）
    - audit.py               — 監査ログ DDL と初期化ロジック
    - (その他：必要に応じて補助モジュール)
  - research/
    - __init__.py
    - factor_research.py     — モメンタム/バリュー/ボラティリティ等の計算
    - feature_exploration.py — 将来リターン計算・IC・ファクター統計等

設計ノート・運用上の注意
- OpenAI 呼び出しや外部 API 呼び出しはネットワークエラーやレート制限に対してリトライやフォールバックを実装していますが、API キーや接続先が正しく設定されていることを確認してください。
- DuckDB の操作は executemany とトランザクションを多用しているため、バージョン互換性（例: DuckDB 0.10 系）に注意してください。コード中に互換性回避のコメントがあります。
- ニュース収集では SSRF 対策や受信上限等のセキュリティ措置を実装していますが、任意の RSS の取り込み先に対する方針を運用ルールで定めてください。
- 設定の自動読み込みはプロジェクトルート（.git / pyproject.toml）を基準に行われます。CI / テスト環境で不要な自動ロードを防ぐには KABUSYS_DISABLE_AUTO_ENV_LOAD を使ってください。
- KABUSYS_ENV は "development", "paper_trading", "live" のいずれかを指定し、ライブ環境では is_live が True になります。ログレベル等の設定を環境に応じて使い分けてください。

よくあるセットアップ例（.env）
例:
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxxxxx
SLACK_CHANNEL_ID=C01XXXXXXX
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

最後に
- 本 README はソースコードの公開部分に基づく概要・使用例です。実践導入時は各環境変数・外部 API の権限設定、DuckDB のバックアップ計画、監査ログの永続化ポリシー等を整備してください。
- 追加の使い方（発注実行フローやモニタリング・監視ジョブ等）は、別途 execution / monitoring モジュールや運用ドキュメントにまとめることを推奨します。