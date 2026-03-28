# KabuSys

日本株向け自動売買基盤（データプラットフォーム・リサーチ・AI支援・監査ログ・ETL等を含む）です。本リポジトリは、J-Quants / kabuステーション / OpenAI 等と連携してデータ取得・前処理・特徴量計算・ニュースセンチメント評価・市場レジーム判定・監査ログの機能を提供します。

## 主な特徴
- データ取得（J-Quants API から株価・財務・カレンダー等を差分取得）
- ETL パイプライン（差分取得、DB 保存、品質チェック）
- ニュース収集（RSS → raw_news、SSRF / サイズ制限 / トラッキング除去）
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価、ai_scores へ保存）
- 市場レジーム判定（ETF 1321 の MA 乖離 + マクロニュースを統合して 'bull/neutral/bear' 判定）
- ファクター計算・研究用ツール（モメンタム、バリュー、ボラティリティ、将来リターン、IC 等）
- 監査ログ（シグナル → 注文 → 約定のトレーサビリティを保つ監査テーブル）
- DuckDB を中心としたローカルデータ管理（冪等保存・トランザクション制御等）

---

## 必要条件（環境）
- Python 3.10+
- 必須 Python パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード等）

（プロジェクトで使用する実際の requirements.txt はリポジトリに合わせて用意してください。）

---

## 環境変数 / .env

config.Settings で参照する主要な環境変数は以下です（README 用の簡易例）。

- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabuAPI ベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack Bot トークン（必須）
- SLACK_CHANNEL_ID: 通知先 Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / regime_detector で使用）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" / "paper_trading" / "live")（デフォルト: development）
- LOG_LEVEL: ログレベル ("DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL")（デフォルト: INFO）

自動で .env ファイルをプロジェクトルートから読み込みます（優先順位: OS 環境変数 > .env.local > .env）。自動ロードを無効化するには環境変数を設定します：
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1

簡易 .env.example（実運用ではシークレットを公開しないでください）:
KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか、.env/.env.local に以下を設定します。

例:
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repository-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実運用では requirements.txt / pyproject.toml に従ってインストールしてください。

4. 環境変数を設定（.env をプロジェクトルートに作成）
   - 上述の環境変数を .env / .env.local に設定

5. DuckDB 用ディレクトリ作成（必要に応じて）
   - mkdir -p data

---

## 使い方（代表的な呼び出し例）

以下は Python REPL / スクリプトでのサンプルです。各関数は duckdb の接続を受け取ります。

- DuckDB 接続例（ファイルベース）:
  from pathlib import Path
  import duckdb
  conn = duckdb.connect(str(Path("data/kabusys.duckdb")))

- 日次 ETL を実行（カレンダー・株価・財務の差分取得 + 品質チェック）
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に書き込む
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} symbols")

  ※ score_news は OPENAI_API_KEY を環境変数から読む（引数 api_key でも指定可）。

- 市場レジームを判定して market_regime に書き込む
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20))

  ※ OpenAI の API キーは環境変数 OPENAI_API_KEY または引数 api_key で指定可能。

- 監査ログ用 DB を初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  # これで監査テーブル(signal_events, order_requests, executions) が作成されます

- 設定値取得（コード内での使用例）
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)

---

## よく使うモジュール（概要）
- kabusys.config
  - .env / 環境変数読み込み、Settings クラス（認証トークン・DB パス・環境フラグ等）
- kabusys.data
  - pipeline.py: ETL メイン処理（run_daily_etl 等）
  - jquants_client.py: J-Quants API との通信・保存ロジック
  - news_collector.py: RSS 取得と raw_news 保存
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - audit.py: 監査テーブル定義と初期化ユーティリティ
  - stats.py: zscore 正規化 等のユーティリティ
- kabusys.ai
  - news_nlp.py: ニュースセンチメント評価（銘柄別）
  - regime_detector.py: ETF MA とマクロニュースを統合した市場レジーム判定
- kabusys.research
  - factor_research.py: モメンタム / ボラティリティ / バリュー 等のファクター計算
  - feature_exploration.py: 将来リターン計算 / IC / 統計サマリー 等

---

## ディレクトリ構成（主要部分）
- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - data/
    - __init__.py
    - jquants_client.py
    - pipeline.py
    - etl.py
    - news_collector.py
    - calendar_management.py
    - quality.py
    - stats.py
    - audit.py
    - pipeline.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - research/ 以下にファクター計算・解析ツール

（実際のリポジトリでは tests/、docs/、scripts/ などの補助ディレクトリが存在する可能性があります）

---

## 注意事項 / 運用上のポイント
- OpenAI・J-Quants など外部 API の使用は課金・レート制限があるため注意してください。jquants_client と AI モジュールはリトライ・バックオフ処理を実装していますが、実運用ではレート配慮が必要です。
- 本コードはルックアヘッドバイアス防止に配慮して設計されています（target_date 未満データのみを参照する等）。バックテストや運用時は仕様をよく理解して使用してください。
- .env に機密情報を置く場合は権限管理・シークレット管理（Vault 等）を検討してください。
- DuckDB の executemany の制約（空リスト不可等）やタイムゾーン扱い（UTC 保存）等、実装上の注意点があります。ログや警告メッセージを参考にしてください。

---

## 貢献 / ライセンス
- 貢献方法、コードスタイル、テストの実行方法は別途 CONTRIBUTING.md を参照してください（なければ issue/pull request を通じてご相談ください）。
- ライセンスはリポジトリの LICENSE ファイルを参照してください。

---

README の内容はコードベースの主要点をまとめています。追加で開発者向けのセットアップ手順（unit tests、ローカルモックサービス、CI 設定等）や運用向けの runbook を用意すると利用しやすくなります。必要であればサンプル .env.example やコマンドのテンプレートも作成します。どの部分を詳しく載せたいか教えてください。