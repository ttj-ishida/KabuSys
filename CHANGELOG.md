# Changelog

すべての重要な変更は「Keep a Changelog」フォーマットに従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- 基本パッケージ初期実装（0.1 系の機能群を追加）
  - アプリケーションメタ情報: kabusys.__version__ を "0.1.0" として定義。
  - 設定管理モジュール (kabusys.config)
    - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から探索）。
    - .env パース機構の強化（export 形式、クォート内エスケープ、行内コメント処理などに対応）。
    - OS 環境変数を保護するための上書き制御（.env.local は override=True、既存 OS 環境変数は保護）。
    - Settings クラスで各種設定値をラップ（DBパス、PID/kill flag、閾値、環境判定、paper trading 設定等）。
    - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE 等）。
  - 実行系エントリスクリプト
    - run_execution: ExecutionEngine の起動エントリポイント。
      - KABUSYS_ENV=paper_trading の場合に Paper Trading 用 SQLite（data/paper_trading.db など）を使用し、MockBrokerClient を利用する想定。
      - ブローカー・OrderRepository・OrderManager・RiskManager・Reconciler を組み立てて ExecutionEngine を起動する処理を実装。
      - DuckDB 接続を受け取りデータ処理に利用。
    - run_monitoring: SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下はデフォルトへフォールバック）。
      - 監視用テーブル初期化（monitoring DB の初期化）と DuckDB 接続。
      - プロセス優先度を高く設定して起動する処理。
  - ユーティリティ (kabusys.utils)
    - process_priority モジュール
      - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
      - CPU affinity を最初 N コアに固定する set_cpu_affinity を実装。
      - アクセス権や未対応プラットフォームに対しては警告を出して安全にスキップする挙動。
  - ポートフォリオ構築モジュール (kabusys.portfolio)
    - portfolio_builder: シグナル選定と重み計算（候補選択、等金額・スコア重み）。
    - risk_adjustment: セクターキャップ適用とレジーム乗数（regime に応じた乗数算出、unknown レジームはフォールバック）。
    - position_sizing: 実際の株数算出ロジック（risk_based / equal / score の割当方法、lot_size による丸め、集計 cap によるスケールダウン、cost_buffer を考慮した保守的見積り、スケーリング後の端数再配分）。
    - モジュール群を package レベルでエクスポート。
  - リサーチ / 特徴量関連 (kabusys.research)
    - factor_research: Momentum / Volatility / Value ファクター計算（DuckDB を直接参照する SQL＋Python 実装）。
      - mom_1m/3m/6m、ma200 偏差、ATR、相対ATR、平均売買代金、出来高比率、PER/ROE 等の算出を実装。
      - データ不足時の None ハンドリング（ウィンドウ内行数不足では None を返す）。
    - feature_exploration: 将来リターン計算、IC（Spearman の ρ）計算、ファクター統計サマリ、ランク付けユーティリティ。
      - forward return の複数ホライズン同時取得（SQL 一括取得）。
      - スピアマン相関のためのランク計算（同順位は平均ランク）。
      - factor_summary による count/mean/std/min/max/median の算出。
    - research package レベルで主要関数をエクスポート（zscore_normalize を含む）。
  - AI ニューススコアリング (kabusys.ai.news_nlp)
    - raw_news から銘柄別に記事を集約して OpenAI (gpt-4o-mini) にバッチ送信し、ai_scores テーブルに書き込むワークフローを実装。
    - ニュース収集ウィンドウの計算（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して利用）。
    - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（1銘柄あたり記事数上限・文字上限）、スコアの ±1.0 クリップ、エラー時のリトライ（指数バックオフ）等の実装方針を採用。
    - API キー未設定時の明確なエラー。
  - ツール (kabusys.tools.paper_verification_report)
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシ等を集計して PASS/FAIL を判定。
    - デフォルト閾値とレポート出力フォーマットを実装（閾値はソース冒頭の定数で管理）。
    - 日付フィルタ (--from/--to) と DB パス指定オプション (--db) をサポート。
    - p95 計算、NULL 対応、DB が存在しない場合のエラー表示を実装。
  - DB 初期化補助
    - monitoring_db.init_monitoring_db を起動前に呼び出して監視テーブルの存在を保証（冪等）。
  - ロギング
    - 起動時に INFO レベルでの基本設定を行う実装（各エントリポイントで logging.basicConfig）。

### Changed
- .env 読み込みロジックの仕様明確化
  - プロジェクトルート探索に __file__ を基点とするため、パッケージ配布後も動作するよう設計。
  - OS 環境変数と .env の優先順位（OS > .env.local > .env）を文書化。
- 実行時挙動の安全化
  - run_monitoring のポーリング間隔は MONITOR_POLL_INTERVAL で上書き可能だが、0 以下の値はデフォルトにフォールバックして time.sleep に渡す際の ValueError を防止。
  - process_priority の未対応 OS や権限不足ケースでは例外にせずログ警告して処理を継続するように変更（堅牢性向上）。
- Position sizing のスケーリングロジック改善
  - aggregate cap により投資合計が available_cash を超えた場合にスケールダウンし、端数は lot_size 単位で残差の大きい順に追加配分する方式を採用して再現性を確保。
  - cost_buffer により保守的にコスト見積りを行い、aggregate cap 判定で考慮するように実装。
- Research / Factor 計算の SQL 最適化（スキャン範囲にバッファを設け、過度なスキャンを抑制）
  - momentum, volatility, forward returns 等でカレンダーバッファを採用。

### Fixed
- 環境変数パースの細かな不具合対応
  - export プレフィックス、クォート中のエスケープ、行中コメントの扱いを正しく処理するよう改善。
- run_execution/run_monitoring の DB クローズを finally で確実に実行するようにしてリソースリークを防止。

### Security
- OpenAI API キーの取り扱いに関する明示的なチェックを追加（未設定時は ValueError を発生させ不要な API 呼び出しを防止）。

---

## [0.1.0] - 2026-04-12
- 初回リリース相当の機能セットを確定（上記 Added の内容をバージョンとしてまとめたもの）。
  - 設定管理、実行スクリプト、監視、ポートフォリオ構築、ポジションサイジング、リスク調整、リサーチ/特徴量分析、ニュース NLP スコアリング、Paper Trading 検証レポート、ユーティリティ群などを含む。

注: 上記はコードベースから推測してまとめた変更履歴です。実際のリリース日やバージョン方針に従って調整してください。