CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ (日本語訳に準拠)

[0.1.0] - 2026-04-18
-------------------

Added
- 基本アプリケーション初版を追加（パッケージバージョン: 0.1.0）。
- 実行・監視用起動スクリプトを追加
  - run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し MockBrokerClient を利用する設計。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - 停止制御: data/stop_requested.flag を監視し、フラグ検知でエンジン停止。PID ファイル出力をサポート。
    - 実行中は別スレッドで engine.run_session を動作させ、停止フラグ検知で安全に停止。
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値は警告してデフォルトにフォールバック。
    - 監視用 DB 接続: Monitoring は環境にかかわらず本番 sqlite_path を利用して監視テーブルを初期化。
    - 停止制御: data/stop_requested.flag を検知してループ終了。
- 設定管理
  - config.py: .env 自動ロード機構（プロジェクトルート検出: .git / pyproject.toml に基づく）、.env / .env.local の読み込み順と OS 環境変数保護、クォート入り値や export 形式に対応する堅牢なパーサ、Settings クラスによる環境変数アクセスラッパー（バリデーション含む）。
  - config_setup.py: インタラクティブな .env 作成/更新ウィザードを追加（項目定義・既存値読み込み・書き込み機能）。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（毎日ローテーション、30 日保持）を設定するユーティリティを追加。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py
    - psutil を利用して Windows / POSIX を吸収したプロセス優先度設定（high/normal/low）を実装。
    - CPU affinity 設定ユーティリティも追加（set_cpu_affinity）。
    - 権限不足や未対応 OS に対して安全にフォールバックする実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選抜。
    - calc_equal_weights, calc_score_weights: 等金額配分／スコア加重配分を実装。スコア合計が 0 の場合は等金額にフォールバックして警告。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有を基にセクター集中を計算し、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_codes パラメータで当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）を追加。未知のレジームは警告して 1.0 をフォールバック。
  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method ("risk_based"/"equal"/"score") に基づく株数計算を実装。
    - risk_based: リスク許容率とストップロス幅からベース株数を算出し、lot_size（単元株）で丸め。
    - equal/score: 各銘柄の重みに基づく配分、max_position_pct による per-stock 上限、aggregate cap として available_cash を超える場合のスケーリング処理を実装。
    - スケーリング時に lot_size 単位で再配分し、余りは fractional 残差の大きい順に追加配分することで再現性を確保。
    - cost_buffer により手数料・スリッページを保守的に見積もる対応。
- 研究・ファクター計算の骨組み
  - research/factor_research.py
    - Momentum / MA200 / ATR / Liquidity などのファクター計算設計と calc_momentum の一部実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）からレポートを生成するスクリプトを追加。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（平均/最大/P95）などを算出。P95 はサンプル取得・ソートで算出。
    - CLI で --from / --to / --db オプションを提供。
    - 判定基準（デフォルト閾値）を定義: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
- パッケージ初期化
  - __init__.py に __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- （初回リリースのため該当なし）

Notes / 実装上の重要点・運用上の注意
- .env 自動読み込みはデフォルトで有効。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env 読み込みは OS 環境変数を保護する設計（.env.local は上書き可能だが、既存の OS 環境変数は上書きされない）。
- run_monitoring は監視テーブル初期化のため常に sqlite_path（本番パス）を使用します。環境に応じた監視 DB 分離は考慮されていません（意図的）。
- ExecutionEngine が利用するブローカーは BrokerClientFactory を通じて生成され、paper_trading モードでは MockBrokerClient を利用するため本番 DB とデータ完全分離が可能。
- process_priority / cpu_affinity の設定は権限や OS により失敗する可能性があるため警告ログを出しつつ安全にスキップします。
- ログファイルの保存先ディレクトリ作成に失敗した場合はファイル出力を無効化し、コンソール出力のみで継続します。
- portfolio/position_sizing のスケーリングは lot_size（現状 100）単位で丸められます。将来的に銘柄ごとの単元対応を想定した拡張余地あり（TODO コメントあり）。
- research/factor_research は完全実装に至っていない箇所があるため、使用する際は依存テーブル（prices_daily 等）の整備と追加テストを推奨します。

今後の予定（例）
- factor_research の完全実装（Value / Volatility / Liquidity の計算）とユニットテスト追加。
- ExecutionEngine / RiskManager / Reconciler 等の統合テスト・モックテスト拡充。
- 銘柄別 lot_size 対応、手数料モデルの細分化、より高度なスケーリングアルゴリズムの導入。

―――

注: 上記はコードベースの内容から推測して作成した変更履歴です。実際のコミット単位の差分や過去履歴が存在する場合は、本 CHANGELOG をベースに適宜編集してご利用ください。