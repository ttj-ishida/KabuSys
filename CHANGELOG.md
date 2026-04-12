CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードベースの実装内容から推測して作成しています（実際のリリース履歴と異なる場合があります）。

Unreleased
----------

- ドキュメントやログレベル、環境変数名の拡張・改善を予定
  - .env ファイル読み込み、PAPER_FILL_MODE の妥当性チェック、各種閾値の設定などに関する微調整。
- TODO に基づく将来の改善候補（コード内コメント参照）
  - price が欠損した際のフォールバック価格（前日終値や取得原価など）を導入する予定。
  - 銘柄ごとの lot_size を stocks マスタから読み込むなど、単元株処理の拡張。
  - DuckDB の executemany に関する制約回避や部分失敗時のロールバック/リトライ改善。
- その他運用改善（監視ポーリングやOpenAI呼出しのさらに堅牢な取り扱いなど）

[0.1.0] - 2026-04-12
--------------------

Added
- 初期リリースを想定する主要機能を追加。
  - 実行・監視エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプト。起動時にプロセス優先度設定、SQLite / DuckDB 接続、ブローカークライアント生成、リスク管理・オーダー管理等の組み立てを行い、セッションを実行。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は常に本番 sqlite_path を参照する。
  - 設定管理
    - kabusys.config.Settings: 環境変数・.env の自動読み込み（.env, .env.local）と検証ロジックを実装。プロジェクトルート検出（.git / pyproject.toml）に基づく自動ロード、保護された OS 環境変数の取り扱い、各種設定値（DB パス、PID ファイル、監視閾値、環境種別等）のアクセスプロパティを提供。
    - .env パーサはクォート・エスケープ・インラインコメントの扱いを考慮。
  - ポートフォリオ構築（Portfolio）
    - portfolio_builder.py: シグナル選定（select_candidates）、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights) を提供。スコア全0の際には等金額配分へフォールバック。
    - risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、マーケットレジームに応じた乗数を返す calc_regime_multiplier を実装。
    - position_sizing.py: 各銘柄の発注株数決定ロジック（risk_based / equal / score）、単元切り上げ・aggregate cap（利用可能現金に応じたスケーリング）、cost_buffer を考慮した安全な配分を実装。
  - 研究（Research）
    - factor_research.py: Momentum / Volatility / Value といった主要ファクター計算の実装（DuckDB 接続を受け prices_daily / raw_financials を参照）。
      - calc_momentum, calc_volatility, calc_value：各ファクターを日次で計算し (date, code) ごとの辞書リストを返す。
    - feature_exploration.py: 将来リターン計算(calc_forward_returns)、スピアマンランク相関に基づく IC 計算(calc_ic)、ファクター統計サマリ(factor_summary)、ランク変換(rank) を提供。外部依存を避け標準ライブラリのみで実装。
    - research パッケージのエクスポートを整備（zscore_normalize なども公開）。
  - AI / ニューススコアリング
    - ai/news_nlp.py: raw_news から記事を集約して OpenAI (gpt-4o-mini) へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルに書き込む処理を実装。
      - タイムウィンドウ計算（JST→UTC 変換）、チャンク処理（最大 20 銘柄/チャンク）、トークン肥大化対策（記事数・文字数の上限）、429/ネットワーク/5xx に対するエクスポネンシャルバックオフによるリトライ、レスポンス検証、スコアクリッピング（±1.0）、部分書き換え（DELETE→INSERT）による部分失敗耐性を備える。
  - ユーティリティ
    - utils/process_priority.py: psutil を用いたプロセス優先度設定（Windows / POSIX の差分吸収）と CPU affinity 設定ユーティリティを提供。アクセス権限や未対応 OS の場合に警告を出して安全にスキップする。
  - 運用ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成ツールを提供。稼働率、注文成功率、送信率、P95 レイテンシ等を算出し、閾値に基づく PASS/FAIL 判定を行う。コマンドライン引数で期間・DB パス指定可能。

Changed
- N/A（初期リリース扱いのため既存機能の変更履歴はなし。ただし実装内にフォールバックや冗長チェックを多めに実装し運用上の安全性を高めている点が特徴）

Fixed
- idempotency / エラー耐性の向上
  - init_monitoring_db の呼び出しを通じて監視テーブルの存在を保証（冪等処理）。
  - paper_verification_report は対象テーブルが存在しない場合や OperationalError を捕捉してレポートを継続的に生成できるようにフォールバック処理を実装。
  - OpenAI 呼び出しに関してはリトライ・例外処理・レスポンス検証を実装し、API 失敗時に全体処理が停止しないようにしている。

Security
- OpenAI API キーやその他秘密情報は環境変数経由で取得する設計。Settings._require による未設定時の明示的エラー通知を導入。

Notes / Known limitations
- price 欠損時のエクスポージャー過小見積りや position_sizing の lot_size 固定（現状 100）など、運用上の注意点がコード内コメントとして残されている。
- PAPER_FILL_MODE の不正値や KABUSYS_ENV / LOG_LEVEL の不正値は ValueError として早期に検出する仕様。
- news_nlp.score_news は OpenAI API キーが未指定の場合 ValueError を送出する（明示的な事前チェック設計）。
- DuckDB に対する一部の操作（executemany 等）に関する制約を考慮した実装（params が空でないことのチェック等）が行われているが、部分失敗時のリトライ/ロールバックは今後改善の余地あり。

パッケージ情報
- バージョン: 0.1.0（src/kabusys/__init__.py より）

参照ファイル（主要）
- src/kabusys/run_execution.py
- src/kabusys/run_monitoring.py
- src/kabusys/config.py
- src/kabusys/portfolio/*.py
- src/kabusys/research/*.py
- src/kabusys/ai/news_nlp.py
- src/kabusys/tools/paper_verification_report.py
- src/kabusys/utils/process_priority.py

作成者注
- この CHANGELOG はコードからの推測に基づいて作成しています。実際のリリースノートや過去リリース履歴がある場合は、それに合わせて差し替えてください。