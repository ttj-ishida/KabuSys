# KabuSys

日本株自動売買システムのコアライブラリ群（データプラットフォーム、研究・ファクター計算、ニュースNLP、レジーム判定、監査ログなど）を含むパッケージです。本リポジトリは ETL、データ品質チェック、ニュース収集・NLP、ファクター計算、監査ログ設計等の機能を提供します。

## 主要な特徴（機能一覧）
- データ取得・ETL
  - J-Quants API から株価（OHLCV）、財務データ、JPX カレンダーを差分取得・保存（冪等）
  - 日次 ETL パイプライン（run_daily_etl）
  - API レート制御・リトライ、トークン自動リフレッシュ対応
- データ品質チェック
  - 欠損、重複、スパイク（急変）、日付不整合の検出（QualityIssue）
- ニュース収集
  - RSS フィード取得（SSRF対策、トラッキング除去、gzip対応）
  - raw_news / news_symbols への冪等保存
- ニュース NLP（OpenAI）
  - 銘柄ごとのニュース統合センチメント（score_news）
  - レジーム判定（ETF 1321 のMA乖離 + マクロニュースセンチメントを合成 → score_regime）
  - API 呼び出しはバッチ化・JSON mode を利用、リトライやフォールバックを実装
- 研究（Research）
  - モメンタム / ボラティリティ / バリュー等ファクター計算（calc_momentum / calc_volatility / calc_value）
  - 将来リターン、IC（情報係数）、統計サマリ、Zスコア正規化ユーティリティ
- 監査ログ（Audit）
  - signal_events / order_requests / executions 等の監査テーブル定義と初期化ユーティリティ（init_audit_schema / init_audit_db）
  - UUID 系列によるトレーサビリティ設計
- 構成・設定管理
  - .env 自動読み込み（プロジェクトルート検出）と Settings API（kabusys.config.settings）
  - 環境（development / paper_trading / live）やログレベル検証

## 要件
- Python 3.10+
- 主要依存（例）
  - duckdb
  - openai
  - defusedxml
  - （必要に応じて requests 等を使用するラッパーがあれば追加）

※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してインストールしてください。

## セットアップ手順

1. リポジトリをクローン / 配布パッケージを展開
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - 例: pip install duckdb openai defusedxml
   - またはプロジェクトに requirements.txt / pyproject.toml があればそれを使用
4. 環境変数の準備
   - プロジェクトルート（.git または pyproject.toml がある場所）に `.env` と（開発用であれば）`.env.local` を配置することで自動読み込みされます。
   - 自動読み込みを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途等）。
   - 必須環境変数例（.env.sample として作る想定）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - SLACK_BOT_TOKEN=...
     - SLACK_CHANNEL_ID=...
     - OPENAI_API_KEY=...
     - （任意）DUCKDB_PATH=data/kabusys.duckdb
     - （任意）SQLITE_PATH=data/monitoring.db
     - KABUSYS_ENV=development|paper_trading|live
     - LOG_LEVEL=INFO|DEBUG|...
5. DuckDB 初期化（監査DB等）
   - 監査用 DB を作る例:
     - from kabusys.data.audit import init_audit_db
     - conn = init_audit_db("data/audit.duckdb")

## 使い方（基本例）
以下は代表的な操作例です。実行は Python スクリプトやジョブランナーから呼び出して下さい。

- DuckDB 接続を使って日次 ETL を実行する（例）:
  - from datetime import date
    import duckdb
    from kabusys.data.pipeline import run_daily_etl
    conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
    result = run_daily_etl(conn, target_date=date(2026, 3, 20))
    print(result.to_dict())

- ニュース NLP（銘柄別スコア）を計算して ai_scores に保存:
  - from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
    n_written = score_news(conn, target_date=date(2026, 3, 20))
    print("written:", n_written)

- 市場レジーム判定を実行:
  - from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime
    conn = duckdb.connect(str(kabusys.config.settings.duckdb_path))
    score_regime(conn, target_date=date(2026, 3, 20))

- 監査スキーマ初期化（既存 DB に追加）:
  - from kabusys.data.audit import init_audit_schema
    conn = duckdb.connect("data/kabusys.duckdb")
    init_audit_schema(conn, transactional=True)

- ファクター計算（研究用途）:
  - from kabusys.research import calc_momentum, calc_value, calc_volatility
    records = calc_momentum(conn, target_date=date(2026, 3, 20))
    # zscore 正規化:
    from kabusys.data.stats import zscore_normalize
    z_records = zscore_normalize(records, ["mom_1m", "mom_3m", "mom_6m"])

注意:
- AI 系（score_news / score_regime）は OpenAI API キー（OPENAI_API_KEY）を環境変数で指定するか、api_key 引数で注入してください。
- これら関数はルックアヘッドバイアスを避ける設計（内部で date.today() を参照しない）になっています。
- DuckDB の executemany は一部バージョンで空リストを受け付けないため、関数内で考慮済みです。

## 設定（Settings API）
kabusys.config.settings オブジェクト経由で設定にアクセスできます。主要プロパティ:
- jquants_refresh_token, kabu_api_password
- kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
- slack_bot_token, slack_channel_id
- duckdb_path, sqlite_path
- env (development / paper_trading / live)、is_live / is_paper / is_dev
- log_level (DEBUG/INFO/...；検証あり)

環境変数読み込み挙動:
- プロジェクトルート（.git または pyproject.toml を基準）にある `.env` → `.env.local` を自動読み込みします（OS 環境変数より下位。ただし .env.local は上書き）。自動読み込みを無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

## ディレクトリ構成（主なファイル）
(リポジトリの src/kabusys 以下を抜粋)

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・設定管理
  - ai/
    - __init__.py
    - news_nlp.py                   # ニュースセンチメント分析（score_news）
    - regime_detector.py            # 市場レジーム判定（score_regime）
  - data/
    - __init__.py
    - calendar_management.py        # 市場カレンダー管理
    - etl.py / pipeline.py          # 日次 ETL パイプライン・ヘルパ
    - stats.py                      # 統計ユーティリティ（zscore）
    - quality.py                    # データ品質チェック
    - audit.py                      # 監査ログスキーマ初期化
    - jquants_client.py             # J-Quants API クライアント＋保存ロジック
    - news_collector.py             # RSS ニュース収集・前処理
    - etl.py                        # ETL 公開インターフェース（ETLResult 再エクスポート）
  - research/
    - __init__.py
    - factor_research.py            # モメンタム / ボラティリティ / バリュー計算
    - feature_exploration.py        # 将来リターン / IC / サマリー
  - (その他)
    - strategy/ execution/ monitoring/  # パッケージエクスポートに含まれるがここに示される

※ 上記はコードベースの主要モジュールを抜粋したものです。

## 運用上の注意・設計上のポイント
- ルックアヘッドバイアス防止: 多くの関数は内部で date.today() を使わず、呼び出し側が target_date を明示する設計です。
- 冪等性: ETL / 保存関数は ON CONFLICT / DELETE→INSERT 等で冪等性を確保しています。
- フェイルセーフ: AI 呼び出しや外部 API エラー時は、可能な限り例外を外へ吐かずフォールバック（0 やスキップ）で継続する箇所が多くあります。ログで状況を確認してください。
- テスト容易性: OpenAI や HTTP 呼び出し箇所はモック可能なように分離・ラップされています。

---

その他、具体的な導入手順や CI / デプロイ手順、モニタリング・アラート、Kabuステーション連携（発注・約定処理）などはプロジェクトの運用ドキュメントを参照してください。必要であれば README を拡張して各 API の使用例、SQL スキーマ定義、サンプル .env.example を追加できます。