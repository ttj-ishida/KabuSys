# KabuSys — 日本株自動売買システム

KabuSys は日本株のデータ取得・品質管理・特徴量作成・AI を用いたニュース評価・市場レジーム判定・監査ログ管理までを含む自動売買プラットフォームのライブラリ群です。本リポジトリは主に次の用途を想定しています：データパイプライン（ETL）、データ品質チェック、ファクター研究、ニュースセンチメント評価（OpenAI）、市場レジーム判定、監査トレーサビリティ、および J-Quants / kabu ステーション など外部 API との連携。

下記は本コードベースに対する README（日本語）です。

目次
- プロジェクト概要
- 主な機能
- 要件
- セットアップ手順
- 環境変数（.env）と自動ロード
- 使い方（クイックスタート）
  - DuckDB 接続
  - 日次 ETL 実行
  - ニュースセンチメント評価
  - 市場レジーム判定
  - 監査 DB 初期化
  - リサーチ（ファクター計算・IC 等）
  - カレンダー関連ユーティリティ
- ディレクトリ構成（主要ファイル一覧）
- 補足 / 注意事項

---

プロジェクト概要
- 名前: KabuSys
- 目的: 日本株のデータ収集（J-Quants）、品質チェック、特徴量作成、AI によるニュース評価、マーケットレジーム判定、監査ログ管理、発注・約定フローの監査などを統合するライブラリ群。
- 設計方針:
  - ルックアヘッドバイアスを避ける（target_date を明示的に渡す、date.today() を内部で参照しない設計を優先）
  - DuckDB を主要データストアとして利用（クエリ + Python で処理）
  - 外部 API 呼び出しにはリトライ・レート制御・フェイルセーフを実装
  - ETL / 品質検査は冪等性を重視

主な機能
- データ ETL（J-Quants から株価・財務・カレンダーを取得、DuckDB に保存）
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- ニュース収集（RSS）と前処理／銘柄紐付け
- ニュース NLP（OpenAI を使った銘柄別センチメント算出 / ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA とマクロニュースの LLM センチメント合成）
- 研究（ファクター計算: momentum / value / volatility、forward returns、IC、統計サマリ）
- マーケットカレンダー管理（JPX カレンダーの差分取得、営業日の判定ユーティリティ）
- 監査ログ（signal → order_request → executions を追跡する監査スキーマの初期化・管理）
- J-Quants API クライアント（認証 / ページング / 保存関数 / レート制御）

要件
- Python 3.10+（型注釈に | を使用）
- 推奨ライブラリ（代表）:
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリ多数（urllib 等）を利用

（実際の requirements.txt はプロジェクトに合わせて用意してください）

セットアップ手順（開発環境）
1. リポジトリをクローンし、プロジェクトルートに移動
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成・有効化（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 依存パッケージをインストール
   （requirements.txt があれば）
   ```
   pip install -r requirements.txt
   ```
   最小限のパッケージ例:
   ```
   pip install duckdb openai defusedxml
   ```

4. パッケージを編集モードでインストール（オプション）
   ```
   pip install -e .
   ```

環境変数（.env）と自動ロード
- このプロジェクトはプロジェクトルート（.git または pyproject.toml のある位置）にある .env / .env.local を自動で読み込みます（kabusys.config）。
  - 読み込み順序（優先度）: OS 環境変数 > .env.local > .env
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します（テスト時など）。
- 必須環境変数（Settings により参照）
  - JQUANTS_REFRESH_TOKEN — J-Quants 用リフレッシュトークン（必須）
  - KABU_API_PASSWORD — kabu API（kabuステーション）パスワード（必須）
  - SLACK_BOT_TOKEN — Slack 通知用 Bot Token（必須）
  - SLACK_CHANNEL_ID — Slack チャネル ID（必須）
- オプション（デフォルト値あり）
  - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL — DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）
  - KABU_API_BASE_URL — kabu API の base URL（デフォルト http://localhost:18080/kabusapi）
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite パス（デフォルト data/monitoring.db）
- .env の書式は一般的な KEY=VALUE。コメントや export 形式も簡易対応します。

例: .env
```
JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

使い方（クイックスタート）
- 共通: DuckDB 接続の例
  ```python
  import duckdb
  from kabusys.config import settings

  # settings.duckdb_path は Path を返します（デフォルト data/kabusys.duckdb）
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

