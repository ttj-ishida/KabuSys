CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
このプロジェクトはセマンティックバージョニングを採用しています（https://semver.org/）。

[Unreleased]
-------------
（現状なし）

[0.1.0] - 2026-04-17
-------------------

Added
- 基本アーキテクチャと主要コンポーネントを実装
  - パッケージエントリポイントのバージョン定義を追加
    - ファイル: src/kabusys/__init__.py
  - 環境設定管理モジュールを実装（.env/.env.local 自動読み込み、厳格な検証）
    - ファイル: src/kabusys/config.py
    - 特長:
      - プロジェクトルート自動検出 (.git / pyproject.toml を基準)
      - .env のパースで export, シングル/ダブルクォート、エスケープ、インラインコメントへの対応
      - OS 環境変数を保護する override/protected ロジック
      - Settings クラスで各種設定値（DBパス、APIトークン、Paper Trading 用オプション、閾値、環境種別など）をプロパティ経由で取得・検証

- 実行系と監視系の起動スクリプトを追加
  - ファイル:
    - src/kabusys/run_execution.py
    - src/kabusys/run_monitoring.py
  - 特長:
    - プロセス優先度を起動時に設定（high/normal/low）
    - 停止フラグ (data/stop_requested.flag) と PID ファイルの利用による安全な起動/停止
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用
    - Execution は paper_trading 環境時に専用の paper_sqlite_path を使用して本番データと分離
    - MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）

- Execution エンジン周辺の依存コンポーネント実装（構成・デフォルト設定）
  - ファイル: src/kabusys/run_execution.py（使用）
  - 組み立てられるコンポーネント（コードは外部モジュール想定）:
    - BrokerClientFactory（環境に応じたブローカークライアント生成）
    - OrderRepository / OrderManager / Reconciler
    - RiskManager と RiskConfig（デフォルト閾値を設定、初期ポートフォリオ値は broker.get_available_cash() を利用）
    - ExecutionEngine の起動/スレッド管理ロジック

- 監視（Monitoring）用 DB 初期化ユーティリティ追加
  - ファイル参照: src/kabusys/monitoring/monitoring_db.py（呼び出しあり）
  - duckdb と sqlite の併用を想定した初期化と接続

- Portfolio 構築ロジック（純粋関数群）を実装
  - ファイル:
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: シグナルスコアでソートして上位 N を選択
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重
      - スコアが全て 0 の際は等配分へフォールバック（警告ログ）
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中上限チェック（既存ポジションを考慮、"unknown" セクターは除外対象外）
      - calc_regime_multiplier: 市場レジームに応じた投下倍率（bull/neutral/bear のマッピング、未知は警告と 1.0 フォールバック）
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method (risk_based / equal / score) に基づく発注株数計算
      - lot_size, cost_buffer を考慮した丸め・スケーリング・aggregate cap 制御
      - 利用可能現金を超える場合のスケールダウンと残差処理（lot 単位での再配分）

- Research / Factor 計算機能を実装（DuckDB を使用した SQL ベースの実装）
  - ファイル:
    - src/kabusys/research/factor_research.py
      - calc_momentum: 1M/3M/6M リターン、MA200 乖離
      - calc_volatility: 20日 ATR、相対ATR、平均売買代金、出来高比
      - calc_value: PER/ROE（raw_financials から最新レコードを取得）
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 将来リターン（任意ホライズン）を一括で取得
      - calc_ic: スピアマン（ランク）IC の算出（結合・欠損除外・少数データ時は None）
      - rank: 同順位の平均ランク処理（丸めで ties 検出漏れを抑制）
      - factor_summary: count/mean/std/min/max/median の集計
    - src/kabusys/research/__init__.py にてエクスポート

- AI ニュース NLP（OpenAI）統合の下地を実装
  - ファイル: src/kabusys/ai/news_nlp.py
  - 特長:
    - ニュース収集ウィンドウ計算（JST→UTC 変換）
    - OpenAI（gpt-4o-mini）を用いた銘柄別センチメントスコア取得の設計方針と定数
    - バッチ化、最大記事数/文字数のトリム、レスポンスバリデーション、クリッピング、逐次的な ai_scores テーブルの置換（部分失敗耐性）
    - API キー解決ロジックと再試行方針（429 / ネットワーク / 5xx に対する指数バックオフ）
    - （注）ソースは途中で切れている部分があり、実処理の一部は継続実装が必要

- ユーティリティ: プロセス優先度・CPU affinity 設定
  - ファイル: src/kabusys/utils/process_priority.py
  - 特長:
    - Windows / POSIX（Linux, Darwin, FreeBSD）差分を吸収した set_process_priority の実装
    - set_cpu_affinity: 指定コア数に固定する機能
    - 権限不足や未対応 OS の場合は警告を出してスキップ（安全設計）

- ツール: Paper Trading 検証レポート生成
  - ファイル: src/kabusys/tools/paper_verification_report.py
  - 特長:
    - SQLite の paper_trading DB を読み取り、稼働率・注文成功率・送信率・P95 レイテンシ等を算出して標準出力に整形出力
    - CLI オプション: --from / --to / --db
    - デフォルト閾値（PASS/FAIL 判定）を設定:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - P95 算出補助、日付フィルタリング、DB 存在チェック

Changed
- なし（初回リリース相当）

Fixed
- なし（初回リリース相当）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Known limitations
- news_nlp.py の実装は設計上詳細が盛り込まれているが、ファイル末尾で切れているため実際の fetch/send 部分は継続実装が必要です。API 呼び出し・DB 書き込みの最終ロジックは追加作業が必要です。
- position_sizing.py の価格欠損（price が 0.0）時はスキップする設計。将来的には前日終値等のフォールバック価格導入を検討。
- .env パーサは多くのケースを扱えるよう実装しているが、極端なフォーマットは想定外の挙動をする可能性があるため .env.example に従うことを推奨します。
- Monitoring（run_monitoring）は常に「本番」sqlite_path を参照する設計（環境によらない）。Paper Trading と完全に分離したい場合は設定見直しが必要です。
- CPU affinity / process priority の設定は実行環境の権限に依存し、設定できない場合は警告を出して処理を続行します。

Usage highlights
- 監視ループ起動:
  - python -m kabusys.run_monitoring
  - 環境変数: MONITOR_POLL_INTERVAL（秒）
- 実行エンジン起動:
  - python -m kabusys.run_execution
  - paper_trading 環境では PAPER_TRADING_SQLITE_PATH を使用
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - または --db で別 DB 指定

Contributing
- このリポジトリは初回リリース相当です。各機能の完成・テスト拡充（特に news_nlp と ExecutionEngine の統合テスト）にご協力ください。

License
- リポジトリ内に別途記載のない限り、適切なライセンス表記を追加してください。