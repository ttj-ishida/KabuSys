# Changelog

すべての notable な変更はこのファイルに記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。  
安定版リリースはセマンティックバージョニングに従います。

注: 内容はソースコードから推測して作成しています（実装説明・機能一覧としての目的）。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。本リリースでは自動売買システムのコアとなる設定管理、ポートフォリオ構築、研究用ファクター計算、AI を用いたニュース解析／レジーム判定、監視用 DB 永続化層などの主要機能を提供します。

### Added
- 共通/パッケージ情報
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの public API を __all__ で整理（data, strategy, execution, monitoring 等を公開）。

- 環境変数・設定管理（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込み機能を実装。
  - 自動 .env ロード:
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して特定（CWD に依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - .env パーサ実装:
    - export KEY=val 形式に対応。
    - シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱い。
    - コメントの扱い（クォート無しの '#' は直前がスペース/タブの場合のみコメントとみなす）等の細かい挙動を実装。
  - Settings クラス（settings）:
    - J-Quants / kabuステーション / LINE / DB パス / Paper Trading / 監視・システム設定 など多数のプロパティを提供。
    - 必須環境変数未設定時は ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
    - KABUSYS_ENV, LOG_LEVEL 等の許容値チェックを実装。
    - PAPER_FILL_MODE の妥当性チェック（instant/partial/never/reject）。
    - ファイルパスは Path オブジェクトで返却（expanduser を適用）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: スコア降順、同点は signal_rank でタイブレークする候補選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率配分（スコア合計が 0 の場合は等配分へフォールバックし WARNING）。
    - これらは DB 非依存の純粋関数として実装（メモリ内計算のみ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を制限。既存保有時価（当日売却予定の銘柄除外可能）を計算し、セクター比率が上限を超える場合は当該セクターの新規候補を除外。unknown セクターは除外対象にしない。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金の乗数を提供（未定義レジームは警告ログを出して 1.0 にフォールバック）。
  - position_sizing:
    - calc_position_sizes: 各銘柄の発注株数を計算（allocation_method: "risk_based" / "equal" / "score" をサポート）。
    - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct からベース株数を算出し単元株（lot_size）で丸め。
    - equal/score: 重み（weights）に基づき position ごとの alloc を計算し単元株丸め。
    - per-stock 上限（max_position_pct）、aggregate cap（available_cash）、lot_size、cost_buffer（手数料・スリッページ見積）を考慮してスケーリング、端数配分のアルゴリズムを実装。
    - open_prices 欠損時はスキップし、ログ出力する設計。
    - 全て純粋関数（外部 DB に依存しない）。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離(ma200_dev) を DuckDB SQL で計算。window の不足時は None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播を厳密に扱う実装。
    - calc_value: raw_financials から直近の財務数値と当日の株価を組み合わせ PER/ROE を算出（EPS が 0/NULL の場合は None）。
    - いずれも DuckDB 接続を受け取り、prices_daily/raw_financials テーブルのみ参照。
  - feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一括取得。horizons のバリデーションあり。
    - calc_ic: Spearman（ランク相関）による IC 計算を実装。データ不足（有効レコード < 3）なら None。
    - rank: 同順位（ties）は平均ランクで処理。浮動小数点丸め（round 12 桁）で ties 検出の安定化を図る。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出（None を除外）。

- AI 関連（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini + JSON Mode）へバッチ送信して銘柄別センチメント（ai_score）を算出。
    - タイムウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（内部は UTC に変換し比較）。
    - バッチサイズ、トークン肥大化対策（記事数上限／文字数上限）を実装（デフォルト: 20 銘柄/チャンク, 10 記事/銘柄, 3000 文字/銘柄）。
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx を指数バックオフ（最大リトライ回数制御）で再試行。その他は失敗時にスキップ。
    - レスポンスバリデーション: JSON パース復元ロジック、results リストの構造チェック、未知コード排除、スコアの数値変換と ±1.0 のクリップ。
    - 書込み: 成功取得した銘柄のみを対象に ai_scores テーブルを冪等的に更新（DELETE → INSERT、部分失敗時は他銘柄の既存スコアを保護）。
    - OpenAI クライアント呼び出し部分はテストで差し替えやすい設計（_call_openai_api の抽象化）。
  - regime_detector:
    - ETF 1321（日経225 連動型）の ma200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull/neutral/bear）を判定。
    - マクロニュース抽出はキーワードベース（多数の日本／米国関連語をデフォルトで用意）でタイトルを取得、最大件数制限あり。
    - レジームスコア合成式を実装（MA 重み 0.7、マクロ重み 0.3、スケーリング・クリップあり）、閾値によるラベル決定。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - 結果は market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - OpenAI 呼び出し部分は news_nlp の実装とは独立しており、テスト時に差し替え可能。

- 監視ログ永続化（kabusys.monitoring.monitoring_db）
  - SQLite を用いた監視 DB 初期化スクリプトを実装（冪等）。
  - 作成テーブル（少なくとも以下を含む）:
    - system_status（CPU/Memory/Disk/プロセス状態の定期記録）およびインデックス
    - trade_logs（発注・約定等のイベントログ）およびインデックス
    - positions（現在ポジションの永続化）およびインデックス
    - risk_logs（リスクイベントログ）など（スクリプトは 5 テーブル＋インデックスを作成する設計）
  - ビジネスロジックを持たない読み書き専用の永続化層として実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーは関数引数で渡すか環境変数 OPENAI_API_KEY を使用する設計。未設定時は ValueError を送出し明示的に扱うようにしている。
- .env 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。

### Notes / Implementation details
- 多くのモジュールは「DuckDB 接続を受け取る」「外部 API には依存しない（研究関数）」「純粋関数で副作用を持たない」などの方針で設計されているため、テスト容易性が考慮されています。
- OpenAI 呼び出しは例外ハンドリングとリトライ戦略を備え、API 失敗時は安全側のデフォルト（スコア 0.0 など）で継続するフェイルセーフを実装しています。
- position sizing のアルゴリズムでは単元丸め、per-stock/aggregate 上限、cost_buffer による保守的見積を組み合わせたスケーリングロジックを採用しています。
- SQL クエリは DuckDB のウィンドウ関数（LAG/LEAD/AVG OVER 等）を多用し、必要行数のチェック（カウント条件）でデータ不足時に None を返す堅牢な実装になっています。
- 一部 TODO コメントあり（将来的な lot_size の銘柄別対応や価格フォールバック等）。

----------

今後のリリースではテストカバレッジ、ドキュメント（API 使用例・設定例）、実行環境での運用上の注意（OpenAI 利用制限など）、および監視／アラート連携機能の強化を予定しています。