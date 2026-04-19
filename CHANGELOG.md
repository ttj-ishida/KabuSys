# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
参考: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 初期リリース。KabuSys のコアユーティリティと CLI、ポートフォリオ構築／実行周りの純粋関数群を導入。
- 環境・設定管理
  - Settings クラスを導入し、アプリケーション設定を環境変数から取得可能に。
  - 自動 .env ロード機能を実装（.env, .env.local。OS 環境変数を保護する仕組みを搭載）。環境変数自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env を対話式に生成・更新する CLI `kabusys.config_setup` を追加（ウィザード形式、.env テンプレート出力、`.env` を絶対にコミットしない注意文を出力）。
  - .env のパース機能を実装（export プレフィックス対応、クォート内のバックスラッシュエスケープ、インラインコメント処理など）。
- 設定検証
  - `kabusys.validate_config` CLI を追加。必須環境変数・DB パス・config/*.yaml の存在や基本的な整合性をチェック。`--strict` オプションで警告を FAIL 扱いに可能。
- 実行・監視ランナー
  - `run_execution.py`（ExecutionEngine 起動スクリプト）を追加。KABUSYS_ENV=paper_trading をサポートし、ペーパートレード用 DB を本番から分離（デフォルト: data/paper_trading.db）。
  - `run_monitoring.py`（SystemMonitor ポーリングループ起動スクリプト）を追加。環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番用 sqlite_path を環境に関係なく使用。
  - 両ランナーともに stop フラグ（data/stop_requested.flag 等）と PID ファイルの取り扱いを実装。
- ロギングとプロセス設定
  - 統一的に利用する `setup_logging` ユーティリティを追加。コンソール（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーに設定。既存ハンドラをクリアすることで二重設定を防止。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
  - `process_priority` ユーティリティを追加。Windows / POSIX を吸収してプロセス優先度（high/normal/low）を設定する API を提供。CPU affinity を設定するユーティリティも実装。
- ポートフォリオ構築（純粋関数群）
  - 銘柄選定: select_candidates（スコア降順、signal_rank でタイブレーク）。
  - 重み計算: calc_equal_weights, calc_score_weights（スコア合計が 0 の場合は等配分にフォールバック）。
  - セクター制限・レジーム乗数: apply_sector_cap（既存保有を考慮したセクター上限フィルタリング）、calc_regime_multiplier（bull/neutral/bear の乗数）。
  - 株数決定: calc_position_sizes（risk_based / equal / score の配分方式、単元株丸め、aggregate cap によるスケーリング、cost_buffer を加味した保守的見積り）。
- リサーチ・ツール類
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の SQLite DB から稼働率、注文成功率、送信率、レイテンシ指標（P95 等）を集計し PASS/FAIL 判定を出力するレポート機能を提供。
- DB 関連
  - duckdb を分析用 DB として利用する設計を導入（Settings.duckdb_path）。
  - 監視用 DB 初期化を行う init_monitoring_db 呼び出しをランナーで行い、テーブル存在を保証（冪等）。

### 変更 (Changed)
- ログ出力先を stdout に変更（StreamHandler）。cron / scheduler 等からのリダイレクト運用を考慮。
- run_execution / run_monitoring の起動フローにて、最初にプロセス優先度を High に設定するように統一。
- run_execution: paper_trading 環境では BrokerClientFactory により MockBrokerClient を利用する想定（本番 DB とは分離）。
- setup_logging: 既存ハンドラを安全に flush/close してから削除する実装に変更（多重登録の防止）。
- .env ロードの優先順位を OS 環境変数 > .env.local > .env に明確化。OS 環境変数は protected として .env の上書きを防止。
- calc_position_sizes のスケーリングアルゴリズムを改善（投下合計が available_cash を超える場合にスケールしてから単元株（lot_size）単位で再配分、残余キャッシュを使った端数配分のロジックを導入）。

### 修正 (Fixed)
- 環境変数読み取り時の堅牢性向上
  - _parse_env_line で export プレフィックスやクォート内エスケープ、インラインコメント判定を適切に処理するよう修正。
- ポーリング間隔取得 (_get_poll_interval)
  - 環境変数に負数や 0 等の不正な値が与えられた場合にデフォルトにフォールバックし、警告ログを出力するように変更（time.sleep に渡すと ValueError となる不具合回避）。
- setup_logging
  - ログディレクトリ作成失敗時にファイルハンドラ作成を安全にスキップし、コンソール出力のみで継続するように修正（起動失敗を避けるため）。

### セキュリティ (Security)
- config_setup による .env 生成時の注意書きを出力（.env を絶対にコミットしない）。README 等での取り扱いを想定。
- Settings/.env ロードでは OS 環境変数を保護（protected）し、意図しない上書きを防止。

### その他 (Other)
- validate_config の本番向けガードチェック（KABUSYS_ENV=live 時の LINE 設定未設定や KILL_FLAG_CLEAR_ON_START の危険な設定検出）を追加。
- 一部モジュール（research/factor_research）の実装が作業中（ファイル末尾が途中で切れている箇所あり）。今後のリリースで補完予定。

### 既知の制限 (Known issues)
- position_sizing の価格フォールバック:
  - apply_sector_cap / calc_position_sizes において price_map / open_prices に欠損 (0.0) があるとエクスポージャーが過少評価される可能性がある旨を TODO コメントで指摘。将来的に前日終値や取得原価を使ったフォールバックが必要。
- research/factor_research の一部未完（実装継続予定）。

---

将来的なリリースでは、戦略ロジック（signals, strategy model）、ExecutionEngine の詳細実装、テストカバレッジ、および research モジュールの完全実装を予定しています。