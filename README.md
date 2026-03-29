# KabuSys

KabuSys は日本株向けの自動売買／データプラットフォーム用ライブラリです。  
データ収集（J-Quants API、RSS ニュース）、ETL、データ品質チェック、特徴量計算（リサーチ）、AI ベースのニュースセンチメント判定、監査ログ（発注トレース）など、自動売買システム構築に必要なコンポーネント群を提供します。

バージョン: 0.1.0

---

## 主要な機能

- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（ページネーション・レート制御・トークン自動更新対応）
  - 日次 ETL パイプライン（差分取得・バックフィル・品質チェック）
- ニュース収集・NLP
  - RSS フィードから記事収集（SSRF・Gzip・サイズ制限等の安全対策）
  - OpenAI（gpt-4o-mini）を用いたニュースセンチメント解析（銘柄単位、JSON Mode 対応、リトライ＆検証）
  - マクロニュース + ETF MA200乖離を合成した市場レジーム判定（bull/neutral/bear）
- データ品質管理
  - 欠損、重複、スパイク（前日比）や日付整合性チェックを実装
  - QualityIssue を集約して ETL 結果に付与
- リサーチ / 特徴量
  - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR）、バリュー（PER/ROE）、流動性等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
  - Zスコア正規化ユーティリティ
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions を含む監査用スキーマの初期化ユーティリティ（DuckDB）
  - 発注フローを UUID ベースで完全トレース可能に保存
- 設定管理
  - .env ファイル / 環境変数からの設定読み込み（自動ロード機能、無効化フラグあり）

---

## 動作環境・前提

- Python 3.10+
  - typing の `X | Y` 構文を使用しているため 3.10 以上を想定しています
- 必要な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセスが必要（J-Quants API、RSS、OpenAI 等）
- DuckDB をデータストアとして利用（既定パス: data/kabusys.duckdb）

---

## セットアップ手順（開発環境向け）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成と有効化（任意）
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows (PowerShell)
   ```

3. 依存パッケージをインストール（プロジェクトで requirements.txt を用意している場合はそれを使用）
   必要な主要パッケージ例：
   ```bash
   pip install duckdb openai defusedxml
   ```
   ※ プロダクションでは requirements.txt / poetry / pyproject.toml を利用してください。

4. 環境変数設定
   - プロジェクトルートに `.env` または `.env.local` を置くと自動読み込みされます（自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。
   - 必須環境変数（例）
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン
     - KABU_API_PASSWORD: kabuステーション API 用パスワード
     - SLACK_BOT_TOKEN: Slack 通知用 Bot トークン
     - SLACK_CHANNEL_ID: Slack の通知先チャネル ID
     - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
   - 任意 / デフォルトあり
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
     - LOG_LEVEL (DEBUG/INFO/...) — デフォルト `INFO`
     - KABU_API_BASE_URL — デフォルト `http://localhost:18080/kabusapi`
     - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
     - SQLITE_PATH — デフォルト `data/monitoring.db`

   例 .env（テンプレート）
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データディレクトリ作成（DuckDB ファイルなどを保存するため）
   ```bash
   mkdir -p data
   ```

---

## 簡単な使い方（Python API 呼び出し例）

以下はライブラリを直接インポートして使う例です。実行前に環境変数を設定してください。

- DuckDB 接続の作成（ファイルベース）
  ```python
  import duckdb
  from pathlib import Path
  from kabusys.config import settings

  db_path = settings.duckdb_path  # Path オブジェクト
  conn = duckdb.connect(str(db_path))
  ```

- 日次 ETL を実行（run_daily_etl）
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日の日付が対象（ただし内部で営業日調整が行われます）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントを計算し ai_scores に書き込む
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  # OPENAI_API_KEY が環境変数に設定されている前提
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written {n_written} scores")
  ```

- 市場レジーム（bull/neutral/bear）を算出して保存
  ```python
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  # OpenAI API キーを引数で渡すことも可能
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査用スキーマ初期化（audit tables）
  ```python
  from kabusys.data.audit import init_audit_schema

  init_audit_schema(conn, transactional=True)
  ```

- 研究用ファクター計算例
  ```python
  from datetime import date
  from kabusys.research.factor_research import calc_momentum, calc_value, calc_volatility

  target = date(2026, 3, 20)
  mom = calc_momentum(conn, target)
  val = calc_value(conn, target)
  vol = calc_volatility(conn, target)
  ```

注意: 上記はライブラリをプログラムから呼ぶ方法です。実運用ではワーカーやバッチジョブ、CI/CD、スケジューラから呼ぶことを想定しています。

---

## よく使うエントリポイント（要旨）

- data.pipeline.run_daily_etl(...) — 日次 ETL（カレンダー取得 → 株価 → 財務 → 品質チェック）
- data.jquants_client.fetch_daily_quotes(...) / save_daily_quotes(...) — J-Quants API 取り回し
- data.news_collector.fetch_rss(...) — RSS 取得ユーティリティ
- ai.news_nlp.score_news(...) — ニュースの銘柄単位センチメント解析（ai_scores へ保存）
- ai.regime_detector.score_regime(...) — 市場レジーム判定（market_regime テーブルへ保存）
- data.audit.init_audit_db(...) / init_audit_schema(...) — 監査ログの初期化

---

## テスト・デバッグのためのヒント

- .env の自動読み込みを抑止したい場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```
- OpenAI 呼び出しやネットワーク依存処理はモックしやすいように設計されています（ユニットテストでは内部の _call_openai_api などを patch してください）。
- DuckDB はメモリモード（":memory:"）でテストすることも可能です。

---

## ディレクトリ構成

（主要ファイル・モジュールのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - data/
      - __init__.py
      - calendar_management.py
      - etl.py
      - pipeline.py
      - stats.py
      - quality.py
      - audit.py
      - jquants_client.py
      - news_collector.py
      - (etl.py から ETLResult を再エクスポートする etl モジュール)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - (その他)
      - strategy/        # strategy 層用（パッケージ公開名に含まれるが実装は将来的に追加）
      - execution/       # execution 層用（発注ラッパー等、将来的に追加）
      - monitoring/      # 監視用コンポーネント（将来的に追加）

各モジュールは DuckDB 接続や外部 API クライアントを引数で受け取る設計になっており、テストやモジュール単位の再利用が容易です。

---

## 注意事項 / セキュリティ

- API キーやパスワードは必ず安全に保管し、ソース管理に含めないでください。
- news_collector は SSRF 対策、サイズ制限、XML パースの安全処理（defusedxml）を実装していますが、運用環境の要件に応じた追加対策を検討してください。
- 本ライブラリは発注機能の一部を含む設計を想定しています。実際にマネーを動かす前に、paper_trading 環境で十分な検証を行ってください（設定: KABUSYS_ENV=paper_trading / live）。

---

## 貢献・拡張

- 新しいデータソースや戦略（strategy 層）、発注アダプタ（execution 層）、監視（monitoring）を追加することでシステムを拡張できます。
- モジュールは比較的小さな責務に分けられているため、単体テストを追加しやすい設計です。

---

README の内容やサンプルが実際の運用スクリプト（cron や Airflow、Kubernetes CronJob 等）に落とし込まれる場合、環境変数・シークレット管理、監査ログの永続化、エラーハンドリング方針をプロダクション要件に合わせて調整してください。必要であれば具体的な運用例や systemd/cron/Airflow 用のサンプルも作成します。必要なら教えてください。