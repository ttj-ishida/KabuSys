# KabuSys

日本株向けの自動売買 / データ基盤ライブラリ群です。  
ETL、ニュース収集・NLP（LLM）によるセンチメント評価、マーケットレジーム判定、リサーチ（ファクター計算）、監査ログ（発注トレーサビリティ）などを提供します。

- 対象言語: Python (3.10+ 推奨)
- 主な外部依存: duckdb, openai, defusedxml（用途に応じて追加パッケージが必要）

---

## 概要

KabuSys は以下の機能を持つモジュール群から構成されるライブラリです。

- データ取得・ETL（J-Quants API 連携）
- ニュース収集（RSS）と前処理
- ニュースの LLM（OpenAI）による銘柄別センチメントスコア生成（ai.news_nlp）
- マクロニュース＋ETF MA を用いた市場レジーム判定（ai.regime_detector）
- research: ファクター計算（モメンタム / バリュー / ボラティリティ）と特徴量解析ユーティリティ
- data: カレンダー管理、品質チェック、監査ログ（audit）などのデータ基盤ユーティリティ
- 環境設定管理（config.Settings）と .env 自動ロード

設計方針として、ルックアヘッドバイアスの回避、ETL の冪等性、API 呼び出しの堅牢なリトライなどを重視しています。

---

## 機能一覧

- ETL（data.pipeline.run_daily_etl）
  - 市場カレンダー、株価、財務データの差分取得・保存
  - 品質チェック（欠損・スパイク・重複・日付不整合）
- J-Quants クライアント（data.jquants_client）
  - 認証トークン取得、自動リフレッシュ、ページネーション対応
  - レート制御とリトライ戦略
  - DuckDB への冪等保存関数（raw_prices / raw_financials / market_calendar 等）
- ニュース収集（data.news_collector）
  - RSS から記事を収集、前処理、記事ID 発行（正規化 URL → SHA-256）
  - SSRF 対策、サイズ制限、XML 安全パース
- ニュース NLP（ai.news_nlp）
  - 指定ウィンドウのニュースを銘柄別に集約し OpenAI（gpt-4o-mini）でスコア化
  - バッチ処理、レスポンス検証、スコアのクリップ、DuckDB への書き込み（ai_scores）
- レジーム判定（ai.regime_detector）
  - ETF（1321）の 200 日 MA 乖離とマクロニュース LLM スコアを重み合成して market_regime に保存
  - フェイルセーフ動作（API 失敗時は中立扱い）
- リサーチ（research）
  - calc_momentum / calc_value / calc_volatility 等のファクター計算
  - forward returns, IC 計算, 統計サマリー、Z スコア正規化
- 監査ログ（data.audit）
  - signal_events / order_requests / executions の監査スキーマ定義と初期化ヘルパー
  - 監査用 DuckDB 初期化関数（init_audit_db）
- 環境設定自動ロード（config）
  - プロジェクトルートの .env / .env.local を自動ロード（OS 環境変数を保護）
  - Settings クラスでアプリ設定を参照（必須環境変数は _require で検査）

---

## セットアップ手順

1. Python の準備（3.10 以上を推奨）

2. リポジトリをクローン / コピーしてパッケージをインストール
   - 開発環境で editable install:
     ```bash
     pip install -e .
     ```
   - 必要ライブラリ（例）:
     ```bash
     pip install duckdb openai defusedxml
     ```
     ※ 実行する機能により他パッケージが必要になる場合があります（例: Slack 通知等）。

3. 環境変数の設定
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` と `.env.local` を配置できます。
   - 自動読み込みはデフォルトで有効。テスト等で無効化するには環境変数を設定します:
     ```bash
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN：J-Quants のリフレッシュトークン（必須）
     - KABU_API_PASSWORD：kabuステーション API パスワード（本システムの一部で使用）
     - SLACK_BOT_TOKEN：Slack ボットトークン（通知用）
     - SLACK_CHANNEL_ID：通知先チャンネル ID
     - OPENAI_API_KEY：OpenAI API キー（score_news / score_regime にも引数で注入可能）
     - DUCKDB_PATH：DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH：SQLite（監視用）パス（デフォルト data/monitoring.db）
     - KABUSYS_ENV： development / paper_trading / live（デフォルト development）
     - LOG_LEVEL：ログレベル（DEBUG/INFO/...、デフォルト INFO）

   - .env の例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token_here
     OPENAI_API_KEY=sk-xxxx...
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C01234567
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```

4. データベース初期化（監査DB を使う場合）
   - 監査用 DuckDB を初期化:
     ```python
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")
     # これで監査スキーマ（signal_events, order_requests, executions）が作成されます
     ```

---

## 使い方（代表的な API と例）

以下は Python スクリプトから直接呼び出す基本例です。DuckDB 接続には `duckdb.connect(path)` を利用します。

1. ETL 日次処理の実行
   ```python
   import duckdb
   from datetime import date
   from kabusys.data.pipeline import run_daily_etl

   conn = duckdb.connect("data/kabusys.duckdb")
   result = run_daily_etl(conn, target_date=date(2026, 3, 20))
   print(result.to_dict())
   ```

2. ニューススコアリング（ai.news_nlp.score_news）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.news_nlp import score_news

   conn = duckdb.connect("data/kabusys.duckdb")
   # OPENAI_API_KEY を環境変数に設定済みであれば api_key 引数は不要
   written = score_news(conn, target_date=date(2026, 3, 20))
   print(f"書き込んだ銘柄数: {written}")
   ```

