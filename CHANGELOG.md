CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

フォーマット:
- 変更はセクション（Added / Changed / Fixed / etc.）ごとに分類しています。
- バージョンにはリリース日を併記しています。

Unreleased
----------

（現時点の未リリース変更はありません）

0.1.0 - 2026-04-09
------------------

Added
- パッケージ基盤
  - パッケージメタ情報を追加: kabusys.__version__ = "0.1.0"。
  - パッケージエクスポートの基本モジュールを定義（data, strategy, execution, monitoring 等）。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数からの自動読み込み機能を実装。
    - プロジェクトルートの自動検出: .git または pyproject.toml を起点に探索（配布後も CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - OS 環境変数は protected として .env による上書きを防止。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理等の実用的なパースをサポート。
  - Settings クラスを提供:
    - J-Quants / kabuステーション / LINE / DB（DuckDB/SQLite）などの設定プロパティ。
    - 型変換・Path 展開・デフォルト値・バリデーション（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（タイブレークは signal_rank）で抽出。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア正規化配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター別既存エクスポージャーを計算し、1セクターの上限（max_sector_pct）を超える場合に新規候補を除外。unknown セクターは適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投資乗数を返す。未知レジームは警告とともに 1.0 でフォールバック。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。リスクベースの算出、単元株（lot_size）丸め、銘柄毎上限・aggregate cap（利用可能現金によるスケールダウン）、cost_buffer による保守的見積り、残差配分ロジックを実装。
    - 設計上、株価欠損時はログを出して該当銘柄をスキップ。

- リサーチ／ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を DuckDB SQL ウィンドウ関数で計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR（true_range の扱いに注意）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。ウィンドウ不足は None を返す。
    - calc_value: raw_financials より直近財務データを取得して PER（EPS が 0/欠損なら None）・ROE を計算。
    - いずれも DuckDB 接続を受け取り SQL+Python で完結（外部 API 非依存）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。horizons の検証（正数かつ <=252）と単一クエリ実装による効率化。
    - calc_ic: スピアマンランク相関（IC）を実装。ties（同率）に対して平均ランクを用いる。有効レコード数が 3 未満の場合は None。
    - rank: 同順位は平均ランクを返す実装（浮動小数の丸めで ties 検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
  - research パッケージ __init__ で zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI 機能（src/kabusys/ai/*）
  - news_nlp:
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄別センチメント（ai_score）を付与し ai_scores テーブルへ書き込む。
    - ニュース収集ウィンドウ計算（JST 基準を UTC に変換）を提供（calc_news_window）。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数上限（トリム）、JSON Mode を用いた厳密なレスポンス期待。
    - リトライポリシー: 429・ネットワーク断・タイムアウト・5xx は指数バックオフでリトライ。その他エラーは失敗時にスキップ（フェイルセーフ）。
    - レスポンスの堅牢な検証を実装（JSON 抽出、results/key/types/コード検証、スコアを ±1.0 にクリップ）。
    - DB 書き込みは部分成功を考慮した冪等操作（対象コードの DELETE → INSERT、executemany の空リスト回避）。
    - テスト用フック: _call_openai_api を patch してモック可能。
  - regime_detector:
    - score_regime: ETF 1321 の ma200 乖離（200日）とマクロニュースの LLM 評価を合成して market_regime に書き込む。
    - マクロニュース抽出はキーワードベースでタイトルを取得（上限あり）。記事がない場合は LLM 呼び出しをスキップし macro_sentiment=0.0 を使用。
    - 合成スコアは重み付け（MA 70%, Macro 30%）、スコアクリップ、閾値判定（bull/neutral/bear）。
    - API 失敗時は macro_sentiment=0.0 にフォールバックして継続（フェイルセーフ）。
    - DB 書き込みは冪等（BEGIN/DELETE/INSERT/COMMIT）。_call_openai_api はニュース側と意図的に別実装で分離。

- 監視用 DB 層（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 用の監視テーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを冪等的に作成するスクリプトを提供。

Design / Implementation Notes
- DuckDB を中心とした SQL 実装により外部 API 呼び出しを最小化（研究系機能は prices_daily/raw_financials/raw_news 等のみ参照）。
- OpenAI 依存箇所は明確に分離し、テスト時に差し替え可能な設計（モックポイントを提供）。
- ルックアヘッドバイアス対策: 日付参照は引数で渡す設計（datetime.today()/date.today() を直接参照しない）。
- ロギングを多用し、データ不足や API 失敗時に WARNING/INFO を出力してフェイルセーフで続行するポリシー。
- 細かなバリデーションとデフォルト値により、環境設定ミス時には早期に ValueError を送出する設計（例: OpenAI API キー未設定、PAPER_FILL_MODE の不正値など）。

Fixed
- 初回リリースのため該当なし。

Notes
- 本 CHANGELOG はコードベースから推測してまとめたものであり、実際のリリースノートにおける文章や粒度はプロジェクト方針に合わせて調整してください。