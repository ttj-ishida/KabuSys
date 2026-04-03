# KabuSys

日本株向けの自動売買プラットフォーム（ライブラリ）。データ収集（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、マーケットレジーム判定、監査ログ等の機能を備え、バックテスト／リサーチ／自動売買の基盤を提供します。

---

## 特長（概要）
- J-Quants API を用いた株価・財務・マーケットカレンダーの差分 ETL（ページネーション・再試行・レート制御対応）
- DuckDB を用いたローカルデータストア（冪等保存）
- ニュース収集（RSS）と LLM による銘柄別センチメントスコアリング（gpt-4o-mini を想定）
- マクロニュースと ETF 200日移動平均乖離を組み合わせた市場レジーム判定
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）スキーマ初期化ユーティリティ
- Research 用ファクター計算（モメンタム、バリュー、ボラティリティ）と特徴量解析ユーティリティ

---

## 機能一覧
- data.jquants_client: J-Quants API クライアント（取得 + DuckDB 保存用ユーティリティ）
- data.pipeline: 日次 ETL（カレンダー・株価・財務）および ETL 結果クラス（ETLResult）
- data.news_collector: RSS 収集 + 前処理 + raw_news への保存ロジック（SSRF 対策・サイズ制限）
- data.quality: 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
- data.calendar_management: JPX カレンダー管理と営業日ユーティリティ
- data.audit: 監査ログスキーマの初期化・DB 作成ユーティリティ
- ai.news_nlp: ニュースを LLM に投げて銘柄別スコアを ai_scores テーブルへ保存
- ai.regime_detector: ETF（1321）MA200乖離 + マクロニュースセンチメントで市場レジーム判定
- research: ファクター計算（calc_momentum / calc_value / calc_volatility）、特徴量探索（forward returns / IC / summary）
- config: 環境変数管理（.env 自動ロード、Settings）

---

## 前提条件（想定）
- Python 3.10+
- DuckDB
- OpenAI Python SDK（gpt-4o-mini を利用する場合）
- defusedxml（RSS パースの安全対策）
- 通常の標準ライブラリ（urllib 等）

（プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

推奨パッケージ例:
- duckdb
- openai
- defusedxml

---

## インストール（例）
1. リポジトリをクローン
   git clone <repo-url>
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
3. 必要パッケージをインストール
   pip install duckdb openai defusedxml
   # 実際はプロジェクトの requirements.txt / pyproject.toml を使用してください

4. パッケージを編集可能インストール（任意）
   pip install -e .

---

## 環境変数 / .env
config.Settings が環境変数を提供します。プロジェクトルートの `.env` / `.env.local` を自動ロードします（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

主な環境変数:
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン（get_id_token 用）
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — デフォルト: http://localhost:18080/kabusapi
- OPENAI_API_KEY (LLM を利用する場合に必要) — OpenAI API キー
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (通知用、任意)
- DUCKDB_PATH (任意) — デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意) — デフォルト: data/monitoring.db
- PID_FILE_PATH / KILL_FLAG_PATH (監視用)
- KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV — {development, paper_trading, live} のいずれか
- LOG_LEVEL — {DEBUG, INFO, WARNING, ERROR, CRITICAL}

※ .env のパースはシェル互換（export 区切り、クォート対応、コメント対応）です。.env.example を参考に作成してください（プロジェクトにある想定）。

---

## セットアップ手順（例）
1. 仮想環境を作成して依存をインストール（上記参照）
2. .env を作成し必要なキーを設定
   例:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   OPENAI_API_KEY=sk-...
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
3. データディレクトリを作成
   mkdir -p data
4. 監査用 DB の初期化（任意）
   Python コンソールまたはスクリプト内で:
   from kabusys.config import settings
   from kabusys.data.audit import init_audit_db
   init_audit_db(settings.duckdb_path)

---

## 使い方（主要 API・実行例）

1) DuckDB 接続を開く（多くの関数は DuckDB 接続を受け取ります）
   import duckdb
   from kabusys.config import settings
   conn = duckdb.connect(str(settings.duckdb_path))

