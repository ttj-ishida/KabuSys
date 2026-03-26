CHANGELOG
=========

すべての notable な変更履歴をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

[Unreleased]
------------

（現時点では未リリースの差分はありません。）

[0.1.0] - 2026-03-26
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ基礎
    - src/kabusys/__init__.py にてバージョン管理と主要サブパッケージのエクスポートを追加。
  - 環境設定 / ロード
    - src/kabusys/config.py
      - .env / .env.local の自動読み込み機能を実装（プロジェクトルート検出は .git または pyproject.toml を参照）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト時に便利）。
      - .env パース処理を充実化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメントの扱い）。
      - ファイル読み込み失敗時に警告発行。
      - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境・ログレベル等の取得・検証（必須環境変数未設定時は ValueError を送出）。
  - ポートフォリオ構築
    - src/kabusys/portfolio/portfolio_builder.py
      - select_candidates: BUY シグナルのスコア降順選定（タイブレークは signal_rank）。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
    - src/kabusys/portfolio/position_sizing.py
      - calc_position_sizes: allocation_method（risk_based / equal / score）に対応した株数算出。
      - リスクベース算出、ポジション上限・単元株丸め、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的コスト見積り、端数処理の再配分ロジックを実装。
    - src/kabusys/portfolio/risk_adjustment.py
      - apply_sector_cap: セクター集中制限（既存保有比率が閾値を超えるセクターの新規候補を除外）。
      - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバックで 1.0）。
  - ストラテジー / シグナル生成
    - src/kabusys/strategy/feature_engineering.py
      - build_features: research モジュールで算出した生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（指定列）、±3 でクリップし、DuckDB の features テーブルへ日付単位で冪等に書き込む（トランザクション使用）。
      - ユニバース最低値等の定数を定義（_MIN_PRICE=300 円、_MIN_TURNOVER=5e8 など）。
    - src/kabusys/strategy/signal_generator.py
      - generate_signals: features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で書き込む（冪等）。
      - final_score 計算は momentum/value/volatility/liquidity/news の重み付き合算（デフォルト重みを用意、ユーザ重みの検証と再スケール処理を実装）。
      - AI スコアの補完、コンポーネント欠損値は中立 0.5 で補完。
      - Bear レジーム判定（ai_scores の regime_score を集計）、Bear 時は BUY 抑制。
      - SELL のエグジット判定実装（ストップロス、スコア低下）。価格欠損時の判定スキップや、features に存在しない保有銘柄はスコア 0.0 とみなす挙動を明確化。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py
      - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照してモメンタム・ATR・出来高・PER/ROE 等を計算。
      - ウィンドウ不足時は None を返す設計。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）に対する将来リターンを一括 SQL で取得。
      - calc_ic: スピアマンのランク相関（IC）計算。サンプル数 3 未満は None。
      - factor_summary / rank: ファクター統計サマリと同順位平均ランク処理（round による tie 保護）。
    - research パッケージの public API を __init__.py で整理。
  - バックテスト / シミュレータ / メトリクス
    - src/kabusys/backtest/simulator.py
      - PortfolioSimulator: メモリ内ポートフォリオ管理、約定処理（SELL を先、続けて BUY）、スリッページ・手数料適用、TradeRecord / DailySnapshot のデータ構造定義。
      - SELL は保有全量クローズ（部分利確は未対応）。
    - src/kabusys/backtest/metrics.py
      - 各種バックテスト指標算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。
      - 実装は DailySnapshot と TradeRecord のみを入力に取る純粋関数設計。
  - コード構成
    - strategy, portfolio, research, backtest など主要モジュールをパッケージ化し、__all__ 経由で公開 API を整理。

Changed
- 初版リリースのため特になし（初期導入）。

Fixed
- .env パーサで以下をサポート／改善
  - export KEY=val 形式への対応。
  - クォートされた値内のバックスラッシュエスケープ処理の実装（閉じクォートまでを正しく取得）。
  - クォートなし値の行内コメント判定ルールを明示（'#' の直前が空白/タブの場合はコメント扱い）。
  - .env ファイル読み込み失敗時に warnings.warn を発行して自動ロードの失敗を明示。

Security
- 重要環境変数未設定時は ValueError を送出して明示的に起動失敗させる（誤設定で秘密情報が漏れたまま動作するのを防止）。

Notes / Known limitations / TODO
- position_sizing の lot_size は現在全銘柄共通（将来的には銘柄別 lot_map への拡張を想定）。
- apply_sector_cap: price_map に price が欠損（0.0）だとエクスポージャー過少見積りになり得る旨の TODO コメントあり（前日終値等でフォールバックする余地）。
- signal_generator の未実装エグジット条件：トレーリングストップ・時間決済は positions テーブルに peak_price / entry_date が必要で未実装。
- PortfolioSimulator の BUY/SELL 部分的な仕様（例: SELL は全量クローズ）や lot_size の扱いは現時点の仕様。実運用前に要要件確認。
- 一部モジュールが外部モジュール（kabusys.data.stats など）に依存している（当該実装は本差分に含まれていない可能性あり）。

Acknowledgements
- 本リリースは内部設計ドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づいた初期実装群をまとめたものです。外部 API（kabu ステーション、Slack 連携等）への接続設定は Settings を通じて行います。

ーーーーー

この CHANGELOG はコードの現在の内容から推測して作成しています。追加で反映したい変更点やリリース日・カテゴリの調整があれば指示ください。