# KabuSys

日本株向けの自動売買・データ基盤ライブラリです。J-Quants / JPX / RSS / kabuステーション 等を統合し、
ETL、データ品質チェック、ニュース NLP（LLM によるセンチメント）、市場レジーム判定、研究用ファクター計算、
監査ログ（トレーサビリティ）の機能を提供します。

主にバックエンドバッチやリサーチ環境で利用することを想定しています。

---

## 特徴（機能一覧）

- データ取得・ETL
  - J-Quants から株価日足・財務データ・市場カレンダーを差分取得・保存（ページネーション / 冪等保存）
  - ETL の日次パイプライン（run_daily_etl）
- ニュース収集 / 前処理
  - RSS 取得、URL 正規化、記事ID生成、raw_news への冪等保存
  - SSRF や gzip bomb 等の安全対策を備えた実装
- ニュース NLP（LLM）
  - gpt-4o-mini を用いた銘柄ごとのセンチメントスコア算出（score_news）
  - マクロニュースから市場センチメントを計算し、ETF（1321）の MA 乖離と合成して市場レジーム判定（score_regime）
  - API リトライ / バックオフ / レスポンスバリデーションを実装
- 研究（Research）ユーティリティ
  - モメンタム、ボラティリティ、バリュー系ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン計算、IC（Information Coefficient）、ファクター統計サマリー等
  - Z スコア正規化ユーティリティ
- データ品質チェック
  - 欠損、重複、日付不整合、スパイク検出（run_all_checks）
- 市場カレンダー管理
  - market_calendar テーブルを参照した営業日判定・前後営業日の取得等
- 監査ログ（Audit）
  - signal / order_request / execution を追跡する監査スキーマの初期化（init_audit_schema / init_audit_db）
- 設定管理
  - .env/.env.local 自動読み込み（プロジェクトルート検出）、環境変数ラッパー（kabusys.config.settings）
- 安全設計・運用配慮
  - ルックアヘッドバイアス対策（date.today() を直接参照しない実装方針）
  - 冪等性（ON CONFLICT DO UPDATE 等）、タイムスタンプは UTC 保存想定
  - ネットワーク／API に対する堅牢なエラーハンドリング

---

## 必要条件

- Python 3.10+
- 主な依存パッケージ（抜粋）
  - duckdb
  - openai（OpenAI SDK）
  - defusedxml
  - （標準ライブラリのみで実装されている機能も多数）

実際のセットアップでは pyproject.toml / requirements.txt に従ってください。

---

## 環境変数（主なもの）

以下は本プロジェクトで参照される代表的な環境変数です（Settings クラスによって取得されます）。

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabuステーション API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: Monitoring 用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト development）
- LOG_LEVEL: ログレベル ("DEBUG" | "INFO" | ...)

自動 .env ロード:
- パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml の存在）を探索し、`.env` と `.env.local` を順序に応じて読み込みます。
- 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## インストール（開発向け）

例）ローカルで editable インストールする場合:

1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml

   （プロジェクトに requirements / pyproject があればそれに従ってください）
3. パッケージをインストール（開発用）
   - pip install -e .

---

## セットアップ手順（基本）

1. リポジトリをクローンし、プロジェクトルートに移動
2. 必要な環境変数を .env に設定（.env.example を参照して作成）
   - 例:
     JQUANTS_REFRESH_TOKEN=...
     OPENAI_API_KEY=...
     SLACK_BOT_TOKEN=...
     SLACK_CHANNEL_ID=...
3. DuckDB データベースファイルの配置先ディレクトリを作成（必要に応じて）
   - デフォルトは data/kabusys.duckdb
4. 必要な外部サービス（J-Quants・OpenAI・kabuステーション等）のアクセス情報を準備

---

## 使い方（簡単な例）

以下は主要なユースケースのサンプルです。実稼働ではログ設定や例外処理、環境の分離に注意してください。

- DuckDB 接続の作成（例）:

  from datetime import date
  import duckdb
  conn = duckdb.connect('data/kabusys.duckdb')

- 日次 ETL の実行（run_daily_etl）:

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメント（LLM）で銘柄ごとのスコアを作成（score_news）:

  from kabusys.ai.news_nlp import score_news
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")

  ※ OPENAI_API_KEY は環境変数か api_key 引数で渡します。

- 市場レジーム判定（score_regime）:

  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key は env か引数で

- 監査ログ用 DuckDB 初期化:

  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/kabusys_audit.duckdb")
  # テーブルが初期化された接続を返す

- Settings を使った設定参照:

  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

---

## 実装上の注意・設計方針

- ルックアヘッドバイアス回避:
  - モジュールの多くは内部で date.today() に依存せず、処理対象日（target_date）を明示的に受け取る設計。
- 冪等性:
  - ETL 保存処理は ON CONFLICT DO UPDATE 等で冪等に実装。
- API 安全 / 信頼性:
  - リトライ（指数バックオフ）、レート制御（J-Quants は 120 req/min 固定間隔スロットリング）を実装。
  - OpenAI 呼び出しはエラー時にフォールバックやリトライを行い、失敗時は安全値（例: macro_sentiment=0）で継続する設計。
- セキュリティ:
  - RSS 収集では SSRF 対策、gzip/サイズ制限、XML の defusedxml を利用。
- テストしやすさ:
  - OpenAI 呼び出しなどは内部のヘルパーをモック可能に設計。

---

## ディレクトリ構成（主要ファイル）

以下は主要なモジュール・ファイルのツリーです（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     -- 環境変数/設定管理
    - ai/
      - __init__.py
      - news_nlp.py                 -- ニュース NLP（score_news）
      - regime_detector.py          -- 市場レジーム判定（score_regime）
    - data/
      - __init__.py
      - jquants_client.py           -- J-Quants API クライアント + 保存
      - pipeline.py                 -- ETL パイプライン（run_daily_etl 等）
      - etl.py                      -- ETL インターフェース（ETLResult 再エクスポート）
      - news_collector.py           -- RSS ニュース収集
      - calendar_management.py      -- 市場カレンダー管理
      - stats.py                    -- 統計ユーティリティ（zscore）
      - quality.py                  -- データ品質チェック
      - audit.py                    -- 監査ログスキーマ初期化
    - research/
      - __init__.py
      - factor_research.py          -- ファクター計算（momentum/value/volatility）
      - feature_exploration.py      -- 将来リターン / IC / 統計サマリー
    - research/...（その他ユーティリティ）
    - ...（その他モジュール）

---

## よくある運用フロー（例）

1. 夜間バッチ（Cron / Airflow 等）で:
   - run_daily_etl を実行して市場カレンダー・株価・財務を更新
   - run_all_checks でデータ品質確認
2. ニュース収集ジョブで RSS を定期取得して raw_news を更新
3. 毎朝（ETL の後）score_news を回して銘柄ごとの AI スコアを更新
4. 毎営業日、市場レジーム（score_regime）を算出して戦略チューニングに利用
5. 監査ログテーブル（order_requests / executions 等）を用いて発注フローをトレース

---

## サポート / 追加情報

- コード内には設計方針・注意点が詳細にコメントされています。実装や運用ルールはコメントを参照してください。
- 実運用・リアルマネーでの利用時はリスク管理（発注ロジックの検証・ドライラン）を十分に行ってください。

---

以上。README に追加したいサンプルや具体的な実行コマンド（CI / systemd / Airflow の設定例など）があれば教えてください。必要に応じてREADME を拡張します。