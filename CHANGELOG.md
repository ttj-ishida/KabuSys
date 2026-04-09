CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。本書式は「Keep a Changelog」に準拠します。

フォーマット:
- 変更はセマンティックに分類（Added, Changed, Fixed, Deprecated, Removed, Security）します。
- 各リリースは日付付きで記載します。

Unreleased
----------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 初回リリース。以下の主要機能を追加。
  - パッケージメタ情報
    - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）。
    - パッケージ公開時にエクスポートされる主要モジュール名を __all__ で定義。

  - 環境変数・設定管理（src/kabusys/config.py）
    - .env / .env.local ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で検出）。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサは以下をサポート・考慮:
      - コメント行（#）・空行の無視。
      - export KEY=val 形式の対応。
      - シングル／ダブルクォート内のバックスラッシュエスケープ処理。
      - クォートなし値のインラインコメント判別ルール（直前がスペース/タブの場合にコメントとみなす）。
    - .env の読み込み優先度: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き不可。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / Paper Trading / 監視・閾値設定 / システム設定（env, log_level）など多数のプロパティを取得可能。
    - 設定値の検証ロジック:
      - PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等の有効値チェックを実装し、無効値は ValueError を送出。
      - 必須値（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は未設定時に ValueError。

  - ポートフォリオ構築ユーティリティ（src/kabusys/portfolio/*）
    - 候補選定: select_candidates — スコア降順、同点は signal_rank でタイブレーク。
    - 重み計算:
      - calc_equal_weights — 等金額配分。
      - calc_score_weights — スコア加重配分。全スコアが 0 の場合は等配分にフォールバックし WARNING を出力。
    - リスク調整:
      - apply_sector_cap — セクター集中制限。既存ポジションに基づきセクター比率が上限（max_sector_pct）を超える場合、新規候補を除外。unknown セクターは適用除外。
      - calc_regime_multiplier — market regime に応じた投下資金乗数 ("bull"=1.0, "neutral"=0.7, "bear"=0.3)。未知レジーム時は 1.0 にフォールバック（警告ログ）。
    - ポジションサイジング:
      - calc_position_sizes — allocation_method ("risk_based" / "equal" / "score") に基づき発注株数を計算。
      - lot_size（単元株）を考慮して丸め、max_position_pct による per-stock 上限、available_cash による aggregate cap を適用。
      - cost_buffer を用いてスリッページ/手数料を保守的に見積もる。aggregate 超過時はスケールダウンし、lot_size 単位で残差（fractional remainders）を大きい順に配分するロジックを実装。

  - リサーチ／ファクター計算（src/kabusys/research/*）
    - calc_momentum — 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB 上の prices_daily から計算。MA200 に必要な行数が不足する場合は None を返す。
    - calc_volatility — 20日 ATR（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。ATR の欠損伝播を制御。
    - calc_value — raw_financials から最新財務（report_date <= target_date）を取得し PER, ROE を計算。EPS がゼロ・欠損の場合は per に None。
    - いずれの関数も DuckDB 接続を受け取り、外部 API に依存しない純粋関数（DB の prices_daily / raw_financials のみ参照）。
    - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

  - 特徴量探索・統計ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns — 指定 horizon（営業日）に対する将来リターンを一括で取得（1 クエリ）。horizons 引数のバリデーションあり（1 <= h <= 252）。
    - calc_ic — ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）や分散ゼロの場合は None。
    - rank — 同順位は平均ランクを与える実装。ランク前に round(v, 12) で丸めて浮動小数誤差による ties 検出漏れに対処。
    - factor_summary — count/mean/std/min/max/median を標本ではなく母分散（n）で計算。None と非有限値は除外。

  - AI 関連機能（src/kabusys/ai/*）
    - ニュース NLP（src/kabusys/ai/news_nlp.py）
      - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込み。
      - バッチサイズ、1銘柄あたり記事・文字数上限（_BATCH_SIZE, _MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）を実装し、トークン肥大化を抑制。
      - API 呼び出しは JSON Mode を利用。429 / 接続断 / タイムアウト / 5xx は指数バックオフでリトライ。その他エラーはリトライせずスキップ。
      - レスポンスの厳密なバリデーションを行い、スコアは ±1.0 にクリップ。部分失敗時でも既存スコアを保護するため、対象 code のみ DELETE → INSERT する冪等書き込みを実装。
      - OpenAI API キーは引数で渡すか OPENAI_API_KEY 環境変数を使用。未設定時は ValueError を送出。
      - ルックアヘッドバイアス回避のため datetime.today()/date.today() を参照しない設計。
    - レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（Nikkei-linked ETF）の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して daily regime を判定（'bull'/'neutral'/'bear'）。
      - MA 計算は target_date 未満のデータのみを使用（ルックアヘッド回避）。データ不足時は中立（ma200_ratio=1.0）。
      - マクロニュースはタイトルベースでキーワード検索（複数キーワード群）し最大記事数を取得。記事が無い場合は macro_sentiment=0.0。
      - LLM 呼び出しは再試行ロジックを備え、失敗時は 0.0 にフォールバック（例外は投げず警告ログ）。
      - 判定結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - OpenAI キー解決は news_nlp と同様。

  - 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
    - SQLite ベースの MonitoringDB 初期化ロジックを提供（init_monitoring_db）。
    - system_status, trade_logs, positions, risk_logs などのテーブルとインデックスを冪等的に作成（スキーマ定義）。
    - ビジネスロジックを持たず、読み書き専用の永続化層として設計。

  - モジュール公開 API
    - portfolio, research, ai モジュールで主要関数を __all__ 経由で再エクスポートし、外部利用を簡素化。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Notes / 実装上の重要な挙動（利用者向け補足）
- .env パーサは複雑なシェル展開（変数展開、コマンド置換等）には対応しない。単純な KEY=VALUE とクォート・エスケープを想定。
- DuckDB / SQLite スキーマやクエリは現在のロジックに依存するため、外部でスキーマ変更する場合は各関数のクエリを確認してください。
- AI 呼び出しは外部ネットワーク・OpenAI に依存するため、テスト時は _call_openai_api をモックできます（各モジュールで明示的に差し替え可能に実装）。
- レジーム判定・ニューススコアはフェイルセーフ設計（API 失敗時は中立スコアや 0.0 にフォールバック）になっており、本番での自動トレードに使用する場合は運用ポリシーを慎重に設計してください。

Contributing
- バグ報告・機能提案はリポジトリの Issue を参照してください。設計方針（ルックアヘッド回避、DB のみ参照する研究関数、フェイルセーフな AI 呼び出し、冪等書き込み等）に沿った実装をお願いします。