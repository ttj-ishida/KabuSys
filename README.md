# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリ。  
ETL（J-Quants からの株価・財務・カレンダー取得）、ニュース収集・NLP（OpenAI を用いた記事センチメント）、市場レジーム判定、リサーチ（ファクター計算）、監査ログ（注文→約定トレーサビリティ）などを含んだモジュール群を提供します。

現在のバージョン: 0.1.0

---

## 特徴（機能一覧）

- 環境変数管理
  - プロジェクトルートの .env / .env.local を自動で読み込み（必要に応じて無効化可能）
- データ取得 / ETL
  - J-Quants API から日次株価、財務、マーケットカレンダーを差分取得・保存（ページネーション・リトライ・レート制御付き）
  - ETL の結果を示す ETLResult クラス
- データ品質チェック
  - 欠損、重複、スパイク、日付の不整合を検出
- ニュース収集
  - RSS 取得（SSRF 対策・サイズ制限・トラッキングパラメータ除去）→ raw_news へ保存
- ニュース NLP（OpenAI）
  - 銘柄別にニュースを集約し LLM でセンチメントを算出して ai_scores に保存
- 市場レジーム判定
  - ETF（1321）の MA200 乖離 + マクロニュースセンチメントを合成して日次で bull / neutral / bear を判定
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン・IC・統計サマリ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブルを初期化・管理（DuckDB 用DDL、冪等）

---

## 前提（依存ライブラリなど）

主要な Python ライブラリ（例）:
- duckdb
- openai
- defusedxml

※ 実際のプロジェクトでは pyproject.toml / requirements.txt を参照してください。

---

## セットアップ手順

1. 仮想環境の作成（例）
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. パッケージのインストール（プロジェクトルートで）
   - 開発中に編集しながら使う場合:
     ```bash
     pip install -e .
     ```
   - または必要な依存のみ:
     ```bash
     pip install duckdb openai defusedxml
     ```

3. 環境変数設定
   - プロジェクトルートに `.env`（および必要なら `.env.local`）を作成します。自動ロードはデフォルトで有効です（無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1）。
   - 必須環境変数（主なもの）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     KABU_API_PASSWORD=your_kabu_api_password
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     OPENAI_API_KEY=sk-...
     ```
   - 任意 / 設定例:
     ```
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development   # development / paper_trading / live
     LOG_LEVEL=INFO
     ```
   - 設定アクセス例（コード内）:
     ```python
     from kabusys.config import settings
     print(settings.jquants_refresh_token)
     ```

4. DuckDB ファイル用ディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

---

## 使い方（主要なユースケース）

以下はモジュール呼び出しの基本例です。各関数は主に DuckDB 接続と日付を受け取ります。

- 日次 ETL 実行（J-Quants からの差分取得＋品質チェック）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースのセンチメントスコア算出（ai_scores へ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("wrote", n_written)
  ```

- 市場レジーム判定（market_regime テーブルへ書き込み）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ（Audit）用 DB 初期化
  ```python
  from kabusys.data.audit import init_audit_db

  conn_audit = init_audit_db("data/audit.duckdb")
  # 以降 conn_audit を使って signal/order/execution を記録
  ```

- リサーチ（ファクター計算）例
  ```python
  from datetime import date
  import duckdb
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  moment = calc_momentum(conn, date(2026,3,20))
  value = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 設定の動作確認
  ```python
  from kabusys.config import settings
  print(settings.env, settings.log_level, settings.is_dev)
  ```

注意点:
- 各関数はルックアヘッドバイアスを避ける設計で、内部で date.today() 等を参照しないものが多いです。必ず適切な target_date を渡してください。
- OpenAI を使う関数 (score_news, score_regime) は OPENAI_API_KEY を引数で渡すか環境変数に設定する必要があります。

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN: Slack ボットトークン（必須）
- SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
- OPENAI_API_KEY: OpenAI API キー（score_news / score_regime などで使用）
- DUCKDB_PATH: デフォルト DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- KABUSYS_ENV: 環境 (development / paper_trading / live)
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化します（テスト等で便利）。

---

## ディレクトリ構成

（src/kabusys 配下の主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI）関連
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント（取得・保存）
    - pipeline.py                  — ETL パイプライン実装（run_daily_etl 等）
    - etl.py                       — ETLResult 再エクスポート
    - stats.py                     — 共通統計ユーティリティ（zscore 正規化等）
    - quality.py                   — データ品質チェック
    - news_collector.py            — RSS 収集と前処理
    - calendar_management.py       — マーケットカレンダー管理
    - audit.py                     — 監査ログ（DDL / 初期化）
  - research/
    - __init__.py
    - factor_research.py           — ファクター計算
    - feature_exploration.py       — 将来リターン・IC・統計サマリ等
  - research/ などの他モジュール（strategy / execution / monitoring 等は __all__ に含める想定）

---

## 開発・運用上の注意

- OpenAI 呼び出しは外部 API であるためレート制限・失敗に備えてリトライやフェイルセーフが組み込まれていますが、API キーの管理（レート・コスト）には注意してください。
- DuckDB の executemany に関する制約（空のパラメータリストは不可）に対応する実装が含まれています。変更する場合は互換性に注意してください。
- ニュース収集は外部 URL にリクエストするため SSRF 対策とサイズチェックが実装されています。RSS ソース追加時は信頼できるソースを登録してください。
- 監査ログテーブルは基本的に削除しない前提です。DDL は冪等で作成されますが、運用時のマイグレーションやバックアップ運用を検討してください。
- 設定の自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。パッケージ配布後・テスト時に挙動が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用できます。

---

## ライセンス・貢献

（ここには実際のライセンスや貢献手順を記載してください。OSS として公開する場合は LICENSE ファイルを追加してください。）

---

以上が README の概要です。必要であれば「使い方」に具体的な CLI スクリプト例や CI / デプロイ手順、より詳細なテーブルスキーマや SQL 定義（DDL）を追記します。どの部分を詳細化したいか教えてください。