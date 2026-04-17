# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した変更履歴です。

## [Unreleased]

- 今後の変更を記載します。

## [0.1.0] - 2026-04-17

### Added
- 基本的な日本株自動売買システム「KabuSys」の初期実装を追加。
  - パッケージメタ情報: src/kabusys/__init__.py にバージョン情報を追加（0.1.0）。
- 環境設定・読み込みまわり
  - .env 自動読み込み機能を実装（プロジェクトルートに基づく探索、.env / .env.local の優先順位を考慮）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。 (src/kabusys/config.py)
  - Settings クラスを実装し、J-Quants / kabuステーション / DB / 監視 / システム設定等の環境変数をプロパティ経由で取得・検証。paper_trading 用の paper_sqlite_path、paper_fill_mode バリデーションなどを含む。 (src/kabusys/config.py)
- 設定関連 CLI
  - 対話式環境設定ウィザードを追加（.env の初期作成・更新を支援）。対話入力、既存値の読み込み、.env ファイル書き出しを行う。 (src/kabusys/config_setup.py)
  - 設定検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の値チェック、DB パスや config/*.yaml の存在・パース確認、live 環境向けの追加ガードを実行可能。--strict モードあり。 (src/kabusys/validate_config.py)
- 実行・監視ランチャー
  - ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の MockBrokerClient を利用し paper_trading 用 SQLite（data/paper_trading.db）に記録するよう分離。停止フラグ（data/stop_requested.flag）・PID 管理をサポート。 (src/kabusys/run_execution.py)
  - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を使用する設計。停止フラグ検出でループを終了。 (src/kabusys/run_monitoring.py)
- DB 初期化 / 接続
  - 監視用テーブルの冪等な初期化を行うヘルパーを利用（init_monitoring_db を呼び出し）。DuckDB と SQLite の接続を組み合わせて利用する構成を採用。 (run_monitoring/run_execution)
- ポートフォリオ構築モジュール（純関数群）
  - 銘柄選定・重み計算: select_candidates, calc_equal_weights, calc_score_weights。スコアが全てゼロの場合のフォールバック・警告ロジックを含む。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限・レジーム乗数: apply_sector_cap（既存ポジションを考慮したセクター上限除外ロジック）、calc_regime_multiplier（bull/neutral/bear マップと未知レジームのフォールバック）。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定・資金配分: calc_position_sizes（risk_based / equal / score の割当方式、単元株丸め、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差分の lot 単位再配分ロジック）。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージのエクスポートを整備。 (src/kabusys/portfolio/__init__.py)
- リサーチ / ファクター計算
  - DuckDB を利用したファクター計算モジュールを実装（モメンタム、移動平均乖離、ATR、出来高系などを計算）。prices_daily / raw_financials テーブルのみ参照し外部 API に依存しない設計。P95 等のスキャン範囲を含む。 (src/kabusys/research/factor_research.py)
- 運用ツール
  - Paper Trading 検証レポート生成スクリプトを追加。指定期間の system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を算出し PASS/FAIL 判定を出力。閾値はソース内で定義（稼働率 99%、注文成功率 90%、送信率 95%、P95 200ms）。 (src/kabusys/tools/paper_verification_report.py)
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows / POSIX（Linux, macOS, FreeBSD）差分を吸収する。psutil による設定を試み、権限不足や未サポート時には警告をログに出力してスキップ。 (src/kabusys/utils/process_priority.py)

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Notes / 実装上の重要事項
- run_monitoring は環境（KABUSYS_ENV）にかかわらず本番の sqlite_path を使用する設計になっている点に注意。run_execution は paper_trading 環境時に専用の paper_sqlite_path を使用することで DB 分離を行う。
- MONITOR_POLL_INTERVAL: 環境変数に不正な値（数値以外、0 以下）が設定された場合はデフォルト 60 秒にフォールバックして警告を出力する。
- config の .env パーサはクォートやエスケープ、インラインコメントの扱いに対応しているが、複雑な .env の記法のすべてを保証するわけではない。
- calc_position_sizes の lot_size は現状共通設定（デフォルト 100）で、将来的に銘柄別単元対応が想定されている（TODO コメントあり）。
- process_priority / set_cpu_affinity は psutil の機能に依存するため、実行環境によっては権限不足で設定できない場合がある（その場合はログに警告）。
- Paper Trading の検証レポートは SQLite 内のテーブル構造に依存する（存在しない場合は N/A や 0 を返し、OperationalError をキャッチして回復する処理あり）。

### Security
- （初期リリースのため特記事項なし）

---

参照: 各機能は src/kabusys 以下のモジュール実装に基づき推測して記載しました。実際のリリースノート作成時はリリース日・コミットハッシュ・関連 Issue/PR を付記してください。