# CHANGELOG

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" 準拠です。

※ 変更内容はソースコードの内容から推測して記載しています。実際のコミット履歴ではありません。

## [0.1.0] - 2026-04-17

初回リリース（ベース機能実装）。以下の機能群と CLI / ユーティリティを追加しました。

### 追加 (Added)
- アプリケーション設定管理
  - 環境変数および .env/.env.local の自動読み込み機能を実装（kabusys.config）。
  - .env ファイルのパースはクォート・エスケープ・コメントに対応（export 形式もサポート）。
  - Settings クラスを提供し、J-Quants / kabuAPI / DB パス / 各種閾値などをプロパティ経由で取得可能。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み抑止をサポート。

- 環境設定ウィザード CLI
  - 対話式で .env を作成・更新する config_setup（kabusys.config_setup）。
  - 複数のプリセット項目（KABUSYS_ENV, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL など）を用意。
  - 秘匿値はマスク表示、保存前に確認を促す。

- 設定検証 CLI
  - .env と config/*.yaml を起動前に検証する validate_config（kabusys.validate_config）。
  - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 値チェック、DB パスの親ディレクトリ確認、YAML パース検証（PyYAML があれば）を実施。
  - --strict モードで警告を FAIL 扱いにできる。

- 実行エンジン起動スクリプト
  - ExecutionEngine 起動スクリプト run_execution を追加（kabusys.run_execution）。
  - KABUSYS_ENV=paper_trading の場合は専用の paper_trading データベースを使用し、本番 DB と完全分離（PAPER_TRADING_SQLITE_PATH）。
  - Broker クライアントファクトリを利用して本番/モックを切り替え。
  - エンジンは別スレッドで実行し、data/stop_requested.flag の検知で停止。PID ファイル出力対応。

- 監視ループ起動スクリプト
  - SystemMonitor ポーリングループ起動用の run_monitoring を追加（kabusys.run_monitoring）。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は環境に関わらず production 用 sqlite_path を利用して監視データを保存。
  - 停止フラグ検知や例外ハンドリングを実装。

- Paper Trading 検証レポートツール
  - paper_verification_report（kabusys.tools.paper_verification_report）を追加。
  - Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計してレポート出力。
  - Pass/Fail 判定基準（稼働率 >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 <= 200ms）を組み込み。

- ポートフォリオ構築ライブラリ
  - 候補選定・重み計算（select_candidates / calc_equal_weights / calc_score_weights）（kabusys.portfolio.portfolio_builder）。
  - セクター集中制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）（kabusys.portfolio.risk_adjustment）。
  - 株数決定・リスク制限・単元丸め（calc_position_sizes）（kabusys.portfolio.position_sizing）。
  - ポートフォリオモジュールの集約エクスポート（kabusys.portfolio）。

- リサーチ / ファクター計算
  - DuckDB を用いたファクター計算モジュール（momentum, volatility 等）（kabusys.research.factor_research）。
  - prices_daily / raw_financials テーブルのみ参照する純粋関数群を実装。

- ユーティリティ
  - プロセス優先度と CPU affinity 設定ユーティリティを追加（kabusys.utils.process_priority）。
    - Windows/Linux(macOS等) の差を吸収して優先度を設定。失敗時は警告でスキップ。
    - CPU affinity を最初の N コアに固定する機能を提供。
  - DuckDB と sqlite3 を併用する設計（分析用に DuckDB を採用）。

### 変更 (Changed)
- n/a（初回リリースのため過去バージョンからの変更はなし）。

### 修正 (Fixed)
- n/a（初回リリースのため過去バージョンからの修正はなし）。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- .env の自動読み込みはプロジェクトルートの検出（.git または pyproject.toml）に依存する。検出できない場合は自動ロードをスキップする。
- PAPER_FILL_MODE の値は "instant" | "partial" | "never" | "reject" のいずれかでなければエラーとなる。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小評価され除外が発生しない可能性あり。将来的にフォールバック価格の導入を検討。
- calc_position_sizes:
  - 現在 lot_size は全銘柄共通の引数で扱う。将来は銘柄別 lot_size をサポートすることを検討（TODO コメントあり）。
  - rounding / aggregate cap のロジックは単元株（lot_size）単位で安全に調整する。
- process_priority, set_cpu_affinity:
  - 権限不足やプラットフォーム未対応の場合は警告を出してスキップする実装。
- run_monitoring は監視用 DB を「環境にかかわらず」 production の sqlite_path で開く設計のため、テストや開発時は意図せず本番 DB を参照しないよう環境設定に注意が必要。
- Paper Trading と本番 DB は分離してあるが、運用時のファイルパス設定ミスに注意（validate_config により親ディレクトリの存在等を警告）。

### セキュリティ (Security)
- n/a（現時点で特筆すべきセキュリティ修正はありません）。

---

今後のリリース候補としては、以下が想定されます：
- 各コンポーネントのユニットテスト追加・CI 統合
- ポートフォリオ関連の銘柄別 lot_size サポート
- apply_sector_cap の価格フォールバック実装
- duckdb / sqlite のマイグレーション・スキーマ管理（マイグレーションツール導入）
- 実行中のメトリクス収集と可視化ダッシュボード連携

この CHANGELOG はコードのコメントや実装から推測して作成しています。実際の変更履歴（コミットメッセージ等）が存在する場合は、そちらに基づく詳細な記録を合わせてご利用ください。