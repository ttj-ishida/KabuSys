CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従います。  
フォーマットの詳細: https://keepachangelog.com/（日本語訳を意訳して記載）

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
--------------------

Added
-----
- 初期リリースを追加。
- 環境設定および管理
  - .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動ロード。
    - .env パースは export 形式・クォート・インラインコメント等に対応。
    - OS 環境変数を保護して .env.local の上書きを制御。
  - Settings クラスを提供し、環境変数経由で設定値を安全に取得（各種パス、API トークン、しきい値、環境種別など）。
  - 対話式環境設定ウィザードを実装（src/kabusys/config_setup.py）。
    - .env の初期生成・更新を支援する CLI（python -m kabusys.config_setup）。
    - J-Quants / kabuステーション / DB パス / ログレベル / Kill Switch 周りの項目を対話入力で設定可能。
- 設定検証ツール
  - 設定チェック CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 検証、DB パスの存在/親ディレクトリチェック、config/*.yaml の存在およびパース検証（PyYAML が利用可能な場合）。
    - --strict オプションで警告を fail 扱いにできる。
    - CLI エントリポイント: python -m kabusys.validate_config
- 実行用スクリプト
  - ExecutionEngine 起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合、paper 用専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し本番 DB と分離。
    - BrokerClientFactory によりランタイムで適切なブローカークライアントを生成（モック/実ブローカーを選択）。
    - ExecutionEngine をスレッドで実行、停止フラグ（data/stop_requested.flag）を検知して安全に停止。PID ファイル管理。
  - SystemMonitor 起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に依らず production の sqlite_path を使用して記録（監視 DB の初期化を保証）。
    - 停止フラグ検知でループを終了。
- 監視 DB 初期化呼び出し
  - init_monitoring_db を呼び出して監視用テーブル群の存在を保証（実行/監視の両スクリプトで冪等に実行）。
- ロギングユーティリティ
  - 統一ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler を stdout にセット（cron/タスクランナーからのリダイレクト対策）。
    - TimedRotatingFileHandler を日次ローテーションで追加（デフォルト logs/、30 日分保持）。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - ログレベル・ログディレクトリの解決順を明確化（引数 > 環境変数 > デフォルト）。
- プロセス優先度・CPU 固定ユーティリティ
  - psutil を用いた set_process_priority / set_cpu_affinity を提供（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収。権限不足などは警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - 銘柄選定・ウェイト計算（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates（スコア降順・タイブレーク）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap（既存保有比率を基に新規候補を除外）、calc_regime_multiplier（bull/neutral/bear マッピング、未知値はフォールバック）。
    - apply_sector_cap は "unknown" セクターは上限適用除外という挙動。
  - 株数決定・丸めロジック（src/kabusys/portfolio/position_sizing.py）。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率（risk_pct）と stop_loss_pct からベース株数を算出、単元株（lot_size）丸め。
    - aggregate cap（available_cash）超過時はスケーリングして再配分（残差を考慮して単元株単位で補正）。
    - cost_buffer により手数料・スリッページを保守的に見積もる。
    - TODO コメントで将来の銘柄別 lot_size 対応などを明記。
- リサーチ / ファクター計算
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（1M/3M/6M、MA200 乖離）、Volatility、Liquidity、Value 等の計算を想定した設計。DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算する方針。
    - ファイルに計算定数や calc_momentum の骨組みを実装（途中まで実装）。
- ツール
  - Paper Trading 検証レポート作成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み取り、システム稼働率、注文成功率、送信率、P95 レイテンシなどを集計し PASS/FAIL 判定を行う。
    - デフォルトの判定閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義。
- パッケージメタ
  - パッケージ初期バージョンを設定（src/kabusys/__init__.py: __version__ = "0.1.0"）。
  - パッケージエクスポートの整理（portfolio パッケージ __all__ を定義）。

Changed
-------
-（初回リリースのため履歴なし）

Fixed
-----
-（初回リリースのため履歴なし）

Deprecated
----------
-（初回リリースのため履歴なし）

Removed
-------
-（初回リリースのため履歴なし）

Security
--------
- （特記事項なし。環境ファイルは Git にコミットしない旨を config_setup の注記に明記）

Notes / Known limitations
-------------------------
- src/kabusys/research/factor_research.py は計算方針と一部関数の実装（calc_momentum の骨組み）を含みますが、ファイル末尾が途中で終わっており完全実装ではありません。今後のリリースで完成させる予定です。
- position_sizing, apply_sector_cap での価格欠損（価格 0.0 や未取得時）の扱いに TODO コメントあり。将来的に前日終値などフォールバック手段を導入することを推奨します。
- process_priority / set_cpu_affinity は権限や OS に依存するため、実行環境によっては期待通りの効果が得られないことがあります（現状は失敗時に警告を出してスキップする設計）。
- .env の自動ロードはプロジェクトルートが検出できない場合はスキップされます（配布環境やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能）。

Acknowledgements
----------------
- 本プロジェクトはローカル開発・ペーパートレード・本番（live）の運用モードを想定して設計されています。設定管理・ログ・プロセス制御・DB 分離・安全停止といった運用面の配慮を優先して実装しています。

--------------------------------
（注）本 CHANGELOG は提供されたコードの内容から推測して作成しています。実際のリリースノートやリリース日付はリポジトリの運用ポリシーに従って調整してください。