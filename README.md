# KabuSys

日本株向けの自動売買 / データ基盤用ライブラリ群です。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュースの NLP スコアリング、研究用ファクター計算、監査ログ（発注→約定トレーサビリティ）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株を対象としたデータプラットフォームと自動売買基盤のコンポーネント群です。主な目的は以下です。

- J-Quants API からの時系列データ・財務データ・市場カレンダーの取得と DuckDB への保存（ETL）
- ニュース収集・前処理および OpenAI を用いた記事/銘柄ごとのセンチメントスコアリング
- 市場レジーム判定（ETF の MA とマクロニュースの LLM センチメントの合成）
- 研究用ファクター計算（モメンタム、ボラティリティ、バリュー等）と統計ユーティリティ
- データ品質チェック（欠損・スパイク・重複・日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース）
- 設定管理（環境変数 / .env の自動読み込み、Settings オブジェクト）

この README はパッケージ内の主要な機能の使い方とセットアップ手順をまとめたものです。

---

## 主な機能一覧

- data
  - jquants_client: J-Quants API クライアント（差分取得 / ページング / 保存関数）
  - pipeline: 日次 ETL パイプライン（run_daily_etl）と個別 ETL ジョブ
  - quality: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector: RSS 収集・前処理ユーティリティ（SSRF 対策・XML サニタイズ）
  - calendar_management: 市場カレンダー操作・営業日判定
  - audit: 監査ログ（DDL / インデックス、init 関数）
  - stats: 汎用統計ユーティリティ（zscore_normalize）
- ai
  - news_nlp: ニュースの銘柄ごとセンチメントスコアリング（score_news）
  - regime_detector: ETF の MA とマクロニュースを合わせた市場レジーム判定（score_regime）
- research
  - factor_research: Momentum / Value / Volatility 等のファクター計算
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリー等
- config
  - Settings: 環境変数から値を読み取るユーティリティ（自動 .env ロード機能含む）

---

## セットアップ手順

以下はローカル環境で動かすための最小セットアップ例です。

1. Python 環境（3.10+ 推奨）を用意します。
2. 依存パッケージをインストールします（プロジェクトに requirements.txt がある場合はそれを使ってください）。代表的な依存は次の通りです:

   pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは追加依存（logging 設定やテストフレームワーク等）があるかもしれません。

3. 環境変数の設定（必須・推奨）
   - 必須:
     - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（ETL 用）
     - KABU_API_PASSWORD: kabu ステーション API のパスワード（発注連携が有る場合）
   - OpenAI 関連:
     - OPENAI_API_KEY: OpenAI を呼び出す場合に必要（score_news, score_regime）
   - その他（任意/デフォルトあり）:
     - KABUSYS_ENV: development / paper_trading / live（デフォルト development）
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB 等（デフォルト data/monitoring.db）
     - KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env の自動読込を無効化

   推奨: プロジェクトルートに .env を置くと config モジュールが自動で .env → .env.local を読み込みます（CWD に依存しないルート検出）。

4. プロジェクトルート例（.env.example）

   ```
   # .env.example
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
   OPENAI_API_KEY=sk-...
   KABU_API_PASSWORD=your_kabu_password
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   ```

5. データディレクトリ作成（必要に応じて）

   mkdir -p data

---

## 使い方（よく使う API の例）

以降の例は Python インタプリタ / スクリプト内で行います。

- Settings の使用（環境変数読み取り）

  ```python
  from kabusys.config import settings
  print(settings.duckdb_path)
  ```

  自動的にプロジェクトルートの .env / .env.local を読み込みます。自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DuckDB 接続の作成

  ```python
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))
  ```

