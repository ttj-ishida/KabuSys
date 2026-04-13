CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠の形式で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------
（今後のリリースに含める予定の変更・改善の候補をコードコメント・設計メモから推測して列挙しています）

Added
- MONITOR_POLL_INTERVAL の値検証を強化し、0 以下や不正な文字列が設定された場合に警告を出してデフォルト間隔にフォールバックする仕組みを run_monitoring に追加予定（既に実装済みの値チェックをより広域で利用する案）。
- ai/news_nlp の堅牢化：OpenAI 呼び出しの再試行ロジックや応答バリデーションの改善、部分的失敗時に既存スコアを保護して更新する動作を本番導入する計画。

Changed
- Settings の自動 .env ロード挙動について、プロジェクトルート検出に失敗した場合は自動ロードをスキップする設計があり、テスト/CI 環境との共存を容易にする方針を明確化予定。
- paper_trading の DB 分離方針（paper_trading 環境では data/paper_trading.db を使用）をドキュメントと運用手順に反映予定。

Fixed
- process_priority ユーティリティで未対応 OS の場合に警告を出してスキップするよう既に安全弁が入っている点を明記（権限不足時の挙動の説明強化）。

Deprecated
- なし

Security
- OpenAI API キー未設定時に明示的にエラーを出して処理を中止する仕様（ai/news_nlp）を継続。キーの扱いに関する運用ルールを整備予定。

---


[0.1.0] - 2026-04-13
--------------------
Initial release — 基本機能と初期アーキテクチャを実装した最初の公開バージョン。

Added
- 基本パッケージ
  - kabusys パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ構成: data / strategy / execution / monitoring 相当のモジュール構成をエクスポート。

- 設定管理 (kabusys.config)
  - 環境変数/.env/.env.local 読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に自動検出。
  - .env パーサを独自実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを提供（J-Quants / kabuAPI / LINE / DuckDB / SQLite / PaperTrading / 監視閾値 / PID/KILL フラグ / 環境判定 等）。
  - 設定値検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE の許容値チェック）。

- 実行系 / 監視
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成（Mock 実装を想定した切替）。
    - OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine の組み立てと実行。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を実装。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告と共にデフォルトにフォールバック。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - プロセス優先度を起動時に high に設定（utils の set_process_priority を利用）。
    - SQLite / DuckDB 接続の初期化と正常なクローズ処理を実装。

- ユーティリティ (kabusys.utils)
  - process_priority モジュールを追加。
    - Windows / POSIX の差分を吸収して nice / priority クラスを設定。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - アクセス権限や未対応 OS では安全にスキップし警告を出すハンドリングを実装。

- Portfolio 構築 (kabusys.portfolio)
  - portfolio_builder: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコア合計が 0 の場合は等金額にフォールバック（警告ログあり）。
  - risk_adjustment: セクター上限適用 (apply_sector_cap)、市場レジーム乗数 (calc_regime_multiplier) を実装。
    - apply_sector_cap は既存保有のセクター別時価を計算し、max_sector_pct を超えるセクターの新規候補を除外。
    - calc_regime_multiplier は "bull"/"neutral"/"bear" に対する乗数を返す（未知の場合は 1.0 にフォールバック）。
  - position_sizing: 株数決定ロジック (calc_position_sizes) を実装。
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（現状全銘柄共通）や cost_buffer を考慮した aggregate cap、スケーリング（残差処理でロット単位で再配分）を実装。
    - 価格欠損時のスキップや上限計算 (_max_per_stock) を考慮。

- 研究 / リサーチ (kabusys.research)
  - factor_research: Momentum / Volatility / Value ファクター計算を DuckDB SQL 組み合わせで実装。
    - mom_1m / mom_3m / mom_6m / ma200_dev、atr_20 / atr_pct / avg_turnover / volume_ratio、per / roe を計算。
    - データ不足時は None を返す設計。
  - feature_exploration: 将来リターン計算 (calc_forward_returns)、IC 計算 (calc_ic)、ファクター統計サマリー (factor_summary)、ランク関数 (rank) を実装。
    - calc_ic はスピアマンのランク相関（ties の平均ランク処理）を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再エクスポート。

- AI / ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores テーブルへ書き込む機能を追加。
    - JST ベースの収集ウィンドウ（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC で計算）を採用。
    - 銘柄ごとに記事を集約し、1銘柄あたり最大記事数・最大文字数でトリム。
    - 1 API コールあたり最大 _BATCH_SIZE=20 銘柄でバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx は指数バックオフでリトライ。リトライ上限値を設定。
    - レスポンスは JSON モードで厳密検証し、スコアを ±1.0 にクリップ。
    - 部分成功時に既存スコアを保護するため、対象コードのみを DELETE → INSERT で置換する設計。
    - API キーが未設定の場合は ValueError を送出して明示的に失敗。

- ツール (kabusys.tools)
  - paper_verification_report: Paper Trading 用検証レポート生成スクリプトを追加。
    - CLI から期間指定（--from / --to）、DB パス指定（--db）で集計・レポート出力可能。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率、リスク却下数、レイテンシ（avg/max/P95）。
    - P95 計算、日付フィルタ、DB 存在チェック、欠損テーブル（OperationalError）への保護処理を実装。
    - 合格基準（閾値）を定義し PASS/FAIL 判定を出力。

Changed
- 監視/実行スクリプト両方で起動時に process priority を high に設定する挙動を導入。
- run_execution は paper_trading 環境で専用 SQLite を使うことで本番データと完全分離するよう設計。

Fixed
- .env のパースロジックでクォート内のバックスラッシュエスケープや行末コメントの取り扱いなど、現実的な .env パターンに対応。
- DuckDB / SQLite の接続を使用後に確実に close するよう finally ブロックで保証。

Known issues / Notes
- position_sizing の価格欠損時の扱いについて TODO コメントあり：price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する必要がある。
- ai/news_nlp 内で DuckDB の executemany に関する制約（params が空の場合の扱い）に注意する実装コメントあり。
- process_priority の設定は権限不足や未対応 OS の場合に失敗する可能性があり、その際はログ警告でスキップする安全設計になっている。
- paper_verification_report は DB スキーマ（system_status, trade_logs, risk_logs など）が存在しない場合に OperationalError を捕捉して N/A 相当で出力する保護ロジックを持つが、完全な互換性保証のためには事前に init_monitoring_db 等でテーブル作成が必要。

Acknowledgements
- DuckDB を分析用ローカルクエリ層として利用。
- OpenAI API（gpt-4o-mini）をニュースセンチメントに利用（API 呼び出し部は堅牢化済み/コメントあり）。
- psutil をプロセス制御ユーティリティとして採用。

----- 

翻訳や項目の補足、日付やバージョニングの変更希望があれば指示ください。コードコメントや設計注記から推測して作成していますので、実際のコミット履歴や運用要件に合わせて調整可能です。