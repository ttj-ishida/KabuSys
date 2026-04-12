KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  
リリース日はコミット時点の想定日です。

## [Unreleased]
- （現在なし）

## [0.1.0] - 2026-04-12
初回リリース。以下の主要機能・モジュールを追加しました。

### Added
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。

- 実行/監視エントリポイント
  - run_execution.py: 実取引/ペーパートレード用の ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、MockBroker を介して本番 DB と完全分離。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て ExecutionEngine.run_session() を呼称。
    - プロセス優先度を起動時に High に設定するユーティリティ呼び出しを実行。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はログ警告のうえデフォルトにフォールバック。
    - 監視は環境に依らず本番用 sqlite_path を使用する設計（監視データは常に共通 DB に保存）。

- 設定/環境変数管理
  - src/kabusys/config.py:
    - .env / .env.local の自動読み込み機能を追加（プロジェクトルートを .git または pyproject.toml で検出）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 複雑な .env パースを実装（export プレフィックス、引用符とエスケープ、インラインコメント処理など）。
    - 各種設定プロパティを提供（DB パス、PID/KILL フラグ、閾値設定、PAPER_FILL_MODE の検証、env/log_level の検証など）。
    - settings 単一インスタンスをエクスポート。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py:
    - シグナルのソート・候補選定（select_candidates）。
    - 等金額・スコア加重での重み計算（calc_equal_weights, calc_score_weights）。スコアが全て 0 の場合は等重にフォールバック。
  - portfolio/position_sizing.py:
    - 各銘柄の発注株数計算（risk_based / equal / score の allocation_method をサポート）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でのスケールダウン、cost_buffer を考慮した保守的見積り。
    - スケールダウン時の端数配分ロジック（再現性のため安定ソート）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 (apply_sector_cap)：既存保有に基づくセクター除外ロジック（"unknown" セクターは制限対象外）。
    - レジーム乗数 calc_regime_multiplier（bull/neutral/bear に対応、未知レジームはフォールバック）。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム、ボラティリティ、バリュー要因の集計関数（calc_momentum, calc_volatility, calc_value）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照して計算。
    - 欠損データ・ウィンドウ長未達成時は None を返す堅牢な実装。
  - research/feature_exploration.py:
    - 将来リターン計算（calc_forward_returns）、IC（スピアマン）計算（calc_ic）、ファクターの統計サマリー（factor_summary）およびランク付けユーティリティ。
    - pandas 等に依存せず標準ライブラリと DuckDB で実装。
  - research/__init__.py で主要関数を公開。

- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - raw_news / news_symbols から銘柄ごとに記事を集約し OpenAI API（gpt-4o-mini）へバッチ送信してセンチメント（-1.0〜1.0）を算出、ai_scores テーブルへ書き込む。
    - バッチサイズ、1銘柄あたりの最大記事数/最大文字数制限、チャンク最大 20 銘柄などのトークン爆発対策を実装。
    - レスポンスバリデーション、スコアの ±1.0 クリップ、部分書き換え（既存コードを保護するため対象コードのみ DELETE → INSERT）などの安全策を実装。
    - 429/ネットワーク/タイムアウト/5xx について指数バックオフによるリトライ。
    - API キー解決（引数 or 環境変数 OPENAI_API_KEY）。未設定時は ValueError。

- 運用ツール
  - tools/paper_verification_report.py:
    - Paper Trading の検証レポート生成スクリプトを追加（期間指定可）。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を計算し PASS/FAIL 判定を出力。
    - DB 存在確認・例外ハンドリング（テーブル欠損時のフォールバック）を実装。
  - tools パッケージ初期化ファイル追加。

- ユーティリティ
  - utils/process_priority.py:
    - Windows / POSIX の差分を吸収してプロセス優先度（high/normal/low）および CPU affinity 設定を行うユーティリティを追加。
    - 実行環境に応じたフォールバック（未対応 OS の場合はスキップ）、権限エラー等は警告でスキップ。

- DB 初期化/統合
  - 各起動スクリプトで sqlite3 と DuckDB 接続を作成し、監視テーブル初期化（init_monitoring_db）を呼ぶことによりテーブル存在を保証。

### Changed
- 設定読み込みの挙動
  - .env の自動読み込みはプロジェクトルートの検出に依存する（__file__ を基点に探索）。CWD に依存しないためパッケージ配布後も安定して動作。
  - .env の読み込みは OS 環境変数を保護する（既存キーを protected として .env.local の上書き時も守る）。
- エラーフォールバックやバリデーションの導入
  - MONITOR_POLL_INTERVAL が不正（0 以下や非整数）の場合はデフォルト 60 秒へフォールバックし警告を出力。
  - PAPER_FILL_MODE や KABUSYS_ENV/LOG_LEVEL の値検証を実装し、不正値時は ValueError を送出。
  - ファクター/リサーチ系関数はデータ不足時に None を返す等、上位での安全な取り扱いを想定した実装。

### Fixed
- （初回リリースのため過去のバグ修正はなし。ファイル内に記載されている TODO／注意点は将来的な改善対象として残す。）

### Notes / Implementation details
- DuckDB と SQLite を併用する設計:
  - DuckDB は大規模時系列データ（prices_daily, raw_financials 等）の集計に利用。
  - SQLite は監視・発注ログ等の軽量ストレージに利用。
- Paper Trading 分離:
  - paper_trading 環境では sqlite の書き込み先を分離し、実発注を模した検証を安全に実行可能。
- OpenAI 呼び出しは外部 API 依存のため、API キー・レート制限・レスポンスフォーマットに注意。
- このリリースは機能群のベースライン提供を目的としており、将来的にテストカバレッジの拡充やエラー監視の強化、lot_size を銘柄ごとに設定する拡張などを予定。

---

（参考）主に変更点のソースファイル:
- src/kabusys/__init__.py
- src/kabusys/config.py
- src/kabusys/run_monitoring.py
- src/kabusys/run_execution.py
- src/kabusys/portfolio/*
- src/kabusys/research/*
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

今後のリリースでは、テスト・エラーハンドリング・可観測性の向上、パフォーマンス最適化、外部サービス（OpenAI・証券 API）との統合テスト結果に基づく改善を予定しています。