CHANGELOG
=========

すべての変更は「Keep a Changelog」形式に従って記載しています。  
日付はリリース日を示します。

Unreleased
----------
（現在のところ未リリースの作業はありません）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回公開リリース。パッケージ名: kabusys、バージョン 0.1.0。
- パッケージ構成（主要モジュールを追加）
  - kabusys.config: .env / 環境変数の自動読み込みと Settings クラスによる設定取得を提供
    - プロジェクトルート検出（.git または pyproject.toml を起点）に基づく .env 自動読み込み
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
    - 複雑な .env パーシング対応（export プレフィックス、引用符、エスケープ、インラインコメント取り扱い、保護キー）
    - 必須値取得関数 _require と Settings プロパティ（J-Quants, kabu API, Slack, DB パス, 環境名・ログレベル等）
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）
  - kabusys.research
    - factor_research: momentum / volatility / value 等のファクター計算を DuckDB SQL で実装
      - mom_1m/mom_3m/mom_6m, ma200_dev（200日移動平均乖離）、ATR/atr_pct、avg_turnover、volume_ratio、per/roe など
      - 欠損データ・最小サンプル数を考慮した実装
    - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman ρ）計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）
      - 外部依存を使わず標準ライブラリのみで実装
    - research パッケージのエクスポートを整備
  - kabusys.strategy
    - feature_engineering.build_features
      - research モジュールから生ファクターを取得してマージ、ユニバースフィルタ（最低株価・平均売買代金）適用、Z スコア正規化（指定列）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保証）
      - 価格取得は target_date 以前の最新価格を参照して休場日対応
    - signal_generator.generate_signals
      - features と ai_scores を統合し momentum/value/volatility/liquidity/news コンポーネントを計算して final_score を作成
      - デフォルト重みと閾値（weights, threshold）の取り扱い、渡された weights の検証と再スケーリング
      - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、サンプル数閾値あり）による BUY 抑制
      - SELL（エグジット）判定の実装（ストップロス、スコア低下）。保有銘柄の価格欠損時のスキップや features 欠損時の取り扱いログ出力を行う
      - signals テーブルへ日付単位で置換（トランザクションで原子性保証）
    - strategy パッケージのエクスポートを整備
  - kabusys.backtest
    - engine.run_backtest: 本番 DB からインメモリ DuckDB へデータをコピーして日次ループでシミュレーションを実行
      - データコピーは期間フィルタ（prices_daily, features, ai_scores, market_regime）と market_calendar 全件コピー
      - 日次処理フロー（前日シグナル約定 → positions 書き戻し → 時価評価記録 → generate_signals 呼び出し → 発注リスト生成）
      - get_trading_days 等のユーティリティ利用に対応
    - simulator.PortfolioSimulator
      - BUY/SELL の擬似約定（始値ベース）、スリッページ・手数料の適用、SELL を先に処理するポリシー、BUY は可能な限り手数料込みで株数調整
      - 全クローズのみ対応（部分利確・部分損切りは非対応）
      - mark_to_market での終値評価と DailySnapshot 記録（終値欠損時は 0 評価して WARNING を出力）
      - TradeRecord / DailySnapshot のデータ構造定義
    - metrics.calc_metrics: DailySnapshot と TradeRecord から CAGR、Sharpe、最大ドローダウン、勝率、Payoff 比等を計算
  - パッケージトップ __init__ による主要エクスポートの整理（backtest, strategy 等）

Changed
- （初版のため「変更」は特になし）

Fixed
- （初版のため「修正」は特になし）

Known limitations / Notes
- 一部機能は意図的に未実装・簡易実装の注記あり
  - トレーリングストップ、時間決済（保有日数ベース）は positions テーブルの拡張（peak_price / entry_date 等）を要するため未実装
  - PBR・配当利回り等のバリュー指標は現バージョンでは未実装
  - 発注（execution）層は分離されており、strategy 層は発注 API に直接依存しない設計。execution パッケージはプレースホルダ的に用意
  - 部分約定や部分利確には対応していない（SELL は保有全量をクローズ）
- DB スキーマ（features, signals, positions, prices_daily, raw_financials, ai_scores, market_calendar 等）に依存
- 外部ライブラリ（pandas 等）に依存せず、標準ライブラリと DuckDB のみで実装
- トランザクション失敗時の ROLLBACK に関する警告ログを出力する安全対策を導入

Security
- 機密情報（API トークン等）は Settings を通じて環境変数から取得する設計。.env ファイルの自動ロードは無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）でテスト・運用時の扱いを想定

Removed / Deprecated
- （初版のため該当なし）

Contributors
- コードベースに含まれるモジュール構成に基づいて作成（詳細なコントリビュータ情報はリポジトリのコミット履歴を参照してください）。

--- 
注: 本 CHANGELOG は提示されたソースコード内容から推測して作成しています。実際のリリースノートにはコミットメッセージやリポジトリ運用ポリシーに基づく補足・修正を反映してください。