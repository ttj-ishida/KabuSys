# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に準拠します。

最新リリースのバージョンはソース内の __version__ に合わせて 0.1.0 としています。

## [0.1.0] - 2026-04-17

### 追加 (Added)
- プロジェクト初期実装を追加。
  - コアモジュール群:
    - portfolio: 銘柄選定・重み算出・ポジションサイズ決定・リスク調整の純粋関数群を実装。
      - select_candidates: BUY シグナルのスコア降順で候補選定。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア加重配分の計算。
      - calc_position_sizes: 発注株数決定ロジック（risk_based / equal / score、lot 丸め、aggregate cap、コストバッファ対応）。
      - apply_sector_cap: セクター集中制限（既存保有のエクスポージャーを考慮して候補除外）。
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング）。
  - 実行・監視関連 CLI / スクリプト:
    - run_execution.py: ExecutionEngine 起動スクリプト。paper_trading 環境時は専用の paper DB を使用し MockBrokerClient を利用する設計。停止フラグ（data/stop_requested.flag）と PID 管理を実装。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。プロセス優先度設定（高）を実行。
  - 設定周り:
    - config.py: 環境変数ラッパー Settings を実装。自動 .env 読み込み機能（プロジェクトルート検出）を追加。多くの設定項目（DB パス、PID/kill フラグパス、各種閾値、env 判定等）を提供。
    - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI を実装。
    - validate_config.py: 起動前に .env と config/*.yaml の基本的な妥当性を検証する CLI を実装（--strict オプションあり）。PyYAML 未インストール時は YAML 検証をスキップして警告。
  - ツール:
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（P95 など）を集計して PASS/FAIL 判定を出力。PAPER_TRADING_SQLITE_PATH 環境変数 / --db オプションで DB を指定可能。
  - リサーチ:
    - research/factor_research.py: DuckDB を用いたファクター計算モジュール（モメンタム、ボラティリティ等の計算ロジックの骨組）を追加。prices_daily / raw_financials テーブルを参照して計算する設計。
  - ユーティリティ:
    - utils/process_priority.py: プロセス優先度（Windows / POSIX の差分を吸収）と CPU affinity 設定ユーティリティを実装。権限不足や未対応 OS の場合は警告を出してスキップする堅牢化あり。

- DB 初期化:
  - monitoring.monitoring_db.init_monitoring_db を利用して監視用テーブルの存在を保証（冪等な初期化）。

### 変更 (Changed)
- 環境読み込みの優先順を明確化:
  - OS 環境変数 > .env.local > .env の順で読み込む実装（既存の OS 環境変数は保護される）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動読み込みを無効化可能（主にテスト用途）。
- run_monitoring の挙動:
  - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する（設計上の決定）。run_execution は paper_trading 環境で専用の paper_sqlite_path を使用して本番 DB と分離する。
- .env パーサーの挙動改善:
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内でのバックスラッシュエスケープに対応。
  - クォートなし行におけるインラインコメントの扱いを改善（# の前にスペース/タブがある場合をコメント扱い）。
- position_sizing のスケーリングロジック:
  - cost_buffer を導入して手数料・スリッページを保守的に見積もれるようにした。
  - aggregate cap 超過時にスケールダウンし、残余現金で fractional 残差の大きい順に lot 単位で追加配分する方式を採用（再現性のため安定した二次キーソートを実装）。

### 修正 (Fixed)
- プロセス優先度設定で権限や未サポート API による例外を捕捉し、ワーニングを出すようにして起動失敗を防止。
- MONITOR_POLL_INTERVAL の不正値（0 以下や非整数）を検出してデフォルト値にフォールバックする保護ロジックを追加。

### 注意事項 / マイグレーション (Notes)
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は必須。Settings._require により未設定時に ValueError が発生するため、.env または OS 環境で設定してください。
- 実行方法（例）:
  - 環境セットアップ: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
  - 実行エンジン起動: python -m kabusys.run_execution
  - 監視起動: python -m kabusys.run_monitoring
  - ペーパートレード検証レポート: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Paper Trading:
  - KABUSYS_ENV=paper_trading の場合、run_execution は paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と完全分離します。
- Kill / Stop フラグ:
  - 停止制御はプロジェクトの data ディレクトリ内の stop_requested.flag / kill.flag 等のファイル存在で行います。運用時は適切に管理してください。
- 依存:
  - duckdb, psutil 等の外部ライブラリが必要です。YAML 検証は PyYAML に依存し、未インストール時は検証がスキップされます（警告が出ます）。

### 既知の制限 (Known issues)
- apply_sector_cap で price_map に価格が欠損（0.0）だとエクスポージャーが過小見積りされ得る点をドキュメント内に TODO として記載しています。将来的に前日終値や取得原価を利用するフォールバックを検討予定。
- position_sizing は現状で全銘柄共通の lot_size（既定 100）を想定。将来的に銘柄別 lot_size マッピングへの拡張を計画。

---

今後のリリースでは、運用で得られた実データに基づく安定化、テストカバレッジの拡充、銘柄単位設定の柔軟化（lot_size 等）、およびさらに詳細なモニタリング・アラート設定の追加を予定しています。