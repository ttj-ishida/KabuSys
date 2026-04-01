# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース NLP（OpenAI を用いた銘柄センチメント評価）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（発注→約定のトレーサビリティ）など、アルゴリズム取引やリサーチに必要な基盤処理を提供します。

バージョン: 0.1.0

---

## 主な特徴

- データ取得（J-Quants API）
  - 株価日足（OHLCV）、財務データ、上場銘柄・市場カレンダー取得（ページネーション・リトライ・レート制御）
- ETL パイプライン
  - 差分取得、バックフィル、品質チェックを含む日次 ETL（run_daily_etl）
- ニュース収集
  - RSS フィード取得、前処理、raw_news / news_symbols への冪等保存（SSRF / XML 脆弱性対策）
- ニュース NLP（OpenAI）
  - 銘柄ごとにニュースをまとめて LLM に投げ、ai_scores にスコアを保存（gpt-4o-mini を想定）
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 と LLM センチメントを合成）
- Research ツール
  - モメンタム／バリュー／ボラティリティ等のファクター計算、将来リターン・IC 計算、Z スコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などを検出して QualityIssue を返す
- 監査ログ（audit）
  - signal_events / order_requests / executions の監査テーブル定義・初期化（DuckDB）
- 設定管理
  - .env（および .env.local）または環境変数から設定を読み込む自動ロード機能

---

## 必要な環境変数

必須（最低限実行に必要なもの）
- OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector 用）
- JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン（jquants_client 用）
- KABU_API_PASSWORD — kabu ステーション API パスワード（発注連携がある場合）
- SLACK_BOT_TOKEN — Slack 通知を使う場合
- SLACK_CHANNEL_ID — Slack 通知を使う場合

任意（デフォルト値あり）
- KABUSYS_ENV — development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — DEBUG|INFO|WARNING|ERROR|CRITICAL（デフォルト: INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite 監視 DB（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

注意:
- 自動でプロジェクトルートの .env / .env.local を読み込みます（プロジェクトルートは .git or pyproject.toml から検出）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数が未設定の場合は Settings プロパティが ValueError を投げます。

---

## セットアップ手順（開発用）

1. Python 仮想環境の作成
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージのインストール（例）
   - 最低限必要なライブラリ:
     - duckdb
     - openai
     - defusedxml
   ```bash
   pip install duckdb openai defusedxml
   ```
   - 追加で Slack やテスト用ライブラリを使う場合は適宜インストールしてください（例: slack_sdk）。

3. 環境変数の設定
   - プロジェクトルートに `.env` または `.env.local` を配置するか、OS 環境変数で設定します。
   - 例（.env）:
     ```
     OPENAI_API_KEY=sk-...
     JQUANTS_REFRESH_TOKEN=xxxx
     KABU_API_PASSWORD=yourpassword
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     ```
   - 自動ロードを無効化したい場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

4. DuckDB 初期化（監査用 DB 例）
   - audit テーブルを作成する簡単な方法:
     ```python
     import duckdb
     from kabusys.data.audit import init_audit_db

     conn = init_audit_db("data/audit.duckdb")
     # conn は初期化済みの DuckDB 接続
     ```

---

## 使い方（主要 API の例）

以下は典型的な利用例です。実行時には適切な環境変数（特に OPENAI_API_KEY / JQUANTS_REFRESH_TOKEN）が必要です。

- 日次 ETL を実行する
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコアを生成して ai_scores に書き込む
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {count} codes")
  ```

- 市場レジーム（bull/neutral/bear）を算出して保存する
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算の例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  momentum = calc_momentum(conn, date(2026, 3, 20))
  volatility = calc_volatility(conn, date(2026, 3, 20))
  value = calc_value(conn, date(2026, 3, 20))
  ```

- 監査ログスキーマ初期化（既存 DB に追加）
  ```python
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

---

## ディレクトリ構成（主要ファイル）

（この README は src/kabusys 以下の主要モジュールに基づきます）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py            — ニュースセンチメント評価（LLM）
    - regime_detector.py     — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/
    - __init__.py
    - calendar_management.py — 市場カレンダー管理（営業日判定 / 更新ジョブ）
    - etl.py                  — ETL インターフェース
    - pipeline.py             — ETL パイプライン実装（run_daily_etl 等）
    - stats.py                — 統計ユーティリティ（zscore_normalize）
    - quality.py              — データ品質チェック
    - audit.py                — 監査ログ（テーブル定義・初期化）
    - jquants_client.py       — J-Quants API クライアント（取得・保存ロジック）
    - news_collector.py       — RSS ニュース収集・前処理・保存
    - etl.py                  — ETL 結果の公開（ETLResult）
  - research/
    - __init__.py
    - factor_research.py      — モメンタム/ボラティリティ/バリュー計算
    - feature_exploration.py  — 将来リターン計算 / IC / 統計サマリー
  - ai/、research/ 等が提供する各種ユーティリティ

- その他
  - data/                    — デフォルトのローカル DB / ファイル保存パス（設定で変更可）
  - .env.example             — （プロジェクトルートに置くことを想定：環境変数サンプル）

---

## 注意事項 / 設計上の要点

- Look-ahead Bias に配慮して、各モジュールは内部で date.today() / datetime.today() を参照しない（外部から target_date を与える設計）。バックテスト用途では特に設計意図に従ってください。
- LLM（OpenAI）呼び出しはリトライやフェイルセーフを備えていますが、API キー・料金に注意して実行してください。API 失敗時は安全側の既定値（例: macro_sentiment=0.0）で継続する実装になっています。
- DuckDB を永続ストレージとして利用する設計です。初期スキーマは ETL 実行や audit.init_audit_db 等で作成してください。
- 自動 .env ロードは便利ですがテスト・CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って明示的に管理することを推奨します。

---

もし README にサンプルの .env.example や requirements.txt を追加したい、あるいは各モジュールの API リファレンス風ドキュメントを生成したい場合は指示してください。