2) 日次 ETL を実行する（市場カレンダー → 株価 → 財務 → 品質チェック）
   from kabusys.data.pipeline import run_daily_etl
   from datetime import date
   result = run_daily_etl(conn, target_date=date(2026,3,20))
   print(result.to_dict())

3) ニュースのスコアリング（LLM を使う。OPENAI_API_KEY が必要）
   from kabusys.ai.news_nlp import score_news
   from datetime import date
   n_written = score_news(conn, target_date=date(2026,3,20))
   print("scored:", n_written)

4) 市場レジーム判定（ETF 1321 の MA200 とマクロニュース）
   from kabusys.ai.regime_detector import score_regime
   from datetime import date
   score_regime(conn, target_date=date(2026,3,20))  # OpenAI API key は env 或いは api_key 引数

5) 監査ログスキーマ初期化
   from kabusys.data.audit import init_audit_db
   init_audit_db(settings.duckdb_path)

6) リサーチ系ユーティリティ例
   from kabusys.research import calc_momentum, calc_value, calc_volatility
   from datetime import date
   mom = calc_momentum(conn, date(2026,3,20))
   vol = calc_volatility(conn, date(2026,3,20))
   val = calc_value(conn, date(2026,3,20))

---

## 開発・テスト
- 自動環境変数読み込みが邪魔なテスト環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- ai モジュールの OpenAI 呼び出しは `_call_openai_api` をモックしてテスト可能です（news_nlp, regime_detector 内の同名関数は独立実装です）。
- ネットワーク呼び出し（J-Quants, RSS, OpenAI）は外部依存があるためユニットテストでは mock を使うことを推奨します。

---

## 注意事項 / 設計上のポイント
- Look-ahead bias（先見バイアス）に配慮した設計：
  - 関数は内部で datetime.today()/date.today() を直接参照しない、または target_date 引数を明示する実装になっています。
  - prices_daily クエリは target_date 未満等の条件でルックアヘッドを防止しています。
- J-Quants API のレート制限（120 req/min）に合わせた rate limiter とリトライ実装があります。
- OpenAI 呼び出しはリトライ・バックオフを実装していますが、API 利用コストに注意してください（バッチ呼び出しを行う設計）。
- DuckDB に対する executemany の空リストバインド制約（DuckDB 0.10 等）を考慮した実装があります。
- RSS 収集は SSRF や XML 攻撃対策（スキーム検証・プライベートアドレス検査・defusedxml）を行っています。

---

## ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py (パッケージ初期化、__version__)
  - config.py (Settings、.env 自動ロード)
  - ai/
    - __init__.py
    - news_nlp.py (ニュース NLP スコアリング)
    - regime_detector.py (市場レジーム判定)
  - data/
    - __init__.py
    - jquants_client.py (J-Quants API クライアント & DuckDB 保存)
    - pipeline.py (ETL パイプライン、run_daily_etl 等)
    - etl.py (ETLResult 再エクスポート)
    - news_collector.py (RSS 収集・前処理)
    - calendar_management.py (市場カレンダー管理、営業日ユーティリティ)
    - quality.py (データ品質チェック)
    - stats.py (z-score 正規化ユーティリティ)
    - audit.py (監査ログスキーマ初期化)
  - research/
    - __init__.py
    - factor_research.py (calc_momentum / calc_value / calc_volatility)
    - feature_exploration.py (forward returns / IC / summary / rank)
  - research パッケージは data.stats 等を再利用してファクター計算や解析を提供

---

## 貢献
プルリクエスト歓迎。設計思想（フェイルセーフ・ルックアヘッド防止・冪等性）を守って実装してください。API キーや資格情報はリポジトリに含めないでください。

---

## ライセンス / 連絡
この README はコードベースの仕様から自動生成的に作成しています。実際のライセンスや連絡先はリポジトリの LICENSE / CONTRIBUTING を参照してください。

---

必要であれば README にサンプル .env.example、より詳細な実行スクリプト例（cron / systemd 用）やデータベーススキーマの説明を追加します。どの部分を拡張しますか？