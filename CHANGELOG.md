CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマット: Keep a Changelog 準拠（https://keepachangelog.com/ja/）

0.1.0 - 初回リリース
-------------------

公開日: 未設定

Added
- パッケージ初期版を追加。以下の主要機能を実装。
  - kabusys.config
    - .env / .env.local ファイルまたは環境変数から設定値を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能（テスト目的）。
    - .env パーサの実装: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
    - 必須 env 取得用 _require()、各種設定プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, LINE_CHANNEL_ACCESS_TOKEN, DUCKDB_PATH, PAPER_FILL_MODE 等）。
    - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値検証とデフォルト値、各種パスの expanduser 対応。
  - portfolio（ポートフォリオ構築）
    - portfolio_builder
      - select_candidates: BUY シグナルをスコア降順・タイブレークにより上位 N 件選択。
      - calc_equal_weights: 等額配分重み算出。
      - calc_score_weights: スコア正規化による重み算出。全銘柄スコアが 0 の場合は等分配にフォールバック（WARNING ログ）。
    - risk_adjustment
      - apply_sector_cap: セクター集中上限チェック。既存保有のセクター別時価を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは制限しない）。sell_codes を除外扱いにするオプションあり。
      - calc_regime_multiplier: market レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告ログを出して 1.0 にフォールバック。
    - position_sizing
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") をサポートする株数算出ロジックを実装。リスクベース算出、単元株（lot_size）での丸め、per-stock 上限・aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer による保守的コスト見積り、スケーリング後の再配分ロジック（残差に基づく lot 単位追加）を実装。
  - research（ファクター計算・探索）
    - factor_research
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB で計算。過去データ不足時は None を返す。
      - calc_volatility: 20日 ATR、ATR 比率（atr_pct）、20日平均売買代金、出来高比率を計算。必要行数が不足する場合は None を返す。
      - calc_value: raw_financials（最新の report_date ≤ target_date）と prices_daily を組み合わせて PER / ROE を計算。
    - feature_exploration
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の検証あり（1〜252 日）。
      - calc_ic: Spearman ランク相関（Information Coefficient）を計算。サンプルが 3 件未満、もしくは分散 0 の場合は None を返す。
      - rank: 同順位は平均ランクを返す実装。浮動小数点の ties を避けるため round(..., 12) を用いる。
      - factor_summary: count/mean/std/min/max/median を算出する統計サマリユーティリティ。
    - research.__init__ で主要関数と zscore_normalize（外部 data.stats の関数）をエクスポート。
  - ai（LLM を用いた解析）
    - news_nlp
      - calc_news_window: ターゲット日に対するニュース収集ウィンドウを JST/UTC 変換で算出（前日15:00 JST ～ 当日08:30 JST に対応）。
      - score_news: raw_news と news_symbols から銘柄別に記事を集約し、OpenAI（gpt-4o-mini）を使って銘柄ごとのセンチメントスコア（-1.0〜1.0）を付与して ai_scores テーブルへ書き込む。バッチ（最大 20 銘柄）、トークン制御（記事数・文字数上限）、JSON mode 想定、API エラーに対する指数バックオフリトライ、レスポンス検証、部分書き換え（DELETE → INSERT）による冪等性/部分失敗保護を実装。API キーは引数または OPENAI_API_KEY 環境変数から解決。未指定時は ValueError。
      - テスト容易性: OpenAI 呼び出し箇所は _call_openai_api を経由しておりモック可能。
    - regime_detector
      - score_regime: ETF 1321 の ma200 乖離とマクロニュースの LLM センチメントを合成して market_regime テーブルへ書き込む。マクロ記事はキーワードマッチで抽出し最大件数制限あり。API 失敗時は macro_sentiment=0.0 にフォールバックしフェイルセーフに動作。書き込みは BEGIN/DELETE/INSERT/COMMIT により冪等。
      - 内部の LLM 呼び出しもモック差替え可能な実装。
  - monitoring
    - monitoring_db
      - init_monitoring_db: SQLite 用監視ログ永続化テーブル（system_status, trade_logs, positions, risk_logs など）とインデックス作成用スクリプトを実装（冪等）。
  - パッケージメタ
    - __version__ = "0.1.0"
    - __all__ 定義（主要サブパッケージの公開）

Security / Safety / Design notes
- ルックアヘッドバイアス回避のため、日付基準処理で datetime.today() / date.today() を参照しない設計（target_date を明示的に受け取る）。
- OpenAI など外部 API 呼び出しは、失敗時に継続可能なフォールバック（スコアを 0.0 とする等）を用意してフェイルセーフ化。
- API 呼び出し箇所はテスト時に差し替え可能（内部関数をパッチ）。
- DuckDB / SQLite を利用してオンプレ型のデータ処理を行う設計（外部 API 非依存の研究処理）。
- .env の読み込み時に OS 環境変数を保護する仕組み（protected set）を導入。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 既知の制約
- 一部関数において price が欠損（0.0）だとエクスポージャーやポジション算出が過少/スキップされる旨の TODO コメントあり。将来的なフォールバック価格導入が示唆されている。
- DuckDB の executemany に関する互換性考慮（空リストを渡さない等）のため、書き込み処理で個別 DELETE を行う実装とした。
- OpenAI SDK のエラーオブジェクト変化に対して互換性を持たせるため getattr 等で安全に扱っている。

マイグレーション / 使用上の注意
- OpenAI を利用する機能（news_nlp / regime_detector）は OPENAI_API_KEY が必要。api_key を明示的に渡すことも可能。
- .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時推奨）。
- PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL の値はバリデーションされ、不正値では ValueError が送出されます。

今後の予定（想定）
- stocks マスタに単元情報を持たせ、銘柄別 lot_size をサポートする拡張。
- price 欠損時のフォールバック価格（前日終値や取得原価など）の追加。
- さらなるファクター拡張（PBR、配当利回り等）および zscore 正規化の統合ドキュメント強化。

---
このCHANGELOGはコードベースからの推測に基づき作成しています。実際のリリースノートや運用方針と差異がある場合があります。