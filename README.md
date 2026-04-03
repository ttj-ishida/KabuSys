# KabuSys

日本株向けの自動売買 / データプラットフォーム用ライブラリです。  
ETL、ニュース・NLP スコアリング、研究用ファクター計算、監査ログ、J-Quants / kabu API クライアントなどを備え、バックテストや運用バッチ処理で利用することを想定しています。

主な設計方針（抜粋）
- Look‑ahead bias を避ける設計（内部で datetime.today() を直接参照しない 等）
- DuckDB を中心としたローカルデータ管理（冪等保存、ON CONFLICT 更新）
- 外部 API 呼び出しはリトライ・レートリミット等の保護付き
- API キー等は .env / 環境変数で管理。パラメータ注入でテスト容易性確保

---

## 機能一覧

- データ収集と ETL
  - J-Quants からの日次株価、財務データ、JPX カレンダー取得（jquants_client）
  - 差分取得/バックフィル/品質チェックを含む日次 ETL パイプライン（data.pipeline）
- ニュース収集 / 前処理
  - RSS 収集 + SSRF 対策、トラッキングパラメータ除去、正規化（data.news_collector）
- ニュースの NLP スコアリング
  - OpenAI（gpt-4o-mini）を使った銘柄別センチメント / マクロセンチメント評価（ai.news_nlp, ai.regime_detector）
  - バッチ・チャンク処理、JSON モードの出力バリデーション、リトライとフォールバック
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（research.factor_research）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー（research.feature_exploration）
  - Z-score 正規化ユーティリティ（data.stats）
- 監査ログ（Audit）
  - signal → order_request → execution までのトレーサビリティ用テーブルと初期化ユーティリティ（data.audit）
- マーケットカレンダー管理
  - JPX カレンダー差分取得、営業日判定ユーティリティ（data.calendar_management）
- データ品質チェック
  - 欠損、重複、スパイク、日付不整合の検出（data.quality）

---

## セットアップ

必要な Python バージョンはプロジェクトポリシーに従ってください（typing の | 型注釈などから Python 3.10+ を想定）。以下は一般的な手順例です。

1. リポジトリをクローン
   - git clone <repo-url>
2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb openai defusedxml
   - （必要に応じて他のパッケージを requirements.txt にまとめてください）
4. ソースを editable インストール（任意）
   - pip install -e .

環境変数は .env または OS 環境変数で設定できます。パッケージはプロジェクトルートの `.env` / `.env.local` を自動で読み込みます（自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）。

---

## 環境変数（主なもの）

主要な設定は `kabusys.config.settings` 経由で取得されます。代表的なキー:

- JQUANTS_REFRESH_TOKEN (必須)
  - J-Quants のリフレッシュトークン（ETL 用認証）
- OPENAI_API_KEY
  - OpenAI API キー（news_nlp / regime_detector）
- KABU_API_PASSWORD (必須)
  - kabu ステーション（発注API）用パスワード
- KABU_API_BASE_URL (任意)
  - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (任意)
  - LINE 通知用
- DUCKDB_PATH (任意)
  - DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意)
  - 監視用 SQLite（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT
  - プロセス監視・終了フラグ等の設定
- KABUSYS_ENV
  - 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL
  - ログレベル: DEBUG / INFO / WARNING / ERROR / CRITICAL

必須環境変数が未設定の場合、Settings のプロパティ呼び出しで ValueError が発生します。

---

## 使い方（主要な例）

ここでは代表的なユーティリティ関数の呼び出し例を示します。すべての関数は DuckDB の接続オブジェクト（duckdb.connect(...) が返す接続）を受け取るので、実行前に DB を作成/接続してください。

- DuckDB 接続例:
  - import duckdb
  - conn = duckdb.connect("data/kabusys.duckdb")

- 日次 ETL を実行（run_daily_etl）
  - from datetime import date
    from kabusys.data.pipeline import run_daily_etl
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

  run_daily_etl はカレンダー→株価→財務→品質チェックまで順に実行し、ETLResult を返します。

