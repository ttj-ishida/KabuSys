CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは "Keep a Changelog" に準拠し、セマンティックバージョニングを採用します。
http://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初版リリース。
- 基本コンポーネントを実装：
  - 環境設定・読み込み・検証
    - Settings クラス（kabusys.config）で環境変数を型変換して提供。KABUSYS_ENV / LOG_LEVEL 等の検証を実装。
    - .env 自動読み込み（プロジェクトルート検出 .git または pyproject.toml を基準）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env パースの堅牢化: export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント処理に対応。
  - 対話式環境設定ウィザード（kabusys.config_setup）
    - .env の初期作成・更新を支援する CLI。各設定項目の説明・デフォルト値・マスク表示（シークレット）機能を提供。
  - 設定検証ツール（kabusys.validate_config）
    - 必須環境変数の存在チェック、KABUSYS_ENV と LOG_LEVEL の妥当性検証、DB パスの親ディレクトリチェック、config/*.yaml の存在および（PyYAML があれば）パース検証、ライブ環境向けガードを実装。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 起動スクリプト
    - 実行エンジン起動スクリプト（kabusys.run_execution）
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite を使用して本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH で上書き可）。
      - ブローカークライアントのファクトリを用いた依存組み立て、ExecutionEngine のデーモンスレッド起動・停止フラグ監視、PID ファイル管理を実装。
    - 監視ループ起動スクリプト（kabusys.run_monitoring）
      - SystemMonitor を用いたポーリングループ。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 監視は環境に関わらず本番 sqlite_path を使用（監視 DB は環境分離しない設計）。
      - 停止フラグ（data/stop_requested.flag）でループ停止。
  - ロギングとプロセス制御ユーティリティ
    - 統一ロギング初期化ユーティリティ（kabusys.utils.logging_setup）
      - stdout へ StreamHandler、日次ローテーションの TimedRotatingFileHandler（デフォルト logs/<app_name>.log）を設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
      - ログレベル・ログディレクトリの解決優先度を明確化。
    - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
      - Windows / POSIX を吸収する実装。psutil を利用し、優先度（high/normal/low）と CPU affinity の設定をサポート。権限不足時は警告を出して安全にスキップ。
  - ポートフォリオ構築ロジック（kabusys.portfolio）
    - 銘柄選定・重み計算（portfolio_builder）
      - select_candidates（スコア降順・タイブレーク）、等金額 / スコア加重の重み計算（calc_equal_weights / calc_score_weights）。全スコアが 0 の場合のフォールバックに警告を出す。
    - セクター集中制限・レジーム乗数（risk_adjustment）
      - apply_sector_cap: 既存保有のセクター別エクスポージャから新規候補を除外するロジック（"unknown" セクターは除外対象外）。
      - calc_regime_multiplier: market regime ("bull","neutral","bear") に応じた投下比率乗数（フォールバック処理と警告）。
    - 株数決定・リスク制限・単元丸め（position_sizing）
      - allocation_method="risk_based"/"equal"/"score" をサポート。stop_loss_pct, risk_pct によるリスクベース計算、lot_size による単元丸め、aggregate cap（available_cash を超える場合のスケーリングと再配分アルゴリズム）を実装。
  - Paper Trading 検証ツール（kabusys.tools.paper_verification_report）
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（P95）等を算出して PASS/FAIL 判定を出力。
    - デフォルト閾値を設定（稼働率 99% / 成功率 90% / 送信率 95% / P95 レイテンシ 200ms）。
  - 研究用ファクター計算スケルトン（kabusys.research.factor_research）
    - DuckDB を用いたファクター計算の設計と一部定数・インターフェースを実装（Momentum / Value / Volatility / Liquidity を想定）。calc_momentum の初期構成が含まれる（未完の可能性あり）。
  - パッケージメタ
    - __version__ を 0.1.0 に設定。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Security
- シークレット値（J-Quants トークン、Kabu API パスワード、LINE トークン）は .env に保存する前提。config_setup は .env を Git にコミットしないよう注意文を出力。

Notes / Implementation details
- 環境ファイルの読み込みルール:
  - 優先順位: OS 環境 > .env.local > .env
  - OS 環境変数は保護され、.env.local の override オプションでも上書きされない。
- 実行時停止制御:
  - data/stop_requested.flag（監視・実行）および data/execution.pid（ExecutionEngine の PID）を用いる設計。
- DB の扱い:
  - monitoring（監視）用 DB は settings.sqlite_path で指定された SQLite を使用。
  - Paper Trading は settings.paper_sqlite_path（デフォルト data/paper_trading.db）で本番 DB と分離。
  - DuckDB は分析用に settings.duckdb_path を使用。
- ログ:
  - stdout に出力するためデフォルトで StreamHandler は stdout を使用（cron 等で stdout/stderr をリダイレクトする運用を想定）。
  - 日次ローテーション・30世代保持。

Breaking Changes
- なし（初回リリース）

Acknowledgements / Future work
- factor_research など一部モジュールは今後の実装拡張を予定（ファクター計算ロジックの完成、strategy/execution の詳細アルゴリズム拡張など）。
- position_sizing の lot_size を銘柄別対応にする等、将来的な拡張を検討中（TODO コメントあり）。

--- 
（この CHANGELOG はコードベースから推測して自動生成しています。実際の開発履歴やコミットログに基づく公式な変更履歴は別途ご用意ください。）