Keep a Changelog 準拠の形式で、提示されたコードベースの内容から推測して CHANGELOG.md を作成しました。日付は現在日（2026-04-12）を使用しています。必要ならバージョン名・日付は編集してください。

CHANGELOG.md
=============

すべての注目すべき変更点をここで管理します。  
フォーマットは "Keep a Changelog" に準拠しています。  

リンク:
- 既知のカテゴリ: Added, Changed, Fixed, Deprecated, Removed, Security

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-12
-------------------

Added
- 基本機能群の初期実装を追加。
  - 実行・監視用エントリポイント
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper DB を使用し、MockBrokerClient を経由してペーパートレードを分離して実行する設計。 (src/kabusys/run_execution.py)
    - run_monitoring.py: SystemMonitor をポーリングする起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き対応、監視は環境に依らず本番 sqlite_path を使用する旨を明記。プロセス優先度を起動時に設定。 (src/kabusys/run_monitoring.py)
  - 設定管理
    - Settings クラスで環境変数の集中管理を実装。パスや閾値、環境（development / paper_trading / live）などのプロパティを提供。バリデーション（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を行う。自動 .env 読み込み（.env/.env.local、プロジェクトルート判定）を実装。OS 環境変数の保護および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。 (src/kabusys/config.py)
  - ポートフォリオ構築（純関数群）
    - portfolio_builder: 候補選定（スコア順、タイブレーク）と等分配・スコア加重配分の実装。スコア合計が 0 の場合に等分配へフォールバック。 (src/kabusys/portfolio/portfolio_builder.py)
    - risk_adjustment: セクター集中制限適用（既存保有を考慮して候補を除外）と市場レジームに応じた乗数（bull/neutral/bear）を実装。 (src/kabusys/portfolio/risk_adjustment.py)
    - position_sizing: weight / risk-based の株数算出アルゴリズム。lot_size 単位で丸め、aggregate cap（利用可能現金）を超えた場合のスケールダウンと端数配分ロジックを実装。コストバッファ考慮機能あり。 (src/kabusys/portfolio/position_sizing.py)
  - リサーチ（DuckDB ベース）
    - factor_research: モメンタム / ボラティリティ / バリュー系ファクターの計算関数（calc_momentum, calc_volatility, calc_value）を実装。prices_daily / raw_financials を参照する設計。 (src/kabusys/research/factor_research.py)
    - feature_exploration: 将来リターン計算（複数ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリを実装。外部依存を避けた標準ライブラリ実装。 (src/kabusys/research/feature_exploration.py)
    - research パッケージのエクスポートを整備。 (src/kabusys/research/__init__.py)
  - ニュース NLP（OpenAI 統合）
    - ai/news_nlp.py: raw_news を銘柄ごとに集約し OpenAI API（gpt-4o-mini）でセンチメントを付与して ai_scores テーブルへ書き込む機能を実装。バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、429/ネットワーク/5xx のリトライ（指数バックオフ）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗に備えた部分置換の方針などを含む。ニュース時間窓計算ユーティリティあり。 (src/kabusys/ai/news_nlp.py)
  - 監視・検証ツール
    - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等の集計と PASS/FAIL 判定ロジックを実装。コマンドライン引数で期間指定・DBパス指定に対応。 (src/kabusys/tools/paper_verification_report.py)
  - プロセス制御ユーティリティ
    - utils/process_priority.py: クロスプラットフォームでプロセス優先度を設定するユーティリティ（Windows / POSIX 対応）。CPU affinity を最初 N コアへ固定する関数も追加。アクセス拒否等の失敗は警告してスキップする安全設計。 (src/kabusys/utils/process_priority.py)
  - パッケージ基本情報
    - パッケージメタ情報を追加（__version__ = "0.1.0"）。 (src/kabusys/__init__.py)

Changed
- DB 接続ポリシー
  - run_monitoring は監視専用に「環境にかかわらず本番 sqlite_path を使用する」挙動を明示（監視データは本番 DB に対して一元管理する方針）。 (src/kabusys/run_monitoring.py)
  - run_execution は paper_trading 環境では paper_sqlite_path を使用して本番データと完全分離する実装。 (src/kabusys/run_execution.py)
- .env 読み込みの挙動
  - プロジェクトルート探索を __file__ ベースで行い、.env/.env.local の読み込み順・上書きルール（.env.local が上書き、OS 環境変数は protected）を採用。 (src/kabusys/config.py)
- 環境変数パース改善
  - _parse_env_line においてクォートあり・無しの両形式でのパース、バックスラッシュエスケープ処理、インラインコメントの扱いを改善。 (src/kabusys/config.py)

Fixed
- 環境変数の数値パース堅牢化
  - MONITOR_POLL_INTERVAL の解析で 0 以下や不正文字列を検出した場合にデフォルトへフォールバックしてログ警告を出すように（run_monitoring のポーリング間隔）。 (src/kabusys/run_monitoring.py)
- レイテンシ・統計計算の欠損値処理
  - 各種集計（avg/max/P95、fill/send 率など）で NULL/データ不足時に N/A を返す等、欠損時に例外を出さない堅牢化を実施。 (src/kabusys/tools/paper_verification_report.py, src/kabusys/research/*)
- process_priority の失敗時のフォールバック
  - 権限不足や未対応 OS の場合に警告ログを出して処理をスキップする安全な挙動に。 (src/kabusys/utils/process_priority.py)

Notes / Implementation details
- DuckDB と SQLite を併用する設計になっており、分析系は主に DuckDB、監視・発注ログは SQLite を想定。 (各所)
- Paper Trading 環境は明確に本番 DB と分離される（PAPER_TRADING_SQLITE_PATH / is_paper 判定）。
- ニュース NLP の OpenAI 利用は API キー必須（引数または OPENAI_API_KEY 環境変数）。失敗時はエラーを投げるかログを残してスキップする設計になっている。
- いくつかの TODO / 拡張ポイントをコード中に明記（例: position_sizing の銘柄別 lot_size 拡張、price 欠損時のフォールバック戦略など）。

Author
- 自動生成（コードベースからの推測） — 実運用の CHANGELOG とする場合は、リリース日・責任者・既知の既往バグなどを追記してください。