# KabuSys

日本株向け自動売買 / 研究プラットフォームのコアライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集とLLMベースのニュースセンチメント、ファクター計算、監査ログなどの機能を提供します。

主な設計方針：
- ルックアヘッドバイアス（未来情報参照）を防ぐ実装
- DuckDB を中心としたローカルデータストア
- 冪等性（ETL/保存処理）の確保
- ネットワーク / API 呼び出しに対するリトライとフェイルセーフ
- セキュリティ配慮（RSS の SSRF 対策、XML の安全パース等）

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）と必須環境変数取得
- データ取得・ETL（J-Quants）
  - 日足（OHLCV）取得・保存（ページネーション対応、レート制御、トークン自動リフレッシュ）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複チェック、日付整合性チェック
- ニュース収集 / NLP
  - RSS フィード収集（SSRF 対策、gzip / サイズチェック）
  - ニュースを銘柄に紐付け raw_news に保存
  - OpenAI（gpt-4o-mini 等）を用いた銘柄別ニュースセンチメント（ai_scores）
  - マクロニュースを組み合わせた市場レジーム判定（bull / neutral / bear）
- 研究用ユーティリティ
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions テーブル定義と初期化ユーティリティ
- ユーティリティ
  - 汎用統計関数、日付（営業日）管理、jquants クライアントなど

---

## 動作環境（推奨）

- Python 3.10+
- 必須ライブラリ（主なもの）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API、RSS、OpenAI）

実際の `requirements.txt` / packaging はプロジェクト側で用意してください。

---

## セットアップ手順

1. リポジトリをクローン / パッケージをインストール
   - 開発環境では pip の editable インストールなどを利用してください。
     - 例: pip install -e .

2. Python パッケージの依存関係をインストール
   - 例:
     - pip install duckdb openai defusedxml

3. 環境変数の設定
   - プロジェクトルートに `.env`（および必要に応じて `.env.local`）を作成します。
   - 主な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN - J-Quants のリフレッシュトークン（必須）
     - OPENAI_API_KEY - OpenAI の API キー（必須 for NLP）
     - KABU_API_PASSWORD - kabuステーション API パスワード（発注連携時）
     - KABU_API_BASE_URL - kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - SLACK_BOT_TOKEN - Slack 通知用 Bot Token（必要に応じて）
     - SLACK_CHANNEL_ID - Slack チャンネル ID（必要に応じて）
     - DUCKDB_PATH - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH - 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV - environment: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL - ログレベル（DEBUG/INFO/...）
   - 注意: パッケージ起動時に自動で `.env` / `.env.local` を読み込みます。自動読み込みを無効化する場合は
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. データディレクトリを作成
   - デフォルト設定では `data/` 配下に DB ファイルが置かれます。必要に応じてディレクトリを作ってください。
     - mkdir -p data

---

## 使い方（主なユースケース）

以下は Python REPL やスクリプトから呼び出す簡単な例です。

- DuckDB 接続を作成して日次 ETL を実行する
  - 目的: 株価 / 財務 / カレンダーを差分取得してローカル DB に保存、品質チェックを実行します。
  - 例:
    ```python
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())
    ```

- ニュースセンチメントのスコアを取得して ai_scores に書き込む
  - 事前に raw_news / news_symbols が存在すること、OPENAI_API_KEY が設定されていることを確認。
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {written}")
    ```

- 市場レジーム（マクロ + MA200 乖離）をスコアリングする
  - OpenAI API キーが必要です（引数で渡すか OPENAI_API_KEY を設定）。
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))
    ```

- 監査ログ DB の初期化
  - 監査用の DuckDB を初期化して接続を受け取ります。
  - 例:
    ```python
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # 以後、order_requests / signal_events / executions テーブルを利用できます
    ```

- 研究用ファクター計算（例: モメンタム）
  - 例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum
    from kabusys.config import settings

    conn = duckdb.connect(str(settings.duckdb_path))
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # records は [{ "date": ..., "code": "...", "mom_1m": ..., ...}, ...]
    ```

注意点:
- すべての公開 API はルックアヘッドバイアスを避けるため、内部で date.today() を安易に参照しない設計になっています。呼び出し側で target_date を明示的に与えることを推奨します。
- OpenAI 呼び出しや外部 API はリトライ/バックオフ処理を内包しますが、APIキーやレート制限には注意してください。

---

## 主要モジュールとディレクトリ構成

（src/kabusys 以下の主要ファイルを抜粋）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・settings オブジェクト
  - ai/
    - __init__.py (score_news をエクスポート)
    - news_nlp.py
      - news の収集ウィンドウ計算、OpenAI 呼び出し、ai_scores に保存
    - regime_detector.py
      - MA200 とマクロニュースを合成して market_regime に書き込み
  - data/
    - __init__.py
    - pipeline.py
      - ETL 実行のメインロジック（run_daily_etl 等）
    - jquants_client.py
      - J-Quants API クライアント（fetch / save / 認証 / レート制御）
    - news_collector.py
      - RSS 収集、前処理、raw_news 保存（SSRF・XML対策あり）
    - calendar_management.py
      - market_calendar を用いた営業日ロジック（is_trading_day, next_trading_day 等）
    - quality.py
      - データ品質チェック（欠損・スパイク・重複・日付不整合）
    - stats.py
      - z-score 正規化などのユーティリティ
    - etl.py
      - ETLResult の公開再エクスポート
    - audit.py
      - 監査ログテーブルの DDL と初期化ユーティリティ
  - research/
    - __init__.py
    - factor_research.py
      - モメンタム / ボラティリティ / バリュー等のファクター計算
    - feature_exploration.py
      - 将来リターン、IC、統計サマリー等

注: パッケージ内には strategy / execution / monitoring といったモジュール名が想定されていますが（__all__ 等）、ここに示したファイルはコードベースの代表です。実運用向けの戦略・注文実行ロジックは別途実装してください。

---

## 環境変数（.env）サンプル

例（.env または .env.local）:

JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-...
KABU_API_PASSWORD=your_kabu_password
KABU_API_BASE_URL=http://localhost:18080/kabusapi
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO

.env の読み込みポリシー:
- プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` → `.env.local` の順で読み込みます。
- OS 環境変数が優先されます。`.env.local` は `.env` を上書きします。
- 自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テストなどで利用）。

---

## 実装上の注意 / 監査

- ETL / 保存処理は可能な限り冪等 (ON CONFLICT DO UPDATE / DO NOTHING 等) を採用しています。
- ニュース収集では SSRF と XML 攻撃対策、受信サイズ制限など安全考慮を入れています。
- OpenAI 呼び出しは JSON mode を想定し、レスポンスのバリデーション・リトライを実装しています。API のバージョン・挙動に依存するため運用時は注意してください。
- market_calendar が未取得の場合は曜日ベースのフォールバックを使い、各日付関数は一貫性を保つよう設計されています。

---

この README はコードベースの主要な使い方と設計意図の要約です。実際に運用する際は .env の管理（シークレット保護）、API レート制御の監視、OpenAI/J-Quants の利用規約順守、テスト・監視の実装を行ってください。