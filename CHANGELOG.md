# Changelog

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 非推奨 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)

## [0.1.0] - 2026-04-16

初回公開リリース。本リリースでは自動売買システム KabuSys のコア機能群を実装・追加しました。主な内容は以下の通りです。

### Added
- 全体
  - パッケージのバージョンを 0.1.0 として追加（src/kabusys/__init__.py）。
  - Settings クラスを通じた環境変数/設定の集中管理を実装（src/kabusys/config.py）。
    - .env/.env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - export KEY=val 形式、クォート付き値、コメント処理、上書き制御（protected）に対応したパーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
    - 各種設定プロパティを提供（DBパス、PID/kill flag パス、監視閾値、paper_trading 用設定、API トークンなど）。
    - 環境変数の妥当性チェック（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。

- 実行スクリプト
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）。不正値時はデフォルトにフォールバックして警告。
    - 監視は環境（development/paper_trading/live）にかかわらず本番 monitoring sqlite（settings.sqlite_path）を使用して初期化。
    - stop_requested.flag による外部停止フラグ検知を実装。
    - 起動直後にプロセス優先度を "high" に設定。
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient 経由で paper_trading 用専用 SQLite DB（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - Engine をデーモンスレッドで起動し、stop flag による安全停止処理を実装。
    - PID ファイル取り扱い（settings.pid_file_path / data/execution.pid 参照）をサポート。

- 監視・モニタリング
  - 監視 DB 初期化ユーティリティを利用（monitoring_db の init_monitoring_db を使用して冪等にテーブルを保証）。

- Execution コンポーネント（起動時の組み立て）
  - BrokerClientFactory を利用したブローカークライアント生成。
  - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み合わせてセッション実行を行う起動処理を実装。
  - RiskConfig のデフォルト閾値を設定（max_position_pct, max_utilization 等）。initial_portfolio_value は broker.get_available_cash() を利用。

- ポートフォリオ構築（pure functions）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates(): スコア降順・signal_rank によるタイブレーク。
    - calc_equal_weights(), calc_score_weights(): スコアゼロ時のフォールバック（等金額）と警告ログ。
  - リスク調整（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap(): セクター集中上限を評価し候補を除外。unknown セクターは上限適用対象外。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。未知レジーム時は警告して 1.0 にフォールバック。
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数計算（risk_based / equal / score）。
    - 単元株 (lot_size) 丸め、per-position 上限、aggregate cap に基づくスケーリング（cost_buffer を考慮した保守的見積）。
    - スケーリング時の余剰キャッシュによる切り捨て端数の再配分アルゴリズム（再現性のため安定ソートを採用）。

- ユーティリティ
  - プロセス優先度・CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX (Linux, macOS, FreeBSD) を吸収して set_process_priority(level) を提供。
    - set_cpu_affinity(cpu_count) によるコア固定処理を実装（権限不足や未対応環境では警告ログでスキップ）。

- リサーチ / ファクター計算
  - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL で実装（src/kabusys/research/factor_research.py）。
    - calc_momentum(), calc_volatility(), calc_value(): 各種ウィンドウ・欠損ハンドリング・行数条件に基づく None フォールバックを実装。
  - feature_exploration: 将来リターン計算、IC（スピアマン）計算、統計サマリー等を実装（src/kabusys/research/feature_exploration.py）。
    - calc_forward_returns(), calc_ic(), factor_summary(), rank()。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - CLI で期間指定（--from/--to）・DB 指定（--db）が可能。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（P95）等の集計を行い PASS/FAIL 判定を出力。
    - デフォルト閾値を設定（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）。

- AI ニュース NLP（部分実装）
  - src/kabusys/ai/news_nlp.py にてニュース記事を OpenAI（gpt-4o-mini）でスコアリングするロジックを追加。
    - ニュース収集ウィンドウ計算、記事集約、バッチ処理、API エラーハンドリング（429/5xx 等のバックオフ）やレスポンスバリデーション、スコアクリップ、DB への安全な置換処理方針を記載。
    - 注意: このスナップショットではファイル末尾が途中で切れており（_fetch_articles 呼び出し付近で中断）、完全実装は別コミットで完了予定。

### Changed
- Settings / .env ローダ
  - 自動ロード順を OS 環境変数 > .env.local > .env として明確化し、OS 環境変数を保護する protected set を導入。
  - .env パーサを堅牢化（クォート内のバックスラッシュエスケープ対応、コメント扱いの改善）。
- 監視挙動
  - run_monitoring はどの環境でも (KABUSYS_ENV に依らず) monitoring 用 sqlite_path を使用するように設計を明確化（監視データは本番 DB を利用）。

### Fixed
- 環境変数の数値パースにおける不正値処理を改善（MONITOR_POLL_INTERVAL の 0 以下や非整数に対してデフォルトへフォールバックし、警告ログを出す）。
- プロセス優先度/CPU affinity の設定で権限不足や未実装 API 使用時に適切に警告してスキップするように修正（例外を握り潰してプロセスを続行）。

### Notes / Known limitations
- ai/news_nlp.py は大部分の仕様を実装していますが、このリポジトリスナップショットではファイル末尾が途中で切れており、記事取得(_fetch_articles) 以降の処理が未完・未保存となっています。実運用前に当該部分の完成・レビューが必要です。
- position_sizing の価格欠損時の挙動について TODO コメントあり（price が欠損するとエクスポージャーが過少評価される可能性）。将来的に前日終値や取得原価をフォールバックする改善を検討。
- DuckDB を利用するクエリ群は prices_daily / raw_financials / raw_news 等のテーブル構造に依存します。DB スキーマの整合性を事前に確認してください。
- Paper Trading 用 DB と本番 DB を分離することでテストと本番の安全性を確保していますが、運用時は各環境変数（PAPER_TRADING_SQLITE_PATH など）を正しく設定してください。

### Security
- OpenAI API キーを直接ハードコーディングしない設計。api_key 引数または環境変数 OPENAI_API_KEY を利用。未設定時はエラーを返す。

---

今後の予定（例）
- ai/news_nlp の未完了部分の完成。
- テストカバレッジ拡充（ユニット/統合）。
- ドキュメント（設計書・運用手順）の整備。