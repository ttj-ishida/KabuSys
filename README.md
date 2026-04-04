# KabuSys

日本株向け自動売買／データ基盤ライブラリ（KabuSys）

概要
- KabuSys は日本株のデータ収集・品質管理・研究（ファクター計算）・AI によるニュースセンチメント解析・市場レジーム判定・監査ログ管理を目的とした Python パッケージです。
- 内部的には J-Quants API からのデータ取得、DuckDB を用いた永続化、OpenAI（gpt-4o-mini）を用いたニュース解析などを行います。
- バックテスト・研究用途と実運用（発注・監視）用途を分離する設計方針を採用しています。

主な機能
- データ収集（J-Quants）
  - 株価日足（OHLCV）、財務諸表、上場銘柄情報、JPX マーケットカレンダーの差分取得（ページネーション・レート制御・トークン自動リフレッシュ対応）
  - ETL パイプライン（差分更新、バックフィル、品質チェック）
- データ品質チェック
  - 欠損（OHLC）検出、スパイク検出、重複検出、日付の整合性チェック
- ニュース収集・前処理
  - RSS フィード収集、前処理（URL 正規化・トラッキング除去・SSRF 対策）、raw_news / news_symbols への保存（冪等）
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（ai_scores へ書き込み）
  - マクロニュースのセンチメントを用いた市場レジーム判定（ETF 1321 の MA200 と組み合わせ）
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - シグナル → 発注 → 約定までのトレーサビリティ用テーブル群の初期化・管理（DuckDB）
- 設定管理
  - .env, .env.local, OS 環境変数からの設定読み込み（自動ロードは無効化可能）

必要条件
- Python 3.10 以上
- 主な依存パッケージ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワークアクセス（J-Quants API / OpenAI / RSS フィード）

セットアップ手順（開発環境）
1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存関係をインストール
   - pip install -U pip
   - pip install duckdb openai defusedxml
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. パッケージをインストール（編集可能モード）
   - pip install -e .

環境変数（.env）
- 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
- 自動ロードを無効化する場合:
  - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

代表的なキー（必須 / 推奨）
- 必須:
  - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（data.jquants_client.get_id_token で使用）
  - KABU_API_PASSWORD: kabuステーション API を使う際のパスワード（存在する機能がある場合）
- OpenAI:
  - OPENAI_API_KEY: OpenAI API キー（score_news / score_regime で使用）
- 任意:
  - KABU_API_BASE_URL (デフォルト http://localhost:18080/kabusapi)
  - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
  - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB）
  - PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL

例（.env.example）
    JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
    OPENAI_API_KEY=sk-xxxx...
    KABU_API_PASSWORD=your_kabu_password
    DUCKDB_PATH=data/kabusys.duckdb
    KABUSYS_ENV=development
    LOG_LEVEL=INFO

使い方（簡易サンプル）
- DuckDB 接続を作成して ETL を実行する
    from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl

    conn = duckdb.connect("data/kabusys.duckdb")
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュースセンチメントをスコアリングして ai_scores に書き込む
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    n = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx...")
    print(f"scored {n} symbols")

- 市場レジームを判定して market_regime に書き込む
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-xxxx...")

- 研究用ファクター計算（例: モメンタム）
    from datetime import date
    import duckdb
    from kabusys.research.factor_research import calc_momentum

    conn = duckdb.connect("data/kabusys.duckdb")
    records = calc_momentum(conn, target_date=date(2026,3,20))
    # records は [{"date":..., "code":..., "mom_1m":..., ...}, ...]

- 監査ログテーブルの初期化
    import duckdb
    from kabusys.data.audit import init_audit_db

    conn = init_audit_db("data/audit.duckdb")
    # または既存接続に init_audit_schema(conn)

設計上の注意点 / ベストプラクティス
- Look-ahead bias の回避:
  - モジュール内の多くの関数（score_news, score_regime, ETL など）は date 引数を明示的に受け取り、内部で datetime.today() を盲目的に参照しない設計です。バックテストでは必ず過去日付を渡すこと。
- OpenAI / J-Quants の API 呼び出しはリトライ・バックオフを内蔵していますが、API キー/トークンの管理（レート制限・課金）に注意してください。
- DuckDB へ executemany に空リストを渡すと問題になるバージョンがあるため、内部で空チェックが行われています。自前で批処理を行う場合は注意してください。
- news_collector は SSRF 対策・XML の安全パース・レスポンスサイズチェックを行っていますが、追加のフィードを扱う際はソース側の形式差に注意してください。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                     （環境変数・設定管理）
  - ai/
    - __init__.py
    - news_nlp.py                 （ニュース NLP / score_news）
    - regime_detector.py          （市場レジーム判定 / score_regime）
  - data/
    - __init__.py
    - jquants_client.py           （J-Quants API クライアント / 保存関数）
    - pipeline.py                 （ETL パイプライン / run_daily_etl 等）
    - etl.py                      （ETLResult 再公開）
    - stats.py                    （統計ユーティリティ / zscore_normalize）
    - quality.py                  （データ品質チェック）
    - calendar_management.py      （市場カレンダー管理 / is_trading_day 等）
    - news_collector.py           （RSS 取得・前処理）
    - audit.py                    （監査ログテーブル定義・初期化）
  - research/
    - __init__.py
    - factor_research.py          （ファクター計算）
    - feature_exploration.py      （将来リターン / IC / 統計サマリー）
  - ai/、data/、research/ のそれぞれにテスト用のモック差替えポイントあり

開発 / 貢献
- コードはモジュール単位で責任範囲が分かれており、テストの差し替え（モック）を想定した実装が多くあります。
- 新規機能追加・バグ修正の際は Look-ahead bias を生まない設計、外部 API への負荷（レート制御）、DuckDB の互換性を意識してください。

ライセンス
- （この README では省略しています。プロジェクトの LICENSE ファイルを参照してください。）

問題がある、または README に追加してほしいサンプル（例: .env.example の完全なテンプレートや CI 設定、requirements.txt など）があれば教えてください。README を拡張して提供します。