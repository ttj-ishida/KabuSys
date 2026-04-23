CHANGELOG
=========
すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
- (なし)

0.1.0 - 2026-04-23
------------------
初回リリース。KabuSys のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定ツールおよび検証・レポート機能を含みます。

Added
- 実行・監視用エントリスクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
    - BrokerClientFactory を使って実行時にブローカークライアントを生成（paper/live に応じて Mock/実ブローカーを抽象化）。
    - 実行中は execution.pid を出力。プロセス監視用の停止フラグ（data/stop_requested.flag）を検出して安全に停止。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告出力。
    - 監視は環境変数 KABUSYS_ENV にかかわらず常に本番用 sqlite_path（data/monitoring.db デフォルト）を使用する設計。
    - 停止フラグ（data/stop_requested.flag）検出でループを終了。

- 設定管理・初期化ツール
  - config.py
    - 環境変数読み込み・ラップ（Settings クラス）。
    - .env 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - クォートやエスケープ、inline コメント、export プレフィックスに対応した .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロード無効化可能。
    - paper_trading / live / development 等の env 検査、各種パスや閾値をプロパティ化。
  - config_setup.py
    - 対話式ウィザードで .env を作成・更新する CLI。
    - 秘匿項目はマスク表示、デフォルト・選択肢・説明を用意。保存時にテンプレート形式で書き出し（.env を絶対に Git にコミットしない旨を注記）。
  - validate_config.py
    - 起動前チェック CLI。必須環境変数、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在と（PyYAML があれば）パース検証などを実施。
    - --strict オプションで警告を失敗扱い（exit(1)）にできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。
    - stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）によるファイル出力（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR / 引数による優先順位で解決。ログディレクトリ作成失敗時はファイル出力をスキップして警告。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（high/normal/low）を提供。Windows と POSIX（Linux, Darwin, FreeBSD）を吸収。
    - CPU affinity 設定関数 set_cpu_affinity を提供。権限不足や未対応 OS の場合は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - portfolio/portfolio_builder.py
    - 銘柄候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を実装。
    - calc_score_weights は全銘柄のスコアが 0 の場合に等金額配分へフォールバック（警告ログ）。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py
    - 株数決定ロジック calc_position_sizes を実装。
    - allocation_method: "risk_based" / "equal" / "score" をサポート。リスクベース計算（risk_pct, stop_loss_pct）や単元株（lot_size）丸め、1 銘柄上限や aggregate cap（available_cash）に基づくスケーリング、cost_buffer（手数料・スリッページ見積り）の考慮を実装。
    - 端数処理は lot_size 単位で再配分するロジックを持ち、最大上限を超えないよう安全弁を設置。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）からレポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなどを集計。
    - デフォルト判定閾値を定義: 稼働率 >= 99.0%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。複数の SQL クエリで耐障害性を重視（テーブル欠損時は安全に N/A を返す）。
    - 日付フィルタ（--from / --to）と DB パス指定（--db）をサポート。

- リサーチ / ファクター計算（骨格）
  - research/factor_research.py
    - Momentum / Value / Volatility / Liquidity に関する設計および計算関数群の骨格を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する方針）。
    - モメンタム計算関数 calc_momentum の実装を開始（ファイル末尾で途中実装の状態あり）。営業日ベースの計算方針と定数（MA200, ATR など）を定義。

Changed
- パッケージ初期化
  - __init__.py にバージョン 0.1.0 を追加し、主要サブパッケージを __all__ に明示。

Fixed
- 環境読み込みの堅牢性向上
  - .env パーサ: クォート内のバックスラッシュエスケープ、export プレフィックス、インラインコメントの解釈を改善。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップして警告を出すようにして起動時の障害を回避。

Security
- .env 管理に関する注意
  - config_setup で生成される .env ファイルに対して「絶対に Git にコミットしないこと」を明記（秘密情報保護に関する警告）。

Notes / Known issues / TODO
- research/factor_research.py の一部関数は実装途中（ファイル終端が途中で切れている）。完全実装とテストが必要。
- position_sizing や apply_sector_cap は価格欠損（price==0 または None）時の扱いに注意する旨の TODO コメントあり（将来的に前日終値等のフォールバック導入を検討）。
- process_priority や set_cpu_affinity は権限不足や未対応 OS ではスキップされるが、運用上の注意（十分な権限を与えること）が必要。
- run_monitoring は「監視は常に本番 sqlite_path を使用」するため、開発環境で監視用 DB を分離したい場合は設定/コードの調整が必要。

参考
- 環境変数の自動ロード順: OS 環境 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化）
- ログの既定場所: logs/<app_name>.log（デフォルト）、日次ローテーション・30日保持

----- 
訳注: 上記はソースコードの内容から推測して記載した変更履歴です。実際のコミット履歴やリリースノートに合わせて適宜編集してください。