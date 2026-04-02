KabuSys — 日本株自動売買システム
================================

概要
----
KabuSys は日本株のデータ収集（ETL）、品質チェック、リサーチ（ファクター計算）、ニュースNLP / LLM を使ったセンチメント評価、監査ログ管理などを備えた自動売買基盤の一部実装です。本リポジトリは主にデータプラットフォーム周り（J-Quants 連携、DuckDB 保存、RSS ニュース収集）と研究（ファクター計算・特徴量評価）、および LLM を用いたニュース評価・市場レジーム判定ロジックを提供します。

主な設計方針（抜粋）
- ルックアヘッドバイアス防止：内部で datetime.today()/date.today() を不用意に参照しない設計。
- 冪等性：DB 保存は可能な限り ON CONFLICT ベースで上書きし、再実行に安全。
- フェイルセーフ：外部 API 失敗時は局所的に 0 やスキップするなどして処理継続を優先。
- セキュリティ考慮：RSS の SSRF 対策、XML パースの安全化、API レート管理など。

機能一覧
--------
- 環境変数 / .env 読み込み（kabusys.config）
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - 必須環境変数取得ユーティリティ settings
- データ ETL（kabusys.data.pipeline / jquants_client）
  - J-Quants API から株価（日足）・財務・マーケットカレンダー取得
  - 差分取得 / バックフィル / 保存（DuckDB）
  - ETL 実行結果管理（ETLResult）
- データ品質チェック（kabusys.data.quality）
  - 欠損・スパイク・重複・日付整合性チェック
- カレンダー管理（kabusys.data.calendar_management）
  - 営業日判定 / next/prev_trading_day / SQ 判定 / 夜間更新ジョブ
- ニュース収集（kabusys.data.news_collector）
  - RSS 収集、前処理、ID 生成、raw_news への冪等保存想定
  - SSRF 対策・受信サイズ制限・トラッキングパラメータ除去
- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の DDL と初期化
  - 監査用 DuckDB 初期化ユーティリティ
- 研究モジュール（kabusys.research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
  - z-score 正規化ユーティリティ
- AI モジュール（kabusys.ai）
  - ニュース NLP による銘柄別センチメントスコア付与（gpt-4o-mini 想定）
  - 市場レジーム判定（ETF 1321 の MA200 とマクロニュースの組合せ）

セットアップ手順
---------------
前提
- Python 3.10+（typing の | 型等を使用）
- DuckDB（pip パッケージで利用）
- OpenAI SDK（openai パッケージ）およびその依存
- defusedxml（RSS の安全パース用）
- ネットワーク接続（J-Quants / OpenAI / RSS）

推奨手順（例）
1. リポジトリをクローン
   - git clone ... (この README はコードベースの説明です)

2. 仮想環境の作成とアクティベート
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 必要パッケージをインストール
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt / pyproject.toml がある場合はそれに従ってください）

4. 環境変数の設定
   - プロジェクトルートに .env または .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化できます）。
   - 必須環境変数（一例）
     - JQUANTS_REFRESH_TOKEN — J-Quants リフレッシュトークン
     - KABU_API_PASSWORD — kabu API 用パスワード
     - SLACK_BOT_TOKEN — Slack 通知用トークン
     - SLACK_CHANNEL_ID — Slack チャンネル ID
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
   - DB パスは環境変数で上書き可能（デフォルト値が設定されています）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（監視用の sqlite、デフォルト data/monitoring.db）

.env 例（参考）
- .env.example を参考に作成してください。最小例:
  JQUANTS_REFRESH_TOKEN=xxxxxxxxxx
  OPENAI_API_KEY=sk-...
  KABU_API_PASSWORD=your_password
  SLACK_BOT_TOKEN=xoxb-...
  SLACK_CHANNEL_ID=C01234567

使い方（主な操作例）
-------------------

設定の利用
- 設定値は kabusys.config.settings 経由で取得できます。
  例:
    from kabusys.config import settings
    token = settings.jquants_refresh_token

ETL を実行する（例: 日次 ETL）
- DuckDB 接続を作り、run_daily_etl を呼ぶ:
    import duckdb
    from datetime import date
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

ニュースの NLP スコア付与
- OpenAI API キーを環境変数にセットしておくか、api_key 引数で渡す:
    import duckdb
    from datetime import date
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 3, 20))
    print(f"scored {n} symbols")

市場レジーム判定
- ETF 1321 の MA200 とマクロニュースを組合せて日次レジームを作成:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026,3,20))

監査ログ DB 初期化
- 監査ログ用の DuckDB を初期化:
    from kabusys.data.audit import init_audit_db
    conn = init_audit_db("data/audit.duckdb")
    # これで signal_events / order_requests / executions 等のテーブルが作成されます

J-Quants API 呼び出し（低レベル）
- jquants_client は get_id_token, fetch_daily_quotes, save_daily_quotes 等を提供します。
  - これらは内部でレートリミッタ・リトライ・トークンリフレッシュを扱います。

注意点 / 実運用メモ
-----------------
- OpenAI 呼び出しは gpt-4o-mini を利用する想定で JSON mode を用いた出力を期待しています。API 失敗時は 0.0 にフォールバックするなどのフェイルセーフがありますが、使用時は課金・レート制限に注意してください。
- .env/.env.local の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行われます。テスト時に自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の executemany はバージョン依存の挙動（空リスト不可など）があるため、コード側で空チェックをしています。DuckDB のバージョンによる差異に注意してください。
- news_collector には SSRF 防御・受信サイズ制限などの安全対策が実装されています。外部 RSS の扱いは慎重に行ってください。
- J-Quants API のレート制限や 401 の自動トークン更新に対応していますが、運用環境では API キーの権限・ローテーション管理を行ってください。

ディレクトリ構成（抜粋）
----------------------
以下は本コードベースに含まれる主なファイル・モジュールの構成（抜粋）です。

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
      - pipeline.py
      - etl.py
      - jquants_client.py
      - news_collector.py
      - quality.py
      - calendar_management.py
      - stats.py
      - audit.py
      - (etl.py は ETLResult を再エクスポート)
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - research/__init__.py (zscore_normalize 再エクスポートなど)
    # その他、strategy / execution / monitoring を想定するトップレベルモジュールが存在します（実装は別ファイル／将来的な拡張）。

ドキュメント・設計ノート
---------------------
- 各モジュールの docstring に設計方針・処理フローが詳細に書かれています。実装の意図やフェイルセーフ動作、ルックアヘッド回避の設計などはソースコードの docstrings を参照してください。
- データベーススキーマ（監査ログなど）の DDL は kabusys.data.audit 内に定義されています。監査トレースの要件（UUID 連鎖、updated_at/created_at の扱い）はここにまとめられています。

貢献・開発
----------
- 単体テスト・モックを用いた外部依存の差し替えが行いやすいよう設計されています（例えば OpenAI 呼び出し・HTTP オープン関数をテスト時にパッチ可能）。
- 新しい ETL ジョブや戦略モジュールは既存の ETL / audit / research API に沿って追加してください。

お問い合わせ
------------
コードの不明点や実装上の意図に関する質問は、リポジトリのイシューを立ててください。README の補足やサンプルスクリプトが必要ならリクエストに応じて追加します。