CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
主にソースコードから推測される追加機能・改善点・挙動について日本語で記載しています。

フォーマット:
- Added: 新規機能
- Changed: 既存挙動の変更 / 重要な設計決定
- Fixed: バグ修正や堅牢性向上
- Security: セキュリティ関連注意事項

Unreleased
----------

- なし

[0.1.0] - 2026-04-13
--------------------

Added
- 実行エントリ/ランナー
  - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。環境に応じて BrokerClient を生成し、注文管理・リスク管理・照合（reconciler）を組み立ててセッションを実行する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
- 設定管理
  - config.py: .env 自動読み込み機能を実装（プロジェクトルート検出 .git / pyproject.toml）。.env / .env.local の優先度管理、保護された OS 環境変数の上書き抑制、export 形式やクォート、エスケープに対応するパーサを追加。
  - Settings クラスを導入し、環境変数から各種設定（DB パス、API トークン、PID ファイルパス、しきい値、環境判定など）をプロパティとして提供。
  - PAPER_FILL_MODE の許容値チェック（instant|partial|never|reject）を追加。
- データベース/ストレージ
  - DuckDB と SQLite を併用する設計を導入。monitoring 用 DB（SQLite）と分析用 DuckDB をそれぞれ接続して使用。
  - Paper Trading 環境では paper_trading 専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離する仕組みを導入。
- 監視・運用ユーティリティ
  - utils/process_priority.py: クロスプラットフォームでプロセス優先度と CPU affinity を設定するユーティリティを追加。Windows / POSIX(Linux, macOS, FreeBSD) を吸収し、権限不足や未対応環境では警告を出してスキップする堅牢な実装。
  - run_* スクリプトは起動時にプロセス優先度を "high" に設定する挙動を持つ。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）を集計し、PASS/FAIL を判定する。期間指定・DB パス指定オプションをサポート。
  - 検証基準（デフォルトの閾値）はソース内定数で定義（稼働率 99%、注文成功率 90% など）。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder: 候補選定 (select_candidates)、等金額配分(calc_equal_weights)、スコア加重配分(calc_score_weights)。
  - portfolio.position_sizing: position size 計算（risk_based / equal / score）、単元株（lot_size）丸め、aggregate cap（available_cash）に基づくスケーリングと端数配分ロジックを実装。
  - portfolio.risk_adjustment: セクター上限適用 (apply_sector_cap) と市場レジームに応じた乗数 calc_regime_multiplier を実装。
- リサーチ / ファクター計算
  - research.factor_research: Momentum / Volatility / Value ファクター計算を DuckDB 上の prices_daily / raw_financials テーブルに対して実装。MA200、ATR、各種リターン等の計算を SQL ウィンドウ関数で行う。
  - research.feature_exploration: 将来リターン計算、IC（Spearman ρ）計算、ファクター統計サマリーとランク変換ユーティリティを実装。外部ライブラリに依存しない純粋 Python 実装。
- AI ニュース NLP
  - ai/news_nlp.py: raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) にバッチで送信し、銘柄ごとのセンチメントスコアを ai_scores テーブルへ書き込む機能を実装。主な特徴:
    - 前日 15:00 JST 〜 当日 08:30 JST を対象にするタイムウィンドウ計算。
    - 最大銘柄数 / 最大文字数でトークン肥大化を抑制（チャンク・トリム）。
    - 最大 20 銘柄/チャンク、429/ネットワーク/5xx に対する指数バックオフ（リトライ上限あり）。
    - レスポンス検証（JSON の results 配列、コード・スコアの形式検査）、スコアを ±1 にクリップ。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を送出。
- パッケージ初期化
  - kabusys/__init__.py に __version__ = "0.1.0" を設定。主要サブパッケージを __all__ に設定。

Changed
- 動作方針・デザイン上の決定
  - 監視 (SystemMonitor) は KABUSYS_ENV に依存せず常に本番用 sqlite_path を使用する設計。Monitoring 側は paper_trading と完全に分離されない点を挙げている（意図的仕様）。
  - .env 自動読み込みの優先順位を OS 環境変数 > .env.local > .env に定義。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加。
  - DB 接続は run_* スクリプトで明示的に開閉し、init_monitoring_db による監視テーブル初期化を冪等に保証。
  - research / portfolio の多くの関数は "DB 参照なし — メモリ内計算のみ" という方針が各モジュールに明記され、テスト容易性を重視した純粋関数設計。

Fixed / Improved
- エラーハンドリング
  - run_monitoring のループ内で monitor.check_once() に例外が発生してもループを継続し、ログ出力して次ポーリングに回すフェイルセーフ処理を導入。
  - process_priority/set_cpu_affinity では権限不足や未実装機能に対して警告ログを出して安全にスキップする実装とした。
  - .env パーサは export プレフィックス、クォート内のバックスラッシュエスケープ、行内コメントの扱い（クォート時は無視、非クォート時は直前が空白ならコメントとみなす）等、実運用でよくあるケースに対応。
  - calc_score_weights: 全銘柄スコアが 0.0 の場合に等金額配分へフォールバックし、警告ログを出すようにして NaN / 0 除算を防止。
  - ファクター / リサーチ系ではデータ不足（ウィンドウ長不足等）を None で返すことで安全に扱えるように設計。
  - Paper verification レポートはテーブル未存在時に sqlite3.OperationalError を捕捉して N/A の扱いに変換し、ツールの頑健性を向上。

Security
- API キーの取り扱い
  - OpenAI API キーは明示的に引数か環境変数から取得し、未設定の場合は失敗（ValueError）することで誤送信を防止。
  - .env ローダーは OS 環境変数を protected として上書きを防ぐ既定挙動を持つ（override フラグの挙動制御あり）。

Notes / Known limitations
- ai/news_nlp.py の完全なエラー処理・DB 書き込みの部分や一部ログの詳細は、ソースの末尾が切れているため推測に基づいて記載しています。実際の部分実装はソース全体を参照してください。
- position_sizing の価格欠損（price が 0.0）の扱いについては TODO コメントが残っており、前日終値や取得原価へのフォールバックは未実装。
- calc_regime_multiplier は未知のレジーム値に対してフォールバック（1.0）し、警告を出す設計。レジーム検出ロジック側の整合性が必要。
- run_monitoring が常に本番 sqlite を使う仕様は運用上の注意点（paper/training と混在し得る）であり、意図的に明記されているため導入時は設定を確認してください。

参考
- 主要ファイル:
  - run_monitoring.py, run_execution.py, config.py, utils/process_priority.py
  - portfolio/*.py, research/*.py, ai/news_nlp.py, tools/paper_verification_report.py

ライセンスやリリース方針に基づき、今後のバージョンでは Breaking Changes / Deprecated / Removed セクションを追記してください。