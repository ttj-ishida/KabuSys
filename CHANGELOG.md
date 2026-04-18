# Changelog

すべての注目すべき変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

なお、本CHANGELOGはコードベースの内容から推測して作成しています。実際の履歴と差異がある可能性があります。

## [0.1.0] - 2026-04-18

### 追加 (Added)
- 基本アプリケーションの初期リリース相当の機能を追加。
  - パッケージメタ情報にバージョンを定義: `kabusys.__version__ = "0.1.0"`。
- 環境設定関連
  - .env 自動読み込み機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で自動ロードを無効化可能。
  - .env のパース機能を実装。`export KEY=val`、クォート（単一/二重）のエスケープ、インラインコメントの扱いなどに対応。
  - 対話式環境設定ウィザードを追加（`kabusys.config_setup`）。.env の作成・更新を支援し、シークレット項目をマスク表示して保存。
  - 設定取得ラッパー `Settings` を導入し、各種環境変数（DB パス、API トークン、実行環境、ログレベル、閾値など）をプロパティ経由で安全に取得・検証。
- 設定検証 CLI を追加（`kabusys.validate_config`）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、`config/*.yaml` の存在およびパース検証（PyYAML があれば実行）などを行う。
  - `--strict` モードで警告も失敗扱いにできる。
- ログ設定ユーティリティを追加（`kabusys.utils.logging_setup.setup_logging`）。
  - stdout 出力用の StreamHandler と日次ローテーションする TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソール出力のみで継続。
  - ログレベル・ログディレクトリの解決順を明示。
- プロセス優先度 / CPU affinity ユーティリティを追加（`kabusys.utils.process_priority`）。
  - Windows / POSIX（Linux/macOS/FreeBSD）に対応。優先度設定・CPU 固定を行い、権限不足等は警告ログで穏やかに無視する実装。
- 実行用エントリスクリプトを追加
  - `kabusys.run_execution`：Execution Engine 起動スクリプト。`KABUSYS_ENV=paper_trading` 時は paper 専用 SQLite（`data/paper_trading.db`）を使用し、本番 DB と分離。Broker クライアントの抽象化を使って Mock 実行が可能。停止フラグファイル検出で安全に停止。
  - `kabusys.run_monitoring`：SystemMonitor ポーリングループ起動スクリプト。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグでループ終了、起動時にプロセス優先度を高く設定。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定・重み計算（`select_candidates`, `calc_equal_weights`, `calc_score_weights`）。
  - セクター集中制限・レジーム乗数（`apply_sector_cap`, `calc_regime_multiplier`）。
  - 発注株数計算（`calc_position_sizes`）:
    - risk_based / equal / score の配分方式に対応。
    - 単元株（lot_size）丸め、1銘柄上限、aggregate cap（合計投資額が利用可能現金を超えた場合のスケールダウン）、残差の lot 単位での再配分ロジックを実装。
- Paper Trading 検証ツール（`kabusys.tools.paper_verification_report`）
  - ペーパートレード用 SQLite のログから稼働率・注文成功率・送信率・API レイテンシ（平均/最大/P95）等を集計し、PASS/FAIL レポートを表示。日付範囲フィルタと DB パス上書きオプションを提供。
- 研究用ファクター計算モジュール（`kabusys.research.factor_research`）を追加（モメンタム等の計算を目的）。DuckDB 接続を使用して prices_daily/raw_financials を参照する設計。

### 変更 (Changed)
- DB の分離設計
  - 実行エンジンは paper_trading 環境時に paper 専用 SQLite を使用するよう設計。監視（monitoring）は環境に依らず本番の sqlite_path を使用する旨を明示。
- ロギング挙動
  - 標準出力に対して StreamHandler を stdout に向けて出力（stderr ではなく）。ログディレクトリ作成に失敗した場合はファイルハンドラを作成せずコンソールのみにフォールバックする保護を追加。
- 環境変数読み込みの保護
  - .env の自動ロード時、OS 環境変数（既存のキー）はデフォルトで上書かれない。`.env.local` は明示上書き可能（ただし OS 環境変数は保護）。
- `MONITOR_POLL_INTERVAL` の取り扱いを強化
  - 無効な値（負数・0・非整数）を与えられた場合に警告を出し、デフォルト値（60 秒）にフォールバックするように変更。
- process_priority の堅牢性向上
  - 権限不足や未実装 API に対して例外を握り潰して警告ログを出す挙動にして、起動失敗を防止。

### 修正 (Fixed)
- DB 初期化の冪等化
  - `init_monitoring_db` を起動時に呼び出し、監視テーブルの存在を保証（複数回呼んでも安全）。
- 実行/監視の停止ハンドリング
  - ファイルベースの停止フラグ（data/stop_requested.flag）を見て安全にループ/エンジンを終了するロジックを追加。ExecutionEngine は別スレッドで実行し、停止要求を受けて engine.stop() を呼ぶ。
- パーサ堅牢化
  - .env パーサが多様な書式（クォート、エスケープ、コメント）に対応。空行・コメント行・export プレフィックスを正しく無視する。

### 既知の問題 (Known Issues)
- 研究モジュールの未完実装
  - `kabusys.research.factor_research.calc_momentum` の実装が途中で切れている（スニペット末尾が不完全）。ファクター計算の一部が未完成のため、当該関数の利用は注意が必要。
- price の欠損時の見積り
  - `apply_sector_cap` 内で price が 0.0 の場合に露出が過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格（前日終値など）を用いる改善が必要。
- lot_size のグローバル扱い
  - 現状は全銘柄共通の単元株数（lot_size=100）を想定。将来的には銘柄別の lot_map へ拡張予定。

### セキュリティ (Security)
- .env は絶対に Git にコミットしない旨を明記するテンプレート（`config_setup` にて出力）を追加。
- 環境変数未設定時は `Settings` の `_require` が ValueError を投げ、起動前に必須値の確認を促す。

### 補足 / 運用メモ
- ログファイル:
  - デフォルト保存先は `logs/`。日次ローテーション・30日分保持。`LOG_DIR` 環境変数や `setup_logging(..., log_dir=...)` で変更可能。
- 実行環境の判定:
  - `KABUSYS_ENV` は `development`, `paper_trading`, `live` のいずれか。`live` の場合は追加の注意喚起（LINE 設定や Kill Switch の扱い）を `validate_config` が行う。
- Paper Trading:
  - ペーパートレードを本番 DB と完全分離することで安全にローカル検証が可能。`PAPER_FILL_MODE` による約定振る舞い（instant/partial/never/reject）をサポート。

---

（次回リリース案）
- factor_research の未完成部分を完成させ、Value/Volatility/Liquidity ファクターや正規化ユーティリティとの統合を行う。
- 銘柄別 lot_size 対応、price フォールバック、より厳密なエラーハンドリングの強化を予定。