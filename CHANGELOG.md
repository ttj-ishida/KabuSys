# Changelog

すべての注目すべき変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

現在のバージョン: 0.1.0 — 2026-04-20

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 基本パッケージ初期実装を追加
  - パッケージ情報: `kabusys.__version__ = "0.1.0"`
- 実行スクリプト
  - run_monitoring: `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御に `data/stop_requested.flag` を利用。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 `sqlite_path` を使用する仕様。
    - 起動時にプロセス優先度を "high" に設定。
  - run_execution: `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 専用 DB (`data/paper_trading.db` など) に記録して本番 DB と分離。
    - 停止フラグ (`data/stop_requested.flag`) の検出で Graceful にエンジン停止。
    - PID ファイルサポート（`data/execution.pid` 等）。
- 設定管理・ヘルパ
  - `src/kabusys/config.py`
    - Settings クラスを実装。環境変数から各種設定を一元取得。
    - 自動 .env 読み込み機能（プロジェクトルートを .git / pyproject.toml で探索）を追加。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - .env のパースはシングル/ダブルクォート、`export KEY=...` 形式、行内コメント対応。
    - 各種プロパティを提供（J-Quants / kabu API / DuckDB/SQLite パス / Paper Trading 設定 / 監視閾値 等）。
    - `paper_fill_mode` のバリデーション実装（有効値: instant/partial/never/reject）。
- 設定補助 CLI
  - `src/kabusys/config_setup.py`
    - .env を対話式に作成・更新するウィザードを追加（保存ファイルに注意喚起を含む）。
    - 各設定項目の説明・デフォルト・シークレット扱い・選択肢をサポート。
  - `src/kabusys/validate_config.py`
    - 起動前チェック CLI を追加。
    - 必須環境変数の有無、KABUSYS_ENV の妥当性、ログレベル、DB パスの親ディレクトリ、config/*.yaml の存在と YAML パース（PyYAML があれば検証）を行う。
    - 本番環境（KABUSYS_ENV=live）に対する追加警告（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険性など）。
    - `--strict` オプションで警告を失敗として扱う。
- ロギング・プロセス制御ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガーへ StreamHandler（stdout）と TimedRotatingFileHandler（日次・30日保持）を設定するユーティリティを追加。
    - ログレベル・ログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX (Linux/Mac/FreeBSD) に対応したプロセス優先度設定を実装（"high"/"normal"/"low"）。
    - CPU affinity を最初の N コアに固定する helper を追加。
    - psutil によるアクセス例外は警告してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補選定（スコア降順、タイブレーク）、等金額 / スコア加重の重み計算を追加。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限（apply_sector_cap）と市場レジーム乗数（calc_regime_multiplier）を実装。
    - レジーム乗数は "bull"/"neutral"/"bear" を対応（不明時はフォールバック 1.0）。
  - `src/kabusys/portfolio/position_sizing.py`
    - position sizing（risk_based / equal / score）を実装。単元株（lot_size）、最大ポジション率、aggregate cap（投下資金が available_cash を超える場合の縮小ロジック）等を含む。
    - 手数料・スリッページを保守的に見積もる cost_buffer を考慮。
- 実行監視・データベース初期化
  - `src/kabusys/monitoring/monitoring_db.py`（参照されているが実装ファイルはコードベースに含まれる想定）
    - run_* スクリプトから DB 初期化を行うフック（冪等性で監視テーブルを保証）。
- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite を解析し、稼働率、注文成功率、送信率、P95 レイテンシなどを算出してレポートを標準出力へ出力する CLI を追加。
    - デフォルト閾値を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - --from / --to / --db オプションをサポート。環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パス指定可能。
- リサーチ（ファクター計算）基盤
  - `src/kabusys/research/factor_research.py`
    - モメンタム / Value / Volatility / Liquidity の計算を行うモジュールを追加。DuckDB を用いた prices_daily / raw_financials 参照を想定。
    - 定数（horizon 等）や calc_momentum のドキュメントを追加（calc_momentum の実装は途中の状態で一部未完）。
- パッケージエクスポート
  - `src/kabusys/portfolio/__init__.py` にて主要関数をまとめてエクスポート。

### 変更 (Changed)
- なし（新規初期実装のため変更履歴はありません）。

### 修正 (Fixed)
- なし（新規初期実装のため修正はありません）。

### 破壊的変更 (Removed)
- なし。

### セキュリティ (Security)
- なし。

---

注意事項 / 実装上の補足
- .env の自動読み込みはプロジェクトルートが特定できない場合はスキップされます。テストや特殊環境では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用してください。
- run_monitoring は監視用 DB（settings.sqlite_path）を環境にかかわらず使用します。運用上の注意を確認してください。
- Paper Trading は本番 DB と完全分離するよう設計されています（Settings.paper_sqlite_path を使用）。
- 一部モジュール（例: monitoring_db の詳細実装や research.calc_momentum の完全実装）はソース内コメントで TODO/未実装が示されており、今後のリリースでの拡張が想定されます。