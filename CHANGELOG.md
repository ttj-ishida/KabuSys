CHANGELOG
=========
すべての変更は「Keep a Changelog」仕様に準拠して記載しています。  
日付はコード内に複数のヒント（スクリプトの使用例やコメント）を踏まえた推定日付（2026-04-21）で記載しています。コードの内容から推測してまとめているため、実際のコミット履歴とは差異がある可能性があります。

Unreleased
----------
- なし

[0.1.0] - 2026-04-21
--------------------
Added
- 基本機能: KabuSys v0.1.0 を初期リリース。
  - パッケージ基本情報: __version__ = "0.1.0" を追加 (src/kabusys/__init__.py)。
- 実行スクリプト:
  - 実行エンジン起動スクリプト run_execution.py を追加。
    - 環境に応じて paper_trading 時は専用の SQLite（data/paper_trading.db）と MockBrokerClient を使用する分離設計。
    - 起動時にプロセス優先度を設定し、PID ファイル管理、停止フラグ監視（data/stop_requested.flag）に対応。
  - 監視ループ起動スクリプト run_monitoring.py を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する旨を明記。
    - SystemMonitor.check_once() を定期実行して監視データを記録。
- 設定管理:
  - Settings クラス（src/kabusys/config.py）を実装。
    - .env 自動ロード（.env, .env.local）機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化。
    - 各種環境変数取得プロパティ（J-Quants, kabu API, DB パス、paper_trading 用設定、監視しきい値など）。
    - env/log_level のバリデーション、paper_fill_mode の検証。
  - 対話式環境設定ウィザード config_setup.py を追加。
    - .env の初期作成/更新を支援。シークレット項目はマスク表示。
- 設定検証 CLI:
  - validate_config.py を追加。
    - 必須/任意環境変数のチェック、DB パスや config/*.yaml の存在・パース検証（PyYAML がなければ警告）。
    - KABUSYS_ENV=live 時の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築（純粋関数群）:
  - portfolio_builder.py
    - 銘柄選定 select_candidates、等配分 calc_equal_weights、スコア加重 calc_score_weights を実装。
  - risk_adjustment.py
    - セクター上限適用 apply_sector_cap、レジーム乗数 calc_regime_multiplier を実装。
  - position_sizing.py
    - position サイズ計算 calc_position_sizes を実装（risk_based / equal / score の割当方式対応、lot_size 単位で丸め、aggregate cap のスケールダウン実装）。
  - portfolio/__init__.py で上記関数群をエクスポート。
- ログ・プロセスユーティリティ:
  - utils/logging_setup.py
    - root ロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを追加。
    - LOG_LEVEL / LOG_DIR の解決順を実装。ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみで継続。
  - utils/process_priority.py
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を実装。
    - Windows / POSIX の差分を吸収し、失敗時は警告してスキップする堅牢性を確保。
- ツール:
  - tools/paper_verification_report.py
    - ペーパートレードログ（SQLite）から稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL 判定を出力する検証レポートスクリプトを追加。
    - デフォルト閾値を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）。
    - --from / --to / --db オプションで期間・DB を指定可能。
- リサーチ:
  - research/factor_research.py を追加（モメンタム等のファクター計算を実装する設計。DuckDB 接続受け取り、prices_daily/raw_financials を参照）。
    - モメンタム（1M/3M/6M）、MA200乖離、ATR、流動性などを計算する方針を記載。※一部実装が未完（ファイル末尾が途中で切れている）。
- DB 初期化ユーティリティ:
  - monitoring/monitoring_db.init_monitoring_db を起動スクリプトから利用（監視テーブルの冪等初期化を保証）。
- その他:
  - scripts/CLI の統一的な使い方とメッセージが整備され、初回設定→検証のワークフローをサポート。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- なし

Removed
- なし

Security
- なし

Known issues / TODOs
- research/factor_research.py が途中で途切れている（関数 calc_momentum の続きが未実装/未コミット）。ファクター計算モジュールは追加済だが、完全実装は今後の作業が必要。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）場合のフォールバック価格使用について TODO コメントあり。将来的に前日終値や取得原価でフォールバックする設計が想定されている。
- apply_sector_cap の "unknown" セクターは現状上限適用対象外。意図的ではあるが運用ルールに応じた見直しが可能。
- ログディレクトリ作成失敗時はファイル出力を行わないが、その旨は標準エラーへ出力される。コンテナ/環境依存で注意が必要。

Upgrade notes
- .env の自動ロードはデフォルトで有効（プロジェクトルート検出に .git または pyproject.toml を使用）。テスト等で自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 本番運用時は KABUSYS_ENV=live を設定する前に validate_config による検証を推奨します。KILL_FLAG_CLEAR_ON_START は本番で 0 を推奨。
- paper_trading と実際の発注 DB は完全に分離される設計（PAPER_TRADING_SQLITE_PATH を利用）。ペーパートレード検証やレポートは専用 DB を指定してください。

Contributing
- 初期リリースのため、機能追加・バグ修正・ドキュメント整備の PR を歓迎します。特に以下を優先して改善してください:
  - research/factor_research の実装完了とテスト
  - position_sizing の価格フォールバック実装
  - CI / ユニットテスト整備（calc_* 関数群、CLI 入出力）

＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝＝
この CHANGELOG はコードの静的解析とソース内コメントから推測して作成しています。実際のコミットログやリリースノートと差分がある可能性がある点をご承知ください。