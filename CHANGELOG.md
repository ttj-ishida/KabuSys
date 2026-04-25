# CHANGELOG

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の書式に準拠しています。

## [Unreleased]

### Added
- なし（次回リリースへ）

### Changed
- なし

### Fixed
- なし

---

## [0.1.0] - 2026-04-25

初回リリース。以下の主要機能とユーティリティを実装・追加しました。

### Added
- コアメタ情報
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として定義。

- 設定管理
  - Settings クラスによる環境変数ベースの設定読み取りを実装（`src/kabusys/config.py`）。
  - .env の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - .env 行パーサを堅牢化（`export KEY=val` 形式、クォート文字列内のバックスラッシュエスケープ、行内コメント処理をサポート）。
  - 自動読み込みを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入。

- 環境設定ウィザード
  - 対話式ウィザードで `.env` を作成・更新する CLI を追加（`src/kabusys/config_setup.py`）。
  - デフォルト項目、選択肢、シークレット入力のマスク表示、保存前確認を実装。

- 設定検証 CLI
  - `.env` と `config/*.yaml` の起動前検証ツールを追加（`src/kabusys/validate_config.py`）。
  - 必須環境変数チェック、KABUSYS_ENV の妥当性検証、DB パス/親ディレクトリ確認、YAML パース検証（PyYAML があれば）を実行。
  - `--strict` オプションで警告も失敗扱いにできる。

- ログ設定ユーティリティ
  - 統一的なログ初期化関数 `setup_logging` を追加（stdout 出力 + 日次ローテートファイル、30日保持）。
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで継続するフォールバックを実装。

- プロセス優先度 / CPU 固定
  - クロスプラットフォームでプロセス優先度を設定するユーティリティ（Windows / POSIX 対応）を追加。
  - CPU affinity を設定するユーティリティを追加（利用可能なコア数と範囲チェックを実装）。
  - 権限不足などで設定に失敗した場合は警告ログを出して安全にスキップする挙動。

- Execution / Monitoring 起動スクリプト
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - `KABUSYS_ENV=paper_trading` 時は paper-trading 専用 SQLite（デフォルト `data/paper_trading.db`）を使用し、本番 DB と完全に分離。
    - ブローカーファクトリ経由で本番用 / モック (paper) ブローカーを選択する設計を想定。
    - デーモン化スレッドで `ExecutionEngine.run_session` を実行し、停止フラグ検知で安全に停止する仕組みを提供。
    - PID ファイル (`data/execution.pid`) を扱うオプションをサポート。
  - 監視ポーリングループ起動スクリプト `run_monitoring.py` を追加。
    - 監視用 DB は環境にかかわらず本番用 sqlite_path を使用（監視は本番 DB を参照）。
    - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値時はデフォルトへフォールバック。
    - 停止フラグファイル検知でループを終了。

- DB / 分析基盤
  - DuckDB 統合（`duckdb` コネクションを各エンジン/ツールに渡す設計）。
  - 監視用 SQLite DB 初期化ユーティリティ（`init_monitoring_db` を要求して冪等にテーブル作成）。

- Portfolio 構築ライブラリ
  - 候補選定・重み計算（`portfolio_builder.py`）
    - 信号に基づく候補選定（スコア降順、タイブレークロジック）。
    - 等金額配分 / スコア加重配分（全スコア 0 の場合等金額へフォールバック）。
  - セクター集中制限・レジーム乗数（`risk_adjustment.py`）
    - セクターごとの既存エクスポージャ計算と、上限超過セクターの新規候補除外。
    - market regime に応じた投下比率乗数（bull/neutral/bear のマップとフォールバック処理）。
  - ポジションサイズ計算（`position_sizing.py`）
    - risk-based / equal / score 配分方式に対応。
    - 単元株（lot_size）の丸め、最大ポジション上限、投下資金合計のスケーリング（aggregate cap）、コストバッファを勘案した保守的見積り。
    - 欠損価格ハンドリングのログを出力しスキップする設計。

- 研究用モジュール（着手）
  - ファクター計算の土台（momentum 等）を実装開始（`research/factor_research.py`）。
    - DuckDB の prices_daily / raw_financials を参照してモメンタムや移動平均乖離などを計算する設計。仕様・定数を明記。

- ツール
  - Paper Trading の検証レポート生成ツール（`tools/paper_verification_report.py`）を追加。
    - 稼働率（uptime）、注文成立率（fill rate）、送信率、P95 レイテンシなどを算出し、しきい値に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ、DB パス指定オプションをサポート。

- 実行コンポーネント（設計参照）
  - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler 等のコンポーネントを参照する起動/組立ロジックを追加（実体は別モジュール想定）。
  - RiskManager のデフォルト設定（最大ポジション比率、利用率、レート制限、サーキットブレーカー、初期ポートフォリオ値の broker 経由取得）を起動時に組み立てる例を提示。

### Changed
- ログ出力
  - StreamHandler を stdout に向ける設計に統一（cron 等で stdout/stderr を一本化しやすくするため）。

- .env 読み込み順序
  - 読み込み優先順位を明確化：OS 環境変数 > .env.local > .env。
  - .env.local は .env の上書きとして扱う。

### Fixed / Robustness
- 環境変数パースの堅牢化
  - 不正な `MONITOR_POLL_INTERVAL` 値を検知して警告を出し、デフォルト値にフォールバックする実装を追加（監視ループでの ValueError 回避）。
  - ログディレクトリ作成失敗時にファイルハンドラ作成をスキップしてもアプリが継続するよう対策。
  - プロセス優先度 / CPU affinity の設定でアクセス権限や未対応プラットフォームの例外を安全にハンドリング。

### Security
- .env の取り扱いについて明確な注意喚起を追加（config_setup にて .env を絶対に Git にコミットしない旨を記載）。

---

注記:
- 本 CHANGELOG は与えられたコードベースの内容から推測して作成しています。実際のリリース履歴やリリース日付はリポジトリの運用方針に従って調整してください。必要であれば、各変更点をさらに細分化してコミット単位やチケット番号を紐付けることを推奨します。