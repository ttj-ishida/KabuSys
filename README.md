# KabuSys — 日本株自動売買プラットフォーム（README）

KabuSys は日本株向けのデータプラットフォーム・調査・AI スコアリング・監査ログ・ETL および市場レジーム判定を備えた自動売買支援ライブラリです。DuckDB を内部データベースとして用い、J-Quants API / RSS / OpenAI（LLM）など外部サービスと連携します。

> 注: この README はリポジトリのソースコード（src/kabusys 以下）に基づいて作成しています。

## 主な特徴 (Features)
- データ ETL
  - J-Quants からの日次株価（OHLCV）や財務データ、JPX カレンダーの差分取得・保存（冪等処理）
  - データ品質チェック（欠損・重複・スパイク・日付不整合）
- ニュース収集・NLP
  - RSS からのニュース収集（SSRF / トラッキング除去 / 前処理）
  - OpenAI を用いた銘柄ごとのニュースセンチメントスコア生成（ai_scores への保存）
- 市場レジーム判定
  - ETF(1321) の 200 日 MA 乖離 + マクロニュースセンチメントを合成して日次レジーム判定（bull / neutral / bear）
- リサーチ / ファクター計算
  - Momentum / Volatility / Value 等のファクター計算、将来リターン、IC（Information Coefficient）、統計サマリ
- 監査ログ（トレーサビリティ）
  - signal → order_request → execution の監査テーブルを DuckDB に準備するユーティリティ
- 運用・監視設定
  - PID / kill flag / CPU/MEM/DISK 閾値など設定により運用監視が可能
- 安全性を考慮した実装
  - API のレート制限・再試行、SSR F対策、XML パースの安全処理（defusedxml）など

## 動作環境 / 必要要件
- Python 3.10+
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
  - その他（標準ライブラリ以外を使う箇所があれば requirements.txt を参照）

（プロジェクトに requirements.txt / pyproject.toml がある場合はそちらを利用してください）

## セットアップ手順 (Setup)

1. リポジトリをクローン、仮想環境を作成・有効化
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate    # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   - もし pyproject.toml / requirements.txt がある場合はそれを利用
   ```
   pip install -U pip setuptools
   pip install duckdb openai defusedxml
   pip install -e .   # 開発インストール（パッケージ化されている場合）
   ```

3. 環境変数 / .env の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須の環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN  — J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD      — kabu ステーション API パスワード（必須）
     - OPENAI_API_KEY         — OpenAI API キー（news_nlp / regime_detector を利用する場合）
   - 任意/デフォルト:
     - KABU_API_BASE_URL      — kabusapi のベース URL（デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH            — デフォルト: data/kabusys.duckdb
     - SQLITE_PATH            — 監視 DB（data/monitoring.db）
     - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など
   - 例 (.env):
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     KABU_API_PASSWORD=your_kabu_api_password
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     ```

4. データディレクトリの作成（必要なら）
   ```
   mkdir -p data
   ```

## 使い方（簡易ガイド / API 呼び出し例）

以下はライブラリ API を直接呼ぶ簡単な例です。実運用ではエラーハンドリングやログ設定を適切に行ってください。

- DuckDB 接続の作成（設定経由でパス取得）
  ```python
  import duckdb
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL（J-Quants からデータ取得して保存、品質チェック実行）
  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメントスコア（OpenAI を使って ai_scores を生成）
  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  n_written = score_news(conn, target_date=date(2026,3,20))
  print(f"scored {n_written} codes")
  ```

- 市場レジーム判定（ETF 1321 を用いた daily regime）
  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

- 監査ログ用テーブルの初期化（冪等）
  ```python
  from kabusys.data.audit import init_audit_db
  # または既存接続に対して:
  # from kabusys.data.audit import init_audit_schema
  init_conn = init_audit_db("data/audit.duckdb")
  ```

- リサーチ用ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, target_date=date(2026,3,20))
  print(len(records), "records")
  ```

- 手動で .env の自動読み込みを抑止する
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

### 注意点
- OpenAI を利用する箇所は API キー（OPENAI_API_KEY）を要します。キーが無いと ValueError を投げます。
- J-Quants API 呼び出しには JQUANTS_REFRESH_TOKEN が必須です。
- ETL 等はネットワーク/API に依存するため、実行には外部接続の許可・キーの設定が必要です。
- DuckDB に保存されるテーブルスキーマは code 中で参照されます。初期スキーマ作成ユーティリティが別にある場合はそちらを実行してください（例: data.schema.init_schema() 等、プロジェクト内にスキーマ初期化関数があれば利用）。

## ディレクトリ構成（src/kabusys の主要ファイル）
（本リポジトリの src/kabusys 以下の主要モジュールと役割の概観）

- kabusys/
  - __init__.py
  - config.py
    - 環境変数読み込み・設定管理（.env 自動ロード、Settings クラス）
  - ai/
    - __init__.py
    - news_nlp.py        — ニュースを OpenAI でスコアリングし ai_scores に保存
    - regime_detector.py — ETF MA とマクロニュースを合成して market_regime を生成
  - data/
    - __init__.py
    - jquants_client.py  — J-Quants API クライアント（取得・保存・レート制御・リトライ）
    - pipeline.py        — ETL パイプライン（run_daily_etl 等）
    - etl.py             — ETLResult の再エクスポート
    - news_collector.py  — RSS 収集と前処理、raw_news への保存ロジック
    - calendar_management.py — 市場カレンダー運用ロジック（営業日判定等）
    - quality.py         — データ品質チェック（欠損、スパイク、重複、日付整合性）
    - stats.py           — 汎用統計ユーティリティ（zscore 正規化など）
    - audit.py           — 監査ログ（signal/order_request/executions）のDDL と初期化
  - research/
    - __init__.py
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ、ランク関数

各モジュールはソース内に詳細なドキュメント（docstring）があるため、実装の意図や設計方針はコードの docstring を参照してください。

## 環境変数一覧（主なもの）
- JQUANTS_REFRESH_TOKEN (必須) — J-Quants リフレッシュトークン
- OPENAI_API_KEY (必要に応じて) — OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD (必須) — kabu ステーション API のパスワード
- KABU_API_BASE_URL — kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 通知用（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- KABUSYS_ENV — 環境 (development | paper_trading | live)
- LOG_LEVEL — ログレベル (DEBUG|INFO|WARNING|ERROR|CRITICAL)

## 開発・テスト
- 自動環境変数読み込みは config._find_project_root を用いて .git または pyproject.toml を探索します。
- テストや一時的な実行で自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI / J-Quants 呼び出しは各モジュールで再試行・フェイルセーフ処理が組み込まれています。ユニットテストでは該当関数をモックして外部 API への依存を切り離してください（コード内にモック用の patch コメントあり）。

## ライセンス / 貢献
- ライセンス情報や貢献ガイドがプロジェクトに含まれている場合はそれに従ってください。

---

README の内容は主要モジュールの実装に基づく要約です。詳細な使い方（スキーマ初期化、運用スクリプト、CLI）が必要な場合は、どの操作（ETL 自動化、ニュース収集の定期実行、監査ログ初期化など）について詳しく知りたいか教えてください。必要に応じてサンプルスクリプトや systemd / cron の設定例も作成します。