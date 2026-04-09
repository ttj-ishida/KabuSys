# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース NLP（OpenAI）、市場レジーム判定、リサーチ用ファクター計算、監査ログ（約定トレーサビリティ）などの機能を提供します。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の目的を持つコンポーネント群を含む Python パッケージです。

- J-Quants API から株価・財務・カレンダー等を差分取得し DuckDB に保存する ETL パイプライン
- ニュース収集・前処理と OpenAI による銘柄／マクロのセンチメント評価（gpt-4o-mini を想定）
- 市場レジーム（bull/neutral/bear）判定（ETF 1321 の MA200 乖離 + マクロセンチメント）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログ（signal → order_request → execution のトレーサビリティ）用テーブル初期化ユーティリティ

設計方針として、Look-ahead Bias を避けるために関数内部で現在時刻を乱用せず、ETL・保存は冪等（idempotent）に実装されています。

---

## 主な機能一覧

- データ取得 / 保存
  - J-Quants から日次株価（OHLCV）、財務データ、取引カレンダーを取得（ページネーション対応）
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE 等）
- ETL
  - run_daily_etl を中心とした差分ETL（カレンダー→株価→財務→品質チェック）
  - ETL の結果を ETLResult で返却・ロギング
- データ品質チェック
  - 欠損データ、重複、スパイク、日付不整合の検出
- ニュース NLP（OpenAI）
  - news_nlp.score_news: 銘柄別ニュースから ai_scores を生成
  - regime_detector.score_regime: ETF 1321 の MA200 乖離とマクロセンチメントの合成による市場レジーム判定
  - JSON Mode を利用した堅牢なレスポンス検証とリトライ制御
- リサーチ
  - calc_momentum / calc_value / calc_volatility（prices_daily、raw_financials 参照）
  - forward returns / IC / factor summary / rank / zscore_normalize 等の統計ユーティリティ
- ニュース収集
  - RSS フィードから記事取得、前処理、raw_news へ冪等保存。SSRF 対策・トラッキング除去など
- 監査ログ
  - init_audit_schema / init_audit_db による監査テーブル初期化（UUID ベースのトレーサビリティ）

---

## 前提 / 必要環境

- Python >= 3.10（型アノテーションで | を利用しているため）
- 主要依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - （標準ライブラリ以外の詳細は setup.py / pyproject.toml を参照）

例（仮）:
pip install duckdb openai defusedxml

---

## セットアップ手順

1. リポジトリをクローン
   - git clone ... && cd your-repo

2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - もしくは最低限: pip install duckdb openai defusedxml

4. パッケージを編集可能モードでインストール（任意）
   - pip install -e .

5. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を用意すると自動で読み込まれます（priority: OS env > .env.local > .env）。
   - 自動ロードを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

推奨の基本環境変数（例）
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector 実行時に必要）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading のモック挙動）
- PAPER_TRADING_SQLITE_PATH: paper trading 用 SQLite（デフォルト: data/paper_trading.db）

.env.example をプロジェクトのルートに置くことを推奨します（README の例を参考に作成してください）。

---

## 使い方（簡単な例）

以下はライブラリ関数を直接使う簡単なコード例です。各コード例は Python スクリプト内で実行してください。

- DuckDB 接続を作る（ファイルパスは settings.duckdb_path に準拠）
  - import duckdb
  - from kabusys.config import settings
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  - from kabusys.data.pipeline import run_daily_etl
  - from datetime import date
  - result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  - print(result.to_dict())

- ニュースのセンチメントをスコアリング（OpenAI API キーが必要）
  - from kabusys.ai.news_nlp import score_news
  - from datetime import date
  - written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  - print(f"Scored {written} codes")

- 市場レジーム判定
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

- 監査ログ DB を初期化する（専用ファイル or :memory:）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")
  - # audit_conn を使って監査ログ操作を行う

- リサーチ関数の利用例
  - from kabusys.research.factor_research import calc_momentum
  - from datetime import date
  - records = calc_momentum(conn, target_date=date(2026, 3, 20))
  - # zscore_normalize を併用可能
  - from kabusys.data.stats import zscore_normalize
  - normalized = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意点:
- OpenAI 呼び出しを含む関数（score_news, score_regime）は api_key 引数、もしくは環境変数 OPENAI_API_KEY を参照します。
- 関数多くは外部 API 呼び出しに対してリトライを行い、失敗時はフェイルセーフ（ゼロ相当のフォールバック）で継続しますが、ログを確認してください。

---

## 推奨ワークフロー / 運用ヒント

- ETL はスケジューラ（cron / systemd timer / Airflow など）で日次実行する想定です。run_daily_etl は内部でカレンダーを取得し、営業日に合わせて差分取得を行います。
- OpenAI を利用するジョブはレートやコストに注意。バッチ実行（_BATCH_SIZE の設定）で効率化しています。
- テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使い、環境を明示的に制御してください。
- OpenAI 呼び出し箇所はテスト用に内部の _call_openai_api をモック差し替えできるよう設計されています（unittest.mock.patch 等）。

---

## 主なモジュール・ディレクトリ構成

（src/kabusys 配下の主要ファイル・モジュール）

- kabusys/
  - __init__.py
  - config.py               — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py           — ニュースセンチメント（銘柄別）
    - regime_detector.py    — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py     — J-Quants API クライアント（取得 & 保存）
    - pipeline.py           — ETL パイプライン / run_daily_etl / ETLResult
    - etl.py                — ETL の公開型再エクスポート
    - news_collector.py     — RSS 収集・前処理
    - calendar_management.py— 市場カレンダー判定 / 更新ジョブ
    - quality.py            — データ品質チェック
    - stats.py              — 汎用統計ユーティリティ
    - audit.py              — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py    — Momentum / Value / Volatility 計算
    - feature_exploration.py— forward returns / IC / rank / summary

各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り SQL と Python を組み合わせて処理します。バックテスト・リサーチ用途と本番の ETL / 発注ロジックは明確に分離されています。

---

## 開発・テスト

- OpenAI 呼び出しやネットワーク I/O 部分はモック可能に実装されています（ユニットテストで _call_openai_api や network 関数を patch）。
- 設定自動ロードの影響を避けるため、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定するか環境を明示的にセットしてください。

---

## 注意事項 / セキュリティ

- news_collector は SSRF 対策（ホストのプライベートアドレス判定、リダイレクト検査など）を行っていますが、実運用では追加のネットワーク制限やプロキシ設定を推奨します。
- OpenAI / J-Quants の API キーは機密情報です。リポジトリにハードコードしないでください。
- ETL や発注系処理の実行前に十分な検証を行ってください（特に live 環境）。

---

以上が簡易 README です。詳細な使用方法や API の引数、例は各モジュールの docstring を参照してください。必要であれば README にサンプル .env.example、より具体的なコード例、Docker / systemd 用の起動例を追記します。どの情報を追記しますか？