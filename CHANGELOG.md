# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。  
主な変更点はコードベース（src/ 以下）の内容から推測して記載しています。

全般的な注意
- 初期リリース相当のまとめです。実装の詳細や内部動作はパッケージ内の各モジュールのドキュメント（docstring）を参照してください。
- 環境変数やファイルパスのデフォルトはソース中に記載されています（例: data/ 以下、logs/ 等）。

## [Unreleased]

- 現時点で未リリースの作業はありません（初期公開相当の内容を [0.1.0] に含めています）。

## [0.1.0] - 2026-04-25

Added
- 実行スクリプト／ランチャー
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合、ペーパートレード用の MockBrokerClient を用いる分離設計（paper_trading.db を使用）。
    - 停止フラグ（data/stop_requested.flag）検知による安全停止、PID ファイル（data/execution.pid）管理、バックグラウンドスレッドでの実行管理を実装。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority を利用）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバック。
    - 停止フラグ検知によるループ終了、例外発生時のログ出力と継続処理を備える。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を利用する設計。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml）。
    - .env / .env.local の読み込み順制御（OS 環境変数を保護）。
    - 複雑な行のパース対応（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント挙動）。
    - Settings クラスを通じた環境値の型チェック・既定値・検証（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - paper_trading 用 DB パスや PID / kill flag などの設定プロパティを提供。

  - config_setup.py（対話式ウィザード）
    - .env の初期作成・更新を対話式に行うウィザードを追加。
    - シークレット項目は表示をマスクし、保存前の確認プロンプトを実装。
    - .env の雛形生成（コメント付き）を行う _write_env を提供。

  - validate_config.py（設定検証 CLI）
    - 起動前に必須環境変数や config/*.yaml の存在・パース（PyYAML がある場合）を検証する CLI を追加。
    - --strict モードで警告を失敗扱いにできる。

- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py
    - 一般的なロギング設定ユーティリティを追加。
    - stdout へ出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でファイル出力（logs/<app_name>.log）を行う。
    - ログディレクトリ作成失敗時のフォールバック（コンソールのみ）や既存ハンドラのクリーンアップ等の堅牢性対策を実装。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）や CPU affinity を設定するユーティリティを追加。
    - 許可がない場合や未対応 OS では警告を出して処理をスキップする安全設計。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（select_candidates）と配分重み計算（calc_equal_weights, calc_score_weights）を追加。
    - スコア全てが 0 の場合のフォールバック等の挙動を定義。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング）。
  - portfolio/position_sizing.py
    - 各銘柄の株数計算 calc_position_sizes（allocation_method: risk_based / equal / score）を追加。
    - lot_size 単位での丸め、1 銘柄上限・集計上限（aggregate cap）・コストバッファを用いたスケーリング処理を実装。
    - 価格欠損時のスキップ、利用可能現金に応じたスケーリング等の詳細なロジックを備える。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加（SQLite の paper_trading.db を参照）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定を行う。
    - 閾値（稼働率 99%、成功率 90% 等）を定義し、期間指定 (--from / --to) によるフィルタ機能を提供。

- リサーチ基盤（雛形）
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム、MA、ATR、流動性、財務指標等の計算を想定）。
    - 実装はモジュール内で説明されており、prices_daily / raw_financials テーブルを参照する設計。

- パッケージメタ情報
  - __init__.py にてバージョン 0.1.0 を設定。

Changed
- 初期設計として、実行・監視処理はファイルベースのフラグ（stop/kill）と PID 管理により外部からの停止操作を想定した実装になっています。
- ロギングは stdout をメインにしつつファイルローテーションを併用する方針に統一。

Fixed
- .env パーサーの堅牢化（クォート内のバックスラッシュエスケープ、インラインコメント処理、export プレフィックス対応など）により、実運用で見られる多様な .env 形式に対応。

Security
- シークレット値（J-Quants トークン・kabu API パスワード等）は .env に保存される想定だが、config_setup の注意書きで .env を Git にコミットしないよう明記。
- Settings._require による必須環境変数未設定時の早期検出を実装。

Deprecated
- なし（初期リリース）。

Removed
- なし（初期リリース）。

Notes / Implementation details（補足）
- DB
  - DuckDB（分析用）と SQLite（監視・ペーパートレード用）を併用する設計。設定により paper_trading 用 DB を完全に分離可能。
- プロセス優先度と安全性
  - 起動直後に set_process_priority("high") を呼び出す設計。権限不足や未対応 OS の場合は警告を出してフォールバック。
- ポートフォリオ・ポジション計算
  - risk_based、equal、score の各方式をサポート。lot_size（現状は共通 100）による丸めや、aggregate cap によるスケールダウンを行うため、実際の発注前に Engine 側で利用可能現金等のチェックが必要。
- CLI
  - validate_config.py / config_setup.py / tools/paper_verification_report.py はそれぞれモジュールとして直接実行可能（python -m kabusys.validate_config 等）。

今後の検討（ソースから推測）
- portfolio.position_sizing の lot_size を銘柄別に拡張する（stocks マスタ導入）。
- apply_sector_cap の価格欠損時のフォールバック（前日終値等）を追加してエクスポージャー推定の精度向上。
- research/factor_research の各ファクター計算の完成・テストと、DuckDB を使ったバッチ処理の最適化。
- 監視（SystemMonitor）や ExecutionEngine の内部詳細（エラーハンドリング、再試行、メトリクス収集）の充実化。

---

著者注: この CHANGELOG は与えられたソースコードの内容から機能追加・設計方針を推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース日、関連 issue/PR を参照して追記・修正してください。