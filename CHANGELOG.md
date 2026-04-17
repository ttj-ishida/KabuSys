# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
バージョン番号はパッケージ内の __version__（0.1.0）に合わせています。日付はこのスナップショット作成日（2026-04-17）を使用しています。コードから推測して機能追加・修正点・既知の制約をまとめています。

## [Unreleased]

- （現時点のスナップショットに基づく初回公開相当の変更は下の 0.1.0 に記載しています）
- 将来的な改善候補・TODO:
  - position_sizing: 銘柄別の lot_size をサポートするための拡張（現在は全銘柄共通の lot_size を想定）
  - apply_sector_cap: price が欠損（0.0）の場合のフォールバック価格利用（前日終値や取得原価など）
  - ai/news_nlp: 大規模処理の部分的失敗に対する保護やより細かなエラーハンドリングの追加

---

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ初期実装（KabuSys 0.1.0）
  - パッケージ定義とバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0"
- 環境設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - .env/.env.local の自動読み込み（プロジェクトルートを自動検出して読み込む。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
    - export 形式・クォート文字列・行末コメント対応の .env パーサ
    - DB パス（duckdb/sqlite）、paper trading 用 DB パス、各種閾値・フラグ等のプロパティを提供
    - 環境値のバリデーション（KABUSYS_ENV, PAPER_FILL_MODE, LOG_LEVEL 等）
- 実行エントリと監視
  - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）
    - BrokerClientFactory によるブローカークライアント生成
    - ExecutionEngine / OrderManager / OrderRepository / RiskManager / Reconciler を組み立ててセッションをスレッドで実行
    - paper_trading モードでは paper 専用 SQLite（デフォルト data/paper_trading.db）を使用して本番 DB と分離
    - 停止フラグ（data/stop_requested.flag）と pid ファイル操作に対応
    - デフォルトの RiskConfig（max_position_pct=0.20, max_utilization=0.80 など）を設定
  - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）
    - SystemMonitor の初期化とポーリングループを提供
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計
- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークに signal_rank）
    - calc_equal_weights / calc_score_weights（スコア合計が 0 の場合のフォールバック）
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮したセクター集中制限）
    - calc_regime_multiplier（bull/neutral/bear に基づく乗数）
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた position size 計算（risk_based / equal / score）
    - 単元株（lot_size）丸め、per-stock 上限、aggregate cap（利用可能現金でスケールダウン）処理
    - cost_buffer を用いた保守的コスト見積りと残差処理による追加配分
- リサーチ / ファクター計算（DuckDB ベース）
  - モメンタム / ボラティリティ / バリュー計算（src/kabusys/research/factor_research.py）
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns（任意ホライズンの将来リターン算出）
    - calc_ic（スピアマンランク相関での IC 計算）
    - factor_summary（基本統計量）
    - rank（平均ランク処理）
  - research パッケージのエクスポートを整備（src/kabusys/research/__init__.py）
- AI ニュース NLP（OpenAI 経由のセンチメントスコアリング）
  - src/kabusys/ai/news_nlp.py にニューススコアリングの実装
    - ニュース収集ウィンドウ計算（JST ベースのウィンドウを UTC に変換）
    - OpenAI（gpt-4o-mini）へ銘柄ごとにまとめてバッチ送信、最大バッチサイズ 20
    - リトライ（429/ネットワーク/5xx に対する指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ
    - ai_scores テーブルへの置換（部分失敗時に他銘柄スコアを保護するため、対象コードのみ DELETE → INSERT）
    - 実装方針としてルックアヘッドバイアス防止のため date.today()/datetime.today() を直接使用しない設計
- ツール
  - Paper Trading 検証レポート生成ツール（src/kabusys/tools/paper_verification_report.py）
    - CLI から期間指定で paper_trading DB を解析し、稼働率・注文成功率・送信率・レイテンシ等の指標を算出してレポート出力
    - P95 計算、閾値による PASS/FAIL 判定（デフォルト閾値をソース内で定義）
- ユーティリティ
  - プロセス優先度 / CPU affinity 設定ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度（high/normal/low）を設定
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供
    - 権限不足や未対応 OS の場合は警告ログを出して安全にスキップ

### Changed
- （初回リリースのため「変更」は特になし。現状は機能追加の集合として扱っています）

### Fixed
- 環境変数パース時の以下の取り扱いを堅牢化（.env パーサ実装）
  - export プレフィックス、シングル／ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱いなどに対応
- MONITOR_POLL_INTERVAL が不正（非数値または 0 以下）だった場合にデフォルトへフォールバックし、警告ログを出力するようにした

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に供給する必要があり、未設定時は ValueError を送出して誤った処理実行を防止する仕様

---

## 既知の制約・注意点（コードから推測）
- apply_sector_cap: price_map に 0.0 が入るとエクスポージャーが過小評価される可能性があり、現在は TODO コメントでフォールバック価格対応が検討課題として残っている。
- position_sizing: 現状は全銘柄共通の lot_size を想定。将来的に銘柄別単元対応が必要。
- DuckDB の executemany に関する制約に注意（ai/news_nlp のコメントに言及あり）。
- ai/news_nlp の処理ログや部分失敗時の挙動はフェイルセーフ設計だが、大規模運用での細かな例外・レート管理の追加が想定される。
- run_monitoring/run_execution は停止フラグファイル（data/stop_requested.flag）を用いるため、運用時はこのファイルの存在管理に注意すること。
- set_process_priority / set_cpu_affinity は権限やプラットフォームに依存して失敗する可能性があり、その場合は警告ログでスキップされる。

---

もし CHANGELOG をリリース履歴として整備したい場合、今後の変更（バグ修正・機能追加・API 変更等）ごとに上記フォーマット（カテゴリ: Added/Changed/Fixed/…）で追記していくことを推奨します。必要であれば、コミット履歴や Pull Request の要約から自動生成するテンプレートも作成できます。