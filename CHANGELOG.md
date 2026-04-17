# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。

## [Unreleased]

（現在未リリースの変更はありません）

---

## [0.1.0] - 2026-04-17

初回公開リリース。日本株自動売買システム KabuSys の基盤機能を実装しました。

### 追加 (Added)
- コアライブラリ
  - kabusys パッケージの初期モジュール群を追加。
  - パッケージバージョンを `0.1.0` として設定（src/kabusys/__init__.py）。

- 環境設定・管理
  - Settings クラスを実装し、環境変数ベースの設定取得を提供（src/kabusys/config.py）。
    - デフォルト値や型検証を含む各種プロパティ（データベースパス、ログレベル、環境種別、paper trading の制御など）。
    - PAPER_FILL_MODE のバリデーション実装（有効値: instant/partial/never/reject）。
    - .env の自動読み込み機能をプロジェクトルート（.git or pyproject.toml）から行う実装。OS 環境変数を保護する仕組みを採用。
    - プロジェクトルート検出ロジック（_find_project_root）により CWD に依存しない自動ロードを実現。

- CLI / ユーティリティ
  - 対話式 .env 作成ウィザード（python -m kabusys.config_setup）。
    - 既存 .env の読み込み、項目定義、シークレットマスク、書き出しロジックを実装。
  - 設定検証コマンド（python -m kabusys.validate_config）。
    - 必須環境変数や KABUSYS_ENV、LOG_LEVEL、DB パス、config/*.yaml の存在とパース（PyYAML インストール時）を検証。
    - --strict オプションで警告を FAIL 扱いにできる。
  - Paper Trading 検証レポート生成スクリプト（python -m kabusys.tools.paper_verification_report）。
    - 指定期間のシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を行う。
    - デフォルト DB パスは `data/paper_trading.db`。--db オプションや環境変数で上書き可能。

- 実行系 / 監視
  - 実行エントリスクリプト run_execution を追加（src/kabusys/run_execution.py）。
    - 環境に応じて paper_trading 用 DB を分離（settings.is_paper 判定）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て。
    - ExecutionEngine をデーモンスレッドで起動。停止フラグ（data/stop_requested.flag）検出で安全停止。
    - プロセス優先度を起動直後に "high" に設定する処理を組み込み（set_process_priority）。
  - 監視ループ起動スクリプト run_monitoring を追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を初期化しポーリングループで定期実行。
    - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計（監視は常に本番 DB を想定）。

- ポートフォリオ構築・ポジション管理
  - portfolio モジュールを追加（src/kabusys/portfolio）。
    - portfolio_builder: 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
    - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに基づく投下資金乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算（calc_position_sizes） — risk_based / equal / score の allocation_method に対応。lot_size（単元）・コストバッファ・aggregate cap のスケーリングロジックを実装。

- リサーチ
  - factor_research モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum / Volatility / Liquidity 等のファクター計算を DuckDB 上で実行する関数群を実装（calc_momentum, calc_volatility 等）。
    - DuckDB による SQL 実行で prices_daily / raw_financials を参照し純粋関数的にファクターを算出。

- ユーティリティ
  - プロセス優先度と CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX を吸収する set_process_priority 実装（psutil ベース）。権限不足や未対応 OS を想定したエラーハンドリング。
    - set_cpu_affinity でプロセスを最初の N コアに固定する機能を提供。引数検証と例外ハンドリングを実装。

### 変更 (Changed)
- .env 読み込みの堅牢化
  - _parse_env_line による詳細な行パース実装を導入。export プレフィックス、クォート内のエスケープ、インラインコメントの扱いなどをサポートし、従来の単純パースより堅牢な読み込みを実現。
  - _load_env_file に protected 引数を導入し、OS 環境変数を上書きしない安全な動作を採用。

- DB 接続ポリシー
  - 監視（run_monitoring）は常に本番用 sqlite_path を参照するように設計（監視データは環境に依存しない想定）。
  - run_execution は paper_trading モード時に paper_sqlite_path を使用し、本番 DB と分離。

- エラーハンドリング / ログ
  - 重要処理における例外キャッチとログ出力を強化（monitor.check_once() の例外をログして継続する等）。
  - set_process_priority / set_cpu_affinity は権限不足等で失敗した際に警告ログを出して処理を継続する設計。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL の不正な設定時に sleep に渡して ValueError になる問題を回避するため、0以下や非整数は警告してデフォルト値（60秒）にフォールバックするロジックを追加（run_monitoring）。
- position_sizing のスケールダウン処理において、lot_size 単位での丸めと残余キャッシュでの再配分を考慮することで、合計コストが available_cash を超える状況での挙動を安定化。
- apply_sector_cap: sector が未定義（unknown）の場合はセクター上限を適用しないことで誤除外を防止。
- factor_research の SQL において移動平均やラグデータ欠損時に NULL を正しく扱うことで不正な計算結果の伝播を抑制。

### ドキュメント / 開発者向け (Docs)
- config_setup の対話ウィザードは .env のテンプレートを出力する実装を含み、項目ごとの説明やデフォルト値を表示することで初期セットアップが容易になった。
- validate_config により、本番運用前に設定不備（必須環境変数未設定、config YAML のパースエラー、DB パスの親ディレクトリ未作成など）を事前検出可能に。

### 注意 / 既知の問題 (Known issues)
- position_sizing や apply_sector_cap は価格データが欠損した場合（price == 0.0 等）に conservative にスキップする実装であり、将来的には前日終値や取得原価でのフォールバックを検討する必要あり（コード中に TODO コメントあり）。
- factor_research の計算は prices_daily / raw_financials のデータ品質に依存するため、欠損データや不整合があると一部銘柄で None が返ることがある。
- set_process_priority / set_cpu_affinity はプラットフォーム依存のため全環境で効果が保証されない。権限が不足していると警告ログでスキップされる。

---

今後の予定（アイデア）
- 銘柄ごとの lot_size をマスタデータで管理する対応。
- factor_research の追加ファクター・Zスコア正規化ユーティリティの公開。
- ExecutionEngine / RiskManager のさらなるテストカバレッジ強化とメトリクス出力の充実。

（以上）