CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

v0.1.0 - 2026-04-23
-------------------

Added
- 初回リリース。以下の主要コンポーネントを追加。
  - 実行 / 監視スクリプト
    - run_execution.py:
      - ExecutionEngine 起動用スクリプトを追加。プロセス優先度を高に設定し、PID ファイル管理・停止フラグ検出に対応。
      - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB（data/paper_trading.db）を使用し、本番 DB と完全に分離する仕組みを実装。
      - BrokerClientFactory を経由して実際の/モックのブローカークライアントを切り替え可能な設計。
      - スレッドでエンジンを起動し、停止フラグ検出で安全にシャットダウンするループを実装。
    - run_monitoring.py:
      - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関係なく本番用 sqlite_path を使用する設計（監視データの統一性確保）。
      - 停止フラグ（data/stop_requested.flag）検出でループを終了。
  - 設定関連
    - config.py:
      - Settings クラスを実装。環境変数からの設定取得を集中管理。
      - .env 自動ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - export 形式やクォート付き値、インラインコメントなどを考慮した .env パーサーを実装。
      - PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH、PID/KILL フラグ関連、しきい値設定（CPU/MEM/DISK）などをプロパティとして提供。
  - 設定支援 CLI
    - config_setup.py:
      - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。既存 .env の読み込み／マスク表示／確認保存機能を提供。
      - 生成される .env に対して「絶対に Git にコミットしないこと」を明記。
    - validate_config.py:
      - 起動前の設定検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の値チェック、データベースパス親ディレクトリの存在確認、config/*.yaml の存在・パースチェック（PyYAML があればパースも実施）などを行う。
      - --strict オプションで警告を FAIL 扱いにできる。
      - KABUSYS_ENV=live 時の追加ガード（LINE 設定未登録や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
  - ロギング & プロセス制御ユーティリティ
    - utils/logging_setup.py:
      - 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日保持）をルートロガーに設定。ログディレクトリ自動作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
      - ログレベルおよびログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。
    - utils/process_priority.py:
      - Windows / POSIX の差分を吸収してプロセス優先度を設定するユーティリティを追加（"high"/"normal"/"low"）。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
      - 権限不足や未対応環境時は警告を出してフォールバック。
  - ポートフォリオ構築ライブラリ
    - portfolio/portfolio_builder.py:
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。スコア全てが 0 の場合は等配分にフォールバックして警告。
    - portfolio/risk_adjustment.py:
      - セクター集中制限を行う apply_sector_cap を実装（既存保有金額を計算し、上限を超えるセクターの新規候補を除外）。
      - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear をマッピング、未知のレジームは 1.0 でフォールバック）。
    - portfolio/position_sizing.py:
      - position size（発注株数）計算ロジックを実装。allocation_method に "risk_based"/"equal"/"score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限(max_position_pct)、aggregate cap（available_cash）に従ったスケーリング、cost_buffer（スリッページ・手数料の保守的見積り）を実装。
      - スケーリング時の端数処理は lot_size 単位で残差を評価して優先的に追加割り当てするアルゴリズムを実装。
  - リサーチ、ツール
    - research/factor_research.py:
      - DuckDB 接続を受けてモメンタム、ボラティリティ、バリュー等のファクター計算（設計と定数）を実装開始。prices_daily / raw_financials テーブルを前提。
      - （一部未完の関数あり。将来的な実装継続を示唆する構成。）
    - tools/paper_verification_report.py:
      - Paper Trading の検証レポート生成スクリプトを追加。期間指定（--from/--to）や DB 指定（--db / 環境変数）に対応。
      - 稼働率、注文成立率、送信率、P95 レイテンシ等を算出、閾値に基づく PASS/FAIL 判定を実装。デフォルト閾値を定義（稼働率 99%、成立率 90% 等）。
  - パッケージ情報
    - __init__.py にバージョン __version__ = "0.1.0" を追加。

Changed
- なし（初回リリースのため「追加」に相当する変更の説明を記載）。

Fixed
- なし（初回リリース）。ただし、実装には各所で例外・エラーケースに対するハンドリング（例: DB 接続クローズ、ファイル作成失敗時のフォールバック、予期しない例外のログ出力など）を盛り込んでいます。

Security
- .env の取り扱いに関する注意喚起: config_setup で生成される .env に「絶対に Git にコミットしないこと」を明記。
- Settings._require により必須環境変数が未設定の場合は早期にエラーとなるため、秘密情報の未設定に起因する誤動作を低減。

Notes / その他
- 環境変数自動ロード:
  - プロジェクトルートの検出に成功した場合、.env を自動ロード（OS 環境変数を保護しつつ .env.local を上書き）します。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Paper Trading 分離:
  - paper_trading モードでは発注関連と DB を本番と完全に分離する方針を採用しており、検証と実トレードの混同を防止します。
- 未実装 / TODO の明示:
  - risk_adjustment.apply_sector_cap にて価格欠損時のフォールバック価格採用の検討（TODO コメント）。
  - research/factor_research.py の関数群は一部で未完（ファイル末尾が途中で切れているため続きの実装が必要）。

Unreleased
----------
- （空）次回リリースでは research モジュールの完全実装、ExecutionEngine/Monitor の統合テスト、さらにドキュメントと CLI の改善（非対話モードでの .env 設定、より詳細なロギング設定オプションなど）を予定しています。