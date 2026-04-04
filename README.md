# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ。J-Quants / RSS / OpenAI（LLM）などの外部データを取り込み、ETL・品質チェック・ファクター計算・ニュースNLP・市場レジーム判定・監査ログなどのユーティリティを提供します。

---

## プロジェクト概要

KabuSys は以下の目的で設計された Python パッケージです。

- J-Quants API から株価日足・財務・マーケットカレンダー等を差分取得して DuckDB に保存する ETL パイプライン
- RSS ニュース収集と OpenAI を使った銘柄別センチメント（ai_score）算出
- マクロセンチメントと ETF（1321）の移動平均乖離を組み合わせた市場レジーム判定（bull/neutral/bear）
- ファクター計算、将来リターン・IC 計算などのリサーチユーティリティ
- データ品質チェック、監査ログ（signal → order_request → execution のトレーサビリティ）
- 安全性を考慮した実装（SSRF 防止、レスポンスサイズ制限、API レート管理、フェイルセーフ）

パッケージはモジュール単位で機能が分離されており、バックテスト・研究用途と本番実行（発注）用途で使い分け可能です。

---

## 主な機能一覧

- ETL
  - run_daily_etl / run_prices_etl / run_financials_etl / run_calendar_etl（jquants_client 経由で差分取得・保存）
  - ETLResult による実行結果集約と品質チェック（quality.run_all_checks）

- データ品質管理
  - 欠損・重複・スパイク・日付不整合チェック（data.quality）

- ニュース収集・NLP
  - RSS 取得と原文前処理（data.news_collector）
  - OpenAI を用いたニュースセンチメント集約・銘柄別 ai_score 書き込み（ai.news_nlp.score_news）

- 市場レジーム判定
  - ETF 1321 の MA 乖離 + マクロ記事の LLM センチメントを合成して日次レジーム判定（ai.regime_detector.score_regime）

- リサーチ / ファクター
  - momentum / value / volatility のファクター計算（research.factor_research）
  - 将来リターン、IC、統計サマリー等（research.feature_exploration）
  - Z スコア正規化ユーティリティ（data.stats.zscore_normalize）

- データ取得クライアント
  - J-Quants API 用クライアント（data.jquants_client）: レート制御・リトライ・トークンリフレッシュ・保存用の save_* 関数を提供

- 監査ログ（オーダートレーサビリティ）
  - audit テーブル定義 / 初期化ユーティリティ（data.audit.init_audit_db / init_audit_schema）

---

## 必須・推奨の環境変数

自動で .env（プロジェクトルート）および .env.local をロードします（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（実行する機能に依存）:
- JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（get_id_token に使用）
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- KABU_API_PASSWORD: kabuステーション API パスワード（注文実行を行う場合）

その他（デフォルト値あり）:
- KABUSYS_ENV: 環境。'development' | 'paper_trading' | 'live'（デフォルト: development）
- LOG_LEVEL: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'（デフォルト: INFO）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

警告: .env の読み込み優先順は OS 環境変数 > .env.local > .env です。重要な OS 環境変数は保護されます。

---

## セットアップ手順（開発 / ローカル実行）

以下は一般的な手順例です。プロジェクトの packaging / requirements ファイルに従ってください。

1. 仮想環境を作成・有効化
   - python >= 3.10 を推奨

2. 依存パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際の requirements.txt / pyproject.toml がある場合はそれに従ってください。

3. パッケージをインストール（開発モード）
   - pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env`（または `.env.local`）を作成し、必要なキーを記載します。例:
     - JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_kabu_password
     - DUCKDB_PATH=data/kabusys.duckdb

   - 自動読み込みを止めたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時に便利）。

5. ディレクトリの準備
   - デフォルトの DB 保存先ディレクトリ（data/）などを作成します。
     - mkdir -p data

---

## 使い方（主要 API・実行例）

以下は Python スクリプトや REPL での利用例です。すべて DuckDB 接続（duckdb.connect）を渡して使用します。

- ETL（デイリー ETL を実行）
  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl, ETLResult
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  result: ETLResult = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュース NLP スコア算出（OpenAI 必須）
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  from kabusys.config import settings

  conn = duckdb.connect(str(settings.duckdb_path))
  # OPENAI_API_KEY が環境変数にある場合は api_key 引数は省略可
  n_written = score_news(conn, target_date=date(2026, 3, 20))
  print("書き込んだ銘柄数:", n_written)
  ```

