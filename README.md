# KabuSys

KabuSys は日本株向けのデータ基盤・リサーチ・自動売買補助ライブラリです。  
DuckDB をデータストアとして利用し、J-Quants / RSS / OpenAI 等と連携してデータ取得・品質チェック・特徴量計算・ニュース NLP・市場レジーム判定・監査ログ初期化などの機能を提供します。

主な用途:
- 日次 ETL（株価・財務・カレンダー）の差分取得・保存
- ニュースの収集と銘柄単位の NLP スコアリング（OpenAI）
- 市場レジーム判定（ETF + マクロニュース）
- ファクター計算・特徴量探索（研究用途）
- データ品質チェック
- 発注・約定のトレーサビリティ用監査テーブル初期化

---

## 機能一覧

- 環境変数管理
  - `.env` / `.env.local` を自動読み込み（必要に応じて無効化可能）
- データ ETL
  - J-Quants から株価日足、財務、JPX カレンダーを差分取得・保存（ページネーション対応、レート制御・リトライ）
  - run_daily_etl を起点にカレンダー→株価→財務→品質チェックを実行
- データ品質チェック
  - 欠損、重複、スパイク（前日比閾値）、日付不整合などを検出
- ニュース収集 & NLP
  - RSS 収集（SSRF 対策・トラッキングパラメータ削除）
  - OpenAI（gpt-4o-mini）を用いた銘柄別センチメント算出（バッチ・リトライ実装）
- 市場レジーム判定
  - ETF (1321) の 200 日移動平均乖離とマクロニュース LLM 評価を合成して daily なレジームを保存
- 研究用ツール
  - モメンタム/バリュー/ボラティリティ等のファクター計算
  - 将来リターン計算、IC（Spearman）計算、統計サマリー、Zスコア正規化
- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions といった監査テーブルを DuckDB に初期化するユーティリティ

---

## 前提・依存関係

- Python 3.10+
- 主要依存パッケージ:
  - duckdb
  - openai
  - defusedxml
- 標準ライブラリで多くを実装しており、外部 heavy ライブラリ（pandas 等）には依存しません。

インストール例:
```bash
python -m pip install -e .
# または最低限
python -m pip install duckdb openai defusedxml
```

---

## セットアップ手順

1. リポジトリをクローン / 取得し、開発インストール（任意）:
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m pip install -e .
   ```

2. 必要な環境変数を設定（推奨: プロジェクトルートに `.env` を作成）
   - 主な環境変数:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
     - KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
     - OPENAI_API_KEY: OpenAI の API キー（score_news 等で未指定時に参照）
     - SLACK_BOT_TOKEN: Slack 通知用トークン（必須）
     - SLACK_CHANNEL_ID: Slack チャンネル ID（必須）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
     - KABUSYS_ENV: 実行環境 (development|paper_trading|live)（デフォルト: development）
     - LOG_LEVEL: ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)
   - 自動読み込み:
     - `kabusys.config` モジュールはプロジェクトルート（.git または pyproject.toml がある場所）から `.env` / `.env.local` を自動読み込みします。
     - 自動読み込みを無効化する場合:
       ```bash
       export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
       ```

3. DuckDB データベースの準備
   - デフォルトパス: `data/kabusys.duckdb`。必要に応じて `DUCKDB_PATH` を設定。
   - 監査ログ専用 DB を作る:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     ```

---

## 使い方（主要な API と例）

以下はライブラリの典型的な使い方例です。各関数は DuckDB の接続を受け取り処理します。

- DuckDB 接続を作成:
  ```python
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  ```

- 日次 ETL 実行:
  ```python
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  # target_date を省略すると今日の日付を使用
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントのスコアリング（OpenAI API キーを環境変数 OPENAI_API_KEY に設定するか、api_key 引数で渡す）:
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定:
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 研究用ファクター計算:
  ```python
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date

  mom = calc_momentum(conn, date(2026,3,20))
  val = calc_value(conn, date(2026,3,20))
  vol = calc_volatility(conn, date(2026,3,20))
  ```

- 監査スキーマの初期化（既存 DuckDB 接続に対して）:
  ```python
  from kabusys.data.audit import init_audit_schema
  init_audit_schema(conn, transactional=True)
  ```

- 環境設定を直接参照:
  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  print(settings.is_live)
  ```

ログや例外は各モジュールで出力／送出されるため、呼び出し側で適切にログ設定（logging.basicConfig 等）や例外ハンドリングを行ってください。

---

## ディレクトリ構成

主要なファイル・モジュール構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                     # 環境変数・設定管理
    - ai/
      - __init__.py
      - news_nlp.py                 # ニュース NLP スコアリング
      - regime_detector.py          # 市場レジーム判定
    - data/
      - __init__.py
      - jquants_client.py           # J-Quants API クライアント（ETL 用）
      - pipeline.py                 # ETL パイプライン（run_daily_etl 等）
      - quality.py                  # データ品質チェック
      - calendar_management.py      # マーケットカレンダー関連ユーティリティ
      - news_collector.py           # RSS 収集・前処理
      - stats.py                    # 統計ユーティリティ（zscore 等）
      - audit.py                    # 監査ログ初期化
      - etl.py                      # ETL 結果クラスの公開（ETLResult）
    - research/
      - __init__.py
      - factor_research.py          # モメンタム/バリュー/ボラティリティ計算
      - feature_exploration.py      # forward returns / IC / サマリーなど

補足:
- 各モジュールは DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り DB のテーブル群（raw_prices, raw_financials, raw_news, ai_scores, market_regime, market_calendar 等）を参照・更新します。
- DB スキーマ定義はこちらの README に含まれていないため、実際の運用では最初に必要なスキーマ作成を行ってください（ETL 実行や audit.init などがテーブル作成を行うものもあります）。

---

## 注意事項 / 運用上のポイント

- "Look-ahead bias" を防ぐ設計思想で実装されています。target_date に対して未来データを参照しないよう工夫されています（内部で date.today() を使わない等）。
- OpenAI 呼び出しは外部 API を利用するため、API レート・コストに注意してください。API キーは環境変数または関数引数で注入してください。
- J-Quants API のレート制御・トークンリフレッシュ・リトライは jquants_client に実装されていますが、本番運用時は API 利用規約に従ってください。
- DuckDB の executemany の挙動（バージョン差）に依存する箇所があるため、推奨する DuckDB バージョンで動作確認を行ってください。
- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml）を基準とします。テストなどで無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

---

## ライセンス / 貢献

この README はコードベースから自動生成したドキュメントサマリです。リポジトリの LICENSE ファイルや CONTRIBUTING ポリシーに従ってください。

不明点や追加したいドキュメント項目があれば知らせてください。README のサンプル .env や schema 初期化手順を追加で用意できます。