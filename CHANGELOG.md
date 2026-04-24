# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
重大な変更点・追加機能・バグ修正などをコードベースから推測してまとめました。

注意: 日付はリリース想定日です。実際のコミット履歴に基づくものではありません。

## [Unreleased]

- DOCS: ドキュメントや README を通じた補足（未リリースの改善案・TODO の整理）
- PERF: research/factor_research.py のファクター計算実装の続き（追加最適化予定）
- TEST: 単体テスト・統合テストの整備（未完）

---

## [0.1.0] - 2026-04-24

Added
- 起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV による paper_trading モード判定を行い、paper_trading の場合は専用の SQLite（既定: data/paper_trading.db）を使用することで本番 DB と分離。
  - run_monitoring.py: SystemMonitor のポーリングループを起動。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔を上書き可能。停止フラグ（data/stop_requested.flag）検知で安全に終了する。
- 設定管理・ウィザード・検証ツールを追加
  - config.py: 環境変数の読み込み・解釈を行う Settings クラスを実装。自動 .env ロード（.env / .env.local）機能、KABUSYS_DISABLE_AUTO_ENV_LOAD による抑止、PAPER_FILL_MODE や env/log レベル等の検証を含む。
  - config_setup.py: 対話式ウィザードで .env を生成・更新する CLI。シークレット入力のマスク表示、デフォルト値・選択肢をサポート。
  - validate_config.py: 起動前チェック用 CLI。必須環境変数・パス・config/*.yaml の存在・YAML パース（PyYAML があれば）を検証。--strict オプションで警告を FAIL 扱いにできる。
- portfolio 関連の純粋関数群を追加（DB 参照なし、メモリ計算）
  - portfolio/portfolio_builder.py: シグナル選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）、市場レジームに応じた資金乗数（calc_regime_multiplier）。
  - portfolio/position_sizing.py: 発注株数計算（calc_position_sizes）。ロット単位丸め、リスクベース・等配分・スコア配分、aggregate cap（利用可能現金でスケールダウン）など。
- utils：運用ユーティリティを追加
  - utils/logging_setup.py: 共通ロギング設定ユーティリティ。stdout ストリームハンドラ + 日次ローテーション（TimedRotatingFileHandler、30 日保持）をルートロガーに設定。LOG_DIR 環境変数や引数でログ出力先・レベルを上書き可能。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
  - utils/process_priority.py: プロセス優先度（nice / Windows priority）と CPU affinity を設定するユーティリティ。プラットフォーム差異を吸収し、安全にフォールバックして警告を出力する。
- monitoring/initialization
  - monitoring.monitoring_db.init_monitoring_db を各起動スクリプトから呼び出し、監視用テーブルが存在することを保証（冪等）。
  - SystemMonitor を利用した監視ループを実装（run_monitoring から起動）。
- tools
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成ツール。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計して PASS/FAIL を判定する。
    - デフォルト閾値: 稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - P95 計算、期間フィルタ（--from / --to）、DB ポイント指定（--db / 環境変数）をサポート。
- research/factor_research.py（初期実装）
  - DuckDB を用いたファクター計算モジュール（モメンタム、MA200 乖離、ATR 等の設計・骨格実装）。prices_daily / raw_financials を前提に計算を行う設計。

Changed
- 起動時のプロセス優先度を明示的に High に設定するようにした（run_execution / run_monitoring の起動直後）。
- logging_setup: stderr ではなく stdout を StreamHandler に使用（cron / Task Scheduler などのリダイレクトを想定）。
- config.py: .env の自動ロード順序を OS 環境 > .env.local > .env に明確化。既存 OS 環境変数は上書き保護。
- config_setup.py: 生成される .env にヘッダ / コメントを付与し、「.env を絶対に Git にコミットしないこと」を明記。
- position_sizing: aggregate cap のスケールダウンロジックを導入。cost_buffer（手数料・スリッページ想定）を考慮して安全側に見積る。

Fixed
- run_monitoring._get_poll_interval(): MONITOR_POLL_INTERVAL のパースエラーや 0 以下の値に対して警告を出し、安全にデフォルト値へフォールバックするよう修正。
- .env パーサ（config._parse_env_line）:
  - export KEY=val 形式をサポート。
  - シングル/ダブルクォート内のバックスラッシュエスケープに対応。
  - 非クォート値における inline コメントの解釈を改善（# の直前がスペース/タブのみコメント扱い）。
- logging_setup: ログディレクトリ作成に失敗した場合でもプロセスが継続するように修正し、失敗時はファイルハンドラを追加せずコンソール出力にフォールバックするようにした。
- process_priority: 未対応 OS や権限不足時に例外で落ちないようキャッチして警告に置き換え。

Security
- .env ウィザードと .env 書き込み時にシークレット値（API トークン等）をマスクして表示するようにし、.env の誤コミットリスクに関する注意書きを追加。

Notes / その他（実装上の設計判断）
- Paper Trading と本番（live）は DB を分離（paper_sqlite_path）しているため、ペーパートレードの履歴・検証が本番データに混在しない設計になっている。
- SystemMonitor は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する仕様（監視は本番 DB を利用する方針）。
- apply_sector_cap は sector_map に存在しない銘柄を "unknown" 扱いとしてセクター上限の対象外にする（未知セクターは除外しない）。
- calc_regime_multiplier は未知のレジームに対して 1.0 でフォールバックし警告を出す。
- calc_position_sizes は lot_size（単元株）で丸め、利用可能現金を超える場合は銘柄ごとにスケールダウンして残余を再配分するロジックを実装。

---

## 既知の制約・今後の TODO
- research/factor_research.py の一部（calc_momentum 等）は骨格実装レベルで、フルテスト／最適化が必要。
- price の欠損（0.0）の扱いに関する注記がいくつか残っており、フォールバック価格（前日終値や取得原価）の導入を検討。
- 将来的な拡張として、銘柄ごとの lot_size を stocks マスタで管理する設計に変更予定（現在はグローバル lot_size）。
- 現在のロギングは日次ローテート 30 日保持だが、運用に合わせて圧縮・長期保存ポリシーの追加を検討。

---

以上。必要であれば各項目をコミット単位で分解した詳細な変更点（ファイル別 diff 想定）や、リリースノート英文版を作成します。どの粒度で出力しますか？