CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

なお、本CHANGELOGは提供されたコードベースの内容から機能・挙動を推測して作成しています。

Unreleased
----------

- （なし）

0.1.0 - 2026-04-17
------------------

### Added
- 基本パッケージ初期リリース (kabusys 0.1.0)
  - パッケージメタ情報を __init__.py に追加（__version__ = "0.1.0"）。

- 実行用スクリプト
  - run_execution.py を追加。
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して paper_trading 用 DB（data/paper_trading.db をデフォルト）に完全分離して記録。
    - 停止フラグ（data/stop_requested.flag）および pid ファイル制御をサポート。
    - コンポーネント組み立て（BrokerClientFactory, OrderRepository, OrderManager, RiskManager, Reconciler, ExecutionEngine）を実装。
    - リスク管理設定（RiskConfig）にデフォルト値を設定、broker.get_available_cash() を初期ポートフォリオ値として使用。

  - run_monitoring.py を追加。
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
    - 監視処理は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグ (data/stop_requested.flag) による優雅な終了をサポート。

- 設定管理
  - config.py を追加。
    - .env/.env.local 自動読み込み機構（OS 環境変数を保護する protected 機構付き）。
    - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープを適切に扱う）。
    - Settings クラスで主要な環境変数をラップ（J-Quants, kabuステーション, LINE, DB パス, 監視閾値, ログレベル, 実行環境フラグ等）。
    - PAPER_FILL_MODE の妥当性チェック、PAPER_TRADING_SQLITE_PATH や各種閾値にデフォルトを設定。

- ポートフォリオ構築ライブラリ
  - portfolio パッケージを追加。
    - portfolio_builder.py
      - select_candidates（スコア順で上位 N を選択）、calc_equal_weights、calc_score_weights（スコア合計が 0 の場合は等金額配分へフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap（セクター集中上限チェック、当日売却予定銘柄の除外対応、"unknown" セクター無視ロジック）。
      - calc_regime_multiplier（market regime に基づく乗数、未定義時はフォールバックと警告）。
    - position_sizing.py
      - calc_position_sizes（risk_based / equal / score の各配分ロジック、lot_size 単位丸め、単銘柄上限・aggregate cap のスケールダウン、cost_buffer による保守見積り、端数処理の安定化ロジック）。
    - package __init__ で主要関数をエクスポート。

- リサーチ / ファクター計算
  - research パッケージを追加。
    - factor_research.py
      - calc_momentum（1M/3M/6M リターン、200日移動平均乖離）, calc_volatility（ATR20、相対 ATR、平均売買代金、出来高比率）, calc_value（PER/ROE の計算）。
      - DuckDB を用いた SQL ベース実装。欠損データ時の None フォールバックを明示。
    - feature_exploration.py
      - calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算、サンプル数が不足する場合は None）、factor_summary（count/mean/std/min/max/median を算出）、rank（同順位は平均ランク）。
    - research.__init__ で zscore_normalize（kabusys.data.stats）と主要関数を公開。

- AI ニュース NLP
  - ai/news_nlp.py を追加。
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を生成して ai_scores テーブルへ反映する処理を実装。
    - 処理フローに関する設計（タイムウィンドウ、1銘柄あたりの記事/文字数上限、最大バッチサイズ、JSON 出力厳格化、429/タイムアウト/5xx の指数バックオフでのリトライ、スコアの ±1.0 クリップ、部分失敗時に既存スコア保護のための部分置換など）を実装方針として明記。
    - calc_news_window ユーティリティを実装（JST -> UTC の窓計算）。
    - OpenAI キー解決（引数 or 環境変数 OPENAI_API_KEY）、未設定時は ValueError。

- ツール
  - tools/paper_verification_report.py を追加。
    - Paper Trading の検証レポート生成ツール（コマンドライン：--from/--to/--db オプション）。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）を集計。
    - 数値判定基準（稼働率 >= 99%、注文成功率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms）を定義し PASS/FAIL を出力。
    - P95 は単純パーセンタイル実装（空リストは N/A）。

- ユーティリティ
  - utils/process_priority.py を追加。
    - set_process_priority(level) の実装（Windows と POSIX の差分吸収、対応 OS の判定、psutil を利用）。
    - set_cpu_affinity(cpu_count) を実装（指定コア数で CPU affinity を固定、例外時は警告でスキップ）。
    - 権限不足や未対応環境での安全なフォールバック（警告ログ）を実装。

- 監視 DB 初期化ユーティリティの利用
  - monitoring.monitoring_db.init_monitoring_db を run_* スクリプトで呼び出し、監視テーブルの存在保証（冪等）を実行起動時に行うようにした。

### Changed
- 環境変数自動ロードの優先順位を明確化
  - 読み込み順: OS 環境 > .env.local > .env
  - OS 環境を protected として .env の上書きを防止する挙動を採用。

- デフォルトとフォールバックの改善
  - MONITOR_POLL_INTERVAL が不正な値（整数でない、0 以下）だった場合にデフォルト 60 秒へフォールバックし、警告を出力。
  - PAPER_FILL_MODE の検証ロジックを追加し、不正な値は ValueError で通知。

- run_monitoring の挙動
  - 監視プロセスは環境にかかわらず production の sqlite_path を用いて監視データを書き込む仕様に変更（安全性・運用上の理由）。

### Fixed
- .env パーサの堅牢化
  - export プレフィックス対応、クォート内でのバックスラッシュエスケープ処理、クォートなしのインラインコメント処理（直前がスペース/タブ の場合にコメントとみなす）など、現実の .env 記述に対する互換性を向上。

- position_sizing の端数処理・スケールダウンの安定化
  - aggregate cap 超過時のスケーリング処理で lot_size 単位の丸め・残余キャッシュを考慮した再配分ロジックを実装し、安定性と再現性を改善。

- research モジュールの SQL クエリでデータ不足時の NULL/None ハンドリングを適切化。

### Deprecated
- なし

### Removed
- なし

### Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で明示的に渡す設計。自動的に外部に送信するような機構は含まれない（設計上の注意喚起）。

注記 / 既知の設計上の制約
- news_nlp の設計では API 応答の JSON 厳密検証や部分置換によるテーブル更新を想定している。API 呼び出し周りは外部依存のため、実運用では API レート・コスト、失敗モードの運用手順の確認が必要。
- apply_sector_cap の現実装は price_map に 0.0（価格欠損）が含まれる場合、エクスポージャーが過少見積りされる可能性があることを注記。将来的に価格フォールバック（前日終値や取得原価）を参照する拡張を検討中。
- set_process_priority / set_cpu_affinity は権限不足（非 root/管理者）やプラットフォーム非対応の場合に警告を出してスキップする安全設計になっているが、期待通りに優先度が適用されない可能性がある。

ライセンスや更なるリリース計画
- 本リリースは基礎機能の集合（監視・実行・ポートフォリオ構築・リサーチ・AI ニュース検出・ユーティリティ・ツール）を含む初期公開版です。今後、テストカバレッジの拡充、ドキュメント（API/アーキテクチャ/運用手順）の整備、運用上の安全機構（再試行/ロギング/監査ログ）の強化を予定しています。