CHANGELOG.md

すべての注目すべき変更はここに記録します。本ファイルは Keep a Changelog の形式に準拠しています。

Unreleased
---------
（現在なし）

v0.1.0 - 2026-04-15
------------------
初回リリース。自動売買システム KabuSys の基本機能を実装しました。主要な追加点と振る舞いの要約は以下のとおりです。

Added
- 基本パッケージ構成
  - パッケージバージョン: __version__ = 0.1.0
  - モジュール分割: data, strategy, execution, monitoring などをエクスポート

- 設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から検出）
  - export KEY=val 形式・クォート付き値・インラインコメント対応の .env パーサ実装
  - 必須環境変数取得関数 _require と Settings クラスによる型変換・検証
  - KABUSYS_ENV（development / paper_trading / live）や LOG_LEVEL の検証
  - データベース・ファイルパス（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）や監視閾値等の設定プロパティを提供

- 実行エンジン起動スクリプト (run_execution.py)
  - ExecutionEngine の起動エントリポイントを実装
  - KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite を使用して本番 DB と分離
  - BrokerClientFactory によるブローカークライアント生成
  - OrderRepository, OrderManager, RiskManager, Reconciler を組み立てて ExecutionEngine を起動
  - 停止フラグ（data/stop_requested.flag）の検知・安全停止処理
  - 実行 PID ファイルの取り扱い（pid ファイルパスを設定経由で指定）

- 監視ループ起動スクリプト (run_monitoring.py)
  - SystemMonitor のポーリングループ実装
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）
  - 監視用 DB を init_monitoring_db で確実に初期化
  - プロセス優先度設定を起動直後に実施
  - 停止フラグによる安全終了、例外時ログとリトライ相当の継続処理

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定: select_candidates（スコア降順・タイブレークルール）
  - 重み付け: calc_equal_weights, calc_score_weights（スコア全0時のフォールバック含む）
  - リスク調整: apply_sector_cap（セクター集中の除外ロジック）, calc_regime_multiplier（市場レジームに基づく乗数）
  - ポジションサイジング: calc_position_sizes（risk_based / equal / score、単元株丸め、aggregate cap スケーリング）

- 研究・ファクター計算 (kabusys.research)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（DuckDB 接続を受け SQL で計算）
  - 研究支援: calc_forward_returns, calc_ic, factor_summary, rank（IC 計算や統計サマリー）
  - データ不足時の None 処理、営業日ベースのスキャン範囲制御、パフォーマンスを考慮したクエリ設計

- ニュース NLP（AI）モジュール (kabusys.ai.news_nlp)
  - OpenAI（gpt-4o-mini）を用いたニュース記事のセンチメントスコアリング機能を実装
  - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ
  - バッチ送信、スコアを ±1.0 にクリップ、API キー未設定時の明示的なエラー
  - API レイヤーでのリトライ（429 / ネットワーク / 5xx に対し指数バックオフを想定）やレスポンス検証の方針を設計

- ツール: Paper Trading 検証レポート (kabusys.tools.paper_verification_report)
  - コマンドラインツールで Paper Trading DB を解析しレポートを出力
  - 指標: 稼働率（uptime）、注文成功率、送信率、リスク却下数、API レイテンシ（avg/max/P95）
  - 判定しきい値（稼働率 99%、成立率 90%、送信率 95%、P95 ≤ 200 ms）を定義
  - --from / --to / --db オプションを提供

- ユーティリティ (kabusys.utils.process_priority)
  - Windows / POSIX（Linux, macOS, FreeBSD）を抽象化したプロセス優先度設定
  - CPU affinity 設定ユーティリティ（コア数指定で最初の N コアに固定）
  - 権限不足や未対応 OS 時のフォールバック（警告ログ）を実装

Changed
- （初回リリースのため該当なし）

Fixed / Robustness improvements
- .env のパース挙動を強化し、クォート・エスケープ・インラインコメント・export 形式に対応
- .env のロード時に OS 環境変数を保護（.env.local の override 時も保護キーは上書きしない）
- 各種ファクター計算・集計処理でデータ欠損に対する安全な None 処理を導入
- calc_score_weights における全スコア 0 の場合のフォールバック（等金額配分）を追加
- position sizing の aggregate スケーリングで端数配分を残差に基づき公平に配分するロジックを実装
- プロセス優先度設定や CPU affinity 設定での AccessDenied 等をトラップし警告に変換

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーを環境変数または明示引数で要求。未設定時は例外を発生させることで誤った運用を防止

Notes / Breaking changes
- 監視（run_monitoring）は KABUSYS_ENV にかかわらず監視用の sqlite_path（デフォルト: data/monitoring.db）を使用する設計です。環境ごとに監視 DB を分離したい場合は設定を変更してください。
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされます（CWD に依存しないよう __file__ を起点に探索するため）。CI やパッケージ配布時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- PAPER_FILL_MODE の有効値を明示的に検証します（instant, partial, never, reject）。不正値は起動時に ValueError を送出します。

今後の予定（例）
- news_nlp の API 呼び出し周りの実装完了・エラー回復性の強化
- ExecutionEngine / Broker の詳細なログ・メトリクス追加
- ポートフォリオ構築の単体テスト充実と銘柄別 lot_size 対応

---

注: 本 CHANGELOG はソースコードから読み取れる機能・設計・例外処理方針に基づいて推測・要約したもので、実際のコミット履歴ではありません。必要があれば各変更点を個別のコミットやイシューに紐づけた詳細版を作成します。