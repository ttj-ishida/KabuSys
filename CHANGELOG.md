CHANGELOG
=========

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠しています。
セマンティックバージョニングを採用しています。  

[Unreleased]
------------

- 特になし。初期リリースは 0.1.0 を参照してください。

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等で有用）。
  - .env のパースは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント等に対応。
  - 既存 OS 環境変数を保護するための override/protected ロジックを実装。
  - Settings クラスでアプリケーション設定を提供（J-Quants / kabu API / Slack / DB パス / 環境判定 / ログレベル等）。
  - KABUSYS_ENV と LOG_LEVEL の入力検証を実装（許容値チェックとエラーメッセージ）。

- 戦略（strategy）モジュール
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 側で計算した生ファクターを統合し、ユニバースフィルタ（最低株価、平均売買代金）を適用。
    - 指定日（target_date）に基づき Z スコア正規化（指定列）を行い ±3 でクリップ。
    - features テーブルへの日付単位の置換（DELETE → INSERT、トランザクションにより原子性保証）を実装。
    - ルックアヘッドバイアスを防ぐ設計（target_date 時点のデータのみ使用）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - 正規化済みファクターと ai_scores を統合し、モメンタム／バリュー／ボラティリティ／流動性／ニュース（AI）の各コンポーネントスコアを計算。
    - シグモイド変換、コンポーネントの欠損は中立値 0.5 で補完。
    - 重みのマージ／検証／正規化（デフォルト重みを持ち、ユーザ指定は検証して合計を 1.0 に再スケール）。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値以上の場合）。Bear 時は BUY を抑制。
    - BUY は閾値を超えた銘柄に付与、SELL は保有ポジションに対するエグジット条件（ストップロス、スコア低下）で生成。
    - signals テーブルへの日付単位置換（トランザクションで原子性確保）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）。価格欠損や不正データに対するログ出力と安全なスキップ。

- Research（研究）モジュール（src/kabusys/research/）
  - ファクター計算（factor_research.py）
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB の SQL と一貫したロジックで計算。
    - 営業日ベースのラグ処理、ウィンドウ集計、欠損ハンドリングを考慮。
  - 特徴量探索（feature_exploration.py）
    - 将来リターン計算(calc_forward_returns)：複数ホライズンに対応、入力検証（horizons）。
    - IC（calc_ic）：スピアマンのランク相関を実装（同順位は平均ランク処理）。
    - 統計サマリー（factor_summary）と rank ユーティリティ（ties の平均ランクを考慮）。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。

- データユーティリティ連携
  - zscore_normalize を利用することで特徴量正規化を統一的に適用（research と strategy 間で再利用）。

- バックテストフレームワーク（src/kabusys/backtest/）
  - エンジン（engine.py）
    - 本番 DB からデータをインメモリ DuckDB にコピーして安全にバックテストを実行する _build_backtest_conn を実装（signals / positions を汚さない）。
    - 日次ループ: 約定（前日のシグナルを当日の始値で約定）→ positions 書き戻し → 時価評価 → シグナル生成 → ポジションサイジング の一連処理を実装。
    - デフォルトパラメータ: initial_cash=10_000_000、slippage_rate=0.001、commission_rate=0.00055、max_position_pct=0.20。
  - シミュレータ（simulator.py）
    - PortfolioSimulator: メモリ内で資金・保有・平均取得単価を管理。
    - execute_orders: SELL を先行処理、BUY は資金按分による株数算出（手数料・スリッページ考慮）、部分利確非対応（SELL は全量クローズ）。
    - 約定記録（TradeRecord）と日次スナップショット（DailySnapshot）を保持。
    - mark_to_market で終値評価、終値欠損時は 0 評価し警告ログ出力。
  - メトリクス（metrics.py）
    - バックテスト後の評価指標を計算（CAGR、Sharpe Ratio、Max Drawdown、勝率、Payoff Ratio、総トレード数）。
    - 入力はスナップショットと約定履歴のみ（DB 参照なし）。

- エラーハンドリングとログ
  - 主要な DB 書き込み処理はトランザクションで囲み、例外時は ROLLBACK を試行している（失敗時は WARN）。
  - 価格欠損や不正入力に対する詳細なログ出力を実装。

Changed
- 初回公開のため該当なし。

Fixed
- 初回公開のため該当なし。

Security
- 初回公開のため該当なし。

Deprecated
- 初回公開のため該当なし。

Breaking Changes
- 初回公開のため該当なし。

Notes / Known limitations
- 一部エグジット条件は未実装：
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有日数による強制クローズ）
- generate_signals や feature_engineering は target_date 時点の DB データに依存するため、DB の整合性・欠損データに注意が必要。
- research モジュールは pandas 等に依存しない実装のため、大量データでのパフォーマンス微調整が今後の改善ポイント。
- Buy の割当ロジックや部分利確などの取引戦略上の詳細はシンプル実装に留めている（必要に応じ拡張推奨）。

作者・貢献
- コードベース（初期リリース）の内容に基づき自動生成した CHANGELOG です。実際の貢献者情報はリポジトリのコミットログ等を参照してください。