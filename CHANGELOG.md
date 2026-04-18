# Changelog

すべての notable な変更は Keep a Changelog の方針に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

全ての日時はコミット日等から推測しています（初回リリース相当のまとめです）。

## [Unreleased]

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本パッケージ初期実装を追加。
  - パッケージメタ情報: `kabusys.__version__ == "0.1.0"` を設定。
- 実行系スクリプト
  - run_execution.py: ExecutionEngine を起動するためのエントリポイントを追加。
    - KABUSYS_ENV に応じて本番／ペーパートレードの SQLite を切り替え（ペーパートレードは `data/paper_trading.db` に分離）。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をバックグラウンドスレッドで実行。
    - 停止フラグ(`data/stop_requested.flag`)検出時に安全に停止。
    - 実行 PID ファイル書き込み機構（`data/execution.pid`）の利用を想定。
    - RiskManager のデフォルト構成（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
- 監視系スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して起動する挙動を実装。
    - 停止フラグを検出するとループを終了。
- 設定管理
  - config.py: 環境変数 / .env 自動読み込み・パースロジックを実装。
    - プロジェクトルート自動検出（.git または pyproject.toml を基準）による .env/.env.local のロード。
    - 複雑な .env の行パースに対応（export プレフィックス、引用符、エスケープ、インラインコメント等）。
    - Settings クラスを実装し、各種設定（API トークン、DB パス、Paper Trading 設定、監視閾値、環境判定など）をプロパティとして提供。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` により自動ロードを無効化可能。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式 .env 設定ウィザードを実装。
    - 初期 .env 生成・更新をサポート。シークレットはマスク表示。
  - validate_config.py: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パス確認、config/*.yaml 存在・パース検証（PyYAML があればパースまで）、本番環境向けガードチェックを実施。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / 実行環境ユーティリティ
  - utils/logging_setup.py: 統一ログ設定ユーティリティを実装。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler、30日保持）のファイル出力をルートロガーに設定。
    - ログレベル/ログディレクトリは引数・環境変数で解決。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - utils/process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを実装。
    - Windows / POSIX の差分を吸収。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にスキップ。
- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等金額にフォールバックする挙動を追加（WARNING ログ出力）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限の適用 (apply_sector_cap) を実装（当日売却予定の銘柄は除外可能）。
    - 市場レジームに応じた乗数 (calc_regime_multiplier) を実装（"bull"/"neutral"/"bear" をサポート、未知レジームは 1.0 でフォールバック）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - lot_size（単元）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ想定）を考慮したスケーリング処理を実装。
    - aggregate cap 超過時のスケールダウンと端数配分ロジック（残余キャッシュを用いて lot 単位で再配分）を実装。
- Research / ファクター計算（骨格）
  - research/factor_research.py: Momentum などのファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily, raw_financials を参照して計算する方針）。
    - モメンタムや移動平均、ATR 等の計算方針と定数を定義。関数骨格（calc_momentum 等）を設けている（将来的に SQL/duckdb を使った実装を続行予定）。
- ツール群
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成ツールを追加。
    - 指定期間の稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均・最大・P95）等を集計してテキストレポートを出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づく PASS/FAIL 判定を行う。
    - DB パスは引数 `--db` > 環境変数 `PAPER_TRADING_SQLITE_PATH` > デフォルトの順で解決。

### 変更 (Changed)
- なし（初回公開のため主に追加項目のみ）。

### 修正 (Fixed)
- なし（初回公開のため特定のバグ修正履歴は無し）。

### セキュリティ (Security)
- なし特記事項。ただし `.env` を絶対にリポジトリへコミットしない旨を config_setup の出力に明記。

### 既知の制約・注意点 (Notes / Known issues)
- research/factor_research.py の一部関数は実装が途中で終わっている（calc_momentum の実装が未完）。今後の実装継続が必要。
- portfolio/risk_adjustment.apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされ、ブロックが外れる可能性がある旨の TODO コメントが存在。将来的にフォールバック価格（前日終値等）の導入を検討する必要あり。
- process_priority と CPU affinity の設定は権限依存で失敗することがある。失敗時は警告ログを出してスキップする挙動で安全側に寄せている。
- logging_setup はログディレクトリ作成に失敗した場合、ファイル出力を無効化して stdout のみで継続する。運用環境では書き込み権限・ディレクトリ存在を事前に確認してください。
- run_monitoring は監視用 DB を環境にかかわらず本番 sqlite_path を使用する設計となっているため、テスト用途では監視 DB のパスに注意が必要。

---

今後の予定（例）
- factor_research の完成と DuckDB を使った完全実装。
- ExecutionEngine / SystemMonitor のユニットテスト充実化。
- 各種構成のドキュメント化（PortfolioConstruction.md 等に準拠した具体的なパラメータ説明）。
- ペーパートレードと本番のさらなる分離（ログや監視テーブルの明確化）。

(END)