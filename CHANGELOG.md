KEEP A CHANGELOG
=================

すべての重要な変更を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

[0.1.0] - 2026-03-22
-------------------

Added
- 初期リリース。本リポジトリは日本株向け自動売買フレームワーク「KabuSys」を提供します。
- パッケージ基本情報
  - src/kabusys/__init__.py: パッケージ名・バージョン (0.1.0) と公開 API を定義。
- 環境設定管理
  - src/kabusys/config.py:
    - .env ファイル及び環境変数からの設定自動読み込み機能を導入（プロジェクトルートを .git または pyproject.toml から検出）。
    - export KEY=val、シングル/ダブルクォート、エスケープ、インラインコメント等に対応した .env パーサ実装。
    - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 必須環境変数チェック（例: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）と各種既定値（KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、LOG_LEVEL、KABUSYS_ENV）。
    - env 値検証（development / paper_trading / live）やログレベル検証（DEBUG/INFO/...）を実装。
- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py:
    - 研究環境で算出した生ファクターを統合・正規化し features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ（最低株価・最低平均売買代金）、Zスコア正規化（zscore_normalize を利用）と ±3 でのクリップ、日付単位の冪等 UPSERT（DELETE → INSERT のトランザクション）を実装。
    - prices_daily / raw_financials を参照して過去データ欠損に耐性のある設計。
  - src/kabusys/strategy/signal_generator.py:
    - features と ai_scores を統合して最終スコア final_score を算出し、BUY/SELL シグナルを生成する generate_signals を実装。
    - momentum/value/volatility/liquidity/news のコンポーネントスコア計算（シグモイド変換・マスク処理）と重み付け（デフォルト重みを定義、ユーザ指定重みの検証・正規化を実装）。
    - 市場レジーム（AI の regime_score 平均）を用いた Bear 相場検知による BUY 抑制。
    - エグジット判定（ストップロス、スコア低下）を実装（positions テーブル参照）。SELL 優先ポリシー、signals テーブルへの冪等書込を実装。
    - ロギングと例外発生時のトランザクションロールバック処理を明確化。
- 研究用ユーティリティ
  - src/kabusys/research/factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を使ったモメンタム、ATR（atr_pct）、平均売買代金、PER/ROE 等の算出を提供。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns（翌日/翌週/翌月等の将来リターン計算）、calc_ic（Spearman ランク相関での IC 計算）、factor_summary（count/mean/std/min/max/median）、rank（平均ランク付き同順位処理）を実装。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB SQL で完結する形に設計。
  - src/kabusys/research/__init__.py: 主要関数のエクスポート。
- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py:
    - PortfolioSimulator 実装。BUY/SELL の擬似約定（始値・スリッページ・手数料適用）、保有・コストベース管理、日次時価評価（mark_to_market）、TradeRecord/DailySnapshot の記録。
    - SELL を先に処理する等の約定順序ルール、手数料再計算による株数調整を実装。
  - src/kabusys/backtest/metrics.py:
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を実装。
  - src/kabusys/backtest/engine.py:
    - run_backtest を実装。実運用 DB からインメモリ DuckDB へデータをコピー（データ範囲フィルタ）、日次ループ（約定・positions 書戻し・時価評価・signal 生成・ポジションサイジング）を実現。
    - データコピー時の失敗は警告ログでスキップする堅牢化を追加。
  - src/kabusys/backtest/__init__.py: 公開 API を定義。
- モジュール結合
  - 各サブパッケージの __init__ で重要な関数/クラスをエクスポートし、外部からの使用性を向上。

Changed
- 本バージョンは初版のため「Changed」はなし。各モジュールは上記の新規実装で構成。

Fixed
- 本バージョンは初版のため「Fixed」はなし。

Deprecated
- なし

Removed
- なし

Security
- 環境変数の自動読み込みには OS 環境変数を保護する仕組み（protected set）を導入し、.env による既存 OS 変数の上書きを制御可能（override フラグあり）。

Known limitations / Notes
- 一部のエグジット条件（トレーリングストップ、時間決済）は未実装（signal_generator._generate_sell_signals の docstring に記載）。
- features 計算では avg_turnover をユニバースフィルタに使用するが、features テーブル本体には保存しない設計。
- calc_forward_returns は営業日を想定するため、内部でカレンダーバッファ（horizon × 2）を使ってデータスキャン範囲を限定している。
- calc_ic は有効サンプル数が 3 未満の場合 None を返す（統計的不安定性回避）。
- run_backtest は本番 DB からのデータコピー時に列型やスキーマ差異がある場合に警告を出して該当テーブルのコピーをスキップするため、事前にスキーマ整合性を保つことが推奨される。
- 外部依存を最小限にし、DuckDB と標準ライブラリのみで主要処理を行う設計。ただし zscore_normalize 等のユーティリティは kabusys.data.stats に依存するため、その実装は別途必要。

今後の計画（例）
- トレーリングストップ・時間決済の追加（generate_signals 側）。
- 一部処理の最適化（大量銘柄・長期履歴でのクエリ性能向上）。
- 単体テスト・CI の整備（現在はコード上の設計原則を重視して実装）。

注: 本 CHANGELOG は提供されたソースコードから推測して作成した初期変更履歴です。実際のリリースノートや運用ログと差異があり得ます。