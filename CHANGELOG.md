# CHANGELOG

すべての notable な変更を記録します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマット:
- すべての変更はセクションごとに分類しています（Added, Changed, Fixed, ...）。
- バージョン 0.1.0 が初回リリースです。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージバージョンを `__version__ = "0.1.0"` として初回リリース。

- 実行 / 監視用スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - プロセス起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV = `paper_trading` の場合は専用の paper trading SQLite DB を使用（デフォルト: `data/paper_trading.db`）し、MockBrokerClient を利用する設計を想定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを実装。
    - RiskManager に初期設定 (max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等) を指定。
    - エンジンは別スレッドで実行され、`data/stop_requested.flag` を監視して安全に停止する仕組みを採用。
    - 起動時および終了時に SQLite / DuckDB 接続を適切にクローズ。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値（0 以下や非整数）はデフォルトへフォールバックし、警告を出力。
    - 監視（monitoring）は KABUSYS_ENV に依らず本番用の `sqlite_path` を使用する（監視レコードは本番 DB に記録）。
    - 起動時にプロセス優先度を "high" に設定。停止フラグ `data/stop_requested.flag` によりループを終了。

- 設定管理
  - config.py
    - .env の自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - .env の自動読み込みは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env ファイルパースが堅牢化（クォート対応、export プレフィックス対応、インラインコメント処理など）。
    - Settings クラスを追加し、アプリケーション設定をプロパティ経由で提供（J-Quants、kabu API、DB パス、監視閾値、環境検証、paper trading フラグ等）。
    - 設定に対するバリデーション（`PAPER_FILL_MODE`、`KABUSYS_ENV`、`LOG_LEVEL` 等）を実装し、不正値時は例外を投げる。

  - config_setup.py
    - 対話式ウィザードで `.env` を作成/更新する CLI を追加。
    - 秘密値は入力表示時にマスクし、既存 .env の読み込みと Enter による既存値再利用をサポート。
    - 出力される `.env` のテンプレートと注意書きを標準で生成。

  - validate_config.py
    - 起動前に環境変数と config/*.yaml の妥当性をチェックする CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース（PyYAML が利用可能な場合）などを実装。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）に対する追加ガード（LINE 未設定、KILL_FLAG_CLEAR_ON_START 等の警告）を実装。

- Paper Trading / レポート
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計してレポート出力。
    - P95 計算ロジックと期間フィルタ（--from / --to）をサポート。
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）および PASS/FAIL 判定を実装。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio.portfolio_builder
    - 候補選定（スコア降順 + signal_rank タイブレーク）。
    - 等金額配分（calc_equal_weights）とスコア加重配分（calc_score_weights）。全スコア 0.0 の場合は等配分へフォールバックし警告を出力。

  - portfolio.risk_adjustment
    - セクター集中制限（apply_sector_cap）。既存ポジションによりセクター比率が上限を超える場合、新規候補を除外するロジック。
    - 市場レジームに応じた投下資金乗数（calc_regime_multiplier）：`bull`/`neutral`/`bear` を想定し、未知レジームは警告を出して 1.0 をフォールバック。

  - portfolio.position_sizing
    - ポジションサイズ計算（calc_position_sizes）。allocation_method として `"risk_based"`, `"equal"`, `"score"` をサポート。
    - risk_based: 損切り幅・リスク許容率から株数を逆算。
    - equal/score: 各銘柄の配分重み・利用可能現金・lot_size を考慮して株数を決定。
    - aggregate cap（投下合計が可用現金を超える場合）でスケールダウンし、lot_size 単位で残余キャッシュにより上位の残差を再配分する細かなアルゴリズムを実装。
    - cost_buffer（スリッページ・手数料見積）を価格に乗じることで保守的な見積りに対応。

- 研究用モジュール
  - research.factor_research
    - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、流動性など）を実装（prices_daily / raw_financials を参照）。
    - モメンタム: 1M/3M/6M リターン、MA200 乖離率（足りない場合は None）。
    - ボラティリティ: ATR20、ATR 比、20日平均売買代金、出来高比率等を計算する SQL ベース実装。
    - 計算対象ウィンドウやパラメータは定数として定義。

- ユーティリティ
  - utils.process_priority
    - クロスプラットフォームでプロセス優先度を設定するユーティリティ関数 `set_process_priority(level)` を追加（Windows: HIGH_PRIORITY_CLASS 等、POSIX: nice 値）。
    - CPU affinity を最初の N コアに固定する `set_cpu_affinity(cpu_count)` を追加。
    - 権限不足や未対応環境では警告を出してフォールバック。

### Changed
- 初回リリースのため履歴なし（新規追加のみ）。

### Fixed
- 初回リリースのため履歴なし。

### Notes / 重要な挙動
- 監視（run_monitoring）は KABUSYS_ENV に関係なく Settings.sqlite_path（本番想定の monitoring DB）を使用します。監視データを分離したい場合は sqlite_path を適切に設定してください。
- ペーパートレードモード（KABUSYS_ENV=paper_trading）は実運用 DB と分離して `PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）を使用するよう設計されています。これにより本番注文と完全に隔離されます。
- .env 自動ロードはプロジェクトルートを検出できない場合はスキップされます。自動ロードを抑制するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- `.env` パーサはクォート、エスケープ、`export KEY=val` 形式、コメントを扱うように改善されていますが、非常に特殊なフォーマットには対応しない場合があります。
- `MONITOR_POLL_INTERVAL` は正の整数を期待します。不正な値（非整数・0・負数）はログ警告を出し、デフォルトの 60 秒にフォールバックします。
- RiskManager の `initial_portfolio_value` はブローカークライアントの `get_available_cash()` を参照して初期化されます。Mock Broker 実装はペーパートレード用 DB と連動する想定です。

### Security
- 初回リリースのため特記事項なし。

---

今後のリリースでは、バグ修正、テスト追加、ドキュメント整備（API ドキュメントや設計書のリンク付与）、およびさらに詳細な運用手順を追記する予定です。