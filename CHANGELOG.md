# CHANGELOG

本ファイルは Keep a Changelog の形式に準拠します。意味のある変更のみを収集しています（コードベースから実装内容を推測して記載）。

すべての変更はセマンティックなまとまりで記載しています。日付は本コードスナップショットの作成日（2026-04-11）を使用しています。

## [0.1.0] - 2026-04-11

Added
- 基本パッケージ情報
  - パッケージルートのバージョンを `__version__ = "0.1.0"` として公開。

- 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機構を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位を OS 環境変数 > .env.local > .env に設定。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化に対応。
  - .env パーサ実装（export 形式、クォート／エスケープ、インラインコメント処理をサポート）。
  - Settings クラスを実装し、各種環境変数をプロパティとして提供（J-Quants, kabu API, LINE, DB パス, 監視閾値, PID/kill flag 等）。
  - 環境値の検証: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など不正値時に例外を送出。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine 起動フローを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成。
    - OrderRepository, OrderManager, RiskManager, Reconciler を組み立て ExecutionEngine.run_session() を実行。
    - duckdb 接続を使用。
    - プロセス起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。無効な値はデフォルトへフォールバックし警告を出力。
    - 監視は環境にかかわらず本番 sqlite_path を利用する（monitoring は常に本番 DB を監視する設計）。
    - プロセス優先度を "high" に設定してから起動（set_process_priority）。

- プロセス制御ユーティリティ (kabusys.utils.process_priority)
  - Windows と POSIX（Linux/Mac/FreeBSD）で動作するプロセス優先度設定を実装（psutil ベース）。
  - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
  - 権限不足や未対応 OS の場合は警告を出してスキップするフェイルセーフを実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコアで上位 N を選択（同点は signal_rank でブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（スコア合計が 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限ロジック（既存ポジションの時価ベースで判定、"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull/neutral/bear をマップ、未知のレジームは警告のうえ 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に応じた発注株数計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でスケールダウン、cost_buffer を考慮した保守的見積り。
    - スケーリング時の端数処理（残差に基づくロット単位追加配分）を実装。

- 研究（research）モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1/3/6 ヶ月リターン、200 日移動平均乖離率を DuckDB 上の prices_daily から計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を考慮。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（target_date 以前の最新財務データを採用）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。horizons 検証を実施。
    - calc_ic: スピアマンランク相関（Information Coefficient）を実装。有効レコードが 3 件未満なら None。
    - rank / factor_summary: 同順位の平均ランク処理、各カラムの基本統計サマリ（count/mean/std/min/max/median）を実装。
  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

- AI 関連 (kabusys.ai)
  - news_nlp:
    - raw_news / news_symbols から銘柄ごとに記事を集約し、OpenAI (gpt-4o-mini) を用いて銘柄別センチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む。
    - タイムウィンドウは JST ベースで定義（前日 15:00 〜 当日 08:30 JST を UTC に変換して比較）。
    - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの最大記事数・最大文字数制限、レスポンスバリデーション、スコアクリッピング（±1.0）を実装。
    - OpenAI 呼び出しに対して 429 / ネットワーク / タイムアウト / 5xx を対象に指数バックオフでリトライ。致命的失敗時は当該チャンクをスキップして継続（フェイルセーフ）。
    - API レスポンスの厳密な JSON モードを期待するが、前後ノイズ混入時に最外側の {} を抽出して復元する耐性を追加。
    - 部分成功時に他銘柄の既存スコアを保護するため、書き込みはスコアを取得した code のみ DELETE → INSERT（トランザクション）を行う。
    - OPENAI_API_KEY の解決（引数優先、環境変数フォールバック）。未設定時は ValueError。

  - regime_detector:
    - ETF 1321 の ma200 乖離 (MA weight 0.7) とマクロニュースの LLM センチメント (weight 0.3) を合成して当該日の市場レジーム（'bull' / 'neutral' / 'bear'）を判定、market_regime テーブルへ冪等書き込み。
    - prices_daily から target_date 未満のデータのみを使用してルックアヘッドバイアスを排除。
    - マクロニュース抽出はキーワードマッチに基づくタイトル取得（最大件数制限）。LLM が利用できない場合は macro_sentiment=0.0 で継続。
    - OpenAI 呼び出しのリトライ / フェイルセーフを備える。

Other notable implementation details (設計判断や堅牢化)
- DuckDB/SQLite をデータ層として利用。多くの分析・AI 関連処理は DuckDB 接続を受け取り SQL で完結する設計（本番取引系 API へのアクセスはしない）。
- ロギングと警告を多用し、データ不足やパラメータ不正時にフェイルセーフにフォールバックする実装。
- 外部 API 呼び出し（OpenAI など）はリトライと部分失敗保護を組み合わせ、安全に継続可能な動作を目指す。
- 内部ドキュメント（関数コメント）にて PortfolioConstruction.md / StrategyModel.md 等の参照箇所を明記し、アルゴリズムの根拠を示す。

Changed
- 新規初期リリースのため該当なし。

Fixed
- 新規初期リリースのため該当なし。

Security
- OpenAI API キー等の取り扱いは環境変数経由とし、.env ファイルの自動読み込みでは OS 環境変数を保護する仕組み（protected set）を実装。

Breaking Changes
- 新規初期リリースのため該当なし。

Future / TODO（コード中コメントより推測）
- position_sizing: 銘柄別単元株情報(lot_size) を銘柄マスタに持たせる拡張。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価など）の導入検討。
- DuckDB の executemany 空リスト制約への対応は既に考慮済みだが、将来的な DB バージョンへ注意。

---

本 CHANGELOG はコードの構成とコメントから推測して作成しています。追加のコミット履歴やリリース情報がある場合はそれに合わせて更新してください。