# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
J-Quants などの外部データソースからの ETL、ニュース収集と LLM ベースのニュース評価、ファクター計算、監査ログ（order → execution トレーサビリティ）など、株式量的運用で必要となる主要機能をモジュール化して提供します。

主な設計方針
- ルックアヘッドバイアスを避けるため、内部で date.today() / datetime.today() を直接参照しない設計
- DuckDB を中心としたローカルデータベース運用（冪等保存を前提）
- 外部 API 呼び出し（J-Quants / OpenAI 等）はリトライ・レートリミット等の考慮あり
- 各パーツはバッチ処理 / 研究用途で独立して利用できる

---

## 機能一覧

- data
  - ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl）
  - J-Quants API クライアント（fetch / save 関数、認証・ページネーション・レート制御・リトライ）
  - 市場カレンダー管理（is_trading_day / next_trading_day / prev_trading_day / calendar_update_job）
  - ニュース収集（RSS フィード取得・前処理・SSRF 対策・raw_news への保存）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal_events / order_requests / executions）テーブルの初期化とユーティリティ
  - 統計ユーティリティ（Zスコア正規化等）
- ai
  - ニュース NLP スコアリング（gpt-4o-mini を使った銘柄別センチメント -> ai_scores へ書込）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの LLM センチメントを合成）
- research
  - ファクター計算（モメンタム / バリュー / ボラティリティ 等）
  - 特徴量探索（forward returns, IC（スピアマン）計算, 統計サマリー, ランク変換）
- config
  - 環境変数読み込み（.env / .env.local 自動読込。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - Settings オブジェクト経由の設定参照（DBパス、kabu API, Slack, 環境種別など）

---

## セットアップ手順

前提
- Python 3.10 以上（PEP 604 の Union 型（a | b）などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS フィード）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell では .venv\Scripts\Activate.ps1)
   ```

3. 依存パッケージをインストール
   必要最低限のパッケージ例:
   ```
   pip install duckdb openai defusedxml
   ```
   （プロジェクトに setup/pyproject がある場合は `pip install -e .` を推奨）

4. 環境変数 / .env の準備
   - プロジェクトルートに `.env`（または `.env.local`）を置くと、自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須例（用途に応じてセットしてください）:
     ```
     # J-Quants
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token

     # OpenAI（AI モジュール利用時）
     OPENAI_API_KEY=sk-...

     # kabuステーション API（発注等）
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi

     # Slack 通知（monitoring 用）
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=CXXXXXXX

     # DB パス（省略時デフォルト）
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db

     # 環境／ログレベル
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - リポジトリに `.env.example` を置いておくと設定ミスを防げます（config._require は未設定時に ValueError を出す箇所があります）。

5. データディレクトリの作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（簡単な例）

以下は最小の利用例です。実運用ではログ設定・エラーハンドリング・スケジューラ等を追加してください。

- DuckDB 接続を作る（デフォルトパスを Settings から取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- ETL（日次パイプライン）を実行
  ```python
  from kabusys.data.pipeline import run_daily_etl

  result = run_daily_etl(conn, target_date=None)  # target_date を指定するとその日分で実行
  print(result.to_dict())
  ```

- ニュースを LLM で評価して ai_scores に書き込む
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込み銘柄数:", n_written)
  ```
  注意: OPENAI_API_KEY を環境変数または api_key 引数で渡す必要があります。

- 市場レジームを判定して market_regime に保存する
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB を初期化する（order/execution用のスキーマ作成）
  ```python
  from kabusys.data.audit import init_audit_db

  audit_conn = init_audit_db("data/audit.duckdb")
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, target_date=date(2026,3,20))
  val = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  ```

---

## 設定と動作に関する注意点

- 自動 .env ロード
  - パッケージはプロジェクトルート（.git または pyproject.toml を基準）から `.env` / `.env.local` を自動ロードします。
  - テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
  - 読み込み優先度: OS 環境変数 > .env.local > .env

- OpenAI
  - LLM 呼び出しには OpenAI の認証キー（OPENAI_API_KEY）が必要です。API の呼び出しはリトライや RateLimit を考慮していますが、API 利用に伴うコスト管理はユーザー責任です。

- J-Quants
  - J-Quants の API キー（リフレッシュトークン）は `JQUANTS_REFRESH_TOKEN` に設定してください。get_id_token で ID トークンを取得して API を利用します。
  - レート制御（120 req/min）や 401 リフレッシュ処理、ページネーション対応が組み込まれています。

- ルックアヘッド回避
  - AI モジュール・ETL・研究モジュールはいずれもバックテストのルックアヘッドバイアスに注意した実装指針に沿っています。target_date 等は明示的に渡す運用を推奨します。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py
- ai/
  - __init__.py
  - news_nlp.py         — ニュースセンチメント評価（OpenAI）
  - regime_detector.py  — マーケットレジーム判定
- data/
  - __init__.py
  - jquants_client.py   — J-Quants API クライアント & DuckDB 保存ロジック
  - pipeline.py         — ETL パイプライン（run_daily_etl 等）
  - etl.py              — ETL 公開型（ETLResult の再エクスポート）
  - news_collector.py   — RSS ニュース収集（SSRF 対策・前処理）
  - calendar_management.py — 市場カレンダー管理（営業日判定 / calendar_update_job）
  - quality.py          — データ品質チェック
  - stats.py            — 汎用統計ユーティリティ
  - audit.py            — 監査ログ（order/execution スキーマ初期化）
- research/
  - __init__.py
  - factor_research.py  — モメンタム / バリュー / ボラティリティ等
  - feature_exploration.py — forward returns / IC / factor summary / rank

（その他モジュールが追加される可能性があります）

---

## 開発・テスト

- 自動ロードされる .env を使うため、CI などで環境分離する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定し、テスト用の env を明示的に注入してください。
- AI / 外部 API 呼び出し部分はモックしやすい設計になっています（内部の _call_openai_api や jquants_client._request を patch してテスト可能）。

---

## ライセンス / 貢献

この README はコードベースの説明を目的としています。ライセンスやコントリビューションガイドラインはリポジトリのルート（LICENSE / CONTRIBUTING.md 等）を参照してください。

---

質問や追加で README に載せたい使用例（cron の設定、スケジューリング例、運用チェックリスト等）があれば教えてください。必要に応じてサンプルスクリプトや運用手順を追記します。