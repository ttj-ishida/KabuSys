# KabuSys

KabuSys は日本株向けの自動売買・データ基盤ライブラリです。J-Quants API / kabuステーション / RSS / OpenAI を組み合わせて、データ取得（ETL）、ニュースのセンチメント解析、マーケットレジーム判定、ファクター計算、監査ログ（発注→約定トレーサビリティ）などを提供します。

主な目的は「バックテスト／リサーチ環境と本番発注システムの共通基盤」を安全に実装することです。
- Look-ahead バイアスを避ける設計
- API 呼び出し・DB 書き込みのフェイルセーフ設計
- 冪等性を重視した ETL / 保存ロジック
- ニュース：SSRF や XML 攻撃対策済みの収集ロジック

---

## 機能一覧

- 環境設定管理（.env / 環境変数の自動ロード / 必須チェック）
  - 設定項目例: JQUANTS_REFRESH_TOKEN, OPENAI_API_KEY, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に `.env` / `.env.local` を読み込み（無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD=1）

- Data（ETL / データ品質 / カレンダー / ニュース収集 / J-Quants クライアント）
  - 日次 ETL パイプライン（run_daily_etl）：市場カレンダー、株価（raw_prices）、財務（raw_financials）を差分取得・保存
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - JPX カレンダー管理（営業日判定・next/prev/get_trading_days）
  - RSS ニュース収集（SSRF 対策・トラッキングパラメータ除去・gzip / サイズ制限）
  - J-Quants API クライアント（レート制御・リトライ・トークン自動リフレッシュ）
  - 監査ログ（signal_events / order_requests / executions）スキーマ初期化ユーティリティ

- AI（ニュース NLP / 市場レジーム判定）
  - ニュースを銘柄単位で集約して OpenAI（gpt-4o-mini）へ JSON モードで投げ、ai_scores テーブルへ書き込み（score_news）
  - ETF（1321）の 200 日 MA とマクロニュースの LLM センチメントを合成して市場レジーム判定（score_regime）

- Research（ファクター計算・特徴量探索）
  - ファクター計算: momentum / volatility / value 等（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリ
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

---

## セットアップ手順（開発向け）

1. リポジトリをクローンしてプロジェクトルートへ移動
   - 例: git clone ... && cd your-repo

2. 仮想環境を作成して有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必須例:
     - duckdb
     - openai
     - defusedxml
   - 例:
     - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

4. 環境変数 / .env を準備
   - プロジェクトルートに `.env`（および開発専用に `.env.local`）を作成。例の項目:
     - JQUANTS_REFRESH_TOKEN=...
     - OPENAI_API_KEY=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development  # development | paper_trading | live
     - LOG_LEVEL=INFO
   - 自動ロードが不要な場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

5. DuckDB 等のデータベース用ディレクトリを作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要ユースケース）

以下は Python スクリプトや REPL から呼び出す例です。すべての関数は duckdb の接続オブジェクトを受け取ります。

- DuckDB 接続の作成例
  - import duckdb, from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL 実行
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースの NLP スコアリング（score_news）
  - from kabusys.ai.news_nlp import score_news
    from datetime import date
    conn = duckdb.connect(str(settings.duckdb_path))
    # OPENAI_API_KEY は環境変数でも渡せる
    n = score_news(conn, target_date=date(2026,3,20), api_key=None)
    print(f"scored {n} codes")

- 市場レジーム判定（score_regime）
  - from kabusys.ai.regime_detector import score_regime
    from datetime import date
    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026,3,20), api_key=None)

  - 注意: api_key が None の場合は環境変数 OPENAI_API_KEY を使用。未設定だと ValueError。

- 監査ログ DB 初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions テーブル等が作成されます

- ファクター計算 / 研究系
  - from kabusys.research.factor_research import calc_momentum
    conn = duckdb.connect(str(settings.duckdb_path))
    momentum = calc_momentum(conn, target_date=date(2026,3,20))
    # 結果は list[dict]。zscore_normalize 等で正規化可能。

- データ品質チェック
  - from kabusys.data.quality import run_all_checks
    issues = run_all_checks(conn, target_date=date(2026,3,20))
    for i in issues:
        print(i)

---

## 主要環境変数（まとめ）

必須／代表的なもの:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL の認証に使用）
- OPENAI_API_KEY: OpenAI API キー（ニュース NLP / レジーム判定に使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（取引実行モジュールで使用）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID: Slack 通知連携
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 開発モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）

自動 .env ロード:
- デフォルトでプロジェクトルートの `.env` と `.env.local`（.env.local は .env を上書き）を読み込みます。
- 無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

---

## ディレクトリ構成（概要）

src/kabusys/
- __init__.py
- config.py                — 環境設定・.env の自動読み込み・Settings
- ai/
  - __init__.py
  - news_nlp.py            — ニュースセンチメント（score_news）
  - regime_detector.py     — マーケットレジーム判定（score_regime）
- data/
  - __init__.py
  - jquants_client.py      — J-Quants API クライアント + DuckDB 保存ロジック
  - pipeline.py            — ETL パイプライン（run_daily_etl 等）
  - etl.py                 — ETLResult 再エクスポート
  - calendar_management.py — 市場カレンダー / 営業日ユーティリティ
  - news_collector.py      — RSS ニュース収集（SSRF・XML対策）
  - quality.py             — データ品質チェック
  - stats.py               — zscore_normalize 等の統計ユーティリティ
  - audit.py               — 監査ログスキーマ初期化 / init_audit_db
- research/
  - __init__.py
  - factor_research.py     — モメンタム/ボラティリティ/バリュー計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリ
- research/*（その他の研究用ユーティリティ）
- その他: strategy/, execution/, monitoring/（パッケージ公開用 __all__ で示唆）

（実際のプロジェクトではさらに tests/ や scripts/、docs/ などが存在する可能性があります）

---

## 注意点 / 実運用上のポイント

- Look-ahead バイアス対策: モジュールの多くは datetime.today()/date.today() を直接参照しない設計です。必ず target_date を明示して呼び出してください。
- OpenAI 呼び出し: レスポンスのパースや API エラーに対してフォールバックを行う実装になっていますが、API キーの設定を忘れないでください。テスト時は内部の _call_openai_api をモックできます。
- J-Quants API: レート制限（120 req/min）を考慮して設計済み（内部で RateLimiter を使用）。id_token の自動リフレッシュを実装しています。
- ニュース収集: SSRF / XML Bomb / レスポンスサイズ制限 等の防御を実装していますが、運用環境のプロキシやネットワーク設定に応じた追加対策を検討してください。
- DuckDB executemany の挙動: 一部コードは DuckDB 0.10 系の制約（空リストでの executemany が不可等）を考慮しています。使用する DuckDB バージョンでの動作確認を行ってください。

---

この README はコードベースの主要機能をまとめた概観です。詳細な API や設定例、運用手順はプロジェクト内のドキュメント（DataPlatform.md / StrategyModel.md 等）や各モジュールのドキュメンテーションをご参照ください。必要であれば README に具体的な実行スクリプト例や .env.example のテンプレートを追加できます。