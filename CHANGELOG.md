# Changelog

すべての注記は Keep a Changelog の形式に従っています。慣例に従いセマンティックバージョニングを想定しています。ここに記載した変更点は、提供されたコードベースの内容から推測してまとめたものです。

現在のバージョン: 0.1.0

## [Unreleased]
（このスナップショットでは未リリースの変更はありません）

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 基本アプリケーションパッケージを追加
  - パッケージ名: `kabusys`、バージョン定義: `__version__ = "0.1.0"`。
- 実行用エントリポイント
  - `run_execution.py`：ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離して使用する（paper_trading 時は `data/paper_trading.db` を使用）。
  - `run_monitoring.py`：SystemMonitor のポーリングループを起動するスクリプトを追加。`MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番用の sqlite_path を参照する。
- 環境設定・検証コマンド
  - `config_setup.py`：対話式ウィザードで `.env` を生成 / 更新する CLI を追加。複数の設定項目（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL など）に対応。
  - `validate_config.py`：.env や `config/*.yaml` の存在・簡易検証を行う CLI を追加。`--strict` による警告の扱い変更をサポート。
- 設定管理
  - `config.py`：.env 自動ロード機能（プロジェクトルート検出、`.env` → `.env.local` の優先順適用、OS 環境変数保護）と、型変換/検証付きの `Settings` クラスを実装。
    - `.env` のパースはシングル/ダブルクォートやエスケープ、`export KEY=val` 形式、コメント処理を考慮。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化をサポート。
    - `paper_sqlite_path`、`paper_fill_mode`、しきい値設定（CPU/MEM/DISK）などをプロパティとして提供。
- ログ・プロセス制御ユーティリティ
  - `utils/logging_setup.py`：StreamHandler（stdout）と日次ローテーションのファイルハンドラを設定する共通ユーティリティを追加。ログディレクトリ自動作成・作成失敗時のフォールバック対応あり。
  - `utils/process_priority.py`：Windows / POSIX を吸収するプロセス優先度設定、CPU affinity 設定関数を追加。アクセス権限や未対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ロジック（純粋関数群）
  - `portfolio/portfolio_builder.py`：候補選定（スコア順）、等金額／スコア重み計算を実装。
  - `portfolio/risk_adjustment.py`：セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - `portfolio/position_sizing.py`：各銘柄の発注株数を計算するロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、aggregate cap によるスケーリング、cost_buffer を考慮。
- Paper Trading 検証レポート
  - `tools/paper_verification_report.py`：paper_trading 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）から集計して検証レポートを生成するスクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等の指標算出と PASS/FAIL 判定をサポート。
- リサーチ基盤（部分実装）
  - `research/factor_research.py`：DuckDB 接続を受けてファクター（Momentum、Value、Volatility、Liquidity）を計算する設計の出発点を追加。関数仕様や定数（窓長など）が定義されている（実装途中の箇所あり）。

### 変更 (Changed)
- 監視起動の既定動作
  - 監視ループは起動時にプロセス優先度を "high" に設定するように変更（`set_process_priority("high")` を最初に呼び出す）。
- データベース扱いの分離
  - Execution エンジンは paper_trading の場合に専用の SQLite を使用することで本番 DB と分離（`Settings.paper_sqlite_path` を使用）。
- DB 初期化の冪等化
  - `init_monitoring_db()` を Execution / Monitoring 起動時に呼び出して監視テーブルの存在を保証（存在していない場合に作成する想定）。

### 修正 (Fixed)
- 環境変数パースとロードの堅牢化
  - `.env` のパースでクォートやバックスラッシュエスケープ、インラインコメントを考慮する実装に改善。
  - 自動ロード時に OS 環境変数を保護する仕組み（protected set）を導入。
- ロギングの安全性向上
  - ログディレクトリの作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソール出力のみ行うようにして二重クラッシュを防止。
- プロセス優先度／affinity 設定のフォールバック
  - 権限不足や未対応環境時に例外を潰して警告ログを出すように修正（起動失敗を防止）。

### 既知の問題・制約 (Known issues)
- `research/factor_research.py` の実装は途中で切れている（冒頭に設計と定数はあるが一部関数が未完：start_da… で切れる）。本格運用前に完成が必要。
- `risk_adjustment.apply_sector_cap` 内で price が 0.0 の場合のフォールバックが未実装（TODO コメントあり）。価格欠損時にエクスポージャーが過少見積になる可能性がある。
- `position_sizing` の将来的拡張（個別銘柄毎の lot_size サポート）に関する TODO が残る。
- `tools/paper_verification_report` の P95 計算は単純な順序統計量（線形補間なし）を使用している点は意図的な設計だが、定義によって差異が出る可能性あり。
- `BrokerClientFactory` など Execution 周りの外部依存（ブローカークライアント実装、ExecutionEngine 本体等）はこのスナップショットでは定義ファイル参照のみで、外部モジュールの実装確認が必要。

### セキュリティ (Security)
- 本リリースにおいては特段のセキュリティ修正は含まれない。注意点として `.env` は絶対に Git にコミットしない旨の注意書きが `config_setup.py` に明記されている。

---

作業のヒント / 次に検討すべきこと
- `research/factor_research.py` の未完実装を完成させる。
- price 欠損時のフォールバックルール（前日終値やマスタデータ）を実装してセクター/ポジション計算の堅牢性を向上させる。
- 単体テストを充実させ、特に position sizing、risk adjustment、portfolio builder の数理的な境界条件を検証する。
- Paper Trading 用の検証レポートの基準値や P95 計算仕様をドキュメント化し、運用基準を確立する。