# KabuSys

日本株向けの自動売買 / データプラットフォームライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースのNLPスコアリング、マーケットレジーム判定、監査ログ（発注→約定のトレーサビリティ）、研究用ファクター計算などを提供します。

---

## 主な特徴

- J-Quants API を用いた株価（OHLCV）、財務データ、JPX カレンダーの差分取得（ページネーション対応、リトライ・レート制御あり）
- DuckDB によるローカルデータストア（冪等保存：ON CONFLICT DO UPDATE）
- 日次 ETL パイプライン（run_daily_etl）：カレンダー → 株価 → 財務 → 品質チェックの一連処理
- ニュース収集（RSS）とニュースの前処理、安全対策（SSRF ガード、レスポンスサイズ制限等）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント分析（銘柄別スコア）およびマクロセンチメントを組み合わせた市場レジーム判定
- 監査ログスキーマ（signal_events / order_requests / executions）と初期化ユーティリティ
- 研究用途のファクター計算（モメンタム・バリュー・ボラティリティ等）と特徴量解析ユーティリティ

---

## 必要条件 / 依存パッケージ（主要）

- Python 3.10+
- duckdb
- openai (OpenAI Python SDK)
- defusedxml
- （標準ライブラリ以外の追加依存はプロジェクトの packaging に従ってください）

例:
pip install duckdb openai defusedxml

---

## 環境変数 / .env

パッケージ読み込み時にプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索し、 `.env` → `.env.local` の順に自動で読み込みを行います（OS 環境変数を上書きしません）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

主に使用される環境変数（必須／任意）:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL (任意) — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- OPENAI_API_KEY (必須: AI 機能を使う場合) — OpenAI API キー
- DUCKDB_PATH (任意) — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) — SQLite 監視 DB（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) — 環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- LOG_LEVEL (任意) — ログレベル ("DEBUG","INFO",...)（デフォルト: INFO）

例 .env（雛形）
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
OPENAI_API_KEY=sk-xxxx...
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C12345678
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（簡易）

1. 仮想環境の作成（推奨）:
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存インストール:
   - pip install duckdb openai defusedxml
   - （プロジェクトが配布パッケージ化されている場合は pip install -e .）

3. 環境変数の設定:
   - プロジェクトルートに `.env` を作成（上記サンプルを参照）
   - あるいは OS 環境変数として設定

4. データディレクトリ作成:
   - mkdir -p data

5. 監査ログ用 DuckDB の初期化（任意）:
   - Python REPL やスクリプトで:
     ```
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     conn.close()
     ```

---

## 使い方（主要な操作例）

- 日次 ETL 実行（DuckDB 接続を用いて Python から呼ぶ例）:
  ```
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  conn.close()
  ```

- ニュースセンチメントのスコアリング（OpenAI 必須）:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("written", n_written)
  conn.close()
  ```

- 市場レジーム判定（1321 の MA200 + マクロニュースで判定）:
  ```
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  conn.close()
  ```

- 監査スキーマ初期化（既存接続を利用）:
  ```
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  conn.close()
  ```

- 研究用ファクター計算例:
  ```
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  m = calc_momentum(conn, target_date=date(2026,3,20))
  v = calc_value(conn, target_date=date(2026,3,20))
  vol = calc_volatility(conn, target_date=date(2026,3,20))
  conn.close()
  ```

注意点:
- AI 機能（news_nlp / regime_detector）は OpenAI の API キー（OPENAI_API_KEY）が必要です。テスト時は内部の API 呼び出し関数をモックできます（コード内に patch しやすい設計あり）。
- ETL / API 呼び出し部分はネットワーク・外部API依存のため、キー・トークン・ネットワーク接続が必要です。
- 自動環境変数読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py — パッケージ定義（バージョン等）
- config.py — 環境変数 / 設定管理（.env 自動ロード・Settings クラス）
- ai/
  - __init__.py
  - news_nlp.py — ニュースのNLPスコアリング（銘柄別 ai_scores 生成）
  - regime_detector.py — マクロニュース + 1321 MA200 を組み合わせた市場レジーム判定
- data/
  - __init__.py
  - jquants_client.py — J-Quants API クライアント（取得 + DuckDB 保存）
  - pipeline.py — ETL パイプライン（run_daily_etl 等）
  - etl.py — ETLResult 再エクスポート
  - news_collector.py — RSS 収集と保存ロジック（SSRF 対策等）
  - calendar_management.py — 市場カレンダー管理 / 営業日判定ロジック
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - stats.py — 汎用統計ユーティリティ（zscore_normalize 等）
  - audit.py — 監査ログスキーマ定義と初期化ユーティリティ
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン、IC 計算、統計サマリー等

（上記はこのリポジトリに含まれる主要モジュールの抜粋です）

---

## テスト・開発ヒント

- OpenAI や外部 API 呼び出しはモックしやすいように内部呼び出し関数に分離されています。unittest.mock.patch を用いて _call_openai_api 等を差し替えてテスト可能です。
- .env 自動ロードはパッケージインポート時に行われます。テストで環境の影響を避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンの挙動に考慮したガードがコード中にあります。テストデータ作成時はこの点を留意してください。

---

以上。必要であれば README に加える例（Dockerfile / systemd ユニット / CI ワークフロー / .env.example の完全版）や、各モジュールの詳細な API リファレンスを別途作成できます。どの情報がさらに必要か教えてください。