# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  

リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- プロジェクト初期リリース。
- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - KABUSYS_ENV による切替:
      - `paper_trading` の場合は専用の Paper Trading SQLite DB（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全に分離。
      - Paper 環境では MockBrokerClient を使用することを想定（BrokerClientFactory 経由で生成）。
    - 実行エンジンは別スレッドで動作し、 data/stop_requested.flag による停止検知機構を実装。
    - 起動時にプロセス優先度を "high" に設定する処理を追加。
  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するスクリプトを提供。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して記録する設計。
    - 停止フラグ（data/stop_requested.flag）検知により安全にループを終了。

- 設定・起動支援
  - config.py
    - 環境変数読み込みと Settings クラスを提供。
    - プロジェクトルート（.git または pyproject.toml）を基準に `.env` 自動ロード機能（.env → .env.local の順でロード、OS 環境変数優先）。
    - 必須/任意の設定項目をプロパティとして整理（DB パス、KABUSYS_ENV、LOG_LEVEL、Paper Trading 関連等）。
    - 環境値の妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等）。
  - config_setup.py
    - 対話式ウィザードで .env の初期作成・更新を支援する CLI を提供。
    - 標準項目（J-Quants トークン、kabu API パスワード、DB パス、ログレベル等）を網羅。
    - シークレット項目はマスク表示。生成された .env の保存と注意喚起（.env を Git にコミットしない旨）を明示。
  - validate_config.py
    - .env と config/*.yaml の設定整合性チェック CLI を提供。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性、DB パスの親ディレクトリ存在チェック、YAML パース検証（PyYAML がインストールされている場合）。
    - `--strict` モードで警告もエラー扱いにできる。

- 監視・レポート関連
  - monitoring モジュール（初期化関数を暗黙的に利用）
    - 監視用 SQLite DB の初期化（init_monitoring_db を使用）。
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime_pct)、注文成功率 (fill_rate_pct)、送信率 (send_rate_pct)、P95 レイテンシ。
    - デフォルト閾値を定義（稼働率 >= 99%、注文成功率 >= 90% 等）し、PASS/FAIL 判定を出力。
    - 日付範囲フィルタ、DB パス引数/環境変数対応、P95 計算ロジックを実装。

- ポートフォリオ構築ライブラリ（pure functions）
  - portfolio.portfolio_builder
    - 候補選定 (select_candidates)、均等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。
  - portfolio.risk_adjustment
    - セクター集中制限 apply_sector_cap、マーケットレジームに応じた乗数 calc_regime_multiplier を実装。
    - レジーム別デフォルト乗数: bull=1.0, neutral=0.7, bear=0.3。未知レジームはフォールバックで 1.0。
  - portfolio.position_sizing
    - 株数計算ロジック calc_position_sizes を実装（risk_based, equal, score の allocation_method をサポート）。
    - 単元株丸め（lot_size、デフォルト 100）、max_position_pct、max_utilization、コストバッファを考慮した aggregate cap スケーリングを実装。
    - 利用可能現金に対してスケールダウンし、残余キャッシュを考慮して lot_size 単位で再配分するアルゴリズムを組み込み。

- ユーティリティ
  - utils.logging_setup
    - ルートロガーに StreamHandler(stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ユーティリティを提供。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップ。
  - utils.process_priority
    - psutil を使ったクロスプラットフォームのプロセス優先度設定（Windows: priority class、POSIX: nice 値）。
    - CPU affinity 設定用の set_cpu_affinity を提供（最初の N コアへ固定）。実行環境による失敗は警告でフォールバック。

- リサーチ（計算モジュール）骨格
  - research.factor_research
    - モメンタム / ボラティリティ / 流動性 等のファクター計算方針と定数を実装。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算を行う設計。
    - （モメンタム計算関数等、機能の骨格が含まれる。実装は段階的に完成予定。）

- パッケージメタ
  - パッケージ初期バージョンを __version__ = "0.1.0" として設定。
  - モジュール公開インターフェイスを __all__ で整理（portfolio 等）。

### 変更 (Changed)
- ログ出力
  - StreamHandler を stdout に出力するように明示（stderr ではなく stdout）。cron / Task Scheduler でのリダイレクト運用を想定。
- .env 自動ロード
  - プロジェクトルート検出に .git / pyproject.toml を使用し、CWD 非依存での動作を目指す。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL のパースを堅牢化。1 未満の値や不正な文字列は警告してデフォルト（60 秒）にフォールバックする実装に変更。
- 監視ループと実行エンジンでの停止検知（stop flag）により、外部から安全に停止できる仕組みを整理。

### 注意事項 / 既知の制限 (Known issues)
- apply_sector_cap 内の価格欠損処理についての TODO:
  - price が欠損 (0.0) の場合にエクスポージャーが過少評価され、誤って候補が通過する可能性がある。将来的に前日終値や取得原価でのフォールバックを検討。
- position_sizing:
  - 現状では全銘柄共通の lot_size を前提。将来的に銘柄別 lot_size を持つ設計へ拡張予定（TODO コメントあり）。
- research.factor_research の一部関数は実装中（骨格は存在するが、完全実装は今後のタスク）。
- .env は絶対にリポジトリにコミットしないこと（config_setup.py にも注意喚起あり）。
- 一部機能は psutil の権限や OS の差異によって期待通り動作しない場合がある（権限不足時は警告でスキップする設計）。

### セキュリティ (Security)
- 機密情報（J-Quants トークン、kabu API パスワード等）は .env に保存される想定。公開リポジトリにコミットしないよう強く注意。

---

今後の予定（例）
- research モジュールの完全実装（ファクター計算の最終化・テスト）。
- テスト整備（ユニットテスト / 統合テスト）、CI パイプライン導入。
- 銘柄別 lot_size 対応、価格フォールバック強化、より高度なリスク管理ロジックの追加。

以上。