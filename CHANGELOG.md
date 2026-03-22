Keep a Changelog に準拠した CHANGELOG.md（日本語）
※コード内容から推測して作成しています。

All notable changes to this project will be documented in this file.
The format is based on "Keep a Changelog" and this project adheres to Semantic Versioning.

Unreleased
---------
- （なし）

[0.1.0] - 2026-03-22
--------------------
初回リリース。以下の主要コンポーネントと機能を実装・追加。

Added
- パッケージ化
  - kabusys パッケージ初版（バージョン 0.1.0）。
  - エクスポート: data / strategy / execution / monitoring を __all__ に設定。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点にルートを探索（cwd 非依存）。
  - .env のパース機能を強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、
    - インラインコメントの扱い、無効行のスキップ等。
  - 自動ロードの順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護（上書き回避）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - Settings クラスを提供（J-Quants / kabu / Slack / DB パス / システム設定等のプロパティ）。
  - 環境値チェック（KABUSYS_ENV / LOG_LEVEL のバリデーション）と必須変数チェック（_require）。

- 戦略（strategy パッケージ）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で算出された raw factor を取り込み、ユニバースフィルタ（最小株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize 利用）し ±3 でクリップ。
    - features テーブルへの日付ごとの置換（冪等・トランザクションで原子性を担保）。
    - build_features(conn, target_date) を公開 API として提供。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して最終スコア（final_score）を計算。
    - デフォルト重みを実装（momentum/value/volatility/liquidity/news）と重みの検証・再スケーリング。
    - Bear レジーム判定（ai_scores の regime_score 平均が負で、サンプル数閾値を満たす場合）。
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8%、スコア低下）シグナル生成。
    - signals テーブルへの日付単位置換（冪等・トランザクション保証）。
    - generate_signals(conn, target_date, threshold=None, weights=None) を公開 API として提供。
    - 欠損値に対する中立補完（コンポーネントが None の場合は 0.5）など安全策を実装。

- リサーチ（research パッケージ）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム: mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）。
    - ボラティリティ/流動性: 20日 ATR、相対 ATR (atr_pct)、20日平均売買代金、volume_ratio。
    - バリュー: PER（EPS より算出、EPS が 0/欠損なら None）、ROE（raw_financials より取得）。
    - DuckDB を用いた SQL + Python 実装で、prices_daily / raw_financials のみ参照。
  - 特徴量探索・評価（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト [1,5,21]）に対応、入力検証あり。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンの順位相関（ランク）実装。サンプル閾値（3）未満は None。
    - factor_summary: 各カラムの基本統計量（count/mean/std/min/max/median）計算。
    - ユーティリティ: tie を平均ランクで扱う rank 関数（丸めによる安定化あり）。
  - research パッケージの __all__ で主要関数を公開。

- バックテスト（backtest パッケージ）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: BUY/SELL の擬似約定ロジック、スリッページ（率）・手数料（率）モデル、BUY は株数算出（floor）、SELL は保有全量クローズ。
    - mark_to_market による日次評価と DailySnapshot / TradeRecord の記録。
    - 約定記録に realized_pnl を持たせる（SELL 時のみ）。
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - BacktestMetrics dataclass（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）。
    - calc_metrics により各指標を算出するユーティリティ群（CAGR, Sharpe, MaxDD, WinRate, Payoff）。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest: 本番 DB から日付範囲で必要テーブルをインメモリ DuckDB にコピーしてバックテストを実行。
    - データコピー時にテーブルごとに日付フィルタを適用（prices_daily, features, ai_scores, market_regime 等）。
    - positions の書き戻し、signals 読み出し、日次ループでの約定 → 評価 → シグナル生成の一連処理を実装。
    - 公開型戻り値 BacktestResult（history, trades, metrics）。
    - パラメータ: initial_cash, slippage_rate, commission_rate, max_position_pct 等を受け付ける。
  - backtest パッケージの __all__ で主要 API を公開。

Changed
- -（初版のため該当なし）

Deprecated
- -（初版のため該当なし）

Removed
- -（初版のため該当なし）

Fixed
- -（初版のため該当なし）

Security
- .env ファイルの読み込み失敗時に warnings.warn を出す実装（読み込み失敗が可視化される）。
- OS 環境変数を protected として扱い、自動ロードでの上書きを避ける仕様。

Known limitations / Notes（既知の制約・未実装項目）
- 戦略:
  - generate_signals のエグジット条件ではトレーリングストップ（直近最高値ベース）や時間決済（保有 60 営業日超）等は未実装（コード内コメントで明示）。
  - バリューファクターでは PBR / 配当利回りは未実装。
- リサーチ:
  - calc_forward_returns はホライズンが営業日ベースである点に注意（内部でカレンダーバッファを使っている）。
- バックテスト:
  - run_backtest は本番 DB からのコピー時に一部のテーブルコピー失敗をスキップする挙動（警告ログ）。
  - signals / positions 等のスキーマ依存があるため、事前にスキーマ初期化（init_schema）と互換性のあるテーブルが必要。
- テスト・CI:
  - テストコードや CI 設定はソース内に見られない（別途追加が必要）。

Authors
- コードベース内のモジュール実装に基づいて推測して記載しています。

ライセンス・バージョニング
- パッケージ __version__ は 0.1.0 に設定済み（src/kabusys/__init__.py）。

（注）本 CHANGELOG は提供されたソースコードの内容から正確に推測して作成しています。実際のプロジェクトのリリースノートとして使う場合は、追加の運用情報・日付・実際の変更履歴に合わせて編集してください。