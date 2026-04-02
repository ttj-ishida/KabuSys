# KabuSys

日本株向けのデータ基盤・リサーチ・自動売買支援ライブラリ群です。  
ETL（J-Quants からのデータ取得）・ニュース収集・ニュース NLP（LLM）によるセンチメント評価・市場レジーム判定・ファクター計算・監査ログ（発注トレーサビリティ）など、バックテスト〜運用に必要な主要コンポーネントを含みます。

注意：本リポジトリのコードは取引所や証券会社への実際の発注を行うための最終実装ではありません。実運用では追加の安全対策・テスト・承認が必須です。

---

## 特徴（機能一覧）

- データ収集 / ETL
  - J-Quants API からの株価（OHLCV）・財務データ・JPX カレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（INSERT ... ON CONFLICT DO UPDATE）
  - ETL の品質チェック（欠損・スパイク・重複・日付不整合検出）
- ニュース処理
  - RSS 取得と前処理（URL 正規化・トラッキングパラメータ除去・SSRF 対策）
  - raw_news の保存と銘柄紐付け
- ニュース NLP（LLM）
  - 銘柄ごとのニュースをまとめて LLM（gpt-4o-mini 等）でセンチメント評価して ai_scores に保存
  - チャンク／バッチ処理、リトライ、レスポンスバリデーションを実装
- 市場レジーム判定
  - ETF 1321（225 連動型）の 200 日移動平均乖離とマクロニュースの LLM センチメントを組み合わせて bull/neutral/bear を判定
- 研究用ユーティリティ
  - ファクター計算（Momentum / Value / Volatility 等）
  - 将来リターン計算、IC（Information Coefficient）や統計サマリー
  - Z スコア正規化ユーティリティ
- 監査（Audit）テーブル
  - signal_events, order_requests, executions 等の監査スキーマ（監査ログ・トレーサビリティ）
  - 監査 DB の初期化ユーティリティ
- 設定管理
  - .env（および .env.local）から環境変数を自動読み込み（プロジェクトルート判定）
  - 必須環境変数の取り纏め（settings オブジェクト）

---

## 要件

- Python 3.10 以上（型ヒントで | 演算子を使用しているため）
- 主要依存パッケージ（抜粋）
  - duckdb
  - openai (OpenAI Python SDK)
  - defusedxml
- 標準ライブラリの urllib、json、logging 等を使用

（必要に応じて他パッケージを追加してください。requirements.txt を用意している場合はそちらを参照してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # macOS / Linux
   - .venv\Scripts\activate     # Windows (PowerShell 等)

3. 必要パッケージのインストール（最低限）
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml

   ※ 実運用では依存バージョンを固定した requirements.txt や Poetry / pip-tools を使うことを推奨します。

4. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml があるディレクトリ）に `.env`（および必要なら `.env.local`）を置くと自動読み込みされます。自動読み込みを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   サンプル（.env）:
   - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>
   - KABU_API_PASSWORD=<kabu_api_password>
   - SLACK_BOT_TOKEN=<slack_bot_token>
   - SLACK_CHANNEL_ID=<slack_channel_id>
   - OPENAI_API_KEY=<openai_api_key>
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development
   - LOG_LEVEL=INFO

   必須（コード内で _require() によって参照される）:
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - SLACK_BOT_TOKEN
   - SLACK_CHANNEL_ID

   LLM を使う場合:
   - OPENAI_API_KEY を設定するか、各関数の api_key 引数で渡してください。

5. データディレクトリの作成（必要に応じて）
   - mkdir -p data

---

## 使い方（主要ユースケース）

以下は Python REPL やスクリプト内での簡単な利用例です。

- DuckDB 接続を作る（デフォルトパスを利用）
  - from kabusys.config import settings
  - import duckdb
  - conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する（J-Quants から差分取得 → 保存 → 品質チェック）
  - from kabusys.data.pipeline import run_daily_etl
  - from kabusys.config import settings
  - result = run_daily_etl(conn, target_date=None, id_token=None)
  - print(result.to_dict())

