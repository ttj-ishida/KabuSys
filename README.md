# KabuSys

日本株向けの自動売買／データプラットフォーム用ライブラリ（KabuSys）。  
J-Quants API や RSS ソースからデータを収集・ETL し、DuckDB に格納して研究／取引ロジックや AI モジュールと連携できるように設計されています。  
設計上の重点：ルックアヘッドバイアス回避、冪等保存、堅牢なエラーハンドリング（リトライ・バックオフ）、セキュリティ対策（SSRF防止 など）。

---

## 主な特徴（機能一覧）

- 環境設定管理
  - .env / .env.local を自動読み込み（任意で無効化可能）
  - 必須環境変数チェック（settings オブジェクト）

- データ取得 / ETL（kabusys.data）
  - J-Quants API クライアント（認証、自動リフレッシュ、ページネーション、レート制御、リトライ）
  - 日足（OHLCV）・財務データの差分取得と DuckDB への冪等保存
  - JPX マーケットカレンダーの差分更新と営業日判定ユーティリティ
  - ニュース収集（RSS）と前処理、raw_news / news_symbols への保存（SSRF対策・サイズ制限）
  - データ品質チェック（欠損・スパイク・重複・日付不整合）
  - 監査ログ（signal / order_request / executions）スキーマ初期化ユーティリティ
  - 汎用統計ユーティリティ（Zスコア正規化など）

- AI（kabusys.ai）
  - ニュース NPL: ニュース記事を LLM（OpenAI）に投げて銘柄ごとのセンチメントスコアを生成し ai_scores に保存
  - 市場レジーム判定: ETF(1321) の MA200 乖離とマクロニュースセンチメントを合成して日次レジーム判定（bull / neutral / bear）

- リサーチ（kabusys.research）
  - ファクター計算（モメンタム、バリュー、ボラティリティなど）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー、ランク変換

- 設計方針（抜粋）
  - データ取得・処理は可能な限り DuckDB + SQL で完結
  - Look-ahead バイアスを避ける実装（target_date ベースで計算）
  - API 呼び出しはリトライ・バックオフ・タイムアウト付き
  - LLM 呼び出しは JSON mode を利用しレスポンス検証を行う

---

## 必要条件 / 推奨環境

- Python 3.10 以上
- 推奨パッケージ（抜粋）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants / OpenAI / RSS 取得のため）

（プロジェクトに requirements.txt / pyproject.toml があればそれを使ってください）

---

## セットアップ手順（例）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール
   （プロジェクトに pyproject.toml や requirements.txt があればそれを使う）
   ```
   pip install duckdb openai defusedxml
   # または開発中: pip install -e .
   ```

4. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動読み込みされます（.env.local は .env を上書き可能）。
   - 自動ロードを無効化する場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 主な環境変数（必須／デフォルト値あり）
     - JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD (必須) — kabuステーション API パスワード
     - KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
     - SLACK_BOT_TOKEN (必須) — Slack 通知用トークン
     - SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI 呼び出しに利用（score_news / score_regime）
     - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH — デフォルト: data/monitoring.db
     - KABUSYS_ENV — one of: development, paper_trading, live
     - LOG_LEVEL — one of: DEBUG, INFO, WARNING, ERROR, CRITICAL

5. データディレクトリを作成（必要であれば）
   ```
   mkdir -p data
   ```

---

## 使い方（主要なユーティリティの例）

- DuckDB 接続を作る
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL を実行する
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（OpenAI API キーが環境変数 OPENAI_API_KEY に必要）
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム評価
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ用 DB 初期化（監査専用 DB を用意する場合）
  ```python
  from kabusys.data.audit import init_audit_db
  conn_audit = init_audit_db("data/audit.duckdb")
  ```

- 設定値参照
  ```python
  from kabusys.config import settings
  print(settings.jquants_refresh_token)  # 設定がなければ ValueError
  print(settings.duckdb_path)
  ```

- ファクター計算（研究用）
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum

  conn = duckdb.connect("data/kabusys.duckdb")
  records = calc_momentum(conn, target_date=date(2026,3,20))
  ```

注意点：
- OpenAI 呼び出しはネットワークエラーやレート制限に対してリトライを行いますが、APIキーが未設定の場合は ValueError を投げます。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）を目指しているため、再実行可能です。

---

## ディレクトリ構成（主なファイル・モジュール）

（src/kabusys 以下）

- __init__.py
  - パッケージ初期化。version 情報など。

- config.py
  - 環境変数読み込み／Settings クラス（必須値チェック、env/log level 判定、ファイル自動ロード）

- ai/
  - __init__.py
  - news_nlp.py — ニュースセンチメントの LLM スコアリング、news-window 計算、レスポンス検証、チャンク処理
  - regime_detector.py — ETF MA200 とマクロニュースセンチメントの合成による市場レジーム判定

- data/
  - __init__.py
  - pipeline.py — ETL パイプライン（run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl 等）
  - jquants_client.py — J-Quants API クライアント（認証・取得・DuckDB 保存）
  - calendar_management.py — 市場カレンダー管理、営業日判定、calendar_update_job
  - news_collector.py — RSS 収集、前処理、SSRF 対策、raw_news 保存
  - quality.py — データ品質チェック群（欠損・スパイク・重複・日付不整合）
  - stats.py — zscore_normalize など統計ユーティリティ
  - audit.py — 監査ログテーブル定義・初期化（signal_events, order_requests, executions）
  - etl.py — ETLResult 型の再エクスポート

- research/
  - __init__.py
  - factor_research.py — モメンタム / ボラティリティ / バリュー ファクター計算
  - feature_exploration.py — 将来リターン計算、IC、統計サマリー、ランク変換

（パッケージ切り分け上、strategy / execution / monitoring といった上位モジュールと連携する想定あり）

---

## 環境変数一覧（要確認）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (任意、デフォルトあり)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- OPENAI_API_KEY (AI 機能利用時に必要)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (デフォルト: data/monitoring.db)
- KABUSYS_ENV (development / paper_trading / live)
- LOG_LEVEL (DEBUG/INFO/...)
- KABUSYS_DISABLE_AUTO_ENV_LOAD (1 にすると .env 自動ロードを無効化)

---

## 開発メモ / 実装上の重要ポイント

- Look-ahead Bias を避けるため、日次処理はすべて target_date（外部指定）ベースで動作し、内部で date.today() を直接参照しない実装方針。
- DuckDB への書き込みは冪等性を重視（ON CONFLICT DO UPDATE／個別 DELETE→INSERT）して部分失敗時のデータ保護を行う。
- J-Quants クライアントは固定間隔レートリミッタ、リトライ、401 リフレッシュ処理を実装。
- ニュース取得は SSRF 対策（ホストのプライベート判定・リダイレクト監視）、XML の defusedxml 解析、サイズ上限を厳格に設ける。
- OpenAI 呼び出しは JSON mode を使い、レスポンスのパースとバリデーションを丁寧に行う。テスト用に内部 API 呼び出しをモックしやすい設計。
- audit テーブルは監査証跡を残す目的で削除しない前提（ON DELETE RESTRICT）で設計。

---

必要であれば README にサンプル .env.example、CI / テスト手順、詳細な API 使用例（J-Quants pagination 例や OpenAI レスポンス例）を追記します。どの箇所を詳しく書いて欲しいか教えてください。