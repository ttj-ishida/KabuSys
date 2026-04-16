CHANGELOG
=========

すべての変更は "Keep a Changelog" の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です（実際のコミット履歴ではありません）。

注意
----
- バージョン番号は src/kabusys/__init__.py の __version__ を参照しています（0.1.0）。
- 実装の抜けや TODO コメントは「未解決・今後の作業」として Unreleased セクションに記載しています。

Unreleased
----------
- 実装途中の機能・要改善点
  - kabusys.ai.news_nlp.score_news(): コードが途中で切れており、記事集約後の API 呼び出しおよび結果の DuckDB への書き込み処理が完全に含まれていません。エラーハンドリングや部分更新ロジックは説明されているが、実装の最終部分が未完了です。
  - portfolio/risk_adjustment.py: apply_sector_cap() にて price が欠損（0.0）の場合のフォールバック価格を使う改善が TODO として残っています（前日終値や取得原価などを使う案）。
  - portfolio/position_sizing.py: lot_size を銘柄毎に持たせる拡張が TODO として記載されています（将来的な拡張計画）。
  - 一部処理でのテストカバレッジ・境界ケース（極端な市場状況、DB スキーマ不整合等）の追加検証が推奨されます。

[0.1.0] - 2026-04-16
--------------------
Added
- 基本モジュール群を追加（初回公開相当）
  - kabusysパッケージ初期化（src/kabusys/__init__.py）にバージョン 0.1.0 を定義。
- 環境・設定管理
  - kabusys.config.Settings クラスを追加し、環境変数から主要設定を取得する仕組みを提供。
  - .env 自動ロード機能を導入（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - .env/.env.local のパース機能を充実:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱いを工夫（クォートの有無で挙動を分離）。
    - OS 環境変数を保護して .env.local で上書きする挙動を実装。
  - 環境変数検証を追加（KABUSYS_ENV や LOG_LEVEL、PAPER_FILL_MODE の検証）。
- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てを実装。
    - 停止フラグ（data/stop_requested.flag）検知による安全な停止処理。
    - 実行用 PID ファイル path を指定してプロセス管理に対応。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番 sqlite_path を使用する（環境に依存しない監視 DB の位置）。
    - 停止フラグ検出と例外ハンドリングによりループの堅牢化。
- プロセス優先度・CPU 設定ユーティリティ
  - kabusys.utils.process_priority.set_process_priority(level) を追加。
    - Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収。
    - 未対応 OS やアクセス拒否時に警告を出してフォールバックする設計。
  - set_cpu_affinity(cpu_count) を追加（任意のコア数へピン留め。権限不足等では警告）。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を実装。
    - calc_score_weights: 全銘柄のスコアが 0 の場合に等金額配分へフォールバックし WARNING を出力。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェック（売却予定銘柄を除外する挙動をサポート）。
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear）と未知レジームのフォールバック。
  - portfolio.position_sizing:
    - calc_position_sizes: allocation_method="risk_based" / "equal" / "score" に基づく株数計算。
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン処理。
    - cost_buffer を使った保守的なコスト見積りと、残余キャッシュによる端数配分ロジックを実装。
- リサーチ・ファクター計算
  - research.factor_research: calc_momentum, calc_volatility, calc_value を追加。
    - DuckDB を用いた SQL ベースの高速計算。prices_daily / raw_financials テーブルのみ参照。
    - MA200、ATR20、各種モメンタム（1m/3m/6m）、流動性指標などを含む。
    - データ不足時は None を返す設計。
  - research.feature_exploration:
    - calc_forward_returns: 将来リターンの一括取得（任意ホライズン対応、horizons バリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）計算、十分なデータがない場合 None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクで扱う安定性のある実装。
  - research パッケージは外部依存（pandas 等）を使わない設計。
- AI ニュース NLP（OpenAI 統合）
  - ai.news_nlp: ニュース記事に対するセンチメントスコアリングの設計実装を追加。
    - gpt-4o-mini を想定した JSON Mode 出力を期待。
    - バッチサイズ、記事トリム（記事数・文字数上限）、スコアクリッピング、リトライ（指数バックオフ）の設計。
    - calc_news_window() により JST ベースのニュースウィンドウを UTC に変換するユーティリティを提供。
    - APIキー未設定時は ValueError を返すガード。
    - レスポンスのバリデーション設計と ai_scores テーブルへの部分置換（DELETE/INSERT）方針を明記。
- ツール
  - tools.paper_verification_report: Paper Trading 用検証レポート生成ツールを追加。
    - コマンドライン引数 --from/--to/--db に対応。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出・出力。
    - 判定基準（閾値）を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 200ms）。
    - DB が存在しない・テーブルがない場合のフォールバックを実装（OperationalError を捕捉して N/A を返す）。
- DB 接続・監視データ初期化
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトで呼び出し、監視用テーブルが存在することを保証（冪等）。
- DuckDB / SQLite の併用
  - DuckDB を分析用途（prices_daily, raw_financials 等）に使用し、SQLite は実行ログ / 監視 / paper_trading 用ストレージに使用する設計を採用。
  - Paper Trading は paper_sqlite_path を用いて本番データと完全に分離。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- OpenAI API キーは環境変数 OPENAI_API_KEY または明示的な引数で供給する設計。未設定時は例外とし、安全に明示する実装を導入。

参考メモ（実装上の注意）
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数の不正値を検出してデフォルトにフォールバックします（0 以下も不正扱い）。
- Settings の自動.envロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
- calc_forward_returns は horizons の重複削除・ソートを内部で行い SQL alias 衝突を避けています。
- position_sizing の aggregate cap スケールダウンは端数配分の再現性を確保するため安定ソート（code を二次キー）を行います。

今後の予定（推奨）
- ai.news_nlp.score_news の実実装完了とエンドツーエンドテスト。
- 価格欠損時のフォールバックロジック実装（apply_sector_cap の TODO）。
- 銘柄毎 lot_size のサポート。
- 各モジュールのユニットテスト・統合テストの追加（特にリスク管理・発注周り）。
- モニタリング・実行プロセスの systemd / コンテナ用の起動・監視ガイド整備。

以上。