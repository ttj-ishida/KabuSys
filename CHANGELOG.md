# CHANGELOG

すべての注記は Keep a Changelog の方針に従っています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### Added
- news_nlp モジュールにニュース集約・OpenAI（gpt-4o-mini）を使ったセンチメントスコアリング処理を追加（バッチ送信やリトライ方針、レスポンス検証、スコアクリップ等を設計）。
  - タイムウィンドウ計算（JST→UTC 変換）、記事トリム制御（記事数/文字数上限）、バッチサイズやリトライ、スコア上下限等の定数を導入。
  - ai_scores テーブルへ部分更新（DELETE/INSERT でコードを絞ることで部分失敗を許容）する方針を反映。
  - 注意: ファイルは途中で切れており（実装継続が必要）、未完の処理が存在する（記事フェッチ処理が途中で中断している箇所あり）。

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-17

初回リリース。以下の主要機能を追加。

### Added
- パッケージメタ情報
  - kabusys.__version__ を "0.1.0" に設定。

- 実行/監視ランチャー
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時に paper_trading 用 DB (デフォルト: data/paper_trading.db) を使用する分離設計を導入。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、EngineConfig を用いた ExecutionEngine 起動処理を実装。
    - data/execution.pid に PID を書き、data/stop_requested.flag による停止フラグを監視する制御を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ（data/stop_requested.flag）でループ終了、例外発生時はログ出力して次回ポーリングへ回すフェイルセーフ実装。
    - 起動時にプロセス優先度を "high" に設定。

- 設定/環境変数管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルートを .git / pyproject.toml から探索）。
    - .env および .env.local の読み込み順序および上書きルール（OS 環境変数は保護）を実装。
    - export KEY=val 形式やクォート処理、インラインコメント対応を行う堅牢なパーサを実装。
    - Settings クラスを導入し、各種設定（DB パス、Paper Trading 関連、監視閾値、PID/kill flag パス、環境判定等）をプロパティとして提供。バリデーションを含む。
    - PAPER_FILL_MODE や KABUSYS_ENV、LOG_LEVEL 等の有効値チェックを実装。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、レイテンシ（P95 含む）を集計し、PASS/FAIL 判定を出力。
    - CLI オプションで期間指定（--from / --to）および DB パス指定（--db）に対応。
    - デフォルトの DB パスは data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH により上書き可能）。
    - P95 計算や欠損データに対する N/A 処理、しきい値定義（稼働率99%、成立率90% 等）を導入。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルの選抜（スコア降順・タイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超える場合、新規候補を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear -> 1.0/0.7/0.3、未知は 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 発注株数算出（risk_based / equal / score の allocation_method 対応）、単元株丸め、per-position 上限、aggregate cap によるスケールダウンと残差再配分ロジックを実装。
    - lot_size 固定（現状 100）や cost_buffer による保守的コスト見積り対応を実装。
  - portfolio パッケージのエクスポート設定を追加。

- 研究/リサーチモジュール
  - research/factor_research.py
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB の prices_daily / raw_financials を参照してファクター群（モメンタム、ATR 等）を計算。
    - データ不足時の None 処理やウィンドウスキャン戦略を導入。
  - research/feature_exploration.py
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得する SQL 実装（リード窓を利用）。
    - calc_ic: スピアマンランク相関（IC）計算の実装。最低レコード数チェックと ties の扱いを実装。
    - factor_summary / rank: ファクター統計サマリー（count/mean/std/min/max/median）とランク計算ユーティリティを追加。
  - research パッケージのエクスポート設定を追加。

- utils/process_priority.py
  - クロスプラットフォームのプロセス優先度設定ユーティリティを追加。
    - Windows 用に psutil の HIGH_PRIORITY_CLASS 等を使用、POSIX 系（Linux/Mac/FreeBSD）では nice 値を設定。
    - set_cpu_affinity 関数を追加し、プロセスを最初の N コアにピン留めする機能を提供（未指定時は何もしない）。
    - 権限不足や未対応 OS の場合は警告ログを出してスキップするフェイルセーフを実装。

- その他ユーティリティ/パッケージ構成
  - 各パッケージ __init__ を整備（portfolio/research/tools/utils）。
  - DuckDB と sqlite3 の接続を多くの処理で採用し、分析処理とランタイム監視／発注処理で共通に利用。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details
- Paper Trading と本番 DB の分離を明確に実装（paper_sqlite_path の導入）。
- 設定ファイルの自動ロードはデフォルトで有効。テスト等で無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することでスキップ可能。
- 一部箇所に TODO／将来的改善メモ（価格欠損時のフォールバック、銘柄別 lot_size 拡張等）が残されている。
- news_nlp モジュールは設計・定数・一部ロジックが整備されているが、実装が途中で切れているため本番利用前に完了と追加テストが必要。

---

以上。必要であれば各セクションをさらに細分化してコミット単位・ファイル単位に落とし込んだ changelog を作成します。