# KabuSys

バージョン: 0.1.0

日本株向けの自動売買・データプラットフォーム用ライブラリ群です。ETL、データ品質チェック、ニュース収集とAIによるニュースセンチメント・市場レジーム判定、リサーチ（ファクター計算）および監査ログ（発注→約定トレーサビリティ）機能を提供します。

主な目的は「データ取得・品質管理→特徴量生成→シグナル生成→発注監査」を一貫して行える基盤機能を提供することです。実際の発注（ブローカー接続）ロジックは分離されており、本パッケージは基盤部分を担います。

---

## 機能一覧

- 環境設定管理
  - .env / .env.local の自動読み込み（プロジェクトルート検出）
  - settings オブジェクト経由で設定値を参照
- データ取得（J-Quants API クライアント）
  - 株価日足（OHLCV）
  - 財務データ（四半期）
  - JPX マーケットカレンダー
  - リトライ、トークン自動リフレッシュ、レートリミット制御を実装
- ETL パイプライン
  - run_daily_etl: カレンダー→日足→財務→品質チェック の一括処理
  - 差分更新、バックフィル対応
- データ品質チェック
  - 欠損、スパイク（急変）、重複、日付整合性チェック
  - QualityIssue を返す（error/warning 指定）
- ニュース収集
  - RSS 取得・正規化・前処理・SSRF 対策
  - raw_news / news_symbols への冪等保存
- AI（OpenAI）連携
  - ニュース単位で銘柄別センチメントを算出し ai_scores に保存（score_news）
  - ETF（1321）200日MA とマクロニュースセンチメントを合成して市場レジーム判定（score_regime）
  - API 呼び出しのリトライ・フェイルセーフ実装（失敗時は中立スコアにフォールバック）
- リサーチ用ユーティリティ
  - モメンタム、ボラティリティ、バリュー等のファクター計算
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー、Zスコア正規化
- 監査ログ（Audit）
  - signal_events / order_requests / executions テーブルを定義
  - init_audit_db / init_audit_schema による初期化（UTC タイムスタンプ、冪等DDL）

---

## 要求環境

- Python 3.10+
- 主な外部ライブラリ（例）
  - duckdb
  - openai
  - defusedxml
- ネットワーク接続（J-Quants, OpenAI など外部API）

requirements.txt は同梱されていないため、必要なパッケージをプロジェクトに応じて追加してください。

---

## セットアップ手順（例）

1. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb openai defusedxml

   ※ 実際のプロジェクトでは testing や lint 用の追加パッケージを用意してください。

