# KabuSys

バージョン: 0.1.0

KabuSys は日本株のデータパイプライン、ファクター計算、ニュース NLP（LLM）によるセンチメント解析、監査ログおよび市場カレンダー管理を備えた日本株自動売買 / 研究プラットフォームのコアライブラリです。

主な目的はデータ取得（J-Quants）、品質チェック、特徴量（ファクター）生成、LLM を使ったニューススコアリング、そして売買監査ログの管理を一貫して行えるようにすることです。

---

## 特徴一覧

- データ ETL（J-Quants API → DuckDB）
  - 株価日足 / 財務データ / 市場カレンダーの差分取得・保存（冪等）
  - レート制限遵守 / リトライ / トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合検出（QualityIssue）
- ニュース収集と NLP（LLM）
  - RSS からニュースを収集して raw_news に保存
  - gpt-4o-mini を用いた銘柄別ニュースセンチメント（score_news）
  - マクロニュースと ETF（1321）200日MA乖離を組み合わせた市場レジーム判定（score_regime）
  - API 呼び出しは堅牢なリトライとフォールバック（失敗時はスコアを 0 にフォールバック）
- 研究用ファクター計算
  - Momentum / Value / Volatility / Liquidity 等のファクター計算関数
  - 将来リターン計算、IC（スピアマン）計算、Z スコア正規化等
- 監査ログ（audit）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - 監査 DB を DuckDB として初期化する関数を提供
- マーケットカレンダー管理
  - market_calendar の差分更新ジョブ（J-Quants 取得）
  - 営業日判定 / next/prev_trading_day / get_trading_days 等のユーティリティ

---

## 前提・依存

主要な実行依存例（プロジェクトに requirements.txt がある前提で）：
- Python 3.9+
- duckdb
- openai（または OpenAI の公式 SDK v1 相当）
- defusedxml
- その他標準ライブラリ（urllib, json, datetime 等）

（利用環境に合わせて pip / Poetry / PDM 等で依存を管理してください。）

---

## 環境変数（主要）

プロジェクトは .env / .env.local / 環境変数から設定を自動ロードします（ただしパッケージ内でプロジェクトルートが検出できる場合のみ）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須・よく使うもの:
- JQUANTS_REFRESH_TOKEN
  - J-Quants のリフレッシュトークン（fetch 系 API に必要）
- KABU_API_PASSWORD
  - kabuステーション API のパスワード（発注機能を使う場合）
- OPENAI_API_KEY
  - OpenAI（LLM） の API キー（score_news / score_regime で使用）

オプション:
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
- CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト: INFO）

settings オブジェクトは kabusys.config.settings から参照できます。

---

## セットアップ手順（例）

1. リポジトリを取得
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存インストール（プロジェクトの管理方法に応じて）
   - requirements.txt がある場合:
     ```
     pip install -r requirements.txt
     ```
   - 必要最低限（例）
     ```
     pip install duckdb openai defusedxml
     ```

4. .env を作成（プロジェクトルートに配置）
   - 例（最低限）
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_password
     DUCKDB_PATH=data/kabusys.duckdb
     ```

   - 自動ロードは .env → .env.local の順で行われ、OS 環境変数が最優先です。

5. データディレクトリ作成（必要に応じて）
   ```
   mkdir -p data
   ```

---

## 使い方（主要な API と実行例）

以下はライブラリをインポートして各処理を呼ぶ一例です。実行はプロジェクトのコンテキストで行ってください。

- DuckDB 接続と ETL（日次パイプライン）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")  # settings.duckdb_path を使っても良い
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（score_news）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None なら OPENAI_API_KEY を使用
  print(f"書き込み銘柄数: {written}")
  ```

- 市場レジーム判定（score_regime）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- 監査 DB の初期化
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  # テーブルが作成され、UTC タイムゾーンが設定される
  ```

- マーケットカレンダー更新ジョブ単体
  ```python
  from kabusys.data.calendar_management import calendar_update_job
  conn = duckdb.connect("data/kabusys.duckdb")
  saved = calendar_update_job(conn)
  print(f"保存したカレンダーレコード数: {saved}")
  ```

注意点:
- OpenAI 呼び出しは gpt-4o-mini を使用し JSON Mode で厳格な JSON 応答を期待しています。API 失敗時はフェイルセーフでスコアを 0 にフォールバックする設計です。
- テスト時は内部の _call_openai_api を unittest.mock で差し替えることで外部 API に依存しないテストが可能です（score_news/_score_chunk、regime_detector/_score_macro 等）。
- DuckDB の executemany に空リストを渡すとエラーとなるバージョンがあるため、コード内で保護されています。

---

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要部分（src/kabusys 以下）です。実際のリポジトリには追加ファイル（pyproject.toml, README, tests 等）がある想定です。

- src/kabusys/
  - __init__.py
  - config.py                # 環境設定・.env 自動ロード・Settings
  - ai/
    - __init__.py
    - news_nlp.py            # ニュース NLU / score_news
    - regime_detector.py     # マクロ + ETF MA による market regime
  - data/
    - __init__.py
    - calendar_management.py # market calendar 更新・営業日ヘルパー
    - pipeline.py            # ETL ランナー（run_daily_etl 等）
    - jquants_client.py      # J-Quants API クライアント + 保存関数
    - news_collector.py      # RSS 取得・前処理・保存
    - quality.py             # データ品質チェック
    - stats.py               # zscore_normalize 等
    - audit.py               # 監査ログ定義・初期化
    - etl.py                 # ETLResult 再エクスポート
  - research/
    - __init__.py
    - factor_research.py     # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py # calc_forward_returns / calc_ic / factor_summary / rank
  - (その他 strategy, execution, monitoring 用のパッケージが __all__ に定義される想定)

---

## 開発・テストに関するヒント

- 環境変数の自動読み込みはパッケージ起点でプロジェクトルート（.git または pyproject.toml）を探索して .env を読みます。テストで明示的に環境制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- OpenAI 呼び出しは内部で _call_openai_api という関数を経由しているため、テストではこの関数をモックすると簡単に外部依存を切れます。
- J-Quants API へのアクセスは jquants_client の _request 関数を通じて行われます。get_id_token は自動でリフレッシュを試みます。HTTP 呼び出しをモックしたい場合は urllib.request.urlopen 等をモックしてください。
- DuckDB のスキーマ初期化や監査 DB 初期化には init_audit_db / init_audit_schema を使用してください。

---

## トラブルシューティング（よくある問題）

- .env が読み込まれない
  - プロジェクトルートが .git または pyproject.toml で検出できないと自動読み込みはスキップされます。ルートに配置するか手動で環境変数をセットしてください。
- OpenAI からのレスポンスが JSON でない・パースできない
  - コードは JSON 以外を受け取った場合にフォールバックしてスコアを 0 とするよう設計されています。レスポンスのログを確認してプロンプトやモデルを調整してください。
- DuckDB executemany 空パラメータでエラー
  - コード側で空チェックがあるため通常は回避されますが、独自に executemany を使う場合は空リストを渡さないでください。

---

## ライセンス・貢献

この README にはライセンス情報は含まれていません。実プロジェクトでは LICENSE ファイルを確認し、貢献ガイドライン（CONTRIBUTING.md）に従ってください。

---

以上。追加で README に載せたい具体的なコマンドやサンプル（Docker / systemd / cron ジョブ等）があれば教えてください。README をさらに詳細化して実運用手順（例: ETL の cron 設定、監視/アラート設定、バックテスト用のデータ取り扱いガイドなど）を追記します。