CHANGELOG
=========

すべての項目は Keep a Changelog 準拠の形式で記載しています。

[0.1.0] - 2026-04-19
-------------------

追加 (Added)
- 初期リリース: KabuSys ベースモジュール群を追加。
  - パッケージ全体のバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0"
- 起動スクリプト:
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に完全分離して記録。
- 設定関連:
  - config.py: 環境変数/ .env 自動読み込み機能と Settings クラスを追加。プロジェクトルート探索ロジック（.git / pyproject.toml）を実装。各種設定（データベースパス、PID/kill flag パス、監視閾値、PAPER_FILL_MODE 検証 など）をプロパティとして提供。
  - config_setup.py: 対話式 .env ウィザードを追加（既存値の読み込み、シークレットマスク、書き込み機能）。
  - validate_config.py: 起動前設定検証 CLI を追加（必須環境変数・パス・YAML の存在/パース・本番環境用ガード等のチェック）。--strict モードあり。
- ポートフォリオ構築:
  - portfolio/portfolio_builder.py: 候補銘柄選定、等金額/スコア加重の重み計算関数を追加（select_candidates, calc_equal_weights, calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに応じた資金乗数 calc_regime_multiplier を追加（unknown セクターの挙動やフォールバックロジックを記載）。
  - portfolio/position_sizing.py: 単元株丸め、リスクベース/等分配方式の株数決定ロジックを実装。aggregate cap のスケールダウンおよび残差配分ロジックを含む。
- ユーティリティ:
  - utils/logging_setup.py: 統一的なロギング設定ユーティリティを追加。stdout ストリームハンドラと日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ自動作成のフォールバックあり。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定、CPU affinity 設定ユーティリティを追加。権限不足時は警告を出してスキップ。
- 分析・レポート:
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL 判定を行う。PAPER_TRADING_SQLITE_PATH 環境変数または --db オプションで DB を指定可能。
- 監視DB 初期化:
  - monitoring.monitoring_db モジュール経由で監視テーブルの冪等な初期化処理を呼び出すコードを run_monitoring / run_execution に追加。
- 分析基盤:
  - DuckDB を分析用に利用（Settings.duckdb_path により指定）。複数コンポーネントで duckdb 接続を受け取る設計。

変更 (Changed)
- デフォルト/安全設定:
  - .env 自動読み込みの挙動: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。自動ロードはプロジェクトルートが検出できない場合はスキップ。
  - ログ出力は標準出力 (stdout) を使用し、ファイル出力に失敗した場合はコンソール出力のみで継続するよう堅牢化。
- CLI/起動フロー:
  - 起動時に最初にプロセス優先度を "high" に設定する呼び出しを追加（run_monitoring.py, run_execution.py）。
  - run_execution は paper_trading 環境時に paper 用 SQLite を使用し、本番 DB と完全分離するよう変更（Settings.is_paper 判定）。
- .env パーサ:
  - export プレフィックス、クォート（シングル/ダブル）内でのバックスラッシュエスケープ、インラインコメント処理など実務的な .env 文法に対応する堅牢なパーサを実装（config._parse_env_line）。

修正 (Fixed)
- 環境変数検証/バリデーション:
  - Settings 側で KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE の値検証を実装し、不正値時に ValueError を投げるようにして早期検出を強化。
- 実行エンジン停止制御:
  - 停止フラグファイル (data/stop_requested.flag) を監視して安全に監視ループ・実行エンジンを終了するロジックを追加。
- Paper レポート:
  - P95 計算の実装と、データ不足時に N/A を返す堅牢なハンドリングを追加。DB が存在しない場合のユーザ向けエラーメッセージを改善。

セキュリティ (Security)
- .env ファイル生成時にシークレット項目（J-Quants トークン、kabu API パスワード）をマスク表示し、.env を絶対に Git にコミットしない旨の警告コメントをファイルへ埋め込む。

既知の問題 / 注意点 (Known Issues / Notes)
- factor_research.py はファイル末尾で途中（calc_momentum の先頭で途切れ）となっており、ファクター計算ロジックの一部が未実装/未完です。将来的に続きの実装が必要。
- position_sizing の price の欠損（0.0）時に exposure が過少に見積もられる点は TODO コメントで指摘しており、フォールバック価格（前日終値や取得原価等）を導入する計画あり。
- process_priority / set_cpu_affinity は権限や OS に依存するため、権限不足時は設定がスキップされる（警告出力）。運用環境での確認を推奨。
- validate_config は PyYAML 未導入時に YAML 内容検証をスキップする（警告）。YAML の構文チェックを必須にしたい場合は PyYAML を追加導入してください。
- .env 自動読み込みはプロジェクトルート探索に依存するため、配布後や特殊なインストールパターンでは期待通り動作しない可能性がある。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定し、明示的に環境変数をセットしてください。

開発者向けメモ
- run_monitoring / run_execution はどちらも起動時にロギングを統一的にセットアップし、ログディレクトリの作成に失敗してもコンソール出力にフォールバックします。
- Paper Trading は本番 DB と完全分離される設計になっているため、ペーパートレードデータを本番 DB に混在させない運用が可能です。
- ログローテーションは日次・30世代保持。ログファイル名は <LOG_DIR>/<app_name>.log（デフォルト logs/）。

署名
- 初期リリース: KabuSys チーム

（今後のリリースでは、factor_research の完成、戦略パイプライン・バックテスト・ユニットテストの強化、さらに細かな監視アラート/LINE 通知等の改善を予定しています。）