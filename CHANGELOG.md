CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
フォーマット: https://keepachangelog.com/ja/

Unreleased
----------

- なし

[0.1.0] - 2026-03-26
--------------------

Added
- 初回リリース。kabusys パッケージの基本機能を実装。
  - パッケージ情報:
    - バージョン: 0.1.0 (src/kabusys/__init__.py)
    - パッケージ公開 API: data, strategy, execution, monitoring をエクスポート

  - 環境設定:
    - .env ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ実装: export プレフィックス対応、クォート内のエスケープ処理、インラインコメント処理などを考慮した堅牢なパース処理。
    - Settings クラスを提供し、必須値取得時に未設定なら ValueError を送出。JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等のプロパティを実装。
    - 設定バリデーション: KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）の検査。

  - ポートフォリオ構築（kabusys.portfolio）:
    - 銘柄選定:
      - select_candidates: BUY シグナルをスコア降順にソートし上位 N 件を返却。スコア同点時のタイブレークは signal_rank の昇順。
    - 重み計算:
      - calc_equal_weights: 等金額配分（各重み = 1/N）。
      - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力）。
    - 株数決定:
      - calc_position_sizes: allocation_method に応じた株数算出（"risk_based" / "equal" / "score" をサポート）。
      - risk_based: 許容リスク率・stop_loss に基づく株数算出。
      - equal/score: 重みと最大利用率に基づく算出。単元（lot_size）で丸め、銘柄毎の上限（max_position_pct）も考慮。
      - aggregate cap: 全銘柄合計金額が利用可能現金を超える場合にスケールダウン。cost_buffer を用いて手数料／スリッページを保守的に見積り、残差は lot_size 単位で再配分（端数配分を frac 順で行う）するロジックを実装。
      - ログ出力・価格欠損時のスキップやデバッグ情報を含む。

    - リスク調整:
      - apply_sector_cap: セクターごとの既存エクスポージャーが閾値を超える場合、新規候補を除外（"unknown" セクターは制限対象外）。当日売却予定銘柄を除外してエクスポージャー計算。
      - calc_regime_multiplier: market レジーム(bull/neutral/bear) に応じた投下資金乗数（1.0 / 0.7 / 0.3）。未知のレジームは 1.0 でフォールバックして警告ログを出力。

  - 戦略（kabusys.strategy）:
    - 特徴量生成:
      - build_features: research モジュールの calc_momentum / calc_volatility / calc_value を組合せ、ユニバースフィルタ（最低株価、20日平均売買代金閾値）を適用、指定列を Z スコア正規化し ±3 でクリップ、DuckDB の features テーブルへ日付単位で置換（トランザクション + バルク挿入）する冪等処理を実装。
    - シグナル生成:
      - generate_signals: features と ai_scores を統合して各銘柄の final_score を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換。
        - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算（sigmoid 変換、欠損は中立 0.5 で補完）。
        - デフォルト重みとユーザ指定重みのマージ・検証（未定義キーや無効値は無視、合計を 1.0 に正規化）。
        - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値以上なら Bear と判定）時は BUY シグナルを抑制。
        - SELL 条件:
          - ストップロス（終値/avg_price - 1 < -8%）
          - final_score が閾値未満
          - SELL は BUY より優先、SELL 対象は BUY から除外しランクを再付与。
        - DuckDB への安全なトランザクション処理（ROLLBACK 時の警告ハンドリング含む）。
        - ロギングにより処理状況を詳細に出力。

  - リサーチ（kabusys.research）
    - factor_research:
      - calc_momentum: mom_1m/3m/6m と ma200_dev を計算（200 日未満は None）。
      - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算（データ不足時は None）。
      - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS=0 や欠損は None）。
    - feature_exploration:
      - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）先のリターンを一括 SQL で取得。
      - calc_ic: factor_records と forward_returns を code で結合し Spearman の ρ（ランク相関）を計算（有効レコード < 3 の場合は None）。
      - rank: 同順位は平均ランクとするランク化（丸めにより ties 検出漏れを防止）。
      - factor_summary: count/mean/std/min/max/median を算出する軽量統計ユーティリティ。
    - 研究用ユーティリティは DuckDB 接続を受け取り prices_daily / raw_financials のみ参照し、外部ライブラリ（pandas 等）に依存しない純粋関数群として実装。

  - バックテスト（kabusys.backtest）
    - simulator:
      - PortfolioSimulator: メモリ内でポートフォリオ状態を管理。SELL を先、BUY を後に処理。SELL は保有全量クローズ（部分利確非対応）。スリッページ / 手数料モデルを適用して TradeRecord を記録。DailySnapshot を保持。
    - metrics:
      - calc_metrics: DailySnapshot と TradeRecord から評価指標を計算して BacktestMetrics を返す（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
      - 内部計算は営業日換算や年次化（Sharpe は年間252営業日）などを考慮。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Limitations
- 一部の機能は将来拡張の余地あり（コード内 TODO 注記あり）:
  - position_sizing: 銘柄別単元サイズ (lot_map) のサポートを将来想定。
  - apply_sector_cap: price が欠損（0.0）だとエクスポージャーが過少見積りされる可能性があるため、将来的にフォールバック価格を使用する検討。
  - sell の一部条件（トレーリングストップや時間決済）は未実装で、positions テーブルに peak_price / entry_date 等の追加が必要。
- DuckDB を前提とするテーブルスキーマ（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、運用前にスキーマ準備が必要。
- features の正規化ユーティリティ（zscore_normalize）は kabusys.data.stats に実装済みで呼び出しているが、本リリースでは外部データ準備とスキーマ整備が前提。

Acknowledgements
- ドキュメント内参照: PortfolioConstruction.md, StrategyModel.md, UniverseDefinition.md, BacktestFramework.md（設計参照のためコードコメントに記載）。

References
- ソースコードは src/kabusys 以下に配置。テスト・CI の指示は含まれていません。