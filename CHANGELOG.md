CHANGELOG
=========

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

新規リリース
------------

### [Unreleased]

- なし

リリース履歴
------------

### [0.1.0] - 2026-04-12

初回公開リリース。主要な機能群（実行・監視・ポートフォリオ構築・リサーチ・AI ニューススコアリング・ユーティリティ／ツール）を実装・追加しました。

Added（追加）
- 実行／監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用に分離された SQLite DB (data/paper_trading.db) を使用する。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
- 環境設定管理
  - config.py: .env 自動ロード機能（プロジェクトルート判定: .git または pyproject.toml）、.env / .env.local の読み込み順序、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化、細かい .env パースロジック（export プレフィックス、クォート、バックスラッシュエスケープ、コメント扱い）を実装。
  - Settings クラスを導入し、J-Quants / kabuAPI / LINE / DB / 監視 / システム設定などのプロパティを提供（バリデーション含む）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定、等重・スコア加重の重み計算を追加。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate キャップ時のスケーリングと端数配分ロジックを追加。
  - portfolio/risk_adjustment.py: セクター集中上限フィルタ apply_sector_cap、レジーム乗数 calc_regime_multiplier を追加（"bull"/"neutral"/"bear" マッピング、未知レジームはフォールバック）。
  - portfolio/__init__.py: 上記 API をエクスポート。
- リサーチ・ファクター計算
  - research/factor_research.py: Momentum / Volatility / Value ファクター計算を実装（DuckDB の prices_daily / raw_financials を使用）。
  - research/feature_exploration.py: 将来リターン計算、Spearman ランク相関による IC 計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部依存を持たない純粋実装。
  - research/__init__.py: zscore_normalize を含む主要 API をエクスポート。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py: raw_news を OpenAI（gpt-4o-mini）へ送信して銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む機能を追加。バッチ処理（最大 20 銘柄/回）、チャンク単位のリトライ（指数バックオフ）、スコアの ±1.0 クリッピング、ニュース時間ウィンドウ計算、入力トリム（記事数・文字数制限）などを実装。
- ツール
  - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）・リスク却下数を集計し PASS/FAIL 判定を行う。コマンドライン引数 (--from/--to/--db) をサポート。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォーム向けプロセス優先度設定と CPU affinity 設定を追加（psutil 使用）。Windows / POSIX（Linux/Mac/FreeBSD）マッピング、未対応 OS や権限不足時は警告を出してフォールバック。
- パッケージメタ
  - __init__.py: パッケージ名・バージョン __version__ = "0.1.0" を設定。

Changed（変更）
- run_monitoring のデフォルト挙動
  - Monitoring 処理は KABUSYS_ENV にかかわらず production 用 sqlite_path を使用する設計を採用（監視テーブルは本番 DB に対して統一して記録される）。
- run_execution の DB 切り替え
  - ExecutionEngine は paper_trading 環境であれば paper_trading 用の SQLite DB を使用して本番 DB と完全分離する（安全設計）。
- .env ロードの保護
  - OS 環境変数は protected として .env/.env.local の上書きを制御（.env.local は override=True だが protected キーは上書きしない）。

Fixed（修正・安全装置）
- 環境変数／設定の堅牢化
  - config._parse_env_line にてクォート・エスケープ・コメント処理を厳密化し、.env の多様な書式を許容。
  - Settings.paper_fill_mode で不正な値が渡された際に明示的な ValueError を発生させるバリデーションを追加。
- run_monitoring のポーリング間隔設定
  - MONITOR_POLL_INTERVAL が 0 または負、非整数のときはログ警告のうえデフォルト値へフォールバックし、time.sleep による ValueError を予防。
- DB 操作の耐障害性（ツール側）
  - paper_verification_report の generate_report はテーブルが存在しない場合の sqlite3.OperationalError を捕捉してデフォルト値で継続（テーブル欠損時にスクリプトがクラッシュしないように）。

Security（セキュリティ）
- OpenAI API キーの扱い
  - ai/news_nlp.score_news は api_key 引数または環境変数 OPENAI_API_KEY を必須にし、未指定時は ValueError を返す（誤ってキーなしで実行するのを防止）。

Notes（注記・今後の課題）
- position_sizing.calc_position_sizes:
  - price 欠損（0.0）の場合にセーフガードを入れているが、将来的には前日終値や取得原価などのフォールバック価格導入を検討中（コード内に TODO コメントあり）。
- apply_sector_cap:
  - "unknown" セクターの扱いは現時点ではセクター上限を適用しない設計。要運用方針の明確化時に変更する可能性あり。
- ai/news_nlp:
  - API レスポンスの検証・部分書き換え（DELETE / INSERT）戦略を実装しているが、部分失敗時の運用挙動を運用で確認することを推奨。

Removed（削除）
- なし

Deprecated（非推奨）
- なし

セマンティックバージョン
------------------------
- 本リリースは 0.1.0（初回リリース）です。

参照
----
- ソース内の docstring と関数コメントに実装の意図・注意点が記載されています。詳細は各モジュールの docstring を参照してください。