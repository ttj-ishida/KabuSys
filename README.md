# KabuSys

日本株向け自動売買／データプラットフォームライブラリ (KabuSys)

簡潔な説明:
KabuSys は日本株のデータ収集（J-Quants）、品質チェック、特徴量計算、ニュースの NLP スコアリング（OpenAI）、市場レジーム判定、監査ログ（発注/約定トレース）などを統合する Python モジュール群です。ETL パイプラインやリサーチ用途のユーティリティ、実運用向けの監視・監査機能を含みます。

---

## 主な機能

- データ取得 / ETL
  - J-Quants からの日次株価（OHLCV）・財務データ・市場カレンダーの差分取得（ページネーション対応）
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）
  - ETL の実行結果を ETLResult として集約

- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出（前日比閾値）、重複チェック、日付整合性チェック
  - QualityIssue を返して呼び出し側で重み付け判断可能

- ニュース収集・NLP（OpenAI）
  - RSS からのニュース収集（SSRF 対策・トラッキングパラメータ除去）
  - ニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメント評価→ ai_scores 書込
  - マクロニュースを用いた市場レジーム判定（ETF 1321 の MA200 乖離 + マクロセンチメントの合成）

- リサーチ支援
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Spearman rank）計算、ファクター統計サマリー
  - z-score 正規化ユーティリティ

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions の監査スキーマ定義と初期化
  - order_request_id を冪等キーとして安全な発注トレーサビリティを実現

- 設定管理
  - .env ファイル（および環境変数）読み込み（プロジェクトルートを自動検出）
  - 必須設定の検証、環境別フラグ（development / paper_trading / live）

---

## 要件（主要）

- Python 3.10+
- 主要ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS）

（プロジェクトに requirements ファイルがある場合はそちらを参照してください）

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```bash
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成（推奨）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存ライブラリをインストール
   例:
   ```bash
   pip install duckdb openai defusedxml
   ```
   （実際の依存はプロジェクトの pyproject.toml / requirements.txt を参照してください）

4. パッケージを開発モードでインストール（任意）
   ```bash
   pip install -e .
   ```

5. 環境変数設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動でロードされます（自動ロードはプロジェクトルートを .git または pyproject.toml から検出）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 必須 / 推奨環境変数

下記は Settings クラスで参照される設定（主要なもののみ）。README に合わせて .env を作成してください。

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL で ID トークン取得に使用）
- KABU_API_PASSWORD (必須)
  - kabuステーション API のパスワード（発注等で使用）
- SLACK_BOT_TOKEN (必須)
  - Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)
  - Slack チャンネル ID
- OPENAI_API_KEY
  - OpenAI API キー（score_news / score_regime の既定）
- DUCKDB_PATH
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH
  - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - 監視設定
- KABUSYS_ENV (development | paper_trading | live)
- LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL)

注意: settings は .env / .env.local / OS 環境変数の優先順位で読み込みます（OS > .env.local > .env）。`.env.local` は上書きが許されます。

---

## 使い方（主要な例）

以下は最小限の使用例です。実際はログ設定やエラー処理・トランザクション管理を追加してください。

- DuckDB 接続を作って日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- OpenAI を使ってニューススコアを算出（ai.news_nlp.score_news）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY が環境変数に設定されているか、api_key 引数で渡す
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"wrote {n_written} ai_scores rows")
  ```

- 市場レジーム判定（ai.regime_detector.score_regime）
  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査スキーマ初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ":memory:" も可
  ```

- ニュース RSS を取得（保存処理は ETL 側で行ってください）
  ```python
  from kabusys.data.news_collector import fetch_rss
  articles = fetch_rss("https://news.yahoo.co.jp/rss/categories/business.xml", source="yahoo_finance")
  for a in articles:
      print(a["id"], a["title"], a["datetime"])
  ```

---

## 実運用上の注意

- Look-ahead bias の回避
  - AI スコアやレジーム判定は内部で target_date 未満のデータのみを参照するよう設計されています。API 呼び出しや日付選択でもこの方針を維持してください。
- 冪等性
  - ETL 保存関数（save_daily_quotes 等）は ON CONFLICT DO UPDATE を使用しており、再実行による上書きを防止／整合性を確保します。
- エラーハンドリング
  - 外部 API（J-Quants / OpenAI）呼び出しにはリトライロジックを備えていますが、APIキーやネットワーク障害に対して適切な監視・アラートを設定してください。
- .env の取り扱い
  - `.env` に機密情報を置く場合はリポジトリ管理から除外してください（.gitignore に追加）。

---

## ディレクトリ構成（主要ファイル）

下記はパッケージ内の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py         # ニュース NLP（OpenAI） → ai_scores 書込み
    - regime_detector.py  # マクロ + MA200 による市場レジーム判定
  - data/
    - __init__.py
    - calendar_management.py  # JPX カレンダー管理（営業日判定等）
    - etl.py                  # ETL API 再エクスポート（ETLResult）
    - pipeline.py             # ETL パイプライン実装（run_daily_etl 等）
    - stats.py                # z-score 等の統計ユーティリティ
    - quality.py              # データ品質チェック
    - audit.py                # 監査スキーマ定義 / 初期化
    - jquants_client.py       # J-Quants API クライアント + 保存ロジック
    - news_collector.py       # RSS 収集・前処理
  - research/
    - __init__.py
    - factor_research.py      # ファクター計算（momentum / value / volatility）
    - feature_exploration.py  # 将来リターン / IC / 統計サマリー

（上記以外に strategy / execution / monitoring 等のサブパッケージが想定される __all__ 宣言あり）

---

## 開発 / テストに関するヒント

- 環境変数自動ロードはプロジェクトルートの検出に依存（.git または pyproject.toml）。テスト時は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して自動ロードを停止できます。
- OpenAI 呼び出しやネットワーク I/O 部分はユニットテストでモックしやすいように実装されています（例: news_nlp._call_openai_api / regime_detector._call_openai_api をパッチする）。
- DuckDB 接続はインメモリ(":memory:") を使えばテスト時にファイルの作成を伴わず実行できます。

---

## ライセンス・連絡先

（この README にライセンスや貢献方法、連絡先情報を追加してください）

---

README はプロジェクトの現状コードベースに基づいて作成しました。追加の使用例（戦略 -> 発注フロー、監視ランナー、Slack 通知等）や CI 設定、依存ファイル（pyproject.toml / requirements.txt / .env.example）があればさらに具体的な手順を追記できます。必要であれば .env.example のテンプレートや具体的な CLI 実行コマンドのサンプルを作成します。要望があれば教えてください。