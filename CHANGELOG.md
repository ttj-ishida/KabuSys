# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
参考: https://keepachangelog.com/ja/1.0.0/

注: 本 CHANGELOG は提示されたソースコードの内容から機能追加・動作仕様・修正点を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-20
初回リリース。本リリースでは、実運用を想定した自動売買フレームワークの基礎機能群を実装しています。以下の主要な機能・改善・修正点を含みます。

### 追加 (Added)
- 全体
  - パッケージ初期バージョンを定義: `kabusys.__version__ = "0.1.0"`。
  - DuckDB / SQLite を用いたデータ管理基盤を導入（`Settings` でパス指定）。
- 設定関連
  - 環境変数管理モジュール `kabusys.config` を追加。
    - .env 自動ロード機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - .env のパース処理でクォート・エスケープ・インラインコメントに対応。
    - 設定値をプロパティ経由で取得する `Settings` クラスを提供（J-Quants、kabu API、DB パス、Paper Trading 設定、監視しきい値等）。
    - Paper Trading 用設定（`PAPER_FILL_MODE`、`PAPER_TRADING_SQLITE_PATH`）をサポート。
- 設定ツール / 検証
  - 対話式 .env 作成ウィザード `kabusys.config_setup` を追加。
    - 質問形式でキーを入力し `.env` を生成・更新する機能。
    - 秘密値はマスク表示。
  - 起動前設定検証 CLI `kabusys.validate_config` を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV の妥当性チェック、ログレベルチェック、DB パスの親ディレクトリ確認、`config/*.yaml` の存在および（PyYAML があれば）パース検証。
    - `--strict` オプションで警告を失敗扱いにできる。
- 起動スクリプト
  - 実行エンジン起動スクリプト `kabusys.run_execution` を追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、paper_trading 専用 SQLite（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離する設計。
    - プロセス優先度を起動時に "high" に設定（`set_process_priority` を呼び出し）。
    - 停止フラグ（`data/stop_requested.flag`）の検知により安全に実行を停止する仕組み。
    - エンジンはデーモンスレッドで実行し、PID ファイルをサポート。
  - 監視ループ起動スクリプト `kabusys.run_monitoring` を追加。
    - 監視ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 `sqlite_path` を使う（監視 DB は本番 DB を参照する仕様）。
    - 停止フラグの検知でループ終了、`check_once()` の例外をログにキャッチして次ポーリングへ継続。
- ログ・プロセスユーティリティ
  - 統一ログ初期化ユーティリティ `kabusys.utils.logging_setup.setup_logging` を追加。
    - stdout への StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイル出力（`logs/<app_name>.log`）を行う。
    - ログディレクトリ作成失敗時はファイルハンドラをスキップして stdout のみで継続。
    - 環境変数 `LOG_LEVEL`, `LOG_DIR` による設定をサポート。
  - プロセス優先度 / CPU affinity ユーティリティ `kabusys.utils.process_priority` を追加。
    - Windows と POSIX(Linux, macOS 等) を吸収して優先度を設定。`set_cpu_affinity` で最初 N コアにピン止め可能。
    - 権限不足や未対応環境では警告を出して安全にスキップ。
- ポートフォリオ構築
  - portfolio モジュールを追加（純粋関数群、DB 参照なし、メモリ内計算）。
    - `kabusys.portfolio.portfolio_builder`:
      - 候補選定: `select_candidates`（スコア降順・タイブレーク処理）。
      - 重み算出: `calc_equal_weights`, `calc_score_weights`（全スコアが0の場合は等分配でフォールバック）。
    - `kabusys.portfolio.risk_adjustment`:
      - セクター集中制限適用: `apply_sector_cap`（"unknown" セクターは除外対象にしない）。
      - レジーム乗数: `calc_regime_multiplier`（`bull`/`neutral`/`bear` をマップ、未知値は警告して 1.0 フォールバック）。
    - `kabusys.portfolio.position_sizing`:
      - 発注株数計算: `calc_position_sizes`（`risk_based` / `equal` / `score` をサポート）。
      - 単元株（lot_size）丸め、ポジション上限 (max_position_pct)、利用率上限 (max_utilization)、コストバッファを考慮した aggregate cap のスケーリング処理を実装。
      - 価格欠損時は該当銘柄をスキップしログ出力。
- リサーチ / ファクター
  - `kabusys.research.factor_research` を追加（Momentum 等のファクター計算を実装予定）。
    - DuckDB の `prices_daily` / `raw_financials` を参照する設計。モメンタム計算のパラメータ（1M/3M/6M、MA200 等）を定義（実装は部分的）。
- ツール
  - Paper Trading 用検証レポート生成スクリプト `kabusys.tools.paper_verification_report` を追加。
    - 指定期間の稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、レイテンシ（avg/max/P95）を算出してレポート出力。
    - デフォルト DB は `data/paper_trading.db`。CLI で `--from` / `--to` / `--db` を指定可能。
    - 判定閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。

### 変更 (Changed)
- DB 初期化
  - `init_monitoring_db` を起動時に呼び出すことで、監視テーブルの存在を冪等的に保証（monitoring と実行エンジン両方で呼び出す）。
- ログ出力先
  - StreamHandler を stdout に固定（cron 等からの起動時に stdout/stderr を統一する目的）。
- 環境変数ロード順
  - OS 環境 > .env.local > .env の優先順位で読み込む実装に変更（既存 OS 環境は保護）。

### 修正 (Fixed)
- .env パーサーの堅牢化
  - クォートされた値のバックスラッシュエスケープ処理、インラインコメント無視、`export KEY=...` 形式対応を追加。
  - クォートなし値の `#` によるコメント認識を改良（`#` の直前がスペース/タブの場合のみコメントと扱う）。
- ポジションサイズ計算での丸め・スケーリングの端数取り扱いを安定化。
- プロセス優先度設定で権限不足 / 未対応 OS の場合でも安全に続行するよう例外処理を追加。

### 注意事項 / 既知の制約 (Known issues / Notes)
- monitoring は設計上「環境にかかわらず本番 sqlite_path を使用する」ため、開発環境で監視テーブルを書き換えたくない場合は起動前に注意が必要です。
- `factor_research` の一部実装は断片的（ファイル末尾でトランケーションあり）。実運用のためには各ファクター計算が完全に実装される必要があります。
- `apply_sector_cap` は price が欠損（0.0）の場合にエクスポージャーを過少見積りする可能性があることを TODO コメントで明記。将来的にフォールバック価格を導入する検討が必要です。
- `set_process_priority` / `set_cpu_affinity` は OS 権限に依存するため、コンテナや制限された環境では期待通り動作しない場合があります（警告を出してスキップします）。

---

今後のリリースでは以下を想定しています（未実装/推奨改善点）:
- factor_research の完全実装（各ファクターの SQL 実装および z-score 正規化）。
- 銘柄別 lot_size 対応（stocks マスタからの取得）。
- より詳細な監視アラート（LINE 通知の統合、しきい値超過時の自動通知）。
- 単体テスト・CI の導入とカバレッジ向上。

もし特定のファイルや差分に基づいてより詳細な CHANGELOG を希望される場合、差分 (git diff) や変更前バージョンのスナップショットを提供してください。