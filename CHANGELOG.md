KEEP A CHANGELOG
すべての変更は Keep a Changelog の規約に従って記載します。
リリースの日付はコードベースから推測した最新開発日（2026-04-20）を使用しています。

v0.1.0 - 2026-04-20
===================

Added
-----
- 基本アプリケーション情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py: __version__ = "0.1.0"）。

- 起動スクリプト / ランタイム
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と分離する設計。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立てを行い、Engine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）を監視し、検知時にエンジン停止処理を実行。
    - 実行 PID を data/execution.pid に書き込む想定（設定経由）。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバックし、ログ出力。
    - 停止フラグ（data/stop_requested.flag）を検知してループを終了。
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する（監視データは共通 DB 想定）。

- 環境設定 / 検証ツール
  - config.py
    - プロジェクトルート自動探索（.git または pyproject.toml を基準）に基づく .env 自動ロード機能を実装。
    - .env / .env.local の読み込み順序・上書きルール（OS 環境変数を保護）を実装。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - Settings クラスを実装し、アプリケーション設定（J-Quants / kabu / DB パス / 監視閾値 / 環境モード等）をプロパティで安全に取得できるようにした。
    - paper_trading 用設定（paper_sqlite_path、paper_fill_mode の検証）をサポート。

  - config_setup.py
    - ユーザ対話式の .env 作成・更新ウィザードを実装。
    - 入力の補助（デフォルト・選択肢・シークレットマスク等）や既存 .env の読み込み・上書きに対応。
    - .env 出力フォーマットと注意書きを自動生成。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の存在・基本整合性を検証する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、ログレベルの検証、DB パスの親ディレクトリ確認、YAML のパースチェック（PyYAML の有無に応じてスキップ）を実施。
    - --strict オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - 銘柄選定（select_candidates）：スコア降順・同点時 signal_rank によるタイブレーク。
    - 等金額配分（calc_equal_weights）。
    - スコア加重配分（calc_score_weights）：全スコアが 0 の場合は等金額にフォールバックし警告を出す。

  - portfolio/risk_adjustment.py
    - セクター集中制限（apply_sector_cap）：既存保有と当日売却予定を考慮し、セクター上限を超える場合は候補から除外。
    - レジームに応じた投下資金乗数（calc_regime_multiplier）：'bull'/'neutral'/'bear' をマッピングし、未知レジームは 1.0 にフォールバック（警告ログ）。

  - portfolio/position_sizing.py
    - ポジションサイズ計算（calc_position_sizes）
      - allocation_method: "risk_based" / "equal" / "score" をサポート。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash に合わせたスケールダウン）、cost_buffer（手数料/スリッページ見積）を実装。
      - 利用可能現金に合わせたスケール配分時に端数処理（lot 単位の残差補正）を実装。

  - portfolio/__init__.py にて上記関数群をエクスポート。

- 研究 / ファクター計算（下地）
  - research/factor_research.py
    - Momentum, Value, Volatility, Liquidity といったファクター設計に関するモジュールの骨組みを追加。
    - DuckDB 接続を想定し prices_daily / raw_financials テーブルを参照して計算する設計（関数インターフェイスと定数は定義）。
    - 注: calc_momentum 関数の実装途中（ファイルが途中で切れているため、未完成部分あり）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI を追加。
    - 稼働率、注文成功率（fill_rate）、送信率（send_rate）、リスク却下数、レイテンシ（avg/max/P95）を集計し PASS/FAIL 判定を行う。
    - 閾値（稼働率 99% など）や P95 算出ロジックを実装。
    - 引数で期間指定（--from/--to）・DB パス指定（--db）可能。環境変数 PAPER_TRADING_SQLITE_PATH にも対応。

- 共通ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定するユーティリティを実装。
    - ログレベル・ログディレクトリ解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。

  - utils/process_priority.py
    - set_process_priority(level) を提供し、Windows（psutil の優先度定数）・POSIX（nice 値）を透過的に扱う。失敗時は警告ログでスキップ。
    - set_cpu_affinity(cpu_count) を実装し、最初の N コアにプロセスをピン留め可能（失敗時は警告ログ）。

Changed
-------
- なし（初期公開）。

Fixed
-----
- なし（初期公開）。

Deprecated
----------
- なし。

Removed
-------
- なし。

Security
--------
- なし特記。

Known issues / Notes
-------------------
- research/factor_research.py の calc_momentum の実装が途中で切れており、完全実装は今後の作業を要します（現段階では設計と定数が定義されているのみ）。
- apply_sector_cap 内の価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過小見積りされる可能性）について TODO コメントが残っています。将来的にフォールバック価格導入を検討。
- .env の読み書き・自動ロードは強力ですが、機密情報の管理（Git へのコミット防止など）に注意してください。.env はデフォルトでコミットしない運用を推奨します（config_setup.py に警告あり）。
- run_execution / run_monitoring は stop flag / pid file をファイルシステムに依存しているため、コンテナ運用や異なるデプロイ方式ではファイルパスの調整が必要です（Settings のプロパティで上書き可能）。

今後の予定（短期）
-----------------
- research モジュールの未完成部分の実装完了（ファクター計算の SQL 実装・テスト）。
- ExecutionEngine / SystemMonitor 周辺の統合テストとエンドツーエンド検証。
- 個別銘柄ごとの lot_size 対応（stocks マスタの導入）および手数料/スリッページ見積りモデルの改善。
- モニタリング・アラート（LINE 通知等）実装の拡張（validate_config の警告に基づく保護強化）。

---

以上がこのコードベースから推測できる初回リリース（v0.1.0）の変更履歴です。必要であれば、リリースノートを英語版で出力したり、より粒度の細かいセクション（例: CLI の使用例、環境変数一覧）を追記できます。どのようにまとめ直しましょうか？