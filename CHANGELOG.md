CHANGELOG
=========

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）準拠で記載しています。

Unreleased
----------
（現在未リリースの変更はありません）

0.1.0 - 2026-04-09
-----------------
初回公開リリース。主要なサブモジュールを実装し、環境設定／ポートフォリオ構築／調査用ファクター計算／AI連携／監視用 DB 初期化などのコア機能を提供します。

Added
- 全体
  - パッケージ初期バージョンとして多数のモジュールを追加。
  - パッケージバージョン: __version__ = "0.1.0"。

- 環境・設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動 .env ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して決定（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - .env.local は .env の値を上書き（ただし OS 環境変数は保護）。
    - 自動ロードを無効にする環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサーは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応。
  - 必須環境変数チェック (_require) と入力検証:
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の有効値検証。
    - PAPER_FILL_MODE の有効値検証とデフォルト化。
  - 便利なパス／フラグ設定:
    - duckdb/sqlite のデフォルトパス、PID/KILL フラグパス、閾値（CPU/MEM/DISK）等を環境変数で設定可能。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順＋タイブレーク（signal_rank）で選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコアに基づく重み計算。全スコアが 0 の場合は等金額配分にフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター別集中上限チェック。既存ポジションの時価を基に上限を超えるセクターの新規候補を除外（"unknown" セクターは除外しない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対応する投下資金乗数を提供（未知レジームは 1.0 にフォールバックし WARNING）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に従い発注株数を計算。
    - リスクベース計算、単元株（lot_size）丸め、1 銘柄上限・全体 aggregate cap、および cost_buffer（手数料・スリッページ見積）を考慮したスケーリングロジックを実装。
    - 利用可能現金を超過した場合のスケールダウンと残差配分アルゴリズムを実装（lot_size 単位で再配分、再現性確保のため安定ソート）。

- リサーチ／ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離を DuckDB の prices_daily テーブルから計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER（EPS が無効な場合 None）と ROE を計算。
    - いずれの関数も DuckDB 接続を受け取り SQL と Python の組合せで計算。外部 API 呼び出しは行わない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - rank: 同順位は平均ランクで扱うランク関数（round(v,12) により浮動小数エラーを緩和）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - 依存関係は最低限（DuckDB と標準ライブラリ）。pandas 等には依存しない。

- AI（kabusys.ai）
  - news_nlp:
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む。
    - 特徴:
      - ニュース収集ウィンドウ計算（JST ベース → UTC に変換、ルックアヘッド防止の設計）。
      - 1 銘柄あたりの記事は最新 N 件（デフォルト 10 件）・文字数上限（デフォルト 3000 文字）でトリム。
      - バッチ処理（最大 20 銘柄/コール）、JSON Mode を期待したパース、レスポンス検証（results リスト、code/score の存在、コード検証、数値検証）。
      - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフ＋リトライ（最大 retry 回数）。
      - スコアを ±1.0 にクリップ。部分書き込み対策として対象コードのみ DELETE → INSERT（executemany）を行い、部分失敗時に他コードの既存スコアを保護。
      - テスト用フック: _call_openai_api をパッチ可能に設計。
      - API キー解決: 引数優先、なければ環境変数 OPENAI_API_KEY。
  - regime_detector:
    - score_regime: ETF 1321（日経225 連動 ETF）の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次レジーム判定（bull/neutral/bear）。
    - 特徴:
      - MA200 は target_date 未満のデータのみを使用（ルックアヘッド防止）。
      - マクロ記事フィルタはキーワードリストに基づく ILIKE 検索、最大取得件数を制限。
      - LLM 呼び出し失敗時は macro_sentiment=0.0 でフォールバック（フェイルセーフ）。
      - レジームスコアをクリップし閾値でラベル化、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - news_nlp の内部 API 呼び出し実装とは独立した実装（モジュール結合の最小化）。

- 監視用 DB（kabusys.monitoring）
  - monitoring_db.init_monitoring_db:
    - SQLite 用の監視ログ永続化スキーマを作成する冪等スクリプトを実装。
    - system_status、trade_logs、positions、risk_logs 等のテーブルとインデックスを作成。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （現時点で特記事項なし）

Notes / Known limitations
- research モジュールは DuckDB 上の tables（prices_daily / raw_financials 等）に依存します。必要なデータが不足している場合、結果フィールドは None になることがあります（ログ出力あり）。
- .env の自動ロードはプロジェクトルートを検出できない場合はスキップされます。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- news_nlp/regime_detector の OpenAI 呼び出しはネットワークや API の失敗があり得るため、多くの箇所でフォールバックと安全策を設けています（スコア 0.0、部分更新回避等）。ただし API キーが未設定の場合は ValueError を発生させます。
- position_sizing の単元丸めは現在一律 lot_size（デフォルト 100）想定。将来的には銘柄別 lot_map への拡張を想定する TODO が残っています。
- monitoring_db モジュールのスキーマ作成コードはファイル末尾が切れている場合でも主要テーブルを作成するが、将来的なスキーマ拡張では注意が必要。

問い合わせ／貢献
- バグ報告・機能要望は issue を作成してください。貢献は歓迎します。

(以上)