3. 環境変数を準備
   - プロジェクトルート（.git または pyproject.toml のあるディレクトリ）に `.env` を作成してください。
   - 自動読み込み: モジュール kabusys.config は起動時にプロジェクトルートの `.env`、続けて `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（代表例）
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
   - その他（任意・デフォルトあり）
     - KABU_API_BASE_URL （デフォルト: http://localhost:18080/kabusapi）
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (デフォルト: data/monitoring.db)
     - PID_FILE_PATH, KILL_FLAG_PATH
     - KABUSYS_ENV (development / paper_trading / live)
     - LOG_LEVEL (DEBUG / INFO / WARNING / ERROR / CRITICAL)

5. データベースの初期化（監査ログなど）
   - 監査ログ専用 DB を作る場合:
     from kabusys.data.audit import init_audit_db
     conn = init_audit_db("data/audit.duckdb")

   - 既存の DuckDB 接続に監査スキーマを追加する:
     from kabusys.data.audit import init_audit_schema
     conn = duckdb.connect(str(settings.duckdb_path))
     init_audit_schema(conn, transactional=True)

---

## 使い方（例）

以下は簡単な利用例です。実行前に環境変数（特に JQUANTS_REFRESH_TOKEN / OPENAI_API_KEY）を設定してください。

- DuckDB 接続を作る（settings 参照）
  from kabusys.config import settings
  import duckdb
  conn = duckdb.connect(str(settings.duckdb_path))

- 日次 ETL を実行する
  from kabusys.data.pipeline import run_daily_etl
  from datetime import date
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())

- ニュースセンチメントの算出（AI、OpenAI API キー必要）
  from kabusys.ai.news_nlp import score_news
  from datetime import date
  count = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # 環境変数 OPENAI_API_KEY を使用
  print("scored:", count)

- 市場レジーム（マクロ + MA200）判定
  from kabusys.ai.regime_detector import score_regime
  from datetime import date
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)

- ファクター計算（リサーチ）
  from kabusys.research import calc_momentum, calc_value, calc_volatility
  from datetime import date
  mom = calc_momentum(conn, target_date=date(2026, 3, 20))
  vol = calc_volatility(conn, target_date=date(2026, 3, 20))

- 監査ログ DB 初期化
  from kabusys.data.audit import init_audit_db
  audit_conn = init_audit_db("data/audit.duckdb")

注意:
- AI モジュール（score_news, score_regime）は OpenAI API を呼び出します。API 呼び出し失敗時は設計上フェイルセーフ（中立スコア0.0等）で継続する実装です。
- J-Quants クライアントは内部でトークン自動取得・リトライ・レート制御を行います。JQUANTS_REFRESH_TOKEN を .env 等で設定してください。

---

## 環境変数一覧（主なもの）

- JQUANTS_REFRESH_TOKEN (必須): J-Quants リフレッシュトークン
- KABU_API_PASSWORD (必須): kabu API のパスワード
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必要）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（任意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite（監視用 DB）パス（デフォルト: data/monitoring.db）
- PID_FILE_PATH, KILL_FLAG_PATH: 実行監視用ファイルパス
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する場合に 1 を設定

---

## ディレクトリ構成（主なファイル）

- src/kabusys/
  - __init__.py
  - config.py
  - ai/
    - __init__.py
    - news_nlp.py            # ニュースの銘柄別センチメント算出（OpenAI）
    - regime_detector.py     # ETF MA + マクロニュースで市場レジーム判定（OpenAI）
  - data/
    - __init__.py
    - jquants_client.py      # J-Quants API クライアント（取得・保存ロジック）
    - pipeline.py           # ETL パイプライン（run_daily_etl 等）
    - etl.py                # ETLResult 再エクスポート
    - calendar_management.py# 市場カレンダー管理（営業日判定 etc.）
    - news_collector.py     # RSS ニュース収集・前処理・保存
    - quality.py            # データ品質チェック
    - stats.py              # zscore_normalize 等
    - audit.py              # 監査ログ DDL・初期化
  - research/
    - __init__.py
    - factor_research.py    # モメンタム/バリュー/ボラティリティ等
    - feature_exploration.py# forward returns / IC / summary / rank

各モジュールは「DuckDB 接続を受け取り SQL と Python で処理する」方針で作られており、外部 API 呼び出し箇所は明記・分離されています（AI 呼び出しや J-Quants 呼び出し）。

---

## 開発・運用上の留意点

- Look-ahead バイアス回避:
  - 日付関連処理（ニュースウィンドウ、MA 計算、ETL の対象日）は内部で明示的に target_date を受け取り、datetime.today() を不用意に参照しない設計です。
- フェイルセーフ:
  - OpenAI / J-Quants の一時障害はリトライ・バックオフ・フォールバック実装がされており、致命的な停止を避ける設計です（ただしログや警告は出ます）。
- 冪等性:
  - ETL 保存処理は ON CONFLICT DO UPDATE 等で冪等に保存します。監査ログも order_request_id を冪等キーに想定。
- テスト容易性:
  - OpenAI 呼び出しなどは内部の呼び出し関数をモックできるように実装されています（ユニットテストでの差し替えが想定されています）。

---

## トラブルシューティング（簡単なヒント）

- .env が読み込まれない場合:
  - プロジェクトルートの判定は __file__ の親ディレクトリを探索して .git または pyproject.toml を見つけます。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境変数を読み込む運用に切り替え可能です。
- OpenAI レスポンスのパースに失敗するとき:
  - LLM の出力バリエーションを考慮し、モジュールでは JSON 抽出・検証をしています。API 側の仕様変更やモデルの挙動で失敗する場合はログを確認してください（失敗時は中立スコアにフォールバックします）。
- J-Quants の認証エラー（401）:
  - jquants_client はリフレッシュを試みます。JQUANTS_REFRESH_TOKEN が正しいか確認してください。

---

ご要望があれば、README に以下を追加できます:
- docker-compose / systemd ユニットのサンプル
- CI (pytest) 用テスト実行例・モックのヒント
- より詳細な API 使用例（各関数の入出力サンプル）
- requirements.txt / pyproject.toml の推奨内容

必要なものを教えてください。