CHANGELOG
=========
すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
今後の改善予定（コード内コメント・TODO から推測）:

- 銘柄ごとの単元情報(lot_size)を導入し、position_sizing の lot_map 対応へ拡張予定。
- position_sizing / risk_adjustment における価格欠損時のフォールバック（前日終値や取得原価など）の導入。
- signal_generator のエグジット条件にトレーリングストップ・時間決済（保有日数）を追加。
- features / research パイプラインの並列化・パフォーマンス改善（大規模データセット向け）。
- テスト用に .env 自動ロードの動作をより詳細に制御する仕組みの追加。

[0.1.0] - 2026-03-26
--------------------

Added
- パッケージ初期リリース (version 0.1.0)。
- 基本パッケージ構成を追加:
  - kabusys.config: 環境変数管理
    - .env/.env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）
    - export 形式・クォート・エスケープ・インラインコメントに対応した .env パーサ実装
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化機能（テスト用途）
    - Settings クラス：必須変数検査（_require）、型・値検証（KABUSYS_ENV, LOG_LEVEL）と便利プロパティ（is_live 等）
  - kabusys.portfolio:
    - portfolio_builder.py
      - select_candidates: スコア降順・タイブレーク実装（score, signal_rank）
      - calc_equal_weights / calc_score_weights: 等配分・スコア加重（全スコア0時は等配分にフォールバック） 
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター別エクスポージャ計算、sell 対象除外、"unknown" セクターは無視）
      - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear とフォールバック）
    - position_sizing.py
      - calc_position_sizes: risk_based / equal / score の割当方式に対応した発注株数計算
      - aggregate cap（available_cash を超える場合のスケールダウン）と lot_size による丸め、cost_buffer による保守的見積り
  - kabusys.strategy:
    - feature_engineering.build_features: research モジュールからファクター取得 → ユニバースフィルタ（株価・流動性）→ Z スコア正規化（±3 クリップ）→ DuckDB へ日単位置換（トランザクション）
    - signal_generator.generate_signals:
      - features と ai_scores の統合による final_score 計算（momentum/value/volatility/liquidity/news の重み付け）
      - 重みの検証・補完・正規化（不正値は警告してスキップ）
      - Bear レジーム検知による BUY 抑制、SELL 優先ポリシー、BUY/Sell のテーブル書き込み（原子性を保証）
      - SELL 判定ロジック（ストップロス、スコア低下）と価格欠損や features 欠損時の安全ハンドリング
  - kabusys.research:
    - factor_research: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials 参照。複数ホライズン・移動平均・ATR・出来高系など）
    - feature_exploration: calc_forward_returns / calc_ic / factor_summary / rank（将来リターン、IC、統計サマリ）
    - zscore_normalize を公開 API に含める（kabusys.data.stats へ依存）
  - kabusys.backtest:
    - metrics.py: バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, trade count）
    - simulator.py:
      - PortfolioSimulator クラス: 擬似約定・ポートフォリオ状態管理、SELL を先に処理するポリシー、スリッページ・手数料モデル、TradeRecord/DailySnapshot 型
- DuckDB を用いた分析パイプラインを中心としたアーキテクチャ（DB 参照は research/strategy/feature_engineering のみ、execution 層に依存しない設計）。
- ロギングと警告を多用した堅牢なエラーハンドリング（例: .env 読み込み失敗の warnings、DB トランザクション失敗時の ROLLBACK ログ、価格欠損時のスキップ警告）。

Fixed
- データ欠損や非有限値（NaN/Inf）に対する耐性を多数実装:
  - feature_engineering / factor_research / signal_generator / research モジュールで None や非有限値の検査と安全なフォールバック実装。
  - generate_signals で無効な weights をスキップし、合計が 1 でない場合に正規化またはデフォルトへフォールバック。
  - position_sizing の aggregate cap スケーリングで端数処理（lot_size 単位）と残余キャッシュの再配分ロジックを実装。
- DB 書き込み時にトランザクション（BEGIN/COMMIT/ROLLBACK）を使い、失敗時に ROLLBACK を試行することで一貫性を確保。

Security
- セキュリティ関連の設定（API トークン等）は Settings 経由で環境変数から取得し、.env ファイルの自動ロードはオプトアウト可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）にしているため、テスト・CI 環境での扱いが容易。

Known limitations / Notes
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別単元情報を導入する予定）。
- risk_adjustment.apply_sector_cap は price_map に 0.0 が入るとエクスポージャが過少見積もられる可能性があり、将来的にフォールバック価格を導入する旨の TODO が残る。
- signal_generator ではトレーリングストップ・時間決済が未実装（コメントで言及）。
- feature_engineering / research の処理は DuckDB の SQL に依存しており、データ品質（欠損・型）により一部結果が None になることがある。
- execution パッケージは存在するが、公開コードでは具体的な API 呼び出し実装は含まれていない（execution 層は別実装想定）。

その他
- 複数箇所で参照されるドキュメント参照（PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等）がコード内に記載されており、設計仕様に従って実装されていることが明記されている。

-----------------------------------------------------------------------------
この CHANGELOG はコードのコメント・実装から推測して作成しています。実際のリリースノートとして使用する場合は、差分履歴（コミットログやリリースタグ）に基づいて適宜修正してください。