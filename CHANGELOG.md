# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-13
初回リリース。自動売買システム KabuSys のコア機能群を追加しました。主な追加・設計方針は以下のとおりです。

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として導入。

- 設定・環境変数管理 (`kabusys.config`)
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で探索）。
  - export 付き行やクォート、エスケープ、インラインコメントなどを考慮した堅牢な .env パーサーを実装。
  - 自動ロードを無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` サポート。
  - 環境設定を取得する `Settings` クラスを提供。J-Quants / kabu / LINE / DB パス /監視・閾値などのプロパティを含む。
  - 環境値のバリデーション（`KABUSYS_ENV`、`LOG_LEVEL`、`PAPER_FILL_MODE` 等）。

- 実行エントリスクリプト
  - 実行エンジン起動スクリプト `run_execution.py`
    - `Settings` から環境を読み取り、paper_trading 環境では paper_trading 用 SQLite を使用して本番 DB と分離。
    - プロセス優先度を起動時に High に設定。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine の起動を行う。
    - DB（SQLite / DuckDB）を確実にクローズする finally ブロックを実装。
  - 監視ループ起動スクリプト `run_monitoring.py`
    - `SystemMonitor` を初期化しポーリングループを回す。ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバック。
    - 監視は環境にかかわらず本番の `sqlite_path` を使用する設計。
    - KeyboardInterrupt を受けて安全に終了。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` の呼び出しを各起動時に行い、監視用テーブルの存在を保証（冪等）。

- プロセス制御ユーティリティ (`kabusys.utils.process_priority`)
  - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定（high/normal/low）。
  - CPU affinity を最初の N コアにピン留めする機能。
  - 権限不足や未対応 OS 時には警告ログを出して安全にスキップ。

- ポートフォリオ構築（純粋関数群） (`kabusys.portfolio`)
  - 候補選定、等ウェイト・スコア加重ウェイト計算（`select_candidates`, `calc_equal_weights`, `calc_score_weights`）。
    - 同点時のタイブレークは `signal_rank` を使用。
    - 全スコアが 0 の場合は等金額配分にフォールバック（警告ログ）。
  - セクター集中制限（`apply_sector_cap`）
    - 既存保有のセクター別エクスポージャーを計算して上限超過セクターの新規候補を除外。`unknown` セクターは除外対象外。
    - 当日売却予定銘柄を除外してエクスポージャー算出可能。
  - レジーム乗数（`calc_regime_multiplier`）
    - `bull`/`neutral`/`bear` に基づく乗数（1.0 / 0.7 / 0.3）。未知のレジームは 1.0 にフォールバック（警告）。
  - ポジションサイジング（`calc_position_sizes`）
    - risk_based / equal / score の割当方法サポート。
    - lot_size（単元）丸め、per-stock cap、aggregate cap（利用可能現金に対するスケーリング）、cost_buffer（スリッページ・手数料の見積り）対応。
    - 合計コストが available_cash を超えるとスケールダウンし、残余キャッシュで端数調整を行う再配分ロジックを実装。

- リサーチモジュール（DuckDB ベース） (`kabusys.research`)
  - ファクター計算（`calc_momentum`, `calc_volatility`, `calc_value`）
    - prices_daily / raw_financials テーブルを用いたモメンタム・ボラティリティ・バリュー指標の算出。ウィンドウ不足時は None を返す設計。
    - DuckDB のウィンドウ関数を積極活用し効率的に集計。
  - 特徴量・検証ユーティリティ（`calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`）
    - 将来リターン、スピアマンランク相関による IC、ファクター統計サマリーを標準ライブラリのみで実装。
    - rank 関数は同順位（ties）を平均ランクで処理し、丸めを用いて ties 検出の安定性を確保。

- ニュース NLP / AI スコアリング (`kabusys.ai.news_nlp`)
  - raw_news と news_symbols から対象記事を集約し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄ごとのセンチメント（-1.0〜1.0）を ai_scores テーブルへ書き込む処理を追加。
  - タイムウィンドウの厳密な定義（前日 15:00 JST ～ 当日 08:30 JST、内部は UTC で処理）。
  - バッチサイズ・最大記事数・最大文字数制限、スコアのクリップ、429/ネットワーク/5xx に対する指数バックオフリトライ（最大回数制限）等、耐障害性を考慮。
  - 出力は厳密な JSON 構造を期待し、部分失敗時に既存スコアを保護するための置換戦略（該当コードのみ DELETE→INSERT）を採用。
  - OpenAI API キーは引数または環境変数 `OPENAI_API_KEY` で指定。未設定時は ValueError。

- ツール
  - Paper Trading 検証レポート生成スクリプト `kabusys.tools.paper_verification_report`
    - SQLite（paper_trading DB）から各種メトリクス（稼働率・注文成功率・送信率・レイテンシ）を集計して標準出力にレポート出力。
    - P95 の計算、閾値（稼働率/成功率/送信率/P95 レイテンシ）に基づく PASS/FAIL 判定を実装。
    - CLI オプションで期間フィルタ（--from / --to）および DB パス（--db）を指定可能。
    - DB テーブルが存在しない場合や OperationalError が発生した場合にフォールバックしてレポート生成（堅牢化）。

- DuckDB / SQLite の併用
  - 実行系・リサーチ系で DuckDB を集計用に採用し、監視/発注ログ等の永続化には SQLite を採用する設計。

### Changed
- なし（初回リリースのため、変更履歴は追加のみ）。

### Fixed
- .env パーサーの強化により、export付き行やクォート付き文字列・エスケープ・インラインコメントの正しい読み込みを確保。

### Security
- 環境変数未設定時に明確なエラー（ValueError）を投げることで、秘密情報の未設定を早期発見可能に。

### Notes / Design decisions
- 本リリースでは「本番監視 DB を環境にかかわらず共通で使う」などの設計判断があるため、本番と paper_trading の DB 分離は発注系（ExecutionEngine）側で担保している点に注意。
- 外部 API（kabu / J-Quants / OpenAI）への依存はインターフェース抽象化を通じて行い、テスト時に差し替えやすい設計としています。
- DuckDB に対する一部クエリは大規模データを想定してウィンドウ関数を多用しており、パフォーマンス面でのチューニングの余地があります（将来的な最適化対象）。

---

今後のリリースでは、ドキュメント整備、単体テスト拡充、外部 API クライアントのモック強化、より詳細なエラーハンドリング（レトライ/監視アラート）や CI パイプラインの追加を予定しています。