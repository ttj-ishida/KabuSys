CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

フォーマット
------------
各リリースごとに Added / Changed / Fixed / Removed / Known issues 等を記載しています。  
日付はコードベースから推測した最新変更日を使用しています。

Unreleased
----------
- なし

[0.1.0] - 2026-03-22
--------------------
初回リリース（推測）として、以下の主要コンポーネントと機能を実装しました。

Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン 0.1.0。
  - __all__ を介した主要サブパッケージ公開: data, strategy, execution, monitoring（execution と monitoring の実装は空または別途実装想定）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用）。
  - .env パーサーの実装（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い、無効行スキップ）。
  - 環境変数の保護（既存 OS 環境を protected として上書きを防止）。
  - Settings クラス提供。J-Quants / kabu ステーション / Slack / DB パス等のプロパティを定義し、必須変数チェックや値検証（KABUSYS_ENV, LOG_LEVEL の妥当性検査）を行う。
- 戦略 (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features)
    - research モジュールで生成した生ファクターをマージ、ユニバースフィルタ適用、Z スコア正規化、±3 でクリップし features テーブルに UPSERT（トランザクションで日付単位の置換）する処理を実装。
    - ユニバースフィルタのデフォルト基準: 最低株価 300 円、20 日平均売買代金 5 億円。
    - DuckDB 接続 (prices_daily / raw_financials) を使用し、ルックアヘッドを防ぐため target_date 時点のみ参照。
  - シグナル生成 (signal_generator.generate_signals)
    - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換挿入（冪等）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。重みの入力は検証・正規化される。
    - BUY 閾値デフォルト 0.60。Bear レジーム検出時は BUY を抑制。
    - SELL のエグジット条件にストップロス（-8%）とスコア低下判定を実装。positions テーブルを参照して判断。
    - AI スコア未登録時は中立値（0.5）で補完。
- リサーチ (kabusys.research)
  - ファクター計算 (research.factor_research)
    - Momentum（mom_1m/mom_3m/mom_6m、MA200乖離）、Volatility（20日 ATR、相対 ATR、20 日平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の SQL とウィンドウ関数で実装。
    - 欠損・データ不足に対する扱い（十分なウィンドウ行数がない場合は None）。
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン calc_forward_returns（複数ホライズンを同時取得）、IC（rank ベースの Spearman 相関）計算、ファクター統計サマリー（count/mean/std/min/max/median）、ランク付けユーティリティを実装。
    - pandas 等に依存せず標準ライブラリのみで実装。
  - モジュールレベルで主要関数を __all__ にエクスポート。
- バックテストフレームワーク (kabusys.backtest)
  - シミュレータ (simulator.PortfolioSimulator)
    - メモリ内での約定処理、売買順序（SELL を先、BUY を後）、BUY の資金不足時再計算ロジック、スリッページ・手数料モデル、全量クローズ SELL（部分利確未対応）、時価評価（mark_to_market）を実装。
    - TradeRecord / DailySnapshot dataclass を定義。
  - メトリクス (metrics.calc_metrics)
    - CAGR, Sharpe Ratio（無リスク金利 0 前提、年次化 by 252 営業日）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。
  - エンジン (engine.run_backtest)
    - 本番 DB からインメモリ DuckDB へデータをコピーしてバックテスト用 DB を構築、日次ループでシミュレータに約定させつつ generate_signals を呼び出すフローを実装。
    - positions を signals 生成前に書き戻す仕組み（_write_positions）を実装し、generate_signals の SELL 判定に対応。
    - データコピー時に日付範囲でフィルタ（prices_daily, features, ai_scores, market_regime 等）し、market_calendar は全件コピー（コピー失敗は警告ログでスキップ）。
    - ポジションサイジングは max_position_pct（デフォルト 20%）等を考慮して配分を計算。
  - パブリック API を __all__ で公開（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。
- 内部ユーティリティ
  - zscore_normalize を含むデータ正規化ユーティリティ（kabusys.data.stats で提供される想定）を活用。

Changed
- なし（初回リリース想定）

Fixed
- なし（初回リリース想定）

Removed
- なし

Known issues / Limitations
- 一部未実装または意図的に保留された機能（コード内コメントに明記）
  - トレーリングストップや時間決済（positions に peak_price / entry_date が必要）: _generate_sell_signals では未実装。
  - Value ファクターの PBR・配当利回りは未実装。
  - execution 層（実際の発注 API）への依存は deliberately 回避されており、実運用では execution 層の実装が必要。
  - strategy.feature_engineering は kabusys.research 側の生ファクター計算に依存するため、research 用データ生成パイプラインが別途必要。
  - execution と monitoring パッケージは初期状態では空（または実装対象外）で、運用環境への統合は追加作業が必要。
- エラー処理
  - DB コピーやファイル読み込みで例外が発生した場合、警告ログを出して処理の一部をスキップする設計。ただし、重大なデータ欠損ケースでは明示的な例外伝播が発生する箇所もある（基本的に早期検出を優先）。
- テストに関して
  - 自動 .env ロードはテスト中に副作用を起こす可能性があるため KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化が必要。

Notes（実装上の設計判断・安全策）
- ルックアヘッドバイアスを防ぐため、すべての分析/シグナル生成は target_date 時点までのデータのみを参照する設計。
- ファクターの欠損に対しては中立値（0.5）で補完するポリシーを採用し、欠損による不当な評価低下を抑制。
- トランザクション＋バルク挿入で日付単位の置換を行い、テーブルの更新を原子的に実施。
- 重みや閾値などは外部から上書き可能だが入力値は厳密に検証・正規化する。

今後の改善提案（参考）
- execution パッケージに実運用向けの kabu API / 注文送信機能を実装。
- monitoring（Slack 通知等）と運用ダッシュボードの実装。
- PBR・配当利回りの追加や、SELL ロジックのトレーリングストップ/時間決済の実装。
- 単体テストと統合テストの整備（特に DB 操作とシミュレータ周り）。
- ドキュメント（StrategyModel.md, BacktestFramework.md 等）の整備とサンプルデータを用いたチュートリアル追加。

---  
（この CHANGELOG は提示されたコードベースの内容から推測して作成しています。実際のリリースノートやバージョン履歴がある場合はそちらを優先してください。）