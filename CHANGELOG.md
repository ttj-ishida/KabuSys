# Changelog

すべての変更は Keep a Changelog の方針に従って記載しています。  
各項目はコードベース（src/ 以下）の内容から推測してまとめています。

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装を追加
  - パッケージバージョン: kabusys v0.1.0（src/kabusys/__init__.py）
- 実行用エントリスクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグファイル (data/stop_requested.flag) による安全停止に対応。
    - 起動時にプロセス優先度を "high" に設定（utils.process_priority）。
    - Monitoring は環境設定にかかわらず本番用 sqlite_path を使用する設計。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し MockBrokerClient を利用（本番 DB と分離）。
    - ExecutionEngine を別スレッドで起動し、停止フラグで安全に停止する仕組みを実装。
    - PID ファイルパスの取り扱いと起動前チェックを実装。
- 設定管理・CLI
  - config.py: 環境変数/.env 読み込みと Settings クラスを実装。
    - .env 自動ロード機能（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env のパースで引用符・エスケープ・export 形式・行内コメント等に対応。
    - 各種設定プロパティ（DB パス、KABUSYS_ENV、paper_trading 関連、監視閾値等）を提供し妥当性チェックを実施。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を追加。
    - デフォルト値、シークレット表示マスク、オプション扱いに対応。
  - validate_config.py: 起動前に .env と config/*.yaml の整合性を検査する CLI を追加。
    - 必須環境変数のチェック、KABUSYS_ENV の検証、YAML ファイルの存在・パースチェック（PyYAML がない場合は警告）等を実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を追加（スコア順選出、スコア加重／等金額配分）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中制限フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）。
  - portfolio/position_sizing.py
    - calc_position_sizes: 複数方式（risk_based / equal / score）の発注株数計算、単元株丸め、aggregate cap によるスケーリング、残余配分ロジックを実装。
    - 手数料・スリッページの保守的見積りを考慮する cost_buffer パラメータをサポート。
- リサーチ / ファクター計算
  - research/factor_research.py
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足時は None を返す挙動）。
    - calc_volatility: ATR、相対 ATR、20 日売買代金平均、出来高比率など（DuckDB 上の prices_daily を参照）。
    - DuckDB を用いた SQL ベースの実装で大規模データに適した設計。
- ユーティリティ
  - utils/process_priority.py
    - set_process_priority: Windows / POSIX（Linux/Mac/FreeBSD）対応の優先度設定（psutil を利用）。権限や未対応 OS の場合は警告を出して安全にスキップ。
    - set_cpu_affinity: 指定コア数にプロセスをピン留めする機能（失敗時は警告）。
- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。稼働率・注文成功率・送信率・P95 レイテンシ等を算出し PASS/FAIL 判定を行う。
    - DB が存在しない、あるいはテーブルが欠けている場合にも例外を吸収してレポートを出力（適切に N/A 表示）。
- DB 初期化呼び出し
  - monitoring.monitoring_db.init_monitoring_db を run_*.py 内で呼び出し、監視用テーブルの冪等な初期化を保証。

### Changed
- 初回の機能実装につき、特別な互換性破壊の記載はありません（新規追加中心）。

### Fixed
- .env パーサーの強化
  - クォート付き値のバックスラッシュエスケープ対応、export 先頭表記のサポート、行内コメントのより厳密な扱い等により .env の互換性・頑健性を向上。
- CLI の堅牢化
  - validate_config と paper_verification_report が依存リソース（PyYAML、SQLite テーブル等）の欠如時に適切に警告/フォールバックするよう改善。
- ポジションサイズ計算の安全弁
  - 価格未取得や 0 の場合をスキップし、単元（lot_size）での丸めや aggregate cap による再配分で過剰発注を防止。

### Notes / Known issues / TODO
- run_monitoring は「監視は環境にかかわらず本番 sqlite_path を使用する」と明記されており、意図的な設計ではあるが、テスト環境で監視 DB を分離したい場合は運用上の注意が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積もられる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討する想定。
- position_sizing:
  - 将来的に銘柄毎の lot_size をサポートする設計に拡張する予定（現状は全銘柄共通の lot_size を想定）。
- process_priority の設定は権限不足や未対応プラットフォームで失敗することがあるが、その場合はログ出力のみで処理は継続する設計。
- 一部モジュールは外部実装（ExecutionEngine、BrokerClientFactory 等）に依存しており、このリリースでは起動スクリプトからの呼び出し点のみを実装／接続している想定。

### Security
- .env は生成時に「絶対に Git にコミットしないこと」を .env ヘッダに明示。シークレット値はウィザードでマスク表示する等の配慮を実装。

---

この CHANGELOG はソースコードから推測して作成しています。実際のリリースノート作成時はコミット履歴やリリース日、影響範囲の確認（特に外部 API / DB 設定に関する注意事項）を行ってください。