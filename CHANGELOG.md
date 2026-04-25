CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。  
Semantic Versioning を意識してバージョニングしています。

[Unreleased]
------------

- （現状なし）次リリースに向けた未公開の変更点はありません。

[0.1.0] - 2026-04-25
-------------------

Added
- 実行スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（data/paper_trading.db）を使用する想定（MockBrokerClient を利用）。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) と pid ファイル (data/execution.pid) を扱う制御を追加。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を参照する仕様。
    - 停止フラグ検出による優雅な終了と例外キャッチのループ化。

- 設定関連のユーティリティを追加
  - config.py: 環境変数 / .env 読み込みと Settings クラスを提供。
    - プロジェクトルート自動検出 (.git または pyproject.toml) に基づく .env 自動読み込み（.env.local の上書き対応、OS 環境変数の保護対応）。
    - export KEY=val 形式、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの取り扱いに対応するパーサを実装。
    - 各種設定プロパティを提供（DB パス、PID パス、監視閾値、paper_trading 用パスや fill_mode 等）。
  - config_setup.py: 対話式 .env 作成ウィザードを追加。
    - デフォルト表示、シークレットマスキング、選択肢サポート、.env 保存機能を実装。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、config/*.yaml の存在・パースチェック（PyYAML 未導入時はスキップ）、本番用の追加ガードを実装。
    - --strict オプションにより警告を FAIL 扱いにできる。

- ポートフォリオ構築モジュールを追加（純粋関数群）
  - portfolio/portfolio_builder.py
    - select_candidates: スコア降順で上位 N を選択。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分を提供（スコアが全て 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮し、売却予定銘柄を除外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull/neutral/bear のマッピング、未知レジームでフォールバック）。
  - portfolio/position_sizing.py
    - calc_position_sizes: risk_based / equal / score の各配分方法に基づき株数を計算。単元株丸め、1銘柄上限、aggregate cap（現金上限）に対するスケーリング、残差処理を実装。

- 解析・研究ツール
  - research/factor_research.py: DuckDB 接続を受けるファクター計算モジュールの骨格を追加。モメンタム・移動平均・ATR 等を想定（実装途中の箇所あり）。

- 運用ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを集計し PASS/FAIL 判定を出力。
    - 日付フィルタ、SQLite パス指定の CLI オプションを提供。
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。
    - stdout 出力用 StreamHandler（stdout を使用）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時のフォールバック（ファイル出力を無効化して stdout のみ）を実装。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX (Linux/Mac/FreeBSD) を抽象化して nice 値や優先度クラスを設定。
    - set_cpu_affinity により最初の N コアにピン留めする機能を提供。権限制約時は警告でスキップ。

Changed
- パッケージ初期リリースとしてモジュール構成を確立
  - kabusys/__init__.py にバージョン 0.1.0 とエクスポートモジュールを定義。

Fixed
- 環境変数・設定読み込みの堅牢化
  - .env パーサで export プレフィクス、クォート処理、バックスラッシュエスケープ、インラインコメント等に対応し、環境設定ミスによる読み込み失敗を低減。
- ロギング・ファイル出力の堅牢化
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でもコンソールログで継続するようフォールバックを追加。
- run_monitoring.py / run_execution.py の起動シーケンスで以下を保証
  - プロセス優先度設定を起動直後に実行して安定性を向上。
  - DB 初期化（監視テーブル）の冪等化（init_monitoring_db を呼ぶ）。

Notes / Implementation details
- Database
  - DuckDB は分析用途、SQLite は監視 / 発注履歴用途で使い分ける設計（設定でパスを変更可能）。
  - paper_trading モードでは paper 用 SQLite を使用して本番 DB と完全分離する想定。
- Stop / Kill フラグ
  - 起動スクリプトはプロジェクト data ディレクトリ下の stop_requested.flag を監視して優雅に終了する仕組みを採用。
- ログ
  - ログはデフォルトで logs/<app_name>.log に日次ローテーションで保存（30 日保持）。環境変数 LOG_DIR で変更可能。
- 一部モジュールは今後拡張予定
  - research/factor_research.py は複数ファクターの計算ロジックを想定しているが、ファイル内に実装途中の箇所が存在するため追加実装・テストが必要。

Security
- 初期リリースにおける重要点:
  - .env ファイルは決してリポジトリにコミットしない旨の警告を config_setup の出力に含めています。
  - 本番環境（KABUSYS_ENV=live）用のガード（LINE 通知設定の確認、KILL_FLAG_CLEAR_ON_START の警告）を validate_config で実装。

Acknowledgements
- このリリースは初期機能群のまとめであり、今後ユニットテスト・ドキュメント・追加のエラーハンドリングを強化していく予定です。

--- 

注: 上記 CHANGELOG は提供されたコード内容から推測してまとめたもので、実際のコミット履歴ではありません。実際の履歴を元にした正確な CHANGELOG を希望される場合は、git のコミットログ（git log）や差分を提供してください。