- ニュース NLP スコアリング（score_news）
  - from datetime import date
    from kabusys.ai.news_nlp import score_news
    num_written = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
    print(f"wrote {num_written} ai_scores")

  OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を用います。失敗時はフェイルセーフでスキップする挙動です。

- 市場レジーム判定（score_regime）
  - from datetime import date
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")

  ETF (1321) の MA200 とマクロ記事の LLM センチメントを重み合成して market_regime テーブルに書き込みます。

- 監査ログの初期化（init_audit_db / init_audit_schema）
  - from kabusys.data.audit import init_audit_db
    audit_conn = init_audit_db("data/audit.duckdb")
    # これで監査用テーブルが作成されます

- マーケットカレンダー判定例
  - from datetime import date
    from kabusys.data.calendar_management import is_trading_day, next_trading_day
    is_td = is_trading_day(conn, date(2026,3,20))
    next_td = next_trading_day(conn, date(2026,3,20))

注意点
- OpenAI / J-Quants 呼び出し時は課金やレート制限に注意してください。
- ETL や API 呼び出し時はログを確認してください。設定により .env で LOG_LEVEL を変更できます。
- 研究関数はバックテストのループ内から直接外部APIを呼ばないよう注意してください（Look-ahead 防止の指針あり）。

---

## ディレクトリ構成（主要ファイル）

以下は `src/kabusys` 以下の主要モジュールと簡単な説明です。

- __init__.py
  - パッケージのバージョン定義とサブパッケージの公開
- config.py
  - 環境変数の自動ロード（.env / .env.local）、設定取得用 Settings
- ai/
  - news_nlp.py : ニュースを銘柄ごとに集約して OpenAI でセンチメント評価、ai_scores へ書込
  - regime_detector.py : ETF(1321) MA200 とマクロ記事の LLM センチメントにより市場レジーム判定
- data/
  - jquants_client.py : J-Quants API クライアント（取得 + DuckDB への保存関数）
  - pipeline.py : ETL パイプライン（run_daily_etl, run_prices_etl, ...）
  - news_collector.py : RSS 収集・前処理・raw_news への保存ロジック
  - calendar_management.py : JPX カレンダー管理・営業日判定ユーティリティ
  - quality.py : データ品質チェック（欠損、重複、スパイク、日付不整合）
  - audit.py : 監査ログ（signal/order_request/execution）テーブル定義と初期化
  - stats.py : z-score などの統計ユーティリティ
  - etl.py : ETLResult の再エクスポート
- research/
  - factor_research.py : Momentum / Value / Volatility 等のファクター計算
  - feature_exploration.py : 将来リターン計算、IC、統計サマリー、rank
  - __init__.py : 研究用ユーティリティの公開
- monitoring / execution / strategy / (その他)
  - パッケージ公開対象として __all__ に含まれていますが、ここに含まれる具体的実装はプロジェクトの別ファイルにある想定です（コードベースにより補完してください）。

---

## テスト & 開発時の便利な設定

- 自動で .env を読ませたくない場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を環境変数に設定すると、config の自動ロードを無効化できます（ユニットテストなどで便利）。
- OpenAI の呼び出しは各モジュールでラッパー関数を定義しており、ユニットテストではこれらをモックして API コールを差し替えられる設計です（例: unittest.mock.patch）。
- DuckDB はファイルパスを ":memory:" にすればインメモリ DB として利用可能。テスト時に便利です。

---

## 注意事項 / ベストプラクティス

- 機密情報（API キー等）は .env や OS のセキュアなシークレットストアで管理してください。リポジトリにコミットしないでください。
- OpenAI / J-Quants の API 利用は課金対象となるため、テストはモックで代替してください。
- ETL 実行時はログと品質チェック結果（ETLResult.quality_issues）を監視し、重大な問題があれば運用側で対応してください。
- 本ライブラリは「データ取得・加工・監査・研究」レイヤを提供します。実際の発注ロジックやライブ運用は、strategy / execution 層と連携して実装してください。

---

README に書ききれない内部の仕様や SQL スキーマ、API の詳細は各モジュールの docstring を参照してください。必要であれば README に追記する項目（例: requirements.txt、CI 設定、デプロイ手順など）を指定してください。