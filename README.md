# KabuSys

日本株向けのデータ基盤・研究・自動売買支援ライブラリです。  
ETL（J-Quants からのデータ取得・保存）、データ品質チェック、ニュース収集・NLP（OpenAI を用いたセンチメント解析）、ファクター計算・リサーチユーティリティ、監査ログ（発注→約定のトレーサビリティ）などを包含します。

主な目的は「ルックアヘッドバイアスを避けつつ安定してデータを収集・加工し、研究・運用に使える形で提供する」ことです。

---

## 機能一覧

- 環境・設定管理
  - .env 自動読み込み（プロジェクトルート検出、自動上書きルール、無効化フラグあり）
  - 必須環境変数の検証（settings オブジェクト経由）
- データ ETL（J-Quants API）
  - 株価日足（OHLCV）取得・保存（ページネーション、レートリミット、リトライ、冪等保存）
  - 財務データ取得・保存
  - JPX マーケットカレンダー取得・保存
  - 日次 ETL パイプライン（差分取得、バックフィル、品質チェック）
- データ品質チェック
  - 欠損、スパイク、重複、日付不整合チェック（QualityIssue を返却）
- ニュース収集
  - RSS フィード取得（SSRF 対策、gzip、サイズ制限、トラッキングパラメータ除去）
  - raw_news / news_symbols への冪等保存（実装参照）
- ニュース NLP / AI
  - ニュースの銘柄別センチメントスコアリング（OpenAI gpt-4o-mini, JSON mode）
  - マクロニュース + ETF(ma200乖離) を組み合わせた市場レジーム判定
  - バッチ・リトライ・レスポンス検証を考慮した堅牢な実装
- 研究支援（Research）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB + SQL ベース）
  - 将来リターン計算、IC（スピアマン）計算、Zスコア正規化 等
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等のテーブル作成・初期化ユーティリティ
  - 監査トレーサビリティ（UUID 階層）をサポート
- ユーティリティ
  - 汎用統計（zscore 正規化）など

---

## 必要条件 / 依存関係

- Python 3.9+
- 必須ライブラリ（主要なもの）
  - duckdb
  - openai
  - defusedxml
- その他、標準ライブラリのみで多くを実装しています。プロジェクトのパッケージングに合わせて requirements.txt / pyproject.toml を用意してください。

（実運用では OpenAI SDK と J-Quants の利用に必要な環境変数を設定する必要があります）

---

## 環境変数（主なもの）

以下は Settings クラスで参照される主要な環境変数です。README 内では大文字で示します。

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants API のリフレッシュトークン（get_id_token に使用）
- KABU_API_PASSWORD (必須)  
  kabuステーション等の API パスワード（使用箇所に依存）
- KABU_API_BASE_URL (任意)  
  デフォルト: http://localhost:18080/kabusapi
- SLACK_BOT_TOKEN (必須)  
  Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須)  
  Slack 通知先チャンネル ID
- DUCKDB_PATH (任意)  
  デフォルト: data/kabusys.duckdb
- SQLITE_PATH (任意)  
  デフォルト: data/monitoring.db
- KABUSYS_ENV (任意)  
  許容値: development / paper_trading / live （デフォルト development）
- LOG_LEVEL (任意)  
  許容値: DEBUG, INFO, WARNING, ERROR, CRITICAL （デフォルト INFO）
- OPENAI_API_KEY  
  OpenAI を呼ぶ関数で参照されます（score_news / score_regime の api_key 引数を省略した場合）

