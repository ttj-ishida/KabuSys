CHANGELOG
=========

すべての重要な変更は Keep a Changelog の方針に従って記載しています。  
このファイルは、リポジトリ内のコードから推測できる機能追加・仕様・既知の制約をまとめたものです。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-26
--------------------

Added
-----

- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージのトップレベル定義と公開 API を追加（kabusys.__version__ = "0.1.0"、__all__ に data/strategy/execution/monitoring 等を公開）。

- 環境設定 / ロード機構（kabusys.config）
  - .env ファイルまたは OS 環境変数からの設定値読み込みを実装。
  - プロジェクトルートの自動検出: .git または pyproject.toml を探索してプロジェクトルートを特定。
  - 自動読み込みの優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式をサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理と対応する閉じクォート検出。
    - クォートなしの場合のインラインコメント判定（直前が空白/タブの場合のみ）。
  - .env 読み込みでの上書き制御（override）と OS 環境変数の保護（protected）。
  - Settings クラスにプロパティ化された各種設定値を提供（必須キー取得で未設定時は ValueError）:
    - J-Quants / kabu API / Slack トークン関連の必須設定
    - duckdb/sqlite の既定パス取得
    - KABUSYS_ENV の検証（development/paper_trading/live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - 環境判定ユーティリティ (is_live, is_paper, is_dev)

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選定、同点時は signal_rank でタイブレーク。
    - calc_equal_weights: 等配分 (1/N) を返す。
    - calc_score_weights: スコア正規化配分（合計スコアが 0 の場合は等配分にフォールバックし WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: 同一セクター集中を制限するフィルタ。既存保有の時価ベースでセクター露出を計算し、max_sector_pct を超えるセクターの新規候補を除外。unknown セクターは適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームは 1.0 にフォールバックして WARNING を出す。
  - position_sizing:
    - calc_position_sizes: allocation_method に応じて各銘柄の発注株数を計算。
      - risk_based: ポジションあたりのリスク（risk_pct, stop_loss_pct）に基づく算出。
      - equal/score: weight に基づく金額配分 → 株数算出。
      - 単元（lot_size）で丸め、per-stock の上限（max_position_pct）を考慮。
      - aggregate cap: すべての候補の合計投資額が available_cash を超える場合にスケールダウン。cost_buffer を考慮して保守的に見積もり、端数は lot 単位で残差が大きい順に追加配分するアルゴリズムを実装。
      - 価格欠損時は当該銘柄をスキップ。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュール (calc_momentum / calc_volatility / calc_value) の生ファクターを取得し、ユニバースフィルタ（最低株価300円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（冪等）して保存。トランザクションで原子性を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算（sigmoid 等の変換を含む）。
    - デフォルト重み（momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10）と閾値（default 0.60）を提供。ユーザ重みはバリデーション後にマージ・正規化。
    - Bear レジーム検知時は BUY シグナルを抑制（AI の regime_score を用いて全銘柄の平均が負の場合に Bear と判断。ただしサンプル数閾値あり）。
    - SELL シグナル（エグジット）判定:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が threshold 未満の場合に SELL。
      - 価格が取得できない場合は SELL 判定をスキップ（誤クローズ防止）、features に存在しない保有銘柄は final_score=0 として SELL 扱い。
    - signals テーブルへ日付単位で置換（トランザクションで原子性）。
    - 実装はルックアヘッドを防ぐため target_date 時点のデータのみを使用し、execution 層への依存を持たない設計。

- リサーチユーティリティ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を算出（データ不足時は None）。
    - calc_volatility: 20日 ATR、atr_pct、20日平均売買代金、出来高比率を算出（ウィンドウ不足時は None）。
    - calc_value: raw_financials と当日の価格を組み合わせて PER / ROE を算出（EPS=0 などで None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装、データ不足（<3）では None を返す。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクとするロバストなランク関数を実装。
  - zscore_normalize は re-export。

- バックテスト（kabusys.backtest）
  - metrics:
    - BacktestMetrics データクラスと calc_metrics。CAGR、Sharpe（無リスク=0）、最大ドローダウン、勝率、ペイオフ比、クローズトレード数を算出。
  - simulator:
    - PortfolioSimulator と DailySnapshot / TradeRecord を実装。
    - execute_orders: SELL を先に処理してから BUY（資金確保）、SELL は保有全量クローズ（部分利確非対応）。
    - スリッページ（BUY:+、SELL:-）と手数料率を適用して約定をシミュレート。lot_size を考慮。

- モジュール公開
  - strategy/research/portfolio/backtest の主要関数群を __init__.py で公開し、外部利用を容易にする。

Known limitations / Notes
-------------------------

- 一部機能は将来的な拡張のために TODO や注釈が残されています:
  - position_sizing: 銘柄別 lot_size マップのサポートは未実装（現状は共通 lot_size）。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）だと露出が過少評価され得るため、将来的に前日終値やコストベース等のフォールバックを検討する旨の注記あり。
  - signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - calc_regime_multiplier: Bear 相場でも generate_signals 自体は Bear 時に BUY シグナルを生成しない設計（multiplier は中間調整用の保護）。
- DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）の存在を前提とするため、DB スキーマ準備が必要。
- 外部依存を極力避ける設計（pandas 等を使わず標準ライブラリ＆DuckDB SQL を活用）になっている。
- エラー処理はトランザクションの ROLLBACK 保守、読み込み失敗時の警告出力等で安全性を高めているが、実運用時はさらにモニタリング・検査が必要。

Changed
-------

- なし（初回リリース）

Fixed
-----

- なし（初回リリース）

Security
--------

- なし（初回リリース）

References
----------

- 本 CHANGELOG はコード内の docstring・ログメッセージ・コメントおよび実装から推測して作成しています。各機能の正確な動作確認や API の利用方法については該当モジュールのドキュメント/ソースコードをご参照ください。