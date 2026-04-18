# Changelog

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

注意: この CHANGELOG はコードベースから推測して作成しています。実装上の詳細や未完成の箇所については "既知の問題 / TODO" セクションを参照してください。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- プロジェクト初期リリース相当の機能群を追加。
- 環境設定・管理
  - Settings クラス（kabusys.config）を追加。
    - 環境変数や .env/.env.local から設定を読み込む自動ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースでクォート文字・エスケープ・`export KEY=val` 形式・インラインコメント等に対応する堅牢なパーサを実装。
    - 各種設定プロパティ（J-Quants / kabu API / DB パス / paper trading の挙動フラグ / 監視閾値 / 実行環境判定など）を提供。
  - 設定ウィザード CLI（kabusys.config_setup）
    - 対話式で .env を作成・更新するウィザードを追加。
    - 保存前の確認、シークレット値のマスク表示、デフォルト値・選択肢対応などを実装。
  - 設定検証 CLI（kabusys.validate_config）
    - 起動前に .env および config/*.yaml の存在や基本的な妥当性をチェックするツールを追加。
    - --strict オプションで警告を FAIL 扱いにできる。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）
    - 環境（KABUSYS_ENV）に応じて Paper Trading 用 DB を分離（data/paper_trading.db をデフォルト）し、MockBroker を使用する仕組みをサポート。
    - プロセス優先度を高（High）に設定して起動する処理を導入。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）を用いた安全な起動/停止制御を実装。
    - ExecutionEngine 起動前に監視テーブルの初期化を保証（冪等な init_monitoring_db 呼び出し）。
  - SystemMonitor ポーリングループ起動スクリプト（kabusys.run_monitoring）
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60 秒）。
    - 停止フラグ検出で安全にループを終了。例外はロギングして次サイクルへ継続。
    - Monitoring は環境にかかわらず本番 sqlite_path（監視 DB）を使用する仕様。

- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ（kabusys.utils.logging_setup）
    - StreamHandler（stdout）および TimedRotatingFileHandler（日次・30世代保持）をルートロガーに設定。
    - ログディレクトリ自動作成と失敗時のフォールバック（コンソールのみ）に対応。
    - ログレベル解決ロジック（引数 > 環境変数 > デフォルト）を実装。
  - プロセス優先度 / CPU affinity 設定ユーティリティ（kabusys.utils.process_priority）
    - Windows / POSIX(Linux, macOS 等) を吸収した set_process_priority, set_cpu_affinity を提供。
    - 権限不足や未サポート環境では警告ログを出して安全にスキップする実装。

- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 銘柄選定・重み計算（portfolio_builder）
    - select_candidates, calc_equal_weights, calc_score_weights を実装（スコアによるソート、フォールバックロジック含む）。
  - リスク制御（risk_adjustment）
    - apply_sector_cap: セクター集中をチェックし上限超過セクターの新規候補を除外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear）を返す。
  - 株数決定（position_sizing）
    - calc_position_sizes: risk_based / equal / score 向けの発注株数計算。単元株丸め、per-stock と aggregate の上限処理、スケーリングと残余分配ロジックを実装。
    - 手数料・スリッページ想定の cost_buffer を考慮した集計キャップ処理を導入。

- リサーチ・計算
  - Factor 計算モジュール（kabusys.research.factor_research）を追加（モメンタム / MA200 / ATR / 出来高等の計算方針を実装予定。duckdb を用いる設計）。
    - （注）ソース末尾が未完であり、実装途中の関数が存在します（詳細は既知の問題参照）。

- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）
    - SQLite の Paper Trading DB を解析して、稼働率・注文成功率・送信率・レイテンシ等を集計し PASS/FAIL 判定を出力。
    - P95 計算、期間フィルタ、閾値の定義（稼働率 99% 等）を実装。
    - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- パッケージ初期情報
  - パッケージのバージョンを __version__ = "0.1.0" として定義。

### 変更 (Changed)
- N/A（新規リリースのため該当なし）。

### 修正 (Fixed)
- N/A（新規リリースのため該当なし）。

### 削除 (Removed)
- N/A

### セキュリティ (Security)
- J-Quants / kabu API のトークン・パスワードは .env のシークレットとして取り扱う設計（config_setup にてマスク表示）。

---

## 既知の問題 / TODO
- research/factor_research.py の実装が途中で終わっている箇所（ファイル末尾に不完全なコード断片あり）。Factor 計算の完全実装は今後のタスク。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）時の取り扱いは一部 TODO コメントあり。将来的に前日終値や取得原価でのフォールバック検討。
  - lot_size を銘柄ごとに異ならせる拡張（stocks マスタからの lot_map 対応）は未実装（TODO）。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターは制限適用外としている点は仕様上の判断。必要に応じて扱いを変更する可能性あり。
- logging_setup: ログディレクトリ作成失敗時はファイル出力をスキップする実装だが、アプリ側でこのケースに対する通知やフォールバック設定が必要な場合がある。
- process_priority / set_cpu_affinity:
  - 一部環境（権限不足、未対応プラットフォーム）では設定に失敗することをログで通知してスキップする。運用環境での動作確認を推奨。

---

もしこの CHANGELOG に追加してほしい項目（例えばリリース手順、マイグレーション注意点、より詳細な実装メモなど）があればお知らせください。必要に応じてバージョンの分割や過去のコミット履歴に基づくより細かいログも作成できます。