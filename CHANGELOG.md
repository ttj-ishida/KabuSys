Changelog
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。
このファイルは後からのリリース履歴追跡用に更新してください。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- 初期リリース: kabusys パッケージの基本機能を実装。
- パッケージ情報
  - バージョン: 0.1.0
  - パッケージ説明ヘッダを追加（src/kabusys/__init__.py）。
- 設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード順: OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索 → 配布後も正しく動作。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - 必須設定の取得時に未設定なら ValueError を送出する _require を提供。
  - 各種バリデーション: KABUSYS_ENV（development/paper_trading/live）、LOG_LEVEL（DEBUG/INFO/...）、PAPER_FILL_MODE（instant/partial/never/reject）など。
  - デフォルト値（DB ファイルパス、kabu API の base URL、PID/flag パスや監視閾値など）を定義。
- ポートフォリオ構築（src/kabusys/portfolio）
  - portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順・同点は signal_rank 昇順でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分 (1/N) を返す。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0 の場合は等金額にフォールバックして警告ログを出力。
  - risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、max_sector_pct を超えるセクターの新規候補を除外。sell_codes を除外して計算。セクター不明（"unknown"）は上限適用対象外。
    - calc_regime_multiplier: レジームに基づく資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告ログを出して 1.0 にフォールバック。
  - position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based" / "equal" / "score") に基づき注文株数を計算。lot_size（単元）で丸め、1 銘柄上限・aggregate 上限（available_cash）・cost_buffer を考慮してスケールダウン（残差配分ロジックあり）。価格欠損や price<=0 の場合はスキップ。
    - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づく株数計算を実装。
    - equal/score: 重みから配分を計算。将来的な拡張（銘柄別 lot_size）用に TODO を記載。
- リサーチ / ファクター計算（src/kabusys/research）
  - factor_research.py
    - calc_momentum: 1M/3M/6M リターンおよび 200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily から算出。データ不足時は該当カラムに None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比などを算出。true_range の NULL 伝播制御やカウントによる閾値判定を実装。
    - calc_value: raw_financials から target_date 以前の最新財務を取得して PER / ROE を算出。EPS 欠損時は PER を None とする。
  - feature_exploration.py
    - calc_forward_returns: 指定ホライズンに対する将来リターンを一括 SQL で取得。horizons のバリデーション（正の整数かつ <=252）を実施。
    - calc_ic: スピアマンのランク相関（IC）を実装。records の結合、None 除外、少数レコード時は None を返す。
    - rank / factor_summary: 同順位は平均ランクとするランク関数、基本統計量（count/mean/std/min/max/median）を pandas 等に依存せず実装。
  - research パッケージは zscore_normalize（kabusys.data.stats 経由）などをエクスポート。
- AI 関連（src/kabusys/ai）
  - news_nlp.py
    - score_news: raw_news と news_symbols を集計して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（ai_scores）を DuckDB に書き込む処理を実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST → UTC に変換）を calc_news_window で提供。
    - バッチサイズ、記事数・文字数上限、レスポンスバリデーション（JSON 抽出、results 配列、コード整合性、数値性）、スコアクリッピング（±1.0）を実装。
    - 再試行ポリシー: 429, ネットワーク断, タイムアウト, 5xx を対象に指数バックオフでリトライ（最大回数・ログ出力）。
    - 部分失敗時のデータ保護: 書き込みは対象コードを限定して DELETE → INSERT（executemany）を実行。DuckDB の executemany 空リスト制約を考慮。
    - テスト時の差し替えポイントとして _call_openai_api を定義。
  - regime_detector.py
    - score_regime: ETF 1321（Nikkei 225 連動 ETF）の直近 200 日 MA 乖離とマクロニュース LLM センチメントを合成して market_regime テーブルへ冪等的に書き込み。
    - マクロ記事抽出はキーワードリストでタイトルをフィルタ（最大取得件数制限）。API 失敗時は macro_sentiment=0.0 としてフェイルセーフで継続。
    - レジーム合成ロジックと閾値（bull/neutral/bear）を実装。OpenAI 呼び出しは独自実装で news_nlp とは分離。
- 監視ログ永続化（src/kabusys/monitoring）
  - monitoring_db.py
    - init_monitoring_db: SQLite 接続に対して system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等に作成する SQL スクリプトを実装。

Changed
- （初期リリースのため無し）

Fixed
- （初期リリースのため無し）

Deprecated
- （初期リリースのため無し）

Removed
- （初期リリースのため無し）

Security
- OpenAI API キーは引数優先で、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は明示的に ValueError を発生させる（安全側フェイル）。

Notes / Known limitations / TODOs
- price が欠損（0.0）の場合にエクスポージャーが過小見積りされブロックが外れる点は TODO として注記。将来的に前日終値や取得原価でのフォールバック検討。
- 単元株（lot_size）は現状グローバル固定。将来的に銘柄別 lot_map を受け取る設計へ拡張予定（TODO コメントあり）。
- calc_score_weights は全スコアがゼロのとき等金額にフォールバックし、警告ログを出す（設計仕様）。
- DuckDB に関する互換性考慮（executemany の空リストを避ける等）を実装済み。
- OpenAI SDK のエラー型やステータスの扱いは SDK のバージョン差を吸収するよう getattr を使用するなど堅牢化しているが、将来の SDK 変更に注意。
- datetime.today()/date.today() を直接参照せず、外部から target_date を渡す設計でルックアヘッドバイアスを防止している点に留意。

パッケージのエクスポート（主な公開 API）
- kabusys.settings (Settings インスタンス)
- kabusys.portfolio: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier
- kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
- kabusys.ai: score_news（news_nlp の公開 API）
- kabusys.ai.regime_detector: score_regime（内部的に利用可能）

お問い合わせ
- バグ報告や機能要望はリポジトリの Issue に投稿してください。