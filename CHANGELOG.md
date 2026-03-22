CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

[Unreleased]
------------

- 現時点で未リリースの変更はありません。

[0.1.0] - 2026-03-22
-------------------

Added
- 初回リリース: KabuSys — 日本株自動売買システムのベース実装を追加。
- パッケージ構成:
  - kabusys.config: 環境変数・設定管理機能を追加。
    - project root（.git または pyproject.toml）を起点として .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）。
    - .env のパースは export プレフィックス、クォート（シングル／ダブル）内のバックスラッシュエスケープ、インラインコメント処理に対応。
    - OS 環境変数を保護する protected set を利用して .env.local の上書きを制御。
    - Settings クラスを提供し、JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須環境変数取得を簡便化（未設定時は ValueError）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証を実装。
  - kabusys.strategy:
    - feature_engineering.build_features:
      - research モジュールで計算された生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
      - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）を行い ±3 でクリップ。
      - DuckDB のトランザクション＋バルク挿入で日付単位の置換（冪等性）を保証。
    - signal_generator.generate_signals:
      - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
      - シグモイド変換や欠損値を中立 0.5 で補完することで頑健性を確保。
      - デフォルト重み（momentum 0.40 等）と閾値（0.60）を提供。ユーザー指定の weights を受け付け、妥当性検査・正規化を実施。
      - Bear レジーム判定（ai_scores の regime_score 平均が負、サンプル数閾値あり）で BUY を抑制。
      - エグジット判定（ストップロス -8%、スコア低下）を実装し、SELL を優先して BUY から除外。
      - DuckDB を用いたトランザクション単位での signals テーブル置換により冪等性を確保。
  - kabusys.research:
    - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials テーブルのみを参照してファクターを算出。
    - feature_exploration: calc_forward_returns（複数ホライズンの将来リターン取得）、calc_ic（Spearman のランク相関）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - 実装は外部依存（pandas 等）を用いず DuckDB + 標準ライブラリで完結。
  - kabusys.backtest:
    - simulator.PortfolioSimulator: スリッページ・手数料を考慮した擬似約定、ポートフォリオ状態管理、mark_to_market、TradeRecord/DailySnapshot を提供。
    - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）を計算。
    - engine.run_backtest: 本番 DB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーションを実行するワークフローを実装。positions の書き戻しや generate_signals の呼び出しを含む。
  - パッケージエクスポート: 各モジュールで明示的に公開 API（__all__）を定義。

Changed
- 初回リリースのため変更履歴はありません（新規追加のみ）。

Fixed
- DB 書き込み時の例外に対して ROLLBACK を試行し、失敗時は警告ログを出す堅牢なトランザクション処理を実装（build_features / generate_signals 等）。
- .env 読み込み失敗時は警告を出して処理を継続するよう改善（テスト環境での扱いを安全に）。

Security
- このリリースでは機密情報（トークン・パスワード）は Settings 経由で環境変数から取得する設計を採用。ファイル読み込みは UTF-8 固定で行い、.env の不正フォーマットを無視して安全にスキップする挙動を取る。

Known limitations / Notes
- 一部設計上の未実装点（engine 内コメント）:
  - トレーリングストップ（peak_price に基づく）や時間決済（保有日数に基づく）等は現バージョンでは未実装。position テーブルに peak_price / entry_date の追跡が必要。
- research / strategy の関数は「ルックアヘッドバイアス防止」を設計方針としており、target_date 時点までのデータのみを使用する実装になっている。
- 外部 API（発注／本番ブローカー接続）への依存は本リリースでは含まれていない（execution パッケージはスケルトン）。

その他
- ログ出力により警告・デバッグ情報を適切に出すよう実装（価格欠損や無効入力等の検出が可能）。
- DuckDB を主要な時系列データ基盤として利用する設計。データスキーマ初期化や calendar 管理は別モジュール（kabusys.data.schema 等）で補完される想定。

----- 

（今後のリリースでは実運用連携、より多彩なリスク管理ルール、ユニットテスト・ドキュメントの追加等を予定）