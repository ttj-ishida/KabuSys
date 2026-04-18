CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現時点では未リリースの変更はありません）

0.1.0 - 2026-04-18
-----------------

Added
- 初回公開: KabuSys コードベースを追加。
- 実行エントリ/デーモン:
  - run_execution.py: ExecutionEngine を起動するエントリスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）。起動時にプロセス優先度を "high" に設定し、停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) を扱う。
  - run_monitoring.py: SystemMonitor 用のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず実運用用 sqlite_path を使用する。
- 設定管理:
  - config.py: 環境変数と .env ファイルの読み込み・解釈ロジックを実装。プロジェクトルート自動検出（.git または pyproject.toml を基準）。.env/.env.local 自動ロード（OS環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可。値取得用の Settings クラスを提供（各種パス、閾値、モード判定プロパティ含む）。
  - config_setup.py: .env の対話式ウィザードを追加（既存値読み込み、シークレットマスク表示、ファイル書き出し）。
  - validate_config.py: 起動前チェック用 CLI を追加。.env と config/*.yaml の存在・基本妥当性チェック。--strict オプションで警告をエラー扱いにできる。
- ロギング・プロセス制御ユーティリティ:
  - utils/logging_setup.py: 統一的なログ設定関数を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日分）をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみにフォールバック。
  - utils/process_priority.py: psutil を用いたクロスプラットフォームなプロセス優先度設定と CPU affinity 設定を追加。Windows / POSIX の差分を吸収。許可エラー時は警告を出してスキップ。
- ポートフォリオ構築（純粋関数群）:
  - portfolio/portfolio_builder.py: 候補選定（score 順）、等配分・スコア加重の重み算出を実装。
  - portfolio/risk_adjustment.py: セクター集中上限適用ロジック（既存保有を考慮して当日売却予定は除外）と市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装。
  - portfolio/position_sizing.py: リスクベースおよび等配分/スコア配分に基づく株数計算を実装。単元（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金を超えた場合のスケーリング）、手数料/スリッページ用の cost_buffer を考慮。価格欠損時のスキップ・デバッグログあり。
- 研究・ツール:
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム・MA200乖離・ATR 等、設計方針と定数を実装）。（注: ファイル末尾で未完の部分あり）
  - tools/paper_verification_report.py: ペーパートレード DB を解析し検証レポートを出力する CLI を追加。稼働率・注文成功率・送信率・レイテンシ（平均・最大・P95）などを算出し PASS/FAIL を判定するしきい値を定義。P95 算出ロジック、日付フィルタ、DB 存在チェック、各種欠損時のフォールバックを実装。

Changed
- （初回公開のため該当なし）

Fixed
- （初回公開のため該当なし）

Deprecated
- （初回公開のため該当なし）

Removed
- （初回公開のため該当なし）

Security
- 機密情報は .env に格納する想定（config_setup にて .env を生成）。.env は絶対にリポジトリにコミットしない旨をウィザードで強調。

Notes / 実装上の注意
- .env パーサ:
  - export KEY=val 形式に対応。
  - シングル/ダブルクォート内のバックスラッシュエスケープを考慮して値を正しく復元。
  - クォートなしの場合は「# の直前が空白またはタブ」の場合のみインラインコメントと見なす（通常の # の扱いに差異あり）。
- 自動 .env ロード:
  - OS 環境変数が優先され、.env.local は .env を上書きする。テスト等で自動ロードを無効化するため KABUSYS_DISABLE_AUTO_ENV_LOAD を使用可能。
- run_monitoring と run_execution の挙動:
  - 両スクリプトとも起動直後にプロセス優先度を設定（set_process_priority("high")）。
  - 監視ループは stop flag の検出、例外発生時のログ出力と次ポーリングまで継続、KeyboardInterrupt のハンドリングを行う。
  - run_execution は paper_trading 環境では Mock ブローカー（BrokerClientFactory にて生成）を利用することを想定。
- ロギング:
  - StreamHandler は stdout を使用（stderr ではない）。ログディレクトリ作成に失敗した場合はコンソール出力のみで継続する。
- process_priority と CPU affinity:
  - psutil の権限エラーやプラットフォーム非対応は警告してスキップする安全設計。
- Paper Verification Report:
  - P95 はパーセンタイルの簡易実装（ソートして上位 95% の境界を選択）。対象データなしの場合は N/A を出力。

既知の未実装 / TODO
- research/factor_research.py の関数実装（ファイル末尾に未完の記述あり）。将来的に完全なファクター計算を実装する予定。
- position_sizing の価格欠損時のフォールバック（前日終値や取得原価を参照する等）は TODO コメントとして残っている。
- 将来的には銘柄毎の lot_size を外部マスタに持たせる拡張を想定（現在は全銘柄共通の lot_size を使用）。

作者
- KabuSys 開発チーム

---