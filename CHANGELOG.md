CHANGELOG
=========

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- なし

0.1.0 - 2026-03-22
------------------

Added
- 初回公開リリース。
- パッケージ概要
  - kabusys: 日本株自動売買システムのコアライブラリを提供。
  - バージョンは __version__ = "0.1.0"。

- 環境設定/ロード機能 (kabusys.config)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - export 形式やクォート／エスケープ、インラインコメントなどに配慮した .env パーサを実装。
  - Settings クラスを提供し、必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の妥当性検証、各種デフォルトパス（DUCKDB_PATH / SQLITE_PATH）を設定。

- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で算出した生ファクターをマージ・正規化し features テーブルへ保存する機能を実装（build_features）。
  - ユニバースフィルタ（最低株価、20日平均売買代金）を導入。
  - Zスコア正規化（指定列）と ±3 クリップで外れ値を抑制。
  - 日付単位での冪等な置換（トランザクション＋バルク挿入）による features テーブル更新。
  - DuckDB を利用した SQL ベースのデータ取得に対応。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を組み合わせ、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出し最終スコア（final_score）を計算。
  - デフォルト重みや閾値（デフォルト threshold=0.60）を採用。ユーザ指定の重みは検証・正規化して適用。
  - Bear レジーム検知（ai_scores の regime_score の平均 < 0 かつサンプル数閾値以上）により BUY シグナルを抑制。
  - 保有ポジションのエグジット判定（ストップロス、スコア低下）を実装し SELL シグナルを生成。
  - signals テーブルへ日付単位の冪等な置換で結果を書き込み。

- Research（データ分析）機能 (kabusys.research)
  - ファクター計算モジュール（factor_research）
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（20日ATR、相対ATR、平均売買代金、出来高比率）、バリュー（PER、ROE）を計算。
    - prices_daily / raw_financials テーブルのみを参照する純粋な分析関数。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（任意ホライズン：デフォルト [1,5,21] 営業日）、IC（Spearman の ρ）計算、ファクター統計サマリーを実装。
    - ties に対する平均ランク処理や数値検証を考慮した実装。
  - zscore_normalize 等のユーティリティを公開。

- バックテストフレームワーク (kabusys.backtest)
  - PortfolioSimulator による擬似約定ロジック（SELL を先に処理、BUY は割当額に基づく整数株数購入、スリッページ・手数料モデルを適用）。
  - mark_to_market で日次スナップショット（DailySnapshot）を記録し、TradeRecord で約定履歴を保持。
  - run_backtest による日次ループ実装
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピー（signals/positions を汚染しない設計）。
    - 当日始値での約定、positions テーブルへの書き戻し、終値での時価評価、generate_signals による翌日シグナル生成、ポジションサイジング→約定のワークフローを実装。
  - バックテストメトリクス (kabusys.backtest.metrics)
    - CAGR、シャープレシオ（無リスク0）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算する機能を実装。

- データ連携について（期待される DB スキーマ）
  - 本ライブラリは DuckDB 上の以下のテーブルを参照／更新することを想定:
    - prices_daily, raw_financials, features, ai_scores, signals, positions, market_calendar, market_regime
  - init_schema など data.schema 側の存在を前提とする実装になっている（バックテスト用の in-memory 初期化を利用）。

Changed
- 新規リリースのため該当なし。

Fixed
- 新規リリースのため該当なし。

Known limitations / Notes
- 未実装の戦略ルール:
  - トレーリングストップ（peak_price に基づく売却）や時間決済（保有 60 営業日超）などは未実装（コード中に注釈あり）。
  - 部分利確／部分損切りは未対応。SELL は現状「保有全量クローズ」実装。
- データ欠損時の挙動:
  - 価格欠損がある場合は該当処理をスキップまたは警告を出し、安全側のデフォルト（score=0.0、評価額0など）を適用する設計。
- 外部依存:
  - 本リリースは外部発注 API への直接依存を持たない（execution 層は別モジュール）。本番注文送信は別実装が必要。
- 安全性:
  - 環境変数の未設定は Settings が ValueError を投げるため、デプロイ時に必須環境変数を設定する必要あり。

開発者向け移行/導入メモ
- 必須環境変数を .env/.env.local または OS 環境に設定してください（JQUANTS_REFRESH_TOKEN 等）。
- DuckDB に prices_daily / raw_financials 等のテーブルを準備してください。バックテストは run_backtest を使用すると本番 DB を汚染せずに実行できます。
- AI スコア連携を行う場合は ai_scores テーブルを target_date 毎に用意するとシグナル生成時に利用されます。

署名
- 初回リリース: kabusys 0.1.0 (2026-03-22)