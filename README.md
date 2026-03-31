# KabuSys

日本株のデータプラットフォームと自動売買補助ライブラリ群です。  
ETL（J-Quants からのデータ取り込み）、ニュース収集・NLP（OpenAI）、ファクター計算、研究用解析、監査ログ／発注監査スキーマなどを含みます。

主な用途：データ取得・品質管理・特徴量生成・ニュースベースのスコアリング・市場レジーム判定・監査ログ初期化など。  
（実際の発注ロジックやブローカー連携の層は別途実装する想定です）

---

## 機能一覧（モジュール別の概要）

- config
  - 環境変数・.env 自動読み込み、アプリ設定取得（J-Quants / kabu / Slack / DB パス /閾値など）
  - 自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に `.env` / `.env.local` を読み込み  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化

- data
  - jquants_client: J-Quants API クライアント（認証・レート制御・リトライ・ページネーション・DuckDB への保存）
  - pipeline / etl: 日次 ETL パイプライン（カレンダー・株価・財務の差分取得、品質チェック）
  - calendar_management: JPX カレンダー管理（営業日判定、next/prev_trading_day 等）
  - news_collector: RSS 取得・前処理・raw_news 登録（SSRF 対策・受信サイズ制限・URL 正規化）
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats: 汎用統計ユーティリティ（Zスコア正規化）
  - audit: 監査ログスキーマ定義と初期化（signal_events, order_requests, executions）
  - ETLResult: ETL 実行結果のデータクラス

- ai
  - news_nlp.score_news: ニュースを銘柄ごとに集約し OpenAI（gpt-4o-mini / JSON mode）でセンチメントを算出、ai_scores テーブルに保存
  - regime_detector.score_regime: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を判定・market_regime へ保存

- research
  - factor_research: モメンタム・ボラティリティ・バリュー等のファクター計算（prices_daily / raw_financials 参照）
  - feature_exploration: 将来リターン計算、IC（Spearman）計算、要約統計、ランク化等
  - data.stats.zscore_normalize の再エクスポートあり

---

## 前提・依存関係

主に以下のライブラリを使用します（バージョンは実行環境に合わせて調整してください）:

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリのみで実装された部分が多い）

パッケージ化されていれば `pip install -e .`、あるいは必要パッケージを個別にインストールしてください。

---

## 環境変数（主なもの）

必須・推奨の環境変数は以下です。README に載せるサンプル `.env` を参考にしてください。

必須
- JQUANTS_REFRESH_TOKEN: J‑Quants のリフレッシュトークン（jquants_client が id_token を取得）
- SLACK_BOT_TOKEN: Slack 通知に使用する Bot トークン（必要な場合）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必要な場合）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注統合を行う場合）

OpenAI
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector が使用）

システム / オプション
- DUCKDB_PATH: デフォルト `data/kabusys.duckdb`
- SQLITE_PATH: 例 `data/monitoring.db`
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: `development` / `paper_trading` / `live`（デフォルト development）
- LOG_LEVEL: `DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`

自動 .env 読込
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化します。

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS/Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - もしパッケージ化されていれば:
     ```
     pip install -e .
     ```
   - 個別に:
     ```
     pip install duckdb openai defusedxml
     ```

4. 環境変数を用意
   - プロジェクトルートに `.env` または `.env.local` を作成します（.env.local は .env を上書き可）。
   - 例（.env.example を参考に）:
     ```
     JQUANTS_REFRESH_TOKEN=xxx
     OPENAI_API_KEY=sk-xxx
     SLACK_BOT_TOKEN=xoxb-xxx
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

5. DuckDB ファイル保存先ディレクトリを作成（必要なら）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

README では Python API の基本的な呼び出し例を示します。実行前に環境変数を設定し、必要な DB ファイルの親ディレクトリを作成しておいてください。

- DuckDB 接続を開いて ETL を実行（日次 ETL）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアリング（OpenAI API key が必要）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # env OPENAI_API_KEY を使用
  print("written:", written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)  # OPENAI_API_KEY を参照
  ```

- 監査ログDB の初期化（監査専用 DB を作る）
  ```python
  from pathlib import Path
  import kabusys.data.audit as audit

  conn = audit.init_audit_db(Path("data/audit.duckdb"))
  # conn を使って監査テーブルが作成されていることを確認できます
  ```

- RSS を取得（ニュース収集）
  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  source = "yahoo_finance"
  url = DEFAULT_RSS_SOURCES[source]
  articles = fetch_rss(url, source)
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

注意点:
- AI 呼び出しは API 利用コストとレート制限があるため、本番での運用前に十分にテストしてください。
- OpenAI 呼び出しは内部でリトライ・フォールバックを実装していますが、API キーの管理は厳重に行ってください。
- jquants_client は J-Quants の API レート制限（120 req/min）を守るため内部でスロットリングしています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトは src/kabusys 以下に配置されています。主なファイル・サブパッケージは次の通りです。

- src/kabusys/
  - __init__.py
  - config.py                       -- 環境設定 / .env 読み込み
  - ai/
    - __init__.py
    - news_nlp.py                    -- ニュースの OpenAI ベースセンチメント
    - regime_detector.py             -- 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py              -- J-Quants API クライアント & DuckDB 保存
    - pipeline.py                    -- ETL パイプライン（run_daily_etl 等）
    - etl.py                         -- ETLResult の再エクスポート
    - calendar_management.py         -- マーケットカレンダー管理・営業日ロジック
    - news_collector.py              -- RSS 収集・前処理
    - quality.py                     -- データ品質チェック
    - stats.py                       -- zscore_normalize 等
    - audit.py                       -- 監査ログスキーマの作成 / init_audit_db
  - research/
    - __init__.py
    - factor_research.py             -- モメンタム/ボラティリティ/バリュー等
    - feature_exploration.py         -- 将来リターン/IC/統計サマリー
  - research/...（その他の分析ユーティリティ）

---

## 運用・開発上の注意事項

- Look-ahead bias の防止設計が随所に織り込まれています（target_date パラメータの明示、DB クエリにおける排他条件など）。ライブラリをバックテストへ利用する際は、必ず同様の注意を払ってください。
- OpenAI や J-Quants の呼び出し部分はリトライ・バックオフ・フォールバックを持っていますが、エラー時の影響範囲を理解した上で運用してください（ログ監視、通知設定を推奨）。
- データ保存（DuckDB）は冪等的に行う実装になっています（ON CONFLICT DO UPDATE 等）。ただし、外部から DB を直接編集する場合は注意が必要です。
- テスト用に内部の HTTP / OpenAI 呼び出しをモックできるよう考慮されています（テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にする等）。

---

## 追加情報 / 今後の拡張アイデア

- ブローカー連携（kabu API）を組み込み、order_requests → 発注 → executions のフローを自動化
- モデル管理・戦略バージョン管理を統合（strategy 層の拡張）
- 時系列データを活用したバックテストエンジンとの統合
- Slack 等への通知・監視の自動化（settings.slack_* を利用）

---

もし README に追加したい具体的な実行シナリオ（例: ETL の Cron 設定、Dockerfile、CI/CD のワークフロー、.env.example の完全な雛形など）があれば教えてください。必要に応じて追記します。