# KabuSys

日本株向けの自動売買／データ基盤ライブラリセットです。  
データ取得（J-Quants）→ ETL → 品質チェック → 特徴量生成 → ニュース NLP / レジーム判定 → 戦略・発注・監視 までを想定したモジュール群を提供します。

このリポジトリはライブラリ形式で、業務バッチや戦略実装から関数単位で呼び出して利用します。

## 主な特徴
- ETL パイプライン（J-Quants からの株価・財務・カレンダー取得）
- DuckDB を使ったローカルデータプラットフォーム（冪等保存）
- データ品質チェック（欠損、スパイク、重複、日付整合性）
- ニュース収集（RSS）と NLP スコアリング（OpenAI / gpt-4o-mini）
  - SSRF・Gzip bomb 等を考慮した安全設計
- 市場レジーム判定（ETF 1321 の MA とマクロニュースを重み合成）
- ファクター計算（Momentum / Value / Volatility 等）と特徴量探索ユーティリティ
- 監査ログ（signal → order_request → executions をトレースするスキーマ）と初期化ユーティリティ
- 再試行・レート制御・フェイルセーフ等の運用を意識した実装

## 依存関係（主なもの）
- Python 3.10+（型アノテーションで `X | None` を使用）
- duckdb
- openai
- defusedxml
- （標準ライブラリの urllib 等も使用）

requirements.txt が無い場合は最低限次をインストールしてください：
pip install duckdb openai defusedxml

※プロジェクトをパッケージ化している場合は `pip install -e .` を推奨します。

## 環境変数（必須 / 任意）
kabusys/config.py の Settings が参照する環境変数:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン（ETL 用）
- KABU_API_PASSWORD — kabu ステーション API のパスワード（取引実行用）
- SLACK_BOT_TOKEN — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID — Slack の通知先チャンネル ID

任意（デフォルトあり）:
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 ("development", "paper_trading", "live")（デフォルト: development）
- LOG_LEVEL — ログレベル ("DEBUG", "INFO", ...)

自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

簡易 `.env` 例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

## セットアップ手順（Quick start）
1. ソースをクローン
   git clone <repo-url>
   cd <repo>

2. 仮想環境作成（任意）
   python -m venv .venv
   source .venv/bin/activate

3. 依存をインストール
   pip install -r requirements.txt
   または最低限:
   pip install duckdb openai defusedxml

4. 環境変数を設定（.env を用意）
   プロジェクトルートに `.env` を配置（上記参照）。

5. DuckDB 初期化（監査DBなど）
   Python REPL またはスクリプトで:
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")
   # 既存接続へスキーマを追加する場合は init_audit_schema(conn)

6. ETL 実行（例）
   from datetime import date
   import duckdb
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect(str(Path("data/kabusys.duckdb")))
   result = run_daily_etl(conn, target_date=date.today())
   print(result.to_dict())

## 使い方（代表的な関数）
- 日次 ETL（株価・財務・カレンダー取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  res = run_daily_etl(conn, target_date)

- ニュースセンチメントスコアリング
  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date, api_key="sk-...")  # api_key を指定可

- 市場レジーム判定
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="sk-...")

- 研究用ファクター計算
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  mom = calc_momentum(conn, target_date)

- 統計ユーティリティ（Z スコア正規化）
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(records, ["mom_1m", "ma200_dev"])

- 監査ログ初期化（既存接続へ）
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)

注意点:
- OpenAI 呼び出しは外部 API なので API キーと料金に注意してください。テスト時は内部の _call_openai_api をモックすることを想定しています。
- ETL・AI 処理はルックアヘッドバイアス対策を組み込んでいます（target_date 未満のデータのみ参照する等）。

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- ai/
  - __init__.py
  - news_nlp.py                 — ニュース NLP（score_news）
  - regime_detector.py          — 市場レジーム判定（score_regime）
- data/
  - __init__.py
  - calendar_management.py      — 市場カレンダー管理
  - pipeline.py                 — ETL 実行ロジック（run_daily_etl 等）
  - etl.py                      — ETL の公開型定義（ETLResult）
  - jquants_client.py           — J-Quants API クライアント（fetch/save）
  - news_collector.py           — RSS ニュース収集
  - quality.py                  — データ品質チェック
  - stats.py                    — 統計ユーティリティ（zscore_normalize 等）
  - audit.py                    — 監査ログスキーマ / 初期化
- research/
  - __init__.py
  - factor_research.py          — Momentum / Value / Volatility 等
  - feature_exploration.py      — forward returns / IC / summary / rank
- (strategy/, execution/, monitoring/ はパッケージ公開対象として __all__ に含まれる想定)

（リポジトリルートには pyproject.toml / .git 等が想定されます）

## 運用上の注意・設計方針
- 冪等性: ETL の保存処理は ON CONFLICT DO UPDATE 等で冪等を保ちます。
- フェイルセーフ: 外部 API（J-Quants, OpenAI）が不調な場合でも例外を局所化し、可能な限り処理継続します（ログ出力）。
- レート制御・リトライ: J-Quants には固定間隔の RateLimiter、OpenAI には再試行ロジックが実装されています。
- セキュリティ: RSS 取得では SSRF 対策、XML パーサは defusedxml を利用、受信サイズ上限などを設けています。
- テスト: 自動ロードする .env は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。OpenAI 呼び出し等はモック可能に設計されています。

## 開発者向けメモ
- ログレベルは LOG_LEVEL 環境変数で制御します。
- 環境は KABUSYS_ENV により "development" / "paper_trading" / "live" のいずれかを指定してください（不正な値は起動時に例外）。
- DuckDB バージョン差異（executemany の空リスト扱い等）に注意して実装されています。

---

詳細な API の使い方や運用手順は各モジュールの docstring（ソース内コメント）を参照してください。ソース内に多くの設計ノート・フェイルセーフ処理・想定動作が記載されています。開発／運用の際はまず config とデータベース初期化周り（audit.schema、raw_* テーブル定義）を確認してください。