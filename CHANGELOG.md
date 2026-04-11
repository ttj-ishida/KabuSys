# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載します。  
このファイルはコードベースの内容から推測して作成した初期の変更履歴です。

All notable changes to this project will be documented in this file.

## [Unreleased]

## [0.1.0] - 2026-04-11
初回リリース — コア機能の実装と基盤ユーティリティ群を追加。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定・環境管理（kabusys.config）
  - `.env` / `.env.local` 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装:
    - export 形式（`export KEY=val`）対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理を考慮して値を抽出。
    - インラインコメントの扱い（非クォート時は直前に空白 or タブがある `#` をコメントと見なす）に対応。
  - `Settings` クラスでアプリケーション設定をプロパティ経由で提供：
    - データベースパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）
    - PID / kill フラグ関連（PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START）
    - 監視しきい値（CPU/MEMORY/DISK）
    - 環境判定（KABUSYS_ENV: development / paper_trading / live）とログレベル検証
    - Paper Trading 用設定（PAPER_FILL_MODE の検証: instant / partial / never / reject）
    - 必須環境変数チェック（_require）

- 実行スクリプト
  - run_execution.py（ExecutionEngine 起動スクリプト）
    - `Settings` を参照し、paper_trading 環境時は専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory により環境に応じたブローカークライアントを生成（paper_trading では MockBrokerClient を想定）。
    - ExecutionEngine/OrderManager/OrderRepository/Reconciler/RiskManager を組み立て、セッション実行。
    - プロセス優先度を起動時に "high" に設定する呼び出しを追加。
    - DuckDB 接続（分析用）を併用。
    - 監視テーブルの存在を保証するために init_monitoring_db を呼び出す（冪等）。

  - run_monitoring.py（SystemMonitor ポーリングループ起動スクリプト）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用（環境に依らず）。
    - プロセス優先度を起動時に "high" に設定。
    - 例外耐性: monitor.check_once() 内で例外が発生してもループを継続し、次ポーリングまで待機。
    - KeyboardInterrupt による graceful shutdown と DB コネクションのクローズ処理を実装。
    - 不正な MONITOR_POLL_INTERVAL の値は警告してデフォルトにフォールバック（0以下や文字列など）。

- ユーティリティ（kabusys.utils.process_priority）
  - プラットフォーム差分を吸収してプロセス優先度を設定するユーティリティを実装。
    - Windows: psutil の HIGH/NORMAL/IDLE_PRIORITY_CLASS を使用。
    - POSIX (Linux/Mac/FreeBSD): nice 値で -10/0/10 を適用。
    - 未対応 OS の場合は警告ログを出してスキップ。
    - 権限不足や未実装例外は捕捉し警告でスキップするフェイルセーフ。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity() を実装（入力検証、権限例外のハンドリング）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates(): BUY シグナルをスコア降順にソートして上位 N 件を返す（同点時は signal_rank でタイブレーク）。
    - calc_equal_weights(): 等金額配分。
    - calc_score_weights(): スコア加重配分（全スコアが 0 の場合は等配分にフォールバックして WARNING）。
  - risk_adjustment:
    - apply_sector_cap(): セクター集中を防ぐため、既存保有のセクター比率が閾値を超える場合に新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier(): market regime（bull/neutral/bear）に応じた資金乗数を返す（未知のレジームは警告のうえ 1.0 でフォールバック）。
  - position_sizing:
    - calc_position_sizes(): allocation_method に応じて発注株数を計算（risk_based / equal / score）。
    - 単元株（lot_size）で丸め、per-position 上限／aggregate cap（available_cash）を考慮。
    - cost_buffer を考慮した保守的評価、スケーリングと端数処理（lot 単位で再配分）を実装。

- リサーチ / ファクター（kabusys.research）
  - factor_research:
    - calc_momentum(): 1M/3M/6M リターンおよび MA200 乖離を計算（ウィンドウ不足時は None を返す）。
    - calc_volatility(): ATR20, ATR_pct, 20日平均売買代金, 出来高比率を計算（データ不足時は None）。
    - calc_value(): raw_financials から最新の財務データを取得して PER/ROE を算出（EPS=0 は None）。
    - DuckDB を利用して SQL ウィンドウ関数で効率的に計算。
  - feature_exploration:
    - calc_forward_returns(): 指定ホライズン（デフォルト: 1,5,21 営業日）で将来リターンを計算。horizons の入力検証あり。
    - calc_ic(): ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが不足（<3）なら None。
    - rank(): 同順位は平均ランクで処理するランク変換（小数丸めで ties 検出の安定化）。
    - factor_summary(): count/mean/std/min/max/median を算出する統計サマリを実装（None 値除外、有限値チェック）。
  - research パッケージの __all__ エクスポートを整備。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news / news_symbols を集約し OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを取得、ai_scores テーブルへ書き込み。
    - タイムウィンドウ: target_date の前日 15:00 JST ～ 当日 08:30 JST（内部では UTC naive datetime を使用）。
    - バッチ処理（最大 20 銘柄／コール）、1銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - 出力バリデーション（JSON パース、results 配列、各要素に code/score、未知コードは無視）。
    - スコアは ±1.0 にクリップ。
    - リトライポリシー: 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフで再試行（上限あり）。
    - API キーは引数で渡すか環境変数 OPENAI_API_KEY を参照。未設定時は ValueError。
    - 書き込みは部分失敗に配慮して対象コードのみを DELETE → INSERT（トランザクション制御）。
    - テストしやすさのため OpenAI 呼び出し部分を別関数で分離（_call_openai_api をパッチ可能）。
    - 実装上の安全策: datetime.today()/date.today() を参照せず与えられた target_date のみを使用（ルックアヘッドバイアス防止）。
  - regime_detector:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market regime を判定（'bull'/'neutral'/'bear'）。
    - マクロニュース抽出はキーワードマッチ（複数キーワードの ILIKE 条件）でタイトルを取得、最大記事数で制限。
    - MA200 算出は target_date 未満のデータを使用してルックアヘッドを防止。データ不足時は中立（1.0）を返す。
    - API エラー時は macro_sentiment=0.0（中立）で継続するフェイルセーフ。
    - 判定結果は market_regime テーブルへ冪等に書き込む（トランザクションで削除→挿入）。
    - OpenAI 呼び出しにはリトライとバックオフを導入。

- DB/接続関連
  - DuckDB と SQLite を併用する設計（DuckDB は分析用、SQLite は監視／発注系の永続化想定）。
  - 監視テーブル初期化用ユーティリティ init_monitoring_db の呼び出しを run 系スクリプトに追加して存在を保証（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーの取り扱いは引数優先／環境変数フォールバック。未設定時は明示的にエラーを出すことでキー無しの呼び出しを防止。

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、全ての時系列・ニュース関連関数は target_date 引数のみを使用し、内部で現在日時を参照しない設計。
- 外部 API 呼び出し（OpenAI 等）は失敗時にフェイルセーフ動作（スコア 0.0 を仮定する、もしくは該当チャンクはスキップ）を組み込むことでシステム全体の安全性を高めている。
- DuckDB 実行時の互換性（executemany に空リストを渡せない等）を考慮した実装が行われている。
- 設定値の検証（列挙型チェックや数値範囲チェック）を行い、不正な設定は ValueError や警告で明示する。

---

今後の更新例（想定）
- Unreleased / 次リリースでは監視アラートの通知（LINE 連携）、Broker 実装の拡張（実取引 API の堅牢化）、単元株数を銘柄別に扱う拡張などを予定。