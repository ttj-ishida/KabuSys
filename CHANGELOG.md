KEEP A CHANGELOG
=================

すべての非互換な変更は（もしあれば）メジャーバージョン番号を上げて記載します。
この CHANGELOG は Keep a Changelog の形式に準拠します。

Unreleased
----------

- 現時点で未リリースの作業はありません。

[0.1.0] - 2026-04-13
-------------------

初回リリース。リポジトリ内の主要機能を実装しました。主な追加・修正点は以下の通りです。

Added
- 基本設定 & 自動環境読み込み
  - .env / .env.local の自動読み込み機能を実装（src/kabusys/config.py）。
  - export プレフィックス、クォート文字列、行内コメント等に対応する堅牢なパーサーを実装。
  - Settings クラスで環境値の取得・検証（KABUSYS_ENV, LOG_LEVEL, 各種 DB パス, PAPER_FILL_MODE 等）を提供。

- 実行・監視エントリポイント
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - BrokerClientFactory を用いたブローカークライアント生成。
    - paper_trading 環境では専用 SQLite（PAPER_TRADING_SQLITE_PATH / data/paper_trading.db）を使用し本番 DB と分離。
    - ExecutionEngine の初期化・セッション起動をサポート。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを実行。MONITOR_POLL_INTERVAL 環境変数で間隔変更可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。

- ポートフォリオ構築ロジック（純関数群）
  - 候補選定・重み計算: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights を実装。
  - セクター制限・レジーム調整: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（セクター集中防止）及び calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。
  - 株数決定・投下額制御: src/kabusys/portfolio/position_sizing.py
    - risk_based / equal / score の割当方式を実装。
    - 単元（lot_size）丸め、per-stock 上限、aggregate cap によるスケールダウン、cost_buffer（手数料・スリッページ見積り）対応。

- リサーチ機能（DuckDB ベース）
  - ファクター計算: src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20、出来高指標）、バリュー（PER, ROE）を実装。
    - prices_daily / raw_financials テーブルを利用する設計。
  - 特徴量探索: src/kabusys/research/feature_exploration.py
    - 将来リターン計算（任意ホライズン）、IC（スピアマンのランク相関）計算、統計サマリーを実装。
    - pandas 等に依存せず、標準ライブラリのみで実装。

- AI ニュース NLP スコアリング
  - src/kabusys/ai/news_nlp.py にて、raw_news を集約し OpenAI（gpt-4o-mini）でセンチメントをスコア化して ai_scores テーブルへ書き込む機能を実装。
  - 特長:
    - ニュース収集ウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST 相当の UTC 範囲）。
    - 銘柄単位で記事をトリム（最大記事数・文字数制限）し、最大 20 銘柄/チャンクで API へ送信。
    - 429/タイムアウト/5xx 等に対して指数バックオフでリトライ、応答をバリデーションして ±1.0 でクリップ。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY で提供。

- 運用ツール
  - Paper Trading 検証レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py
    - 稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を集計して標準出力レポートを生成。
    - デフォルト DB は data/paper_trading.db。期間フィルタ（--from / --to）対応。
    - PASS/FAIL 判定基準（稼働率 99% など）を設定。

- ユーティリティ
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX (Linux, macOS, FreeBSD) に対応したプロセス優先度設定（set_process_priority）。
    - CPU affinity 設定ユーティリティ（set_cpu_affinity）を提供。
    - 許可エラーや未対応環境はログ警告で安全にスキップ。

- パッケージ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

Changed
- なし（初回リリースのため全て追加扱い）。

Fixed
- 環境変数パースに関する堅牢化（クォート、エスケープ、インラインコメント、export プレフィックス等の扱いを改善）。
- MONITOR_POLL_INTERVAL の不正値取り扱いを改善し、0 以下や非整数入力時にデフォルトへフォールバックして警告を出す実装（run_monitoring.py）。
- Paper Trading と本番 DB の分離（run_execution.py）が明確化され、paper_trading 環境では別 DB を使用することで実運用データ汚染を防止。

Security
- OpenAI API キーは環境変数または明示引数で供給するよう設計。未設定時は明示的にエラーを返す（news_nlp.py）。

Notes / Known issues / TODO
- src/kabusys/portfolio/risk_adjustment.py:
  - price が欠損（0.0）の場合、セクター露出が過少見積もられる可能性があり、将来的に前日終値や取得原価等のフォールバックを検討する旨の TODO を残しています。
- src/kabusys/portfolio/position_sizing.py:
  - 将来的に銘柄別の lot_size を渡せるよう拡張する TODO を残しています（現状は固定単元対応）。
- src/kabusys/ai/news_nlp.py:
  - 大規模な部分失敗時の部分的な書き込み戦略（DELETE/INSERT の扱い）は注意深く設計されていますが、外部 API の信頼性に依存するため運用ルール（リトライ回数、監視）を検討してください。
- 一部モジュールのエラーハンドリングは「フェイルセーフで継続」する設計ですが、運用上はログ監視とアラート設定を推奨します。

Upgrade Notes
- 実行前に必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を .env に設定してください。
- Paper Trading を利用する場合は KABUSYS_ENV を paper_trading に設定すると data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に分離して記録されます。
- news_nlp を使用する場合は OPENAI_API_KEY の設定が必須です。

ライセンス等
- 本 CHANGELOG はコードベースから推測して作成しています。実際のリリースノートや変更履歴はリポジトリのコミット履歴やリリース管理に基づいて調整してください。