自動 .env 読み込み:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` / `.env.local` を自動で読み込みます。
- 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットすると自動読み込みを無効化できます（テスト時に有用）。

.env のパースはシェル形式に準拠（export KEY=val, クォート処理、コメントの扱い 等）しています。

---

## セットアップ手順（開発マシン）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトで pyproject.toml / requirements.txt があればそれに従ってください）
   - 開発インストール: pip install -e .

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数を直接設定します。
   - 例 `.env`（例示）:
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     KABU_API_PASSWORD=your_kabu_pass
     SLACK_BOT_TOKEN=xoxb-...
     SLACK_CHANNEL_ID=C0123456789
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development

5. DuckDB データベース初期化（監査ログ等）
   - 以下のように Python から初期化できます（data.audit を使用）:

     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/kabusys_audit.duckdb")

   - または既存の conn を渡して init_audit_schema を実行できます。

---

## 使い方（簡単な例）

以下は主要ユースケースのサンプルコード例です。事前に必要な環境変数が設定されていることを想定します。

1) DuckDB 接続を開いて日次 ETL を実行する

- 例:

    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    # target_date を指定しない場合は今日が使われます
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

2) ニュースセンチメントのスコアリング（OpenAI を使用）

- 例:

    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    # api_key を指定しない場合は環境変数 OPENAI_API_KEY を参照
    written = score_news(conn, target_date=date(2026, 3, 20))
    print(f"書き込んだ銘柄数: {written}")

3) 市場レジーム判定

- 例:

    import duckdb
    from datetime import date
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20))  # OpenAI API key via env or api_key arg

4) 監査ログ DB の初期化（発注/約定トレース用）

- 例:

    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/kabusys_audit.duckdb")
    # conn を保持して発注フローのログを書き込む

---

## 主要モジュール説明（ディレクトリ構成）

src/kabusys/
- __init__.py
  - パッケージトップ。version と公開サブパッケージを定義。

- config.py
  - 環境変数・設定管理。Settings クラスを通じてアプリ設定を取得。
  - .env 自動読み込み（.env / .env.local）、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。

- ai/
  - __init__.py: score_news を公開。
  - news_nlp.py: 銘柄別ニュースセンチメントスコア算出（OpenAI 呼び出し、レスポンス検証、結果の ai_scores テーブル書込）。
  - regime_detector.py: ETF(1321) の ma200 乖離とマクロニュースセンチメントを合成して市場レジーム（bull/neutral/bear）を daily 単位で判定し market_regime テーブルに書込。

- data/
  - __init__.py
  - jquants_client.py: J-Quants API クライアント（取得関数 + DuckDB への保存関数 + トークン管理 & レート制御 & リトライ）
  - pipeline.py: ETL パイプライン（run_daily_etl, run_prices_etl 等）と ETLResult。
  - quality.py: データ品質チェック（欠損・重複・スパイク・日付整合性）。
  - news_collector.py: RSS 取得・正規化・前処理・SSRF 対策・記事ID生成ロジック等。
  - calendar_management.py: 市場カレンダー管理（営業日判定 / next/prev_trading_day / calendar_update_job）。
  - stats.py: 汎用統計ユーティリティ（zscore_normalize）。
  - audit.py: 監査ログ（audit スキーマ定義・初期化ユーティリティ）。
  - etl.py: pipeline.ETLResult の再エクスポート。

- research/
  - __init__.py: 便利関数の再エクスポート。
  - factor_research.py: モメンタム・バリュー・ボラティリティ等の計算。
  - feature_exploration.py: 将来リターン計算、IC、統計サマリー、ランク関数等。

各モジュールは「DuckDB 接続を引数に取る」「ルックアヘッドバイアスを避ける（date 引数を明示）」「外部副作用を最小化する」などの設計方針に沿って実装されています。

---

## 注意点 / ベストプラクティス

- すべての「日次」処理関数（ETL、score_news、score_regime、ファクター計算等）は target_date を引数で受け取り、内部で datetime.today() を参照しないよう設計されています。バックテストや履歴再計算を行う際は必ず target_date を明示してください。
- OpenAI 呼び出しは外部ネットワークへのコストとレイテンシを伴います。API キーの管理・レートとコストに注意してください。
- DuckDB への書き込みはいくつかの箇所で executemany / ON CONFLICT を使っています。DuckDB のバージョンによる動作差異に注意してください（README で使用する DuckDB バージョンを固定することを推奨）。
- .env ファイルの自動読み込みは便利ですが、CI / テストでより明示的な制御が必要な場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化し、テスト用の環境を直接注入してください。

---

## よくある運用フローの例

1. 毎朝（夜間バッチ）に run_daily_etl を実行してデータを更新。
2. ETL 完了後に quality.run_all_checks の結果を監査・アラート。
3. ニュース収集ジョブ（複数 RSS）をスケジュールして raw_news を補完。
4. 毎朝またはオンデマンドで score_news を実行して ai_scores を更新。
5. score_regime を実行して market_regime を更新し、戦略のリスク許容やポジション比率に反映。
6. research モジュールでファクターを生成・正規化し、戦略のシグナル生成に使用。
7. strategy 層（本リポジトリ外の場合もある）は signal_events / order_requests を使って監査トレースを行う。

---

## 参考（よく使う API）

- ETL:
  - from kabusys.data.pipeline import run_daily_etl
- ニューススコア:
  - from kabusys.ai.news_nlp import score_news
- レジーム判定:
  - from kabusys.ai.regime_detector import score_regime
- 監査 DB 初期化:
  - from kabusys.data.audit import init_audit_db

---

問題の報告や改善提案、ドキュメントの補足が必要であれば教えてください。README の英語版や詳細な運用手順（Systemd / Airflow / Cron のサンプル、CI 設定、Dockerfile など）も必要であれば作成します。