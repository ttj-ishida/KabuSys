CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。

[Unreleased]
------------

- 特になし。

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期リリース。基本アーキテクチャと主要機能を実装。
- パッケージ情報
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - __all__ に主要サブパッケージを公開: data, strategy, execution, monitoring

- 環境変数/設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルや既存の OS 環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - .env.local を .env の上から上書き（OS 環境変数は保護される）。
  - Settings クラスを提供（settings インスタンス）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等の必須チェック。
    - KABU_API_BASE_URL, LINE_* 等の既定値。
    - ファイルパス系は Path に変換（expanduser）。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の妥当性チェック。
    - 各種しきい値（CPU/MEM/DISK）や監視ファイルパスの設定取得ユーティリティ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順にソート、タイブレークは signal_rank の小さい順。max_positions で切り取り。
    - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等金額にフォールバック（WARNING ログ）。
  - risk_adjustment
    - apply_sector_cap: 既存保有比率に基づくセクター集中制限。sell_codes を考慮して当日売却予定銘柄を除外。unknown セクターは上限対象外。
    - calc_regime_multiplier: レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）。未知レジームは 1.0 でフォールバック（WARNING）。
  - position_sizing
    - calc_position_sizes: 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - risk_based: 許容リスク率、損切り率から株数を算出。
    - equal/score: weight に基づく配分。per-position 上限、lot_size（現状 100）による丸め、_max_per_stock による上限。
    - aggregate cap 実装: 合計投資が available_cash を超える場合スケールダウンし、端数は lot_size 単位で残差順に再配分するアルゴリズムを採用。
    - cost_buffer によりスリッページや手数料の保守的見積りを考慮。

  - パッケージ公開（src/kabusys/portfolio/__init__.py）:
    - select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier をエクスポート。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離率を計算。必要行数不足時は None を返す。DuckDB の prices_daily を直接 SQL で参照。
    - calc_volatility: 20 日 ATR、ATR/株価、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials から直近財務データを取得し PER/ROE を計算。prices_daily と結合して出力。
    - 設計方針として DuckDB 接続を受け取り、外部 API へはアクセスしない純粋関数群。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。horizons の入力バリデーションあり。
    - calc_ic: ファクター値と将来リターンの Spearman ランク相関（IC）を計算。レコード不足や定数分散時は None を返す。
    - rank: 同順位は平均ランクにするランク関数。浮動小数の丸め（round 12 桁）による ties 対策。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - パッケージ公開（src/kabusys/research/__init__.py）: calc_momentum, calc_volatility, calc_value, zscore_normalize（data.stats からインポート）, calc_forward_returns, calc_ic, factor_summary, rank をエクスポート。

- AI 関連（src/kabusys/ai/*）
  - news_nlp (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとにセンチメント ai_score を ai_scores テーブルへ書き込む。
    - 処理の主な特徴:
      - ニュースウィンドウ計算（JST 基準で前日 15:00 〜 当日 08:30 を UTC に変換）。
      - 1 チャンク最大 _BATCH_SIZE=20 銘柄、1 銘柄あたり最大 10 記事・3000 文字にトリム。
      - OpenAI 呼び出しは JSON Mode を利用し、レスポンスの検証（results 配列、code/score 型など）を行う。
      - 429 / タイムアウト / ネットワーク断 / 5xx は指数バックオフでリトライ（リトライ上限あり）。その他例外はリトライしない。
      - スコアは ±1.0 にクリップ。部分失敗に備え、書き込みは対象コードのみ DELETE→INSERT で行い既存の他コードスコアを保護。
      - OpenAI クライアント生成は OpenAI(api_key=...)。api_key 引数が None の場合は環境変数 OPENAI_API_KEY を参照（未設定は ValueError）。
      - テスト容易性: _call_openai_api をパッチ差し替え可能に設計。
  - regime_detector (src/kabusys/ai/regime_detector.py)
    - ETF 1321（日経連動型）の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次レジーム（bull/neutral/bear）を判定、market_regime テーブルへ冪等書き込み。
    - 主な仕様:
      - ma200_ratio は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）でフォールバック。
      - マクロニュースはキーワードリストでフィルタしてタイトルを取得、最大 20 件。
      - マクロセンチメント計算は LLM 呼び出しで非同期ではなく同期実行。API 失敗やパース失敗時は macro_sentiment=0.0 でフォールバック（WARNING）。
      - 合成スコアは clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1)。
      - 判定閾値により regime_label を決定（閾値は定数化）。
      - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等処理。api_key 解決ロジックは news_nlp と同様。
    - テスト容易性: _call_openai_api と _score_macro の挙動は差し替え可能。

  - パッケージ公開（src/kabusys/ai/__init__.py）: score_news をエクスポート。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を利用した MonitoringDB 初期化関数 init_monitoring_db を実装。
  - system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを作成するスクリプト（冪等）。

Security
- 環境変数や API キーは環境から解決する設計。自動 .env ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Changed
- 新規リリースにつき該当なし。

Fixed
- 新規リリースにつき該当なし。

Removed
- 新規リリースにつき該当なし。

Notes / 実装上の注意
- DuckDB の SQL は prices_daily / raw_financials / raw_news 等のテーブル構成を前提としている。実運用前にスキーマとデータの整合性を確認してください。
- OpenAI の呼び出しは外部 API に依存するため、API キーとネットワーク環境、レート制限対応が必要です。テストでは _call_openai_api をモックすることを推奨します。
- position_sizing の lot_size は現状グローバル固定（デフォルト 100）。将来的に銘柄別 lot_map に拡張可能な設計をコメントで残しています。
- .env パーサは一般的な形式をサポートしていますが、非常に複雑なシェル式展開等はサポートしていません。

Acknowledgements
- 本リリースはパッケージの初期機能群をまとめたものです。今後のリリースでドキュメントの充実、テストカバレッジ拡大、さらに堅牢なエラーハンドリングを追加予定です。