# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ群です。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定トレーサビリティ）等の機能を提供します。

バージョン: 0.1.0

---

## 主な特徴（機能一覧）

- 環境変数管理
  - `.env` / `.env.local` の自動読み込み（プロジェクトルート基準）
  - 必須設定取得時のバリデーション
- データ取得（J-Quants）
  - 株価日足（OHLCV）、財務諸表、JPX マーケットカレンダーの API クライアント
  - レートリミット管理 / リトライ / トークン自動リフレッシュ
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
- ETL パイプライン
  - 日次 ETL（カレンダー → 株価 → 財務 → 品質チェック）
  - 差分取得・バックフィルロジック
  - ETL 実行結果を表す ETLResult
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合などの検出
  - 問題を QualityIssue として集約
- ニュース収集 & NLP
  - RSS フィード収集（SSRF 対策、トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini）を用いた銘柄ごとのニュースセンチメント（ai_scores への保存）
  - API 呼び出しの堅牢なリトライ/バリデーション
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次で判定
  - LLM 呼び出しは失敗時フォールバック（macro_sentiment=0.0）
- 研究用ユーティリティ
  - ファクター計算（モメンタム / バリュー / ボラティリティ等）
  - 将来リターン、IC（Spearman）、Zスコア正規化、統計サマリー
- 監査ログ（audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ
  - DuckDB ベースでの監査 DB 初期化関数を提供

---

## セットアップ手順

前提:
- Python 3.10+（型ヒントに union 型などを使用）
- ネットワークアクセス（J-Quants / OpenAI / RSS）

1. リポジトリをクローンしてインストール（開発環境例）:
   ```bash
   git clone <repo-url>
   cd <repo-root>
   pip install -e .
   ```

2. 依存パッケージ（主なもの）
   - duckdb
   - openai
   - defusedxml
   - その他標準ライブラリのみで多くを実装しています。`pyproject.toml` や `requirements.txt` を参照してください。

3. 環境変数 / .env の準備  
   プロジェクトルート（`.git` または `pyproject.toml` のあるディレクトリ）に `.env` / `.env.local` を配置すると自動的に読み込まれます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

   最低限必要な変数（例）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456789
   OPENAI_API_KEY=sk-...
   ```

   - 指定が無い場合のデフォルト:
     - DuckDB: `DUCKDB_PATH=data/kabusys.duckdb`
     - SQLite (monitoring): `SQLITE_PATH=data/monitoring.db`
     - Kabu API Base URL: `KABU_API_BASE_URL=http://localhost:18080/kabusapi`
   - 自動ロードの挙動:
     - 読み込み順: OS 環境変数 > `.env.local` > `.env`
     - `.env` のパースはシェル形式に準拠した扱い（クォート / コメント考慮）

---

## 使い方（簡単なサンプル）

下記はモジュールの代表的な使用例です。DuckDB 接続は `duckdb.connect(path)` で取得します。

- 日次 ETL の実行:
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP（ai_scores 生成）:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored: {count}")
  ```
  - `api_key` 引数を渡さない場合は環境変数 `OPENAI_API_KEY` を使用します。

- 市場レジーム判定:
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査 DB 初期化（監査専用 DuckDB を作る）:
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # これで signal_events / order_requests / executions 等が作成されます
  ```

- J-Quants クライアントの直接利用（例: 上場銘柄取得）:
  ```python
  from kabusys.data.jquants_client import fetch_listed_info
  infos = fetch_listed_info()
  ```

---

## 環境変数の主な一覧

- JQUANTS_REFRESH_TOKEN: J-Quants 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack 通知用ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector のデフォルト）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用）パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV: 環境 ("development" | "paper_trading" | "live")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)

---

## 開発・テストのヒント

- 自動 .env の読み込みはプロジェクトルート（.git または pyproject.toml を基準）から行われます。テスト時に自動ロードを無効化したい場合:
  ```bash
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出し等外部 API をモックする設計になっています（モジュール内の _call_openai_api 等をパッチする）。
- DuckDB の executemany は空リストを渡すとエラーになるバージョンがあるため、コード内で空チェックを行っています。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         — ニュース NLP / ai_scores 書き込み
    - regime_detector.py  — レジーム判定（ma200 + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（fetch / save）
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - etl.py              — ETL 結果型の再エクスポート（ETLResult）
    - news_collector.py   — RSS 収集・raw_news 保存
    - calendar_management.py — 市場カレンダー管理（is_trading_day 等）
    - quality.py          — 品質チェック（check_missing_data / check_spike 等）
    - stats.py            — ゼロ依存の統計ユーティリティ（zscore_normalize）
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン / IC / サマリー等
  - research/* 他...
- pyproject.toml / setup.cfg / README.md（本ファイル）

各モジュールにはドキュメント文字列（docstring）で詳細な設計方針・戻り値・例外が記載されています。実運用前に各 ETL / API の認証情報や DB バックアップ、レート制限の確認を行ってください。

---

もし README に追記してほしい項目（例えば具体的な schema 定義、SQL スキーマダンプ、CI 実行手順、デプロイ手順など）があれば教えてください。必要に応じて追補します。