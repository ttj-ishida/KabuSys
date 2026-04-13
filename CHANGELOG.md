CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注記
----
- 本 CHANGELOG は提示されたソースコードの内容から推測して作成しています。実際のリリース履歴と差異がある可能性があります。
- 日付は生成日（2026-04-13）を基準にしています（必要に応じて実際のリリース日へ差し替えてください）。

Unreleased
----------
- 継続的な改善予定：
  - news_nlp.score_news の処理完了・例外ハンドリング強化（API失敗時の部分コミット保護、ログ改善など）。
  - モニタリング・検証ツールのレポート出力フォーマットや自動通知（LINE 等）拡張。
  - 単元株（lot_size）を銘柄ごとに管理するための拡張（stocks マスタの導入）。
  - 性能改善（DuckDB クエリの最適化、バッチサイズ調整）とユニットテスト充実。

[0.1.0] - 2026-04-13
--------------------
Added
- プロジェクト初期実装を追加。
  - 実行系
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。環境に応じて本番/ペーパートレーディングを切り替え可能（KABUSYS_ENV）。
    - BrokerClientFactory によるブローカークライアント生成を導入し、paper_trading 環境では MockBrokerClient を使用して paper_trading 用 DB に記録する仕様を実装。
    - OrderRepository / OrderManager / Reconciler / RiskManager を組み合わせて ExecutionEngine を起動するワークフローを提供。
    - RiskConfig のデフォルト値（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を設定。
  - 監視系
    - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可（デフォルト60秒）。
    - 監視データは環境にかかわらず本番 sqlite_path を使用する（監視は本番 DB 基準で記録）。
    - init_monitoring_db による監視用テーブルの初期化処理を導入。
  - 設定/ユーティリティ
    - config.py: 環境変数／.env 自動ロード機構の実装（.env / .env.local をプロジェクトルートから読み込み、OS 環境変数は保護）。
      - .git または pyproject.toml を基準にプロジェクトルートを発見するロジックを実装。
      - .env ファイルの柔軟なパース（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント判別等）を実装。
      - 設定クラス Settings を提供し、各種設定プロパティ（DBパス、PIDファイル、閾値、環境判定など）を集約。
      - PAPER_FILL_MODE のバリデーション、PAPER_TRADING_SQLITE_PATH 等のデフォルトを定義。
    - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティと CPU affinity 設定を実装（Windows / POSIX 対応）。
  - ポートフォリオ構築
    - portfolio モジュールを追加（純粋関数群、DBアクセスなし）。
      - portfolio_builder.py: 候補選定（score 降順、tie-breaker）、等比率・スコア加重比率計算。
      - risk_adjustment.py: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
      - position_sizing.py: 発注株数算出（risk_based / equal / score）、単元株丸め、aggregate cap（利用可能現金でのスケールダウン）、コストバッファの考慮。
  - リサーチ
    - research モジュールを追加。
      - factor_research.py: Momentum / Volatility / Value ファクター計算を DuckDB 経由で実装（prices_daily / raw_financials を参照）。
      - feature_exploration.py: 将来リターン計算、スピアマンの IC（rank を用いたランク相関）、ファクター統計サマリー等を実装。pandas 等に依存しない純正 Python 実装。
      - zscore_normalize を含むデータ統計ユーティリティをエクスポート（kabusys.data.stats へ依存）。
  - AI ニューススコアリング
    - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を実装。
      - タイムウィンドウ計算（JST基準の前日15:00～当日08:30に対応）、記事トリム（最大記事数／文字数）、バッチ処理、リトライ（429/ネットワーク/5xx）方針、レスポンス検証、スコアクリップを導入。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。system_status / trade_logs / risk_logs から稼働率・成功率・レイテンシ等を集計し PASS/FAIL 判定を出力。
  - パッケージ基本情報
    - __init__.py にて __version__ = "0.1.0" を設定。

Changed
- （初期リリースのため変更履歴はなし）

Fixed
- 設定やユーティリティの耐障害性を向上。
  - MONITOR_POLL_INTERVAL の環境値が不正（0 / 負値 / 非整数）の場合はデフォルトにフォールバックし、警告ログを出力する実装を追加。
  - .env の読み込み失敗時に warnings.warn で通知し処理を継続するようにした（ファイル IO エラー耐性）。
  - process_priority、set_cpu_affinity においてアクセス権限エラーや未実装 API の例外をキャッチして警告ログを出すことで起動を妨げないようにした。
  - DuckDB executemany に関する注意（空パラメータ回避）や NULL の扱いに配慮したクエリ実装（ファクター計算等での NULL 伝播制御）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または関数引数で渡す仕様。未設定時は ValueError を送出して明示的に失敗することで誤操作による秘密鍵漏洩リスクを低減。

Notes / 注意事項
- 環境自動ロード: デフォルトで .env/.env.local を自動読み込みしますが、テスト等で無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB の分離: paper_trading 環境では paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と完全分離する設計になっています。監視用 DB は環境にかかわらず本番 sqlite_path を参照する実装です（意図的な設計）。
- Paper Trading の挙動: PAPER_FILL_MODE により MockBroker の約定動作を制御します。無効値は起動時に ValueError を発生させます。
- PID / Kill フラグ: Settings は pid_file_path / kill_flag_path / kill_flag_clear_on_start 等のプロセス監視用パスと動作フラグを提供します。実運用時は適切に設定してください。
- 単元株（lot_size）や銘柄別取引制約は現状グローバル定数で扱っています。将来的に銘柄別設定を導入する余地があります（TODOコメントあり）。

開発・運用に関する提案
- CI にユニットテストを追加し、factor_research / feature_exploration / position_sizing 等の数値ロジックを網羅してください。
- DuckDB クエリのベンチマーク、インデックス（パーティショニング）検討により大規模データセットでの性能改善を行ってください。
- news_nlp の API 呼び出し部分は料金・レート制限に依存するため、バッチスケジューラやキャッシュ戦略の導入を検討してください。

----- End of CHANGELOG -----