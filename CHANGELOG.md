# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記録します。  
このファイルはコードベースから推測して作成した変更履歴です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

### 追加
- ドキュメント生成用のテンプレートを追加（初期リリースに向けた準備）。  

### 変更
- 小さなコード整備・ログメッセージの改善（内部実装の安定化）。

---

## [0.1.0] - 2026-04-20

初回リリース。自動売買システム「KabuSys」の基本コンポーネントを実装しました。

### 追加
- 実行入口スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite （デフォルト: data/paper_trading.db）を使用する分離を実装。
    - ストップフラグ（data/stop_requested.flag）検知による安全停止処理を実装。
    - 実行用 PID ファイル（data/execution.pid）をサポート。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）を実装。
    - 監視は環境に関わらず本番用の sqlite_path を使用する旨の仕様を導入。

- 設定・環境管理
  - config.py
    - Settings クラスにより環境変数/設定を集中管理。
    - プロジェクトルート自動検出（.git または pyproject.toml）を実装し、.env/.env.local の自動読み込みを提供（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化あり）。
    - PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE、各種閾値などのプロパティを追加。
  - config_setup.py
    - 対話式ウィザードで .env ファイルを初期作成・更新する CLI を追加。
    - 必須/任意項目、シークレット入力、既存 .env 読込、保存確認などをサポート。

- 設定検証
  - validate_config.py
    - .env と config/*.yaml の起動前検証を行う CLI を追加。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、YAML パースチェック、`--strict` モードを実装。

- ロギング/プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（デイリーローテーション）を設定する setup_logging を追加。
    - LOG_DIR 指定・作成、ログレベル解決（引数・環境変数・デフォルト）をサポート。ログディレクトリ作成に失敗した場合のフォールバック処理を実装。
  - utils/process_priority.py
    - Windows / POSIX の差を吸収してプロセス優先度や CPU affinity を設定するユーティリティを追加。
    - set_process_priority, set_cpu_affinity を提供。権限不足時は警告を出してスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定 (select_candidates)、等重み (calc_equal_weights)、スコア重み (calc_score_weights) を実装。
  - portfolio/risk_adjustment.py
    - セクター曝露上限を適用する apply_sector_cap を実装（"unknown" セクターは上限除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear マッピング、未知レジームはフォールバック）。
  - portfolio/position_sizing.py
    - position sizing（risk_based / equal / score）アルゴリズムを実装。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、コストバッファの考慮、スケールダウンと端数処理ロジックを提供。

- 解析・研究
  - research/factor_research.py（ファクター計算基盤を追加。モメンタム等の算出を想定）
    - DuckDB を用いた価格/財務データに基づくファクター計算の設計を導入（実装は本ファイルの続きに依存）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、API レイテンシ（平均、最大、P95）等を集計。
    - Pass/Fail 判定閾値を定義（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 <= 200ms）。
    - コマンドライン引数 --from/--to/--db をサポート。

- パッケージ初期化
  - __init__.py にバージョン設定 __version__ = "0.1.0" を追加。

### 変更（設計上の重要な決定）
- DB の分離
  - Paper Trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番監視 DB と完全に分離する設計を採用。
- 監視側の DB 利用
  - run_monitoring は KABUSYS_ENV に関係なく本番用 sqlite_path を使用する（監視用 DB は本番の監視データを記録するため）。
- ログ出力の統一
  - stdout へ StreamHandler を設定（stderr ではない）し、cron/task scheduler 等でのリダイレクト運用を考慮。

### 修正（バグ修正・堅牢化）
- .env パーサーの強化（config._parse_env_line）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い、クォートなし値でのコメント認識の改良などを実装し、.env の柔軟な解析に対応。
- logging_setup の堅牢化
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合、ファイル出力を無効化してコンソール出力のみで継続する安全なフォールバックを実装。
- process_priority のフォールバック
  - 権限不足や未対応 OS の場合に例外を投げず警告で処理をスキップするように変更（サービス環境での起動失敗を防止）。
- position_sizing の安全弁強化
  - price が欠損・0 の場合にスキップするロジック、aggregate cap でのスケーリング後の端数処理（lot_size 単位で残余キャッシュに基づく再配分）を強化。
- risk_adjustment の "unknown" セクター取り扱い
  - セクター未定義銘柄は上限チェックの対象外とし、誤ったブロックを回避。
- run_monitoring のポーリング間隔バリデーション
  - 環境変数 MONITOR_POLL_INTERVAL が不正（0以下や非整数）の場合は警告を出してデフォルト（60秒）へフォールバック。
- validate_config のチェック拡張
  - config/*.yaml の存在確認と（PyYAML があれば）パース検証、KABUSYS_ENV が live の際の追加安全チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険性警告）を追加。

### ドキュメント/メッセージ改善
- 多くのモジュールで docstring やログメッセージを充実化。運用時の挙動が分かりやすくなっています。
- CLI（config_setup, validate_config, paper_verification_report）の使用方法・ヘルプを整備。

### 既知の制限 / 注意点
- 一部機能（research/factor_research の詳細計算など）は DuckDB のテーブル構造（prices_daily / raw_financials 等）に依存します。実行前にデータが整備されていることを確認してください。
- .env は絶対にリポジトリにコミットしないでください（config_setup のヘッダにも明記）。
- process_priority / cpu_affinity の設定は実行権限が必要な場合があります。権限不足時は警告が出て設定をスキップします。

---

## 将来の改善案（メモ）
- 銘柄ごとの lot_size を銘柄マスタで管理し、position_sizing に注入できるようにする。
- price 欠損時のフォールバック（前日終値や取得コスト）を実装してエッジケースを改善する。
- ファクター計算のユニットテスト・ベンチマーク整備。
- モニタリングのメトリクス収集（Prometheus 等）やアラート連携の強化。

---

著者: 自動生成（コードベースから推測）  
注: この CHANGELOG は提供されたソースコードの内容に基づき推測して作成しています。実際のリリースノート作成時は実作業・コミット履歴に基づいて適宜調整してください。