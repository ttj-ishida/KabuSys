# CHANGELOG

このファイルは Keep a Changelog の形式に準拠しています。
すべての注目すべき変更を時系列で記録します。

## [Unreleased]

- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-11

Added
- 初期リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプト。BrokerClientFactory により環境に応じて実ブローカー／モックを切替え（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用、paper_trading 用 DB に記録）。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用。
- 設定管理
  - kabusys.config.Settings: 環境変数/.env 読み込み、自動ロード（.env / .env.local の優先順位）、各種設定プロパティ（DB パス、PID ファイル、閾値、env 判定等）を整理。
  - .env パーサ実装: export 形式、クォート内のエスケープ、インラインコメントの扱いなどに対応。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定（スコア順）、等配分・スコア加重配分の計算。
  - portfolio.position_sizing: 株数決定ロジック（risk_based / equal / score）。単元株丸め、最大ポジション比率、aggregate cap（利用可能現金に基づくスケーリング）、手数料/スリッページ用 cost_buffer を考慮。lot_size に基づく繰下げ/再配分ロジックを実装。
  - portfolio.risk_adjustment: セクター集中制限（apply_sector_cap）、市場レジームに応じた投資乗数（calc_regime_multiplier）。
- リサーチ機能（DuckDB ベース）
  - research.factor_research: Momentum / Volatility / Value ファクター計算（prices_daily / raw_financials を参照）。200 日移動平均、ATR、平均売買代金、PER/ROE 等を算出。
  - research.feature_exploration: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ランク付けユーティリティ、ファクター統計サマリ。
  - すべて DuckDB 接続を受け取り SQL + Python で完結（外部 API に非依存）。
- AI 関連機能
  - ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングし ai_scores テーブルへ書き込む機能。処理はバッチ（最大 20 銘柄）で API 呼び出し、JSON モードのレスポンスを検証して ±1.0 にクリップ、部分失敗時に既存スコアを保護する形で DELETE→INSERT を実施。リトライ（指数バックオフ）、429/ネットワーク/5xx 対応、JSON パース失敗時の復元（最外側 {} 抽出）などの耐障害性を備える。
  - ai.regime_detector: ETF 1321（日経関連）の MA200 乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。API 失敗時は macro_sentiment=0.0 でフォールバック。
- ユーティリティ
  - utils.process_priority: Windows/Linux/Mac の差分を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足や未サポート環境では安全にスキップして警告を出力。
- パッケージ情報
  - kabusys.__init__.py にバージョン 0.1.0 を設定。

Changed
- （初回リリースのため該当なし）

Fixed / Robustness improvements
- .env 読み込み:
  - quote 内のバックスラッシュエスケープ、export プレフィックス、インラインコメント処理などを考慮してより堅牢にパース。
  - .env.local は .env を上書きするが OS 環境変数は保護。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
- DB 書き込み/トランザクション:
  - ai_scores 書き込みは部分失敗時に既存データを破壊しないよう code を絞って DELETE → INSERT を実行。DuckDB の executemany の制約（空リスト不可）に対応。
  - regime_detector / news_nlp 等で BEGIN/COMMIT/ROLLBACK を適切に使用。
- AI API 呼び出し:
  - RateLimitError / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ。その他の APIError や想定外エラーはログを残して安全にスキップ。
  - レスポンス検証を厳格化（results 配列の存在、各要素の型チェック、未知コード無視、スコアの有限性チェック）。
- 計算ロジックの防御:
  - position_sizing, risk_adjustment, factor 計算等でデータ欠損時に安全にスキップし、ログを出力して不正な数値伝播を防止（例: 価格欠損、0 除算、データ不足）。
  - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告ログを出力。
  - calc_regime_multiplier は未知レジーム時に 1.0 へフォールバックし警告を出力。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- AI モジュールは OpenAI API キー未設定時に明示的にエラーを返す（キー未提供時の誤動作防止）。
- 環境変数の自動ロードで OS 環境変数を保護（上書き不可）。

Notes / 補足
- 多くの機能は DuckDB の prices_daily / raw_financials / raw_news 等のテーブルを前提としており、データ投入・スキーマ整備が必要です。
- 設計方針として「ルックアヘッドバイアスの排除」を重視しており、target_date ベースで過去データのみ参照する実装になっています。
- ドキュメント参照: モジュール docstring に PortfolioConstruction.md / StrategyModel.md 等への言及があり、仕様はそちらを参照する想定です。

--------
（今後のリリースでは各機能のユニットテスト、運用向け監視・メトリクス、さらに細かなエラーハンドリング強化を計画してください。）