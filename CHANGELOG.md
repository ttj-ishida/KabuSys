# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
本プロジェクトの初期リリース情報を以下に示します。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 実行用エントリポイントを追加
  - run_execution.py
    - ExecutionEngine を起動するスクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用の SQLite（デフォルト: data/paper_trading.db）で本番 DB から完全に分離して動作する仕組みを導入。
    - 実行中は data/execution.pid に PID を書き、 data/stop_requested.flag による停止フラグを監視して安全に停止可能。
    - プロセス優先度を高く設定するユーティリティ呼び出しを追加。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知でループを終了。
    - 監視は環境にかかわらず本番 sqlite_path を使用して DB を初期化。

- 設定・環境管理
  - config.py
    - .env 自動読み込み機能を追加（プロジェクトルート検出に .git / pyproject.toml を使用）。
    - .env の読み込みロジックを強化（export プレフィックス、クォート／エスケープ、インラインコメント処理などに対応）。
    - Settings クラスを提供し、アプリケーション設定（J-Quants / kabu API / DB パス / PID・Kill フラグ / 各閾値 / 環境判定等）をプロパティとして取得可能に。
    - PAPER_FILL_MODE の検証（有効値の限定）や paper_trading 用 DB パスを別途参照するプロパティを追加。

- 設定支援・検証 CLI
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI を追加。既存 .env の読み込み、シークレットマスキング、確認保存等を実装。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数・KABUSYS_ENV・LOG_LEVEL・DBパス・config/*.yaml の存在とパース等をチェック。--strict オプションで警告を失敗扱いにできる。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py
    - ルートロガーの統一設定ユーティリティを実装。コンソール（stdout）と日次ローテーション（TimedRotatingFileHandler）を設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして継続。
  - utils/process_priority.py
    - Windows/Linux/macOS を透過するプロセス優先度設定ユーティリティを追加。CPU affinity 設定関数も実装（権限やプラットフォームが対応していない場合はスキップして警告）。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）と配分重み計算（等金額 calc_equal_weights、スコア加重 calc_score_weights）を実装。スコア全0時のフォールバック挙動を定義。
  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap を追加（売却予定銘柄の除外や unknown セクター扱いの説明あり）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear をマップし、未知レジームは警告の上フォールバック）。
  - portfolio/position_sizing.py
    - 各銘柄の発注株数算出 calc_position_sizes を実装（risk_based / equal / score の allocation_method、lot_size 単位で丸め、最大ポジション上限・投下資金上限・集計スケールダウンロジック、cost_buffer を加味した安全な切り捨てと残余分配ロジックなど）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。指定期間／DB からシステム稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計し PASS/FAIL を判定する。しきい値はソースで定義（稼働率 99% 等）。

- 研究用モジュール（実装開始）
  - research/factor_research.py
    - DuckDB を想定したファクター計算モジュールを追加。モメンタム / MA200 乖離 / ATR / 流動性等の設計と定数が定義され、calc_momentum の骨組みを実装開始（未完部分あり）。

### 変更 (Changed)
- パッケージ情報
  - src/kabusys/__init__.py にバージョン文字列 __version__ = "0.1.0" を設定し、主要サブパッケージを __all__ で公開。

- DB 初期化
  - run_execution と run_monitoring で共通の監視テーブル初期化関数 init_monitoring_db を使用するようにし、監視テーブルの存在を冪等に保証。

- ログ出力の統一
  - すべての起動スクリプトから setup_logging を呼び出すことでログ設定を統一。

### 修正 (Fixed)
- 環境読み込みの頑健化
  - .env のパースでクォート・エスケープ・コメント処理を丁寧に扱うようにし、意図しない値の取り込みやインラインコメントの誤解析を防止。

- ポリシーと安全弁
  - ExecutionEngine 起動前に停止フラグを検知した場合はエンジンを起動せずに終了するようにして、誤起動を防止。
  - run_execution のスレッド監視ループと停止手順を明確化（デーモンスレッドで engine.run_session を起動、停止フラグで engine.stop を呼ぶ）。

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- なし

----

注記:
- ここに記載した変更は、リポジトリ内のソースコードから推測してまとめたものです。実際のリリースノートはプロジェクト運用者が検証の上で確定してください。
- research/factor_research.py の実装は途中で切れている箇所があり、今後追加実装・テストが必要です。