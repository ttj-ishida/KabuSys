# KabuSys

KabuSys は日本株向けの自動売買・データプラットフォーム用ライブラリです。  
ETL（J-Quants からのデータ取得）、ニュース収集・NLP スコアリング（OpenAI）、市場レジーム判定、ファクター計算、データ品質チェック、監査ログ（約定トレーサビリティ）などを包含したモジュール群を提供します。

バージョン: 0.1.0

---

## 主要な特徴

- ETL
  - J-Quants API から株価（日次 OHLCV）、財務データ、JPX カレンダーを差分取得し DuckDB に保存
  - 差分取得／バックフィル／品質チェック機能を備えた日次パイプライン
- ニュース収集 & NLP
  - RSS からニュースを収集し raw_news に保存（SSRF 対策、トラッキングパラメータ除去）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメントスコアリング（ai_scores へ保存）
- 市場レジーム判定
  - ETF 1321 の 200 日移動平均乖離とマクロニュースの LLM センチメントを合成して日次レジームを判定・保存
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等の定量ファクター計算、将来リターン・IC 解析、Z スコア正規化
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合などの検出を行う品質チェック群
- 監査ログ（audit）
  - signal → order_request → execution までのトレーサビリティテーブルを提供（DuckDB）

---

## 必要条件

- Python 3.10 以上（Union 型記法などを使用）
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS ソース）
- J-Quants / OpenAI の API キー

（実運用では追加の依存性が必要になる場合があります。プロジェクトの requirements.txt がある場合はそちらを参照してください。）

---

## セットアップ手順

1. リポジトリをクローン / チェックアウト
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要パッケージをインストール（例）
   ```
   pip install duckdb openai defusedxml
   # またはプロジェクトに requirements.txt があれば:
   # pip install -r requirements.txt
   ```

4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動的に読み込まれます（ただしテスト時などに自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）
   - 必要な主要環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API パスワード（発注機能を使う場合）
     - OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector）
   - その他（デフォルト値あり）
     - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PID_FILE_PATH / KILL_FLAG_PATH / 各種監視閾値など

   例 `.env`（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   LOG_LEVEL=INFO
   KABUSYS_ENV=development
   ```

5. DuckDB 用ディレクトリ作成
   ```
   mkdir -p data
   ```

---

## 使い方（代表的な API）

以下は Python REPL やスクリプト中で利用する例です。各関数は DuckDB の接続オブジェクト（duckdb.connect() の戻り値）を受け取ります。

- ETL(日次パイプライン) の実行例
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニューススコアリング（ai_scores への書き込み）
  ```python
  from kabusys.ai.news_nlp import score_news
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  n_written = score_news(conn, target_date=date(2026,3,20))
  print("scored:", n_written)
  ```

- 市場レジーム判定
  ```python
  from kabusys.ai.regime_detector import score_regime
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査（audit）スキーマ初期化（専用 DB を作る例）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # init_audit_schema は自動的に呼ばれる
  ```

- ファクター/リサーチ関数の呼び出し例
  ```python
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility
  import duckdb
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  mom = calc_momentum(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  ```

注意点:
- OpenAI を呼ぶ関数（news_nlp, regime_detector）は API キー（OPENAI_API_KEY）を環境変数か引数で渡す必要があります。
- テスト時には内部の API 呼び出し（_call_openai_api など）をモックして行う設計になっています。

---

## 自動環境変数ロードの挙動

- 起動時にプロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を探索し、`.env` と `.env.local` を順に読み込みます。
  - 読み込み順: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` の値を上書きします。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。

---

## テスト / モック方針（運用メモ）

- OpenAI / J-Quants / RSS などネットワーク I/O を伴う関数は、内部で呼ばれる低レイヤ関数（例: _call_openai_api, _urlopen, _request など）をモックすることでユニットテストが可能です。
- DuckDB の接続はインメモリ `":memory:"` を使ってテストを高速化できます。
- ETL の各ステップは独立して例外処理されるため、部分的な失敗を再現して結果の集約挙動を検証できます。

---

## ディレクトリ構成

（主要なファイル・モジュールのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / 設定管理
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（銘柄別スコアリング）
    - regime_detector.py           — 市場レジーム判定
  - data/
    - __init__.py
    - jquants_client.py            — J-Quants API クライアント + DuckDB 保存
    - pipeline.py                  — ETL パイプライン（run_daily_etl 等）
    - etl.py                       — ETL 公開インターフェース（ETLResult re-export）
    - calendar_management.py       — 市場カレンダー管理（営業日判定等）
    - news_collector.py            — RSS ニュース収集
    - quality.py                   — データ品質チェック
    - stats.py                     — 統計ユーティリティ（zscore_normalize 等）
    - audit.py                     — 監査ログスキーマ（init_audit_schema / init_audit_db）
  - research/
    - __init__.py
    - factor_research.py           — モメンタム / バリュー / ボラティリティ計算
    - feature_exploration.py       — 将来リターン / IC / 統計サマリー 等

---

## 追加情報 / 運用上の注意

- Look-ahead bias 回避のため、日付処理は target_date を明示的に渡す設計になっています。バックテストや再現性のために呼び出し元で日付を適切に固定してください。
- J-Quants と OpenAI の API 呼び出しにはレート制限・リトライロジックが組み込まれていますが、運用時は API クォータや課金に注意してください。
- 監査ログは削除しない前提の設計です（FK は ON DELETE RESTRICT）。監査テーブルのサイズは監視してください。
- 本リポジトリは自動発注を含む機能を持ち得ます。実際の発注を有効化する場合は必ずシミュレーション（paper_trading）や十分なリスク管理を行ってください。

---

README の内容はコードベースに基づく概要・利用方法の抜粋です。各モジュールには詳細な docstring が記載されているので、実装やパラメータの挙動は該当ファイルを参照してください。必要であれば README にサンプルスクリプトや運用手順（systemd / cron / コンテナ化）のテンプレートを追加できます。どのような追加ドキュメントを望みますか？