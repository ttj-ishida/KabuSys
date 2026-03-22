Keep a Changelog
=================

すべての重要な変更点をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

[Unreleased]: https://example.com/kabusys/compare/HEAD...develop
[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0

0.1.0 - 2026-03-22
------------------

Added
- 初回リリース: KabuSys 日本株自動売買フレームワークの初期実装を追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py にバージョン (0.1.0) と公開モジュールを定義。
  - 環境変数・設定管理
    - src/kabusys/config.py
      - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込み。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用途）。
      - export KEY=val 形式やシングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応した行パーサを実装。
      - OS 環境変数を保護する protected 機構（.env.local での上書き時に既存OSキーを保護）。
      - 必須環境変数取得時の検証メソッド (_require) と各種設定プロパティ（J-Quants, kabuAPI, Slack, DB パス, 環境・ログレベル検証）。
  - 戦略（Strategy）
    - src/kabusys/strategy/feature_engineering.py
      - research モジュール由来の生ファクターを統合して features テーブルに保存する処理を実装（build_features）。
      - ユニバースフィルタ（最低株価・平均売買代金）と Z スコア正規化（指定列）＋±3 クリップを実装。
      - DuckDB トランザクションを用いた日付単位の置換（冪等）を実装。COMMIT/ROLLBACK の安全な扱いとログ出力を含む。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY/SELL シグナルを生成・signals テーブルへ書き込む処理を実装（generate_signals）。
      - コンポーネントスコア（momentum, value, volatility, liquidity, news）の計算ロジックとシグモイド変換、欠損値の中立補完（0.5）を実装。
      - 重みのバリデーション・マージ・再スケーリングを実装（未知キーや非数値はスキップ）。
      - Bear レジーム判定（AI の regime_score 平均が負の場合に BUY を抑制）、および保有ポジションに対するエグジット判定（ストップロス、スコア低下）を実装。
      - SELL 対象は BUY から除外しランクを再付与するポリシーを実装。
  - Research（研究用ユーティリティ）
    - src/kabusys/research/factor_research.py
      - momentum（1/3/6M、MA200乖離）、volatility（20日ATR/相対ATR、平均売買代金、出来高比率）、value（PER, ROE）を DuckDB 上で SQL により計算する関数を実装。
      - データ不足時の None 処理やスキャン範囲のバッファ（カレンダー日換算）などの実装。
    - src/kabusys/research/feature_exploration.py
      - 将来リターン計算（calc_forward_returns、任意ホライズンの一括取得）、IC（スピアマンρ）計算（calc_ic）、ファクター統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
      - Pandas 等に依存せず標準ライブラリのみで実装。
    - research パッケージの __all__ を整備。
  - Data / スキル補助
    - DuckDB を前提とした設計。各処理は prices_daily / raw_financials / features / ai_scores 等のテーブルのみを参照する方針で実装（発注 API への直接依存なし）。
  - Backtest（バックテストフレームワーク）
    - src/kabusys/backtest/simulator.py
      - PortfolioSimulator: メモリ上での約定ロジック（SELL を先、BUY を後）、スリッページ・手数料計算、平均取得単価管理、mark_to_market と DailySnapshot/TradeRecord の記録を実装。
      - BUY の資金再計算（手数料込みで買える株数に調整）や、始値/終値欠損時のログと安全なスキップ処理を実装。
    - src/kabusys/backtest/metrics.py
      - バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を実装。入力は DailySnapshot/TradeRecord のみで DB 参照なし。
      - エッジケース（サンプル不足、ゼロ分散、初期資産 0 など）に対する安全な戻り値処理を実装。
    - src/kabusys/backtest/engine.py
      - run_backtest: 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションを行うエンジンを実装。
      - _build_backtest_conn による日付範囲フィルタ付きコピー（signals/positions を汚染しない）、market_calendar 全件コピー、コピー失敗時の警告ロギングを実装。
      - 日次処理フロー：前日シグナルを約定 → positions を DB に書き戻し（generate_signals の SELL 判定で参照）→ 終値で時価評価 → generate_signals 呼び出し → 発注リスト作成・約定待ち、という一連の流れを実装。
    - backtest パッケージの __all__ を整備。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なしだが、多数のエッジケース保護を実装）
  - .env パーサにおけるクォート／エスケープ／コメント処理を堅牢化。
  - DuckDB のトランザクションにおける COMMIT/ROLLBACK 失敗時のログ保護。
  - シグナル生成・売却判定で価格欠損時に誤クローズしないように警告して判定をスキップ。

Deprecated
- なし

Removed
- なし

Security
- なし

注記 / 設計方針
- ルックアヘッドバイアス防止: すべての戦略・研究処理は target_date 時点のデータのみを参照するよう設計。
- 本番環境汚染回避: バックテスト時は本番 DB の signals/positions を直接更新しない（インメモリコピー + 書き戻しの明確な制御）。
- 外部依存の最小化: Research ツールは pandas 等に依存しない実装（標準ライブラリ + DuckDB）。
- ロギング: 重要な異常やスキップ条件は logger を用いて記録。

今後の予定（例）
- PBR・配当利回り等のバリューファクター拡張。
- トレーリングストップや時間決済などのエグジット条件の追加（StrategyModel.md に未実装の項目あり）。
- AI スコア生成パイプラインの統合（現状は ai_scores テーブル参照のみ）。
- 単体テスト・CI の整備（.env 自動ロードを切るフラグあり）。

[0.1.0]: https://example.com/kabusys/releases/tag/v0.1.0