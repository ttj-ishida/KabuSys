# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
市場データ収集（J-Quants）、ニュース収集・NLP、ファクター計算、ETL、監査ログなどを含むモジュール群を提供します。

主な用途:
- J-Quants からの株価・財務・カレンダーの差分 ETL
- RSS ニュース収集と LLM を用いたニュースセンチメント付与
- 日次の市場レジーム判定（MA + マクロニュースの LLM 評価）
- ファクター計算・リサーチユーティリティ
- 監査ログ（シグナル → 発注 → 約定トレース）テーブル初期化・管理
- データ品質チェック

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API との通信、ページネーション、保存（DuckDB へ冪等保存）
  - pipeline / etl: 日次 ETL（calendar / prices / financials）の差分更新エントリポイント
  - news_collector: RSS 収集、SSRF対策、テキスト前処理、raw_news への保存補助
  - quality: データ品質チェック（欠損、スパイク、重複、日付不整合）
  - calendar_management: JPX カレンダー管理・営業日判定ユーティリティ
  - audit: 監査ログ（signal_events, order_requests, executions）スキーマ作成・初期化
  - stats: 汎用統計ユーティリティ（Zスコア正規化 等）
- ai
  - news_nlp.score_news: ニュースを銘柄別に集約し LLM でセンチメントを算出・ai_scores へ保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュース LLM スコアを合成して market_regime に保存
- research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC（Spearman）, ランク/統計サマリー
- config
  - Settings: 環境変数・.env 自動読み込み（プロジェクトルート検出）、必須値の検査

---

## 動作要件

- Python 3.10+
- 必要なライブラリ（例）
  - duckdb
  - openai
  - defusedxml

実行環境により他ライブラリ（例: typing_extensions 等）が必要になる場合があります。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン（例）
   git clone <repo-url>
2. 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
3. 依存パッケージをインストール
   pip install duckdb openai defusedxml
   # パッケージをプロジェクトとしてインストールする場合
   pip install -e .

4. 環境変数の設定
   プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を置くと自動で読み込まれます（起動時に KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると無効化可）。

   例（.env）:
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db

   ※ 必須:
   - JQUANTS_REFRESH_TOKEN
   - OPENAI_API_KEY（ai モジュールを使う場合）
   - KABU_API_PASSWORD（kabu ステーション連携を追加する場合）
   - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（Slack 通知を使う場合）

5. データディレクトリを作成
   mkdir -p data

---

## 使い方（例）

以下は代表的な利用例です。DuckDB 接続はライブラリの関数に直接渡します。

- 基本的な ETL（日次パイプライン）
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュース NLP スコア付与（特定日）
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {written} codes")

- 市場レジーム判定（MA + マクロニュース）
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化（監査専用 DB を作る）
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # conn は初期化済みの DuckDB 接続

- ファクター / リサーチユーティリティ
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value
  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))

注意点:
- モジュール設計上、内部では datetime.today()/date.today() を安易に参照せず、target_date を明示的に渡すことでルックアヘッドバイアスを避けています。バックテスト用途では target_date を明示的に指定してください。
- OpenAI 呼び出しは OpenAI の Python SDK を利用しており、APIキーは関数引数経由または環境変数 `OPENAI_API_KEY` で指定可能です。API エラー時はフェイルセーフで継続する設計の箇所が多くあります（ログ出力して 0.0 を返す等）。

---

## 環境変数一覧（主要）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必須 for AI) — OpenAI API キー
- KABU_API_PASSWORD — kabu ステーション API パスワード
- KABU_API_BASE_URL — kabu API ベース URL (デフォルト: http://localhost:18080/kabusapi)
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID — Slack 通知に利用
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV — development / paper_trading / live (デフォルト: development)
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL (デフォルト: INFO)
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env の自動ロードを無効化

設定は .env ファイルあるいは OS の環境変数で行えます。パーサはシェルの `export KEY=val` 形式やクォート付き値、行末コメントなどに対応しています。

---

## ディレクトリ構成

リポジトリは src レイアウトの Python パッケージ構成です（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                   — 環境設定読み込みと Settings
    - ai/
      - __init__.py
      - news_nlp.py               — ニュースセンチメント（LLM）
      - regime_detector.py        — 市場レジーム判定（MA200 + マクロLLM）
    - data/
      - __init__.py
      - jquants_client.py         — J-Quants API クライアント & DuckDB 保存
      - pipeline.py               — ETL パイプライン（run_daily_etl 等）
      - etl.py                    — ETLResult 再エクスポート
      - news_collector.py         — RSS 収集・前処理
      - quality.py                — データ品質チェック
      - calendar_management.py    — マーケットカレンダー管理 / 営業日判定
      - stats.py                  — 汎用統計ユーティリティ
      - audit.py                  — 監査ログスキーマの初期化
    - research/
      - __init__.py
      - factor_research.py        — Momentum/Volatility/Value 等
      - feature_exploration.py    — forward returns / IC / rank / summary
    - ai/                        — AI 関連（既出）
    - research/                  — リサーチ関連（既出）
    - ...（将来的に strategy, execution, monitoring 等のパッケージが想定される）

---

## 開発・テストについて

- OpenAI 呼び出しや外部 API はモックが容易になるように内部で呼び出し関数を分離しています（テスト時は該当関数を patch して差し替え可能）。
- .env の自動読み込みは Settings モジュールで行われます。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して無効化できます。

---

## 注意事項 / 運用上の考慮

- 本コードは実際の売買を伴うモジュール設計を想定しています。実環境で稼働させる際は十分なテストとリスク管理（発注の冪等性・監査ログ・SLACK 通知等）を行ってください。
- OpenAI や J-Quants 等の API レート制限・課金、認証トークンの取り扱いには注意してください。
- DuckDB の executemany の仕様（空リスト不可など）や SQL の互換性を考慮した実装が含まれています。DuckDB のバージョンとの互換性テストを推奨します。

---

README に記載のない機能や追加の使い方、CI 設定、サンプル ETL ジョブなどが必要であれば教えてください。利用ケースに合わせた README の拡張やサンプルスクリプト作成を支援します。