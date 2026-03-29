# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群。  
市場データの ETL、ニュース収集と AI によるセンチメント解析、ファクター計算、監査ログ整備などを統合的に提供します。

主な設計方針：
- ルックアヘッドバイアス回避（内部で date.today() を直接参照しない等）
- DuckDB を中心としたローカルデータプラットフォーム
- J-Quants API や OpenAI など外部 API 呼び出しに対するレート制御・リトライ・フォールバック実装
- ETL / 保存処理は冪等（idempotent）かつトランザクション保護を考慮

---

## 機能一覧

- 環境設定管理
  - .env / .env.local からの自動読み込み（プロジェクトルート検出）
  - 必須設定の検証（Settings クラス）

- データプラットフォーム（data パッケージ）
  - J-Quants API クライアント（jquants_client）
    - 株価（OHLCV）、財務データ、JPX カレンダー、上場銘柄情報取得
    - レートリミット制御・トークン自動リフレッシュ・リトライロジック
  - ETL パイプライン（pipeline）
    - 差分取得、保存、品質チェックの統合（run_daily_etl 等）
  - カレンダー管理（calendar_management）
    - 営業日判定、next/prev/get_trading_days、カレンダー更新ジョブ
  - ニュース収集（news_collector）
    - RSS 収集、前処理、raw_news への冪等保存、SSRF 対策等
  - データ品質チェック（quality）
    - 欠損・スパイク・重複・日付不整合検出
  - 監査ログ（audit）
    - signal / order_request / executions 等の監査スキーマ初期化・DB 作成ユーティリティ
  - 汎用統計ユーティリティ（stats）

- AI（ai パッケージ）
  - ニュース NLP（news_nlp.score_news）
    - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント解析と ai_scores への保存
    - バッチ処理・レスポンスバリデーション・クリッピング・リトライ実装
  - 市場レジーム判定（regime_detector.score_regime）
    - ETF(1321) の 200 日移動平均乖離 + マクロニュースの LLM センチメントを合成してレジームを評価

- 研究用ユーティリティ（research パッケージ）
  - ファクター計算（momentum / value / volatility）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、正規化ユーティリティ

---

## セットアップ手順（ざっくり）

1. Python 環境
   - 推奨: Python 3.10+（コードは型ヒントで | 型結合を使用しているため 3.10 以上が望ましい）

2. 仮想環境作成（例）
   - python -m venv .venv
   - source .venv/bin/activate

3. 依存パッケージのインストール（例）
   - 必須例：
     - duckdb
     - openai
     - defusedxml
   - pip 例:
     - pip install duckdb openai defusedxml

   ※ プロジェクトの配布形式によっては pyproject.toml / requirements.txt を使用してください。

4. 環境変数設定
   - 必須（最低限、用途に応じて設定）:
     - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン
     - SLACK_BOT_TOKEN — Slack 通知利用時
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - KABU_API_PASSWORD — kabu API（発注）パスワード
     - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI モジュール実行時）
   - 任意 / デフォルト:
     - KABUSYS_ENV (development | paper_trading | live) デフォルト "development"
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) デフォルト "INFO"
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env の自動ロードを無効化可
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）

   - .env 自動読み込みの挙動:
     - プロジェクトルート（.git または pyproject.toml がある場所）を探索して `.env` を読み込みます。
     - `.env.local` は `.env` の上書き（override）として読み込まれます。

5. データベース初期化（監査ログなど）
   - 監査ログ用 DB を初期化する例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

---

## 使い方（簡単な例）

以下は簡単な Python REPL / スクリプトでの利用例です。実行前に必要な環境変数（特に OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN）を設定してください。

- DuckDB 接続を作る
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行する
  - from datetime import date
  - from kabusys.data.pipeline import run_daily_etl
  - result = run_daily_etl(conn, target_date=date(2026,3,20))
  - print(result.to_dict())

- ニュースのスコア付け（OpenAI 必須）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026,3,20), api_key="sk-...")  # api_key を引数で渡すことも可

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - score_regime(conn, target_date=date(2026,3,20), api_key="sk-...")

- ファクター計算（研究用）
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - momentum = calc_momentum(conn, target_date=date(2026,3,20))

- 監査ログスキーマ初期化
  - from kabusys.data.audit import init_audit_schema
  - init_audit_schema(conn, transactional=True)

注意点：
- OpenAI を利用する処理は API レートやコストに注意してください。リトライやフォールバックが実装されていますが、API キー管理は厳重に。
- J-Quants API 呼び出しはレート制限（120 req/min）およびトークン管理に対応しています。リフレッシュトークンは安全に保管してください。

---

## ディレクトリ構成（要旨）

src/kabusys/
- __init__.py
- config.py — 環境変数 / 設定の読み込み・検証（.env 自動読み込み）
- ai/
  - __init__.py
  - news_nlp.py — ニュースをまとめて LLM に投げるロジック、スコア保存
  - regime_detector.py — ETF MA とマクロセンチメントを合成する市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得・保存関数群）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集と raw_news 保存、SSRF 対策等
  - calendar_management.py — JPX カレンダー管理・営業日ロジック
  - quality.py — データ品質チェック
  - stats.py — z-score 正規化など統計ユーティリティ
  - audit.py — 監査スキーマ初期化、init_audit_db など
- research/
  - __init__.py
  - factor_research.py — モメンタム/バリュー/ボラティリティ等の計算
  - feature_exploration.py — 将来リターン、IC、統計サマリー等

各モジュールはコメントドキュメントに設計意図や安全性（例：ルックアヘッド回避、フェイルセーフ挙動、冪等性）を明記しています。

---

## 運用上の注意・ベストプラクティス

- 本ライブラリは外部 API（J-Quants / OpenAI / 証券会社 API 等）へアクセスします。テスト・開発環境と本番環境で適切に環境変数を分けてください（KABUSYS_ENV を活用）。
- AI モジュールでは API 失敗時に安全なフォールバック（スコア 0.0 など）を行いますが、重大な判断ロジックに用いる場合はヒューマンインザループ（監査・確認プロセス）を導入してください。
- ETL 実行は定期バッチ（cron / airflow 等）で運用する想定です。run_daily_etl の戻り値（ETLResult）を監視・通知する仕組みを整えることを推奨します。
- .env / .env.local には機密情報が含まれるため、バージョン管理には絶対に含めないでください。

---

もし README に加えたい内容（例: 詳しいデータスキーマ、サンプル .env.example、デプロイ手順、CI 設定例など）があれば教えてください。必要に応じて追記・整形します。