- 日次 ETL を実行（run_daily_etl）

  ```python
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date

  # target_date を指定（省略時は today）
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

  run_daily_etl はカレンダー → 株価 → 財務 → 品質チェックの順で処理し ETLResult を返します。J-Quants の認証は settings.jquants_refresh_token を使用して自動取得します。テスト時は id_token を直接渡すことも可能です。

- ニュースのセンチメントスコア取得（銘柄単位）

  ```python
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  # OpenAI API キーは環境変数 OPENAI_API_KEY または api_key 引数で指定
  written = score_news(conn, target_date=date(2026, 3, 20))
  print(f"written scores: {written}")
  ```

  score_news は raw_news / news_symbols / ai_scores テーブルを参照し、取得後 ai_scores テーブルに結果を書き込みます。API 呼び出しは gpt-4o-mini を想定しています。失敗時は該当チャンクをスキップするフェイルセーフ設計です。

- 市場レジーム判定

  ```python
  from kabusys.ai.regime_detector import score_regime
  from datetime import date

  score_regime(conn, target_date=date(2026,3,20))
  ```

  ETF コード 1321 の 200 日 MA 乖離とマクロニュースの LLM スコアを合成し `market_regime` テーブルへ保存します。OpenAI API キーは環境変数か引数で指定してください。

- 監査ログ（監査 DB）の初期化

  ```python
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")
  ```

  init_audit_db は監査用テーブル（signal_events, order_requests, executions）とインデックスを冪等に作成します。デフォルトで transactional=True にして安全に初期化します（タイムゾーンを UTC にセット）。

- 研究用ファクター計算の呼び出し例

  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date

  records = calc_momentum(conn, date(2026,3,20))
  # records は [{ "date": ..., "code": "...", "mom_1m": ..., "ma200_dev": ... }, ...]
  ```

- データ品質チェック

  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=date(2026,3,20))
  for i in issues:
      print(i.check_name, i.severity, i.detail)
  ```

---

## 実行上の注意点 / ヒント

- OpenAI / J-Quants API の呼び出しは外部ネットワークを利用します。レート制限・課金に注意してください。
- LLM 呼び出しは失敗した場合でも概ねフェイルセーフで動くよう設計されています（スコアを 0 にする、チャンクをスキップする等）。
- DuckDB の executemany に空リストを渡すとエラーになるバージョンがあるため、関数内で空チェックがされています。
- .env の自動読み込みはプロジェクトルート（.git もしくは pyproject.toml を基準）を探索して行われます。CI/テスト時に自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- テストやモックが想定されている箇所（OpenAI 呼び出し、HTTP open）には差し替え可能な内部関数が存在します（unittest.mock.patch 等で差し替え可能）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                           # Settings / .env 自動ロード
  - ai/
    - __init__.py
    - news_nlp.py                        # score_news（News→ai_scores）
    - regime_detector.py                 # score_regime（market_regime）
  - data/
    - __init__.py
    - jquants_client.py                  # J-Quants API クライアント・保存関数
    - pipeline.py                        # ETL パイプライン（run_daily_etl 等）
    - etl.py                             # ETLResult 再エクスポート
    - quality.py                         # データ品質チェック
    - news_collector.py                  # RSS 取得・前処理
    - calendar_management.py             # 市場カレンダー / 営業日判定
    - audit.py                           # 監査ログ DDL / init
    - stats.py                           # zscore_normalize 等
  - research/
    - __init__.py
    - factor_research.py                 # calc_momentum / calc_value / calc_volatility
    - feature_exploration.py             # calc_forward_returns / calc_ic / factor_summary / rank

---

## トラブルシューティング

- "OpenAI API キーが未設定です" エラー:
  - OPENAI_API_KEY を環境変数に設定するか、score_news / score_regime の api_key 引数で渡してください。

- J-Quants の認証エラー:
  - JQUANTS_REFRESH_TOKEN が正しいか確認してください。jquants_client は 401 を受けると自動的にリフレッシュを試みます。

- DuckDB 関連エラー:
  - ファイルパスの親ディレクトリが存在するか確認してください（init_audit_db は親ディレクトリを自動作成しますが、他の接続や使用箇所で注意してください）。

---

## 開発・テスト向けメモ

- LLM / ネットワークを使う部分は、ユニットテスト時にモック化してテストしてください（モジュール内に差し替えポイントが用意されています）。
- ETL / 保存処理は冪等（ON CONFLICT DO UPDATE）で実装してあるため、繰り返し実行しても基本的に安全です。
- 日付の扱いは Look-ahead bias を避けるために内部で date.today() を使わない関数が多く、target_date を明示して呼び出すことを推奨します。

---

ライセンスや CI 設定、パッケージングに関する情報はプロジェクトルートの他ファイル（pyproject.toml 等）を参照してください。必要なら README を拡張して具体的な起動スクリプトや systemd / supervisor のサンプルも追加できます。