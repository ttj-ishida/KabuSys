CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに準拠して記載しています。  
日付や分類は、コードベースの内容から推測してまとめたものです。

Unreleased
----------

- 今のところ未リリースの変更はありません。

[0.1.0] - 2026-04-12
-------------------

Added
- 初期リリース: KabuSys パッケージ公開（__version__ = 0.1.0）。
- 環境/設定管理
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で探索）。
  - .env ファイルパーサを実装。export プレフィックス、クォート／エスケープ、インラインコメントの扱いに対応。
  - OS 環境変数を保護する protected オプション付きの .env 上書きロジックを実装。
  - Settings クラスを追加し、各種設定（DB パス、ログレベル、KABUSYS_ENV、Paper Trading 関連設定など）をプロパティ経由で取得可能に。
  - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH 等の環境変数サポートを追加。
- 起動スクリプト
  - run_monitoring.py: SystemMonitor 用ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨の挙動を実装。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB を使用して本番と分離。プロセス優先度設定・DB初期化・ExecutionEngine 組み立て・セッション実行を行う。
- データベース初期化
  - monitoring テーブル群の初期化を保証する init_monitoring_db 呼び出しを実装（冪等）。
- プロセス制御ユーティリティ
  - process_priority モジュールを追加。Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する set_process_priority を提供。
  - set_cpu_affinity によりカレントプロセスを指定コアにピン止めするユーティリティを追加。
- Portfolio（ポートフォリオ構成）
  - portfolio_builder: シグナル選定（select_candidates）・等金額配分（calc_equal_weights）・スコア重み配分（calc_score_weights）を実装。
  - risk_adjustment: セクター集中排除ロジック（apply_sector_cap）・市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: 重み・候補・資金量・現在ポジション・価格情報を元に発注株数を計算する calc_position_sizes を実装（risk_based / equal / score の allocation_method をサポート）。単元株（lot_size）丸め、aggregate cap によるスケーリング、コストバッファ考慮などを実装。
  - portfolio パッケージの __all__ を定義し、主要関数をエクスポート。
- リサーチ（研究）
  - research/factor_research.py: モメンタム、ボラティリティ（ATR等）、バリュー（PER/ROE）ファクター計算を実装。DuckDB の prices_daily / raw_financials を参照する設計。
  - research/feature_exploration.py: 将来リターン計算（複数ホライズン対応）、IC（Spearman ランク相関）計算、ファクター統計要約、ランク処理ユーティリティを実装。外部依存を抑え標準ライブラリのみで実装。
  - research パッケージで zscore_normalize（kabusys.data.stats 経由）を含む主要関数を公開。
- AI ニューススコアリング
  - ai/news_nlp.py: raw_news + news_symbols から記事を集約し、OpenAI API（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores テーブルへ書き込む機能を実装。
    - 前日 15:00 JST ～ 当日 08:30 JST 相当のニュースウィンドウを計算して対象記事を集約。
    - 銘柄ごとに記事数・文字数上限を設定（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - 最大 20 銘柄/バッチで API 呼び出し、429/ネットワーク/5xx に対して指数バックオフでリトライ（一部失敗はスキップして継続するフォールトトレラント設計）。
    - レスポンス検証、スコアの ±1.0 クリップ、部分更新（該当コードのみ置換）で堅牢性を確保。
    - OpenAI API キー未設定時は明示的に ValueError を送出。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。コマンドライン引数 (--from, --to, --db) をサポート。
  - tools パッケージを追加（空の __init__ 含む）。
- その他
  - 複数モジュールで DuckDB / sqlite の接続パターンを導入（研究・AI・実行エンジン間での一貫性）。

Changed
- run_monitoring.py: MONITOR_POLL_INTERVAL の解釈を厳密化。0 以下や不正文字列はデフォルト（60 秒）へフォールバックし、警告ログを出力する扱いに変更（time.sleep に渡す不正を回避）。
- run_monitoring.py: 監視コンポーネントは環境（development/paper_trading/live）に関わらず設定上の sqlite_path（本番パス）を使用する仕様を明示。
- run_execution.py: paper_trading 環境では settings.paper_sqlite_path を使い、本番 DB と完全分離する運用を採用。
- Settings: KABUSYS_ENV / LOG_LEVEL 等の値チェックを追加し、不正値で ValueError を送出するように改良。
- position_sizing: aggregate cap 適用時のスケーリングと端数処理（lot_size 単位での再配分ロジック）を実装して現金上限超過時の振る舞いを改善。
- risk_adjustment: unknown セクター（sector_map にないコード）はセクター上限チェックの対象外とする扱いを明文化。
- process_priority: 未対応 OS に対するフォールバックと例外吸収（AccessDenied 等での警告ログ）を追加。

Fixed
- .env パースの不具合緩和: クォート・エスケープシーケンスやインラインコメントの扱いを明確化し、誤解釈による環境変数設定漏れを軽減。
- calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックするようにして divide-by-zero を回避（警告ログを出力）。
- factor_research / feature_exploration: データ不足時に None を返す仕様を統一し、Null 伝播や行数不足での例外を避ける実装に改善。
- ai/news_nlp: API 呼び出しでの失敗（レスポンス欠損・形式不正）が発生しても他銘柄の処理を継続する設計（部分更新）により、一部失敗が全体失敗へ波及しないように修正。

Security
- ai/news_nlp.py: OpenAI API キーの未指定を検出して早期にエラーにすることで、誤った無認証呼び出しを防止。
- .env 読み込み時に OS 環境変数を保護（protected set）することで、システム側の既存環境変数を上書かない安全策を導入。

Notes / Known limitations (推測ベース)
- position_sizing の lot_size は現在全銘柄共通の想定であり、将来的に銘柄別単元対応が想定されている（TODO コメントあり）。
- apply_sector_cap は price_map に欠損（0.0）があるとエクスポージャー低めに評価される可能性があり、前日終値等のフォールバックが将来の改善点として示唆されている。
- research / ai モジュールはいずれも DuckDB を前提にしており、外部 API への実行時アクセスは設計上排している（ただし ai/news_nlp は OpenAI を使用するため API キーが必要）。
- run_monitoring が「本番 sqlite_path を使用する」挙動は意図的（監視データは常に本番 DB に記録）だが、運用ルールに注意が必要。

その他
- ドキュメントや README による利用手順、データマイグレーション手順、実稼働時の監視・アラート設定等は別途整備が必要と推測されます。

もし特定の変更点をより詳しく（例えば各関数の挙動やログ出力の例、想定される運用手順）記載することを希望される場合は、対象範囲を指定していただければ追記します。