- ニュースセンチメントスコアを生成（ai_scores に保存）
  - from datetime import date
  - from kabusys.ai.news_nlp import score_news
  - n = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # api_key が None の場合環境変数 OPENAI_API_KEY を使用

- 市場レジーム判定（market_regime テーブルへ保存）
  - from kabusys.ai.regime_detector import score_regime
  - from datetime import date
  - score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- 監査ログ DB の初期化（監査専用 DB）
  - from kabusys.data.audit import init_audit_db
  - audit_conn = init_audit_db("data/audit.duckdb")  # :memory: も可

- 研究用ファクター計算
  - from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  - res = calc_momentum(conn, target_date=date(2026, 3, 20))

- 設定オブジェクト（便利な参照）
  - from kabusys.config import settings
  - settings.duckdb_path  # Path オブジェクト
  - settings.is_live, settings.log_level  # etc.

実例スクリプト（簡易）:
- python -c "from datetime import date; import duckdb; from kabusys.config import settings; from kabusys.data.pipeline import run_daily_etl; conn=duckdb.connect(str(settings.duckdb_path)); print(run_daily_etl(conn, date.today()).to_dict())"

---

## ディレクトリ構成

主要ファイルのみ抜粋（src/kabusys 下）

- kabusys/
  - __init__.py
  - config.py                           # 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                       # ニュースを LLM でスコアリング
    - regime_detector.py                # 市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py            # マーケットカレンダー管理
    - etl.py                            # ETL の再エクスポート (ETLResult)
    - pipeline.py                       # ETL パイプライン
    - stats.py                          # 統計ユーティリティ (zscore_normalize)
    - quality.py                        # データ品質チェック
    - audit.py                          # 監査ログスキーマ / 初期化
    - jquants_client.py                 # J-Quants API クライアント（取得 + DuckDB 保存）
    - news_collector.py                 # RSS ニュース収集
  - research/
    - __init__.py
    - factor_research.py                # ファクター計算（Momentum, Value, Volatility）
    - feature_exploration.py            # 将来リターン, IC, 統計サマリー

---

## 実装上の注意点 / 設計方針（概略）

- Look-ahead bias 回避
  - date.today() / datetime.today() の直接参照を極力避け、target_date を明示的に渡す設計。
  - DB クエリで date < target_date のような排他条件により未来データ参照を防止。
- 冪等性
  - J-Quants からの保存は ON CONFLICT DO UPDATE を使用し冪等化。
  - 監査ログでは order_request_id を冪等キーとして扱う。
- フェイルセーフ設計
  - LLM/API の一時障害時は安全側のデフォルト（0.0 など）で継続する設計。
  - ETL は各ステップで例外をキャッチして処理継続し、結果オブジェクトにエラー情報を蓄積。
- セキュリティ対策（ニュース収集）
  - SSRF 対策・リダイレクト検査・プライベートアドレス検出・受信サイズ制限・defusedxml を使用。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabu API パスワード（必須）
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN — Slack ボットトークン（必須）
- SLACK_CHANNEL_ID — Slack チャンネル ID（必須）
- OPENAI_API_KEY — OpenAI API キー（LLM を使う場合）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル（DEBUG|INFO|WARNING|ERROR|CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 をセットすると .env 自動読み込みを無効化

---

## 開発者向けメモ

- テスト可能性
  - AI モジュール内の API 呼び出しは小さなラッパー関数になっており、テスト時に patch / mock しやすい設計です（例: news_nlp._call_openai_api を差し替え）。
- トランザクション管理
  - 重要な書き込みは BEGIN / DELETE / INSERT / COMMIT パターンで冪等性と整合性を担保しています。DuckDB の executemany の挙動（空リスト不可）などの実装考慮があります。
- ロギング
  - 各モジュールは logger を使用して処理状況・警告・エラーを出力します。LOG_LEVEL で制御してください。

---

問題・改善提案・バグ報告があれば issue を作成してください。README に載せる追加の利用例や運用手順（cron / systemd / Docker 化など）をご希望であれば教えてください。