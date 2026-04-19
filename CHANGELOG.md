CHANGELOG
=========

すべての注目すべき変更を時系列で記録します（Keep a Changelog 準拠）。
このファイルは、コードベースの内容から推測して作成しています。

[Unreleased]
------------

- （なし）

0.1.0 - 2026-04-19
-----------------

Added
- 初回リリース。主要な機能群を追加。
  - 起動スクリプト / デーモン機能
    - `src/kabusys/run_monitoring.py`
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
      - 停止フラグファイル (`data/stop_requested.flag`) を監視して安全にループを終了する仕組みを実装。
      - 監視は常に本番用の `sqlite_path` を使用する仕様。
    - `src/kabusys/run_execution.py`
      - ExecutionEngine 起動スクリプトを追加。
      - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、Paper Trading 用 DB (`data/paper_trading.db` など) に記録して本番 DB と分離。
      - ストップフラグと PID ファイル (`data/execution.pid`) を扱うロジックを実装。
      - エンジンを別スレッドで実行し、停止フラグ検知で安全に停止させる仕組み。

  - 環境設定まわり
    - `src/kabusys/config.py`
      - 環境変数・設定取得用の `Settings` クラスを追加。
      - 自動 `.env` ロード（プロジェクトルート検出：`.git` または `pyproject.toml` を基準）。ロード順: OS 環境 > `.env.local` > `.env`、`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - `.env` の行パーサは `export KEY=...`、クォート、インラインコメント等に対応。
      - 各種設定（DB パス、API トークン、Paper Trading モード、監視閾値、ログレベル等）をプロパティとして提供し、値検証を行う。
    - `src/kabusys/config_setup.py`
      - 対話式ウィザードで `.env` を作成/更新する CLI を追加。
      - シークレットのマスク表示、選択肢、デフォルト値、保存前確認を実装。
    - `src/kabusys/validate_config.py`
      - 起動前に `.env` と `config/*.yaml` を検証する CLI を追加。
      - 必須環境変数チェック、`KABUSYS_ENV` / `LOG_LEVEL` 等の妥当性チェック、DB パスの親ディレクトリ確認、YAML パース（PyYAML が無ければスキップ）を実施。
      - `--strict` オプションで警告を FAIL 扱いにする機能を追加。

  - ポートフォリオ構築関連（純粋関数）
    - `src/kabusys/portfolio/portfolio_builder.py`
      - 候補選定（スコア降順・タイブレーク）、等金額配分、スコア加重配分を実装。スコア全てが 0 の場合は等分にフォールバック。
    - `src/kabusys/portfolio/risk_adjustment.py`
      - セクター集中制限（既存ポジションを考慮し、上限を超えるセクターの新規候補を除外）と市場レジームに応じた資金乗数（bull/neutral/bear）を実装。
      - 未知のレジームに対するフォールバック (1.0) とログ警告を追加。
    - `src/kabusys/portfolio/position_sizing.py`
      - 複数の配分方式 (`risk_based`, `equal`, `score`) に対応した発注株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケーリング）、cost_buffer を考慮した保守的見積りと再配分ロジックを実装。

  - 監視・実行共通ユーティリティ
    - `src/kabusys/utils/logging_setup.py`
      - ルートロガーに対する統一ロギング初期化ユーティリティを追加。Console (stdout) と日次ローテートファイル（TimedRotatingFileHandler）を設定。既存ハンドラの重複を防止するため一度クリアする。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - `src/kabusys/utils/process_priority.py`
      - クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定を追加。
      - `set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を実装。権限不足などは安全にスキップして警告。
    - `src/kabusys/__init__.py`
      - パッケージ情報とバージョン (`__version__ = "0.1.0"`) を追加。

  - 分析 / 検証ツール
    - `src/kabusys/tools/paper_verification_report.py`
      - Paper Trading 用 SQLite DB を解析し、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などの指標を算出してレポート表示する CLI を追加。
      - デフォルトの閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を提供し、Pass/Fail 判定を行う。
      - 日付フィルタ（--from/--to）や DB パス指定（--db）に対応。DB が存在しない場合のエラーメッセージを実装。

  - 研究モジュール（骨格）
    - `src/kabusys/research/factor_research.py`
      - DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、移動平均乖離、ATR、流動性等の計算方針と定数を定義）。
      - 実装途中の関数（例: calc_momentum の実装が途中で開始されている）を含む。

Changed
- n/a（初回リリースのため履歴なし）

Fixed
- n/a（初回リリースのため履歴なし）

Security
- 環境変数取り扱いの注意点と `.env` を Git にコミットしない旨を `config_setup` の出力で明記。

Notes / Implementation details（推測）
- DB 周りでは SQLite（監視 DB / paper_trading DB）と分析向け DuckDB を併用する設計。
- 実行系（ExecutionEngine）はブローカークライアント、オーダーマネージャ、リスクマネージャ、レコンシリエーション等のコンポーネントを組み立てて稼働させる前提（`BrokerClientFactory` 等の実装を参照）。
- 環境依存の挙動（本番/ペーパートレードやログ保存先など）は `Settings` で集中管理。
- 多くの箇所で安全なフォールバック（存在しないファイルの無視、権限不足のログ警告、データ不足時の N/A 表示など）が採用されている。

ライセンス・貢献
- 本 CHANGELOG はコードの内容から推測して作成しています。実際の変更履歴やリリースノートと差分がある場合は、正確な履歴に合わせて更新してください。