3. 市場レジーム判定（ai.regime_detector.score_regime）
   ```python
   import duckdb
   from datetime import date
   from kabusys.ai.regime_detector import score_regime

   conn = duckdb.connect("data/kabusys.duckdb")
   score_regime(conn, target_date=date(2026, 3, 20))
   ```

4. ファクター計算（research）
   ```python
   import duckdb
   from datetime import date
   from kabusys.research import calc_momentum, calc_value, calc_volatility

   conn = duckdb.connect("data/kabusys.duckdb")
   mom = calc_momentum(conn, date(2026, 3, 20))
   val = calc_value(conn, date(2026, 3, 20))
   vol = calc_volatility(conn, date(2026, 3, 20))
   ```

5. 監査スキーマ初期化（既存接続への追加）
   ```python
   import duckdb
   from kabusys.data.audit import init_audit_schema

   conn = duckdb.connect("data/kabusys.duckdb")
   init_audit_schema(conn, transactional=True)
   ```

注意点:
- score_news / score_regime は OpenAI API を呼びます。API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
- ETL・API 呼び出しはネットワークや外部サービスに依存するため、例外処理やログ監視を行ってください。
- DuckDB の executemany に空リストを渡すと問題になるバージョンがあるため、コード内で空チェックがなされています。

---

## .env 自動読み込みについて（config モジュール）

- config モジュールはパッケージの実ファイルの位置から上位ディレクトリを探索してプロジェクトルートを特定します（.git または pyproject.toml が目印）。
- 自動ロード順序:
  1. OS 環境変数（既存）
  2. .env（プロジェクトルート）
  3. .env.local（.env を上書き、OS 環境変数は保護）
- 無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用）。
- .env のパーサは `export KEY=val` 形式、シングル/ダブルクォート、行中コメントなどに対応しています。

---

## ディレクトリ構成（主要ファイル）

以下はパッケージ内の主要モジュール構成です（path はプロジェクト内部の src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定管理
  - ai/
    - __init__.py
    - news_nlp.py         — ニュースセンチメントスコア生成（OpenAI）
    - regime_detector.py  — 市場レジーム判定（ETF MA + マクロセンチメント）
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 + DuckDB 保存）
    - pipeline.py         — ETL パイプライン本体（run_daily_etl 等）
    - etl.py              — ETLResult の再エクスポート
    - news_collector.py   — RSS 収集・前処理
    - calendar_management.py — マーケットカレンダーの管理と営業日ユーティリティ
    - stats.py            — 統計ユーティリティ（zscore_normalize）
    - quality.py          — データ品質チェック
    - audit.py            — 監査ログスキーマ初期化
  - research/
    - __init__.py
    - factor_research.py  — モメンタム/バリュー/ボラティリティ計算
    - feature_exploration.py — forward returns, IC, summary, rank

上記の各モジュールは、DuckDB 接続オブジェクト（duckdb.DuckDBPyConnection）を受け取る設計のものが多く、テストしやすく分離された責務を持ちます。

---

## 運用上の注意 / ベストプラクティス

- OpenAI や J-Quants の API キーは機密情報です。CI や本番では安全なシークレット管理を利用してください。
- レジーム判定 / ニューススコアは外部 API に依存するため、API 障害時のフォールバック（コード内で用意）を理解してください（多くの箇所で 0.0 などの中立値にフォールバックします）。
- DuckDB ファイルはバックアップやスナップショットを定期的に行ってください。
- run_daily_etl は複数ステップ（カレンダー→株価→財務→品質チェック）で動作します。運用時はログを監視し、result.has_errors / result.has_quality_errors をチェックしてアラートを出すと良いでしょう。
- 監査ログは削除しない前提で設計されています。ディスク管理（アーカイブやローテーション）を検討してください。

---

## 貢献 / 開発

- 型ヒント・ドキュメントが各関数に豊富に記載されています。新機能追加はまずユニットテストを追加してください。
- 自動ロードされる .env の振る舞いに依存するテストは、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化してください。
- OpenAI 呼び出しや外部ネットワーク呼び出しはユニットテストでモック可能な設計になっています（内部の _call_openai_api や _urlopen は差し替え可能）。

---

質問や特定機能の使い方サンプルが必要であれば教えてください。さらに具体的なコード例や運用手順（cron ジョブ例、ログ設定、監視設定など）も提供できます。