1) 日次 ETL の実行（J-Quants からデータ取得・保存・品質チェック）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # conn は上で作成した duckdb の接続
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```
  - run_daily_etl は market calendar → prices → financials の順に ETL を実行し、品質チェックをオプションで実行します。
  - J-Quants 認証は settings.jquants_refresh_token を使います。必要なら api トークンを引数で渡せます。

2) ニュースセンチメント評価（ai_scores へ書き込み）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OpenAI API Key が環境変数 OPENAI_API_KEY に設定されているか、api_key 引数で渡す
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)
  print(f"scored {count} codes")
  ```
  - score_news は raw_news / news_symbols を使用し、1 銘柄に対して最大記事数・文字数をトリムして LLM に送る。失敗はスキップして続行します。

3) 市場レジーム判定
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  res = score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```
  - ETF 1321 の 200 日 MA 乖離とマクロニュース（LLM）から regime_score と regime_label を生成し、market_regime テーブルへ冪等書き込みします。

4) 監査 DB の初期化（発注／約定ログ用）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```
  - init_audit_db は監査用テーブル群（signal_events / order_requests / executions）を作成します。TIMESTAMP を UTC 固定します。

5) リサーチ機能（ファクター計算など）
  ```python
  from datetime import date
  from kabusys.research import calc_momentum, calc_value, calc_volatility, zscore_normalize

  momentum = calc_momentum(conn, target_date=date(2026, 3, 20))
  volatility = calc_volatility(conn, target_date=date(2026, 3, 20))
  value = calc_value(conn, target_date=date(2026, 3, 20))

  # 正規化
  normalized = zscore_normalize(momentum, ["mom_1m", "mom_3m", "mom_6m", "ma200_dev"])
  ```

6) カレンダー関連ユーティリティ
  ```python
  from datetime import date
  from kabusys.data.calendar_management import is_trading_day, next_trading_day, get_trading_days

  d = date(2026, 3, 20)
  print(is_trading_day(conn, d))
  print(next_trading_day(conn, d))
  print(get_trading_days(conn, date(2026,3,1), date(2026,3,31)))
  ```

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py — パッケージ初期化, __version__ 等
  - config.py — 環境変数 / Settings 管理（.env 自動読み込みロジック）
  - ai/
    - __init__.py
    - news_nlp.py — ニュースセンチメント（OpenAI）→ ai_scores 書き込み
    - regime_detector.py — マーケットレジーム判定（1321 MA + マクロニュース LLM）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理、営業日判定等
    - pipeline.py — ETL パイプラインの実装（run_daily_etl 他）
    - etl.py — ETLResult の公開（エクスポート）
    - jquants_client.py — J-Quants API クライアント（取得／保存関数）
    - news_collector.py — RSS 収集・前処理・raw_news 保存（SSRF／サイズ制限などの保護あり）
    - quality.py — データ品質チェック（欠損・重複・スパイク・日付不整合）
    - stats.py — zscore_normalize 等の統計ユーティリティ
    - audit.py — 監査テーブル DDL / 初期化 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py — momentum / value / volatility を計算
    - feature_exploration.py — forward returns / IC / factor summary / rank 等
  - research モジュールは data.stats を利用してファクター処理・正規化を行います。

補足 / 注意事項
- OpenAI / J-Quants リクエストには API キー・トークンが必要です。API の使用は各サービスの利用規約に従ってください。
- 自動ロードされる .env はプロジェクトルートにある場合に読み込まれます。CI / テスト時に自動読み込みを止めたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 側のテーブルスキーマ（raw_prices, raw_financials, market_calendar, raw_news, news_symbols, ai_scores, market_regime, など）はプロジェクトの別スクリプト／マイグレーションで定義することを想定しています。ETL / 保存関数は ON CONFLICT DO UPDATE など冪等性を考慮して実装されていますが、利用前にスキーマの準備が必要です。
- 外部ネットワークアクセス（RSS 取得、J-Quants、OpenAI）はネットワーク障害やレート制限に備えたリトライ・バックオフ処理が組み込まれていますが、プロダクション運用での監視と適切なエラーハンドリングを推奨します。
- KABUSYS_ENV は実行モード（development / paper_trading / live）を切り替えます。live モードでは本番発注等の保護ロジックを有効化する想定です（実装側でチェックしてください）。

貢献 / ライセンス
- プロジェクトに貢献する場合は、まず Issue を立ててください。Pull Request は小さな単位でわかりやすく。
- ライセンス情報はリポジトリの LICENSE を参照してください（ここには含めていません）。

---
必要に応じて README に手を加え、実行用スクリプトや docker-compose、requirements.txt、データベーススキーマ定義ファイルなどを追加してください。README の補強（例: SQL スキーマ、サンプル .env.example、実運用の注意点）を望む場合は、その内容を指定してください。