Keep a Changelog 準拠 — 以下は提供されたコードベースから推測して作成した CHANGELOG.md です。変更点はコード内容に基づく推測であり、実際のコミット履歴とは異なる場合があります。

Unreleased
---------
- なし

[0.1.0] - 2026-04-22
--------------------
Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - エントリスクリプト / 実行管理
    - run_execution.py: ExecutionEngine 起動スクリプト。プロセス優先度設定、停止フラグ監視、ペーパートレード時の専用 DB 分離を実装。
    - run_monitoring.py: SystemMonitor 起動スクリプト。ポーリングループ、MONITOR_POLL_INTERVAL 環境変数対応、停止フラグ検知を実装。
  - 設定管理
    - config.py: .env 自動読み込み、.env パース（export プレフィックス、クォートとエスケープ、インラインコメント処理対応）、Settings クラス（各種環境変数プロパティ）を提供。ペーパートレード用 DB パスや閾値などの設定を含む。
    - config_setup.py: 対話式ウィザードで .env を生成／更新する CLI を実装（シークレットマスク表示、選択肢・デフォルト対応）。
    - validate_config.py: 起動前検証 CLI を追加（必須/任意環境変数のチェック、config/*.yaml の存在と YAML パース検証、--strict オプション）。
  - ロギング・プロセス制御ユーティリティ
    - utils/logging_setup.py: StreamHandler（stdout）＋ TimedRotatingFileHandler（日次ローテーション）で統一的ロギング設定。ログディレクトリ作成失敗時のフォールバック処理を実装。
    - utils/process_priority.py: psutil を利用したクロスプラットフォームのプロセス優先度設定（Windows/Linux/Mac）および CPU affinity 設定ユーティリティ。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等配分・スコア加重配分の計算を提供。
    - portfolio/position_sizing.py: 複数の配分方式（risk_based / equal / score）に対応した株数決定ロジック、単元株（lot_size）丸め、aggregate cap によるスケールダウンを実装。
    - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）を実装。
    - portfolio/__init__.py: 上記 API をエクスポート。
  - 分析 / レポート
    - tools/paper_verification_report.py: ペーパートレード用 SQLite DB から検証レポートを生成する CLI。稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL 判定を出力。期間フィルタ、DB パス指定対応。
  - リサーチ（ファクター計算）
    - research/factor_research.py: Momentum / Value / Volatility / Liquidity 等のファクター計算を行う設計のモジュールを追加（DuckDB 接続を受け SQL/Python で処理する設計）。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- n/a（初回リリースのため "追加" が中心）

Fixed
- n/a（初回リリースのため明確な修正履歴なし）

Security
- 環境変数の取り扱いにおいて、.env ファイルは Git にコミットしない旨を明記（config_setup.py 内ヘッダ）。

Notes / Implementation details（重要な実装上の注記）
- run_execution.py は KABUSYS_ENV が paper_trading の場合、paper_sqlite_path を使用して本番 DB と分離する仕様を採用（MockBrokerClient を経由する設計を想定）。
- .env のパースはクォート文字内のバックスラッシュエスケープ、export プレフィックス、インラインコメント（スペース前の # をコメント判定）などを考慮しており、既存 OS 環境変数を保護する機能を持つ。
- logging_setup は stdout をメインに使用する設計（stream を stdout に設定）で、ログファイル出力はログディレクトリ作成成功時のみ有効化するフォールバックロジックを持つ。
- process_priority は psutil の機能差を吸収する実装で、権限不足や未対応 OS では警告を出してスキップする安全な設計。
- position_sizing のスケールダウンロジックは可再現性のため残差処理を行い、lot_size 単位で配分するアルゴリズムを実装。
- paper_verification_report は DB が存在しない場合やテーブル欠落時に安全に N/A を出力するよう例外処理を多用。

Acknowledgements / TODO（今後の改善が推奨される点、コード中に TODO コメントあり）
- position_sizing: 銘柄別の lot_size を将来的にサポートする（現在は全銘柄共通）。
- risk_adjustment.apply_sector_cap: price が欠損した場合のフォールバック（前日終値や取得原価の利用）を検討。
- research/factor_research: 実装の続き（ファイル末尾が途中で切れているため、実装完了が必要）。
- run_monitoring / run_execution: SystemMonitor, ExecutionEngine 等の具象実装が別ファイルにある前提（本 changelog はこれらの存在を仮定して記述）。

以上。

もし実際のコミット履歴やリリース日を反映した正確な CHANGELOG が必要であれば、git の履歴（git log / tags）やプロジェクトのリリースノートを提供してください。