- 市場レジーム判定
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect(str(settings.duckdb_path))
  score_regime(conn, target_date=date(2026, 3, 20))
  ```

- 監査ログ DB 初期化（監査用 DuckDB）
  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")  # ディレクトリがなければ自動作成
  ```

- ファクター計算例
  ```python
  from kabusys.research.factor_research import calc_momentum
  from datetime import date
  conn = duckdb.connect("data/kabusys.duckdb")
  rows = calc_momentum(conn, target_date=date(2026, 3, 20))
  print(len(rows), "銘柄のモメンタム計算結果")
  ```

注意点:
- LLM 呼び出し（OpenAI）はネットワーク・API レート制御の影響を受けます。テストでは _call_openai_api をモックしてください。
- ETL は差分更新で動作します。初回ロードでは過去開始日から取得するため時間がかかります。

---

## ディレクトリ構成（主要ファイル）

※ ここでは src/kabusys 配下の主要モジュールを抜粋して説明します。

- src/kabusys/__init__.py
  - パッケージのメタ情報（__version__）と公開モジュール定義

- src/kabusys/config.py
  - 環境変数読み込み・Settings クラス（設定値へのプロパティアクセス）
  - .env 自動読み込みロジック（.env / .env.local）

- src/kabusys/ai/
  - news_nlp.py: ニュースをまとめて OpenAI に投げ、銘柄別 ai_score を ai_scores テーブルへ書き込む
  - regime_detector.py: ETF(1321)の MA とマクロ記事の LLM センチメントを合成して market_regime を更新
  - __init__.py: score_news を再エクスポート

- src/kabusys/data/
  - jquants_client.py: J-Quants API クライアント（取得＋DuckDB 保存用 save_* 関数）
  - pipeline.py: ETL パイプラインのメイン実装（run_daily_etl など）
  - etl.py: ETLResult の再エクスポート
  - news_collector.py: RSS フィード取得・前処理・raw_news 保存
  - calendar_management.py: 市場カレンダーの操作・営業日判定・更新ジョブ
  - quality.py: データ品質チェックと QualityIssue 定義
  - stats.py: zscore_normalize 等の統計ユーティリティ
  - audit.py: 監査ログ（signal / order_request / executions）スキーマ初期化

- src/kabusys/research/
  - factor_research.py: momentum / volatility / value 等のファクター計算
  - feature_exploration.py: 将来リターン / IC / 統計サマリー等
  - __init__.py: 研究用 API の再エクスポート

---

## 開発・テストのヒント

- 環境依存を切り離す
  - OpenAI 呼び出しやネットワーク I/O はモック可能です。テストでは kabusys.ai.news_nlp._call_openai_api や kabusys.ai.regime_detector._call_openai_api を patch してください。
  - J-Quants クライアントの _request はネットワークアクセスを行うため、unit test では jq.fetch_* / save_* の呼び出しをモックすることを推奨します。

- 自動 .env ロードの無効化
  - テスト実行時に環境を制御したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして自動ロードを無効にできます。

- データベース
  - DuckDB のインメモリを使う場合は db_path に ":memory:" を指定できます（data.audit.init_audit_db 等）。

- ロギング
  - settings.log_level を環境変数 LOG_LEVEL で設定できます。テストやデバッグ時は DEBUG にすると詳細が出力されます。

---

## その他

- セキュリティ・安全性設計
  - news_collector では SSRF 対策、レスポンスサイズ制限、XML の安全パーサ（defusedxml）を使用しています。
  - jquants_client はレート制御、トークン自動リフレッシュ、リトライを実装しています。

- 注意
  - 本ライブラリの一部（発注実行など）は実際の資金を動かす可能性があります。本番で利用する際は必ず十分な検証・監査を行ってください。
  - Look-ahead bias を防ぐため、モジュール内では基本的に datetime.today()/date.today() を直接参照しない設計になっています（関数引数で日付を受け取る）。

---

ご要望があれば README に含める具体的な実行スクリプト例（cron、systemd、docker-compose 用のサンプル）、または requirements.txt / pyproject.toml のテンプレート案を作成します。