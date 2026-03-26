Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測して記載しています。

Keep a Changelog
=================
すべての注目すべき変更をここに記録します。  
このファイルは Keep a Changelog のフォーマットに従います。  
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

[0.1.0] - 2026-03-26
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買用コアライブラリを追加。
  - パッケージエントリポイント
    - src/kabusys/__init__.py: バージョン (0.1.0) と主要サブパッケージのエクスポートを定義。

- 環境変数 / 設定管理
  - src/kabusys/config.py:
    - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）。
    - .env / .env.local の自動読み込み（環境変数優先、.env.local は上書き、OS 環境変数を保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化（テスト向け）。
    - .env パーサ（クォート・エスケープ・export プレフィックス・行内コメント処理対応）。
    - Settings クラスで各種必須設定をプロパティで提供（J-Quants / kabu API / Slack / DB パス / env / log_level 等）。
    - 値検証（KABUSYS_ENV, LOG_LEVEL 等）とデフォルト値の定義。

- ポートフォリオ構築
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: スコア降順ソート（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア比率配分。全銘柄スコアが 0 の場合は等金額配分へフォールバック（WARNING ログ）。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算。
    - 単元（lot_size）丸め、1銘柄上限（max_position_pct）、集計キャップ（available_cash）を考慮。
    - cost_buffer を用いた保守的な約定コスト推定とスケーリングロジック（スケールダウン時の端数配分を残差に基づき決定、決定性確保のため安定ソート）。
    - 価格欠損時のスキップ処理と詳細なデバッグログ出力。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限の適用（既存保有をセクター別に時価評価して上限を超えるセクターの新規候補を除外）。"unknown" セクターは制限適用外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 でフォールバック。

- ストラテジー（研究→特徴量→シグナル）
  - src/kabusys/strategy/feature_engineering.py:
    - build_features: research モジュールから取得した生ファクターを統合し、ユニバースフィルタ（最低株価・最低売買代金）を適用、Z スコア正規化、±3 クリップを行い features テーブルへ日付単位で冪等的に書き込み（トランザクション + バルク挿入）。
    - 欠損・休場日に対応するため target_date 以前の最新価格を参照。
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals:
      - features と ai_scores を統合して momentum/value/volatility/liquidity/news のコンポーネントスコアを算出し final_score を計算（デフォルト重みを採用、ユーザ指定重みは検証・正規化）。
      - AI ニューススコアを統合（未登録は中立）。
      - Bear レジーム検知時は BUY シグナル抑制（ai_scores の regime_score に基づく集計）。
      - BUY シグナル閾値（デフォルト 0.60）による選別、SELL シグナルはストップロスおよびスコア低下で生成。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）と日付単位の冪等的 signals テーブル更新（トランザクション + ROLLBACK 保護）。
    - 生成処理は DuckDB を通じて features / ai_scores / positions / prices_daily を参照。

- リサーチ & ファクター
  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と 200 日移動平均乖離率 (ma200_dev) を計算。
    - calc_volatility: 20 日 ATR、ATR 比率 (atr_pct)、20 日平均売買代金、出来高比 (volume_ratio) を計算。true_range の NULL 伝播を厳密に制御。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算（EPS が 0/欠損の場合は None）。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数不足時は None。
    - rank / factor_summary: ランク変換（同順位は平均ランク）と列ごとの統計要約を提供。
  - research パッケージは zscore_normalize と各ファクター計算を再エクスポート。

- バックテスト
  - src/kabusys/backtest/simulator.py:
    - DailySnapshot / TradeRecord dataclass を定義。
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理と擬似約定ロジックを実装。SELL を先に処理し BUY を後で処理（資金確保のため）。スリッページ・手数料モデルを反映。
    - 約定は単元・スリッページ率・手数料率を考慮し、約定記録（TradeRecord）と日次履歴を保持。
  - src/kabusys/backtest/metrics.py:
    - BacktestMetrics dataclass と各種指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, トレード総数）。
    - 各計算関数は入力のバリデーションとゼロ除算回避を実装。

- パッケージ API
  - strategy / research / portfolio パッケージの __init__.py による主要関数のエクスポートを用意。

Changed
- 初版リリースのため変更履歴なし（今後のバージョンで追記予定）。

Fixed
- 初版リリースのため修正項目なし。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known limitations (コード中コメントからの推測)
- apply_sector_cap:
  - price が 0.0 の場合にエクスポージャーが過少見積りされる可能性があるため、将来的に前日終値や取得原価などのフォールバック価格を導入予定（TODO コメントあり）。
- position_sizing:
  - lot_size は現状グローバル固定（通常 100）で、将来的に銘柄別単元対応の拡張を検討（TODO コメントあり）。
- signal_generator:
  - トレーリングストップ・時間決済など一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- calc_value:
  - PBR・配当利回りは未実装。
- データ前提:
  - 多くの機能は DuckDB の prices_daily, features, ai_scores, raw_financials, positions テーブルを前提としている。スキーマ・データ品質が不足すると処理がスキップされたり警告を出す設計。
- 外部依存:
  - zscore_normalize は kabusys.data.stats に依存（本スナップショットでは該当ファイルを参照）。
- トランザクション安全性:
  - DB 更新処理は BEGIN/COMMIT/ROLLBACK を用いた日付単位の置換で冪等性と原子性を確保。ROLLBACK 失敗時は警告ログを出力。

開発上のメモ（実装から推測）
- ロギングが詳細に組み込まれており、欠損データ・不正設定・異常系に対して警告やデバッグログを出す方針。
- 多くの箇所で「安全第一（スキップ・フォールバック・警告）」の設計が採用されているため、本番導入時は十分なデータ品質と環境変数の設定が前提。
- テスト環境向けに KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動 .env 読み込みを抑制可能。

今後のリリースで期待される改善点（コード内 TODO/未実装より）
- 銘柄別 lot サイズ対応
- price fallback ロジック（セクター曝露計算の堅牢化）
- 追加のエグジット条件（トレーリングストップ、時間決済）
- 追加ファクター（PBR、配当利回り等）
- より詳細な手数料・スリッページモデルの拡張

以上。必要であれば項目の粒度を調整したり、日付・担当者情報を追加した更新版を作成します。