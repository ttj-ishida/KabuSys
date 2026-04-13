# Changelog

すべての変更は "Keep a Changelog" の形式に従い、日本語で記載しています。  
リリース日はコードベースから推測可能な最新の作成日（このドキュメント生成日）を用いています。

フォーマット:
- Unreleased — 今後の変更用（空）
- 各バージョンは追加（Added）／変更（Changed）／修正（Fixed）等のカテゴリで記載

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
初期リリース。プロジェクトのコア機能を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys）とバージョン設定（__version__ = "0.1.0"）。
- 環境設定 / ロード
  - Settings クラス（kabusys.config）を実装。環境変数から各種設定（DB パス、API トークン、運用環境判定、各種閾値など）を取得する。
  - .env 自動読み込み機能を実装（プロジェクトルート判定: .git / pyproject.toml）。.env / .env.local の優先度を考慮した注入。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env パーサーは export プレフィックス・クォート・エスケープ・インラインコメント処理に対応。
  - 各設定値は入力検証を実施（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE などの許容値チェック）。
- 実行エントリスクリプト
  - run_execution: ExecutionEngine の起動フローを提供。プロセス優先度設定、SQLite / DuckDB 接続確立、Broker クライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のセッション実行を行う。
    - KABUSYS_ENV が paper_trading の場合は paper_sqlite_path（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - init_monitoring_db を実行して監視テーブルの存在を保証（冪等処理）。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを提供。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。監視は本番 sqlite_path を使用する（環境に依存せず本番 DB を参照する設計）。
- 監視・実行ユーティリティ
  - process_priority ユーティリティ（kabusys.utils.process_priority）を実装。Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity 固定関数も提供。権限不足や未対応プラットフォーム時は警告で安全にスキップ。
- データベース統合
  - DuckDB と SQLite を組み合わせて利用する設計を採用（research / ai / monitoring / execution の用途に応じて使い分け）。
- Portfolio（ポートフォリオ構築）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選抜（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分／スコア重み配分。スコアが全て 0 の場合は等配分にフォールバック（警告）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（既存保有を踏まえ、上限超過セクターの新規候補を除外）。unknown セクターは除外対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告の上 1.0 フォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算。ロット丸め、1銘柄上限、aggregate cap によるスケール調整、cost_buffer（手数料・スリッページを想定）考慮、利用可能現金に応じたスケーリングと残差処理を実装。
- Research（研究 / バックテスト支援）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離の計算（DuckDB の prices_daily を参照）。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率の計算。
    - calc_value: EPS / ROE に基づく PER / ROE 計算（raw_financials + prices_daily）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズンの将来リターンを一括算出（LEAD を用いた効率的取得）。
    - calc_ic / rank / factor_summary: ランク相関（Spearman）による IC 計算、ランク化（同順位は平均ランク処理）、ファクター統計サマリ（count/mean/std/min/max/median）。
  - research パッケージはデータ標準化ユーティリティ（zscore_normalize）を外部から参照可能にエクスポート。
- AI ニュース NLP
  - news_nlp モジュール:
    - raw_news を銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントスコア（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
    - バッチ処理（最大 20 銘柄/コール）、記事数・文字数のトリム（1銘柄あたり最大記事数・最大文字数の制限）、JSON Mode による厳密な JSON 応答期待、レスポンス検証、スコアの ±1.0 クリップ、部分成功時の DB 保護（対象コードで限定した DELETE→INSERT）を行う。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライの実装設計。API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を投げる。
    - ニュース集計ウィンドウ（JST ベースの前日 15:00 ～ 当日 08:30）を UTC に変換して DB クエリに使用。
- ツール
  - tools.paper_verification_report:
    - Paper Trading 用検証レポート生成 CLI。稼働率、注文成功率、送信率、P95 レイテンシなどを計算して標準出力にレポートを出力。日付フィルタ（--from / --to）対応、DB パスを引数／環境変数で指定可能。
    - 判定基準の定義（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。P95 の計算や欠損データの扱いを考慮。
- 監視 DB 初期化
  - init_monitoring_db を利用して monitoring 用テーブルを（冪等に）初期化するフローを整備。

### Changed
- （このリリースは初期実装のため該当なし）

### Fixed / Defensive behavior
- 環境値不正時のフォールバックと警告:
  - MONITOR_POLL_INTERVAL が不正（非数値・0 以下）の場合、デフォルト 60 秒にフォールバックして警告を出力。
  - PAPER_FILL_MODE の不正値は ValueError を発生させて明示的に検出。
  - LOG_LEVEL / KABUSYS_ENV の不正値は ValueError で検出。
- 安全な外部操作:
  - process_priority / set_cpu_affinity は権限不足や未対応プラットフォームで例外を握りつぶし警告ログにより安全にスキップする実装。
- 計算上のフォールバック:
  - calc_score_weights: 全てのスコアが 0.0 の場合は等金額配分へフォールバック（警告）。
  - factor_research の窓不足や NULL の伝播を考慮して、データ不足時には None を返す等、上位コード側で扱いやすい形に整形。

### Notes / Known behaviors
- run_monitoring は説明どおり「監視は本番 sqlite_path を使用する」実装で、KABUSYS_ENV にかかわらず本番監視 DB を参照する点に注意。
- run_execution は paper_trading 環境で paper_trading 用 DB へ完全分離して記録する設計。paper と live の DB 分離により誤送信リスク低減を図っている。
- news_nlp は OpenAI API の呼び出し失敗時（キー未設定等）は例外を投げるが、API 呼び出しの途中エラーはリトライとフェイルセーフ（スキップ）を組み合わせた設計。
- DuckDB を SQL 処理基盤として多用しているため、prices_daily / raw_financials 等のスキーマ整備が前提となる。
- データ欠損（価格 null、EPS null 等）に対しては多くの関数が None を返すかスキップする設計で、上位ロジック側でのハンドリングが前提。

### Security
- API キー（J-Quants、kabu、OpenAI 等）は環境変数から供給する設計。.env の自動読み込みは OS 環境を保護する実装（override フラグと protected set）で既存の OS 環境変数を不意に上書きしないよう配慮。

---

今後のリリースでは、実運用での観測に基づく以下の改善が想定されます（想定事項）:
- 単体テスト・統合テストの整備（特に OpenAI 呼び出しや DuckDB クエリ周りのモック化）
- ロギングの改善（構造化ログ / ログレベル設定反映）
- position_sizing の銘柄別 lot_size 対応（現状は全銘柄共通の lot_size）
- news_nlp のエラーハンドリング改善（部分成功時の自動再試行や遅延リトライの強化）
- DuckDB マテリアライズやクエリ最適化による大規模データ時の性能改善

（注）上記はコードから推測して作成した CHANGELOG です。実際のコミット履歴や PR に基づくものではないため、必要に応じて修正してください。