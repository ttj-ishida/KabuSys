Keep a Changelog
=================

このファイルは Keep a Changelog の仕様に準拠します。
安定化されたリリースと主要な変更点を日本語で記録しています。

フォーマット:
- 変更はセマンティックバージョニングに従って記録します。
- 日付は YYYY-MM-DD 形式で記載します。

Unreleased
----------

- （現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-22
-------------------

初回リリース。日本株向け自動売買フレームワーク「KabuSys」の基本機能を実装しています。主な追加点と設計方針は以下の通りです。

Added
- パッケージ基礎
  - パッケージバージョンを src/kabusys/__init__.py にて "0.1.0" として定義。
  - パブリック API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local と OS 環境変数から設定を自動読み込み（プロジェクトルート判定は .git / pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパース機能を強化（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュによるエスケープ対応）。
  - OS 環境変数を上書きしない保護機構（protected set）を実装。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / データベース / 実行環境等の設定プロパティを取得。値検証（env, log_level の検査）を実施。

- 戦略関連（src/kabusys/strategy）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - 研究モジュール（research）で算出した生ファクターをマージ・ユニバースフィルタ・Zスコア正規化し features テーブルへ冪等的に書き込み。
    - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 >= 5 億円。
    - 正規化対象カラムの Z スコアを ±3 でクリップして外れ値影響を抑制。
    - DuckDB を使ったトランザクション（DELETE→INSERT）による日付単位の置換処理を実装。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティを実装（シグモイド変換、欠損時の中立補完など）。
    - デフォルト重み・閾値を定義し、ユーザ指定の weights を検証・マージ・再スケールするロジックを実装。
    - Bear レジーム判定（AI の regime_score の平均が負でかつサンプル数閾値を満たす場合）により BUY を抑制。
    - エグジット条件（ストップロス -8%、スコア低下）に基づく SELL 生成を実装。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を確保。
    - 位置（positions）テーブルと連携して SELL 判定を行う設計（バックテストや本番運用での整合性を確保）。

- 研究（research）モジュール（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200日移動平均乖離）、Volatility（20日 ATR、相対ATR、平均売買代金、出来高比）、Value（PER/ROE）を DuckDB を用いて算出。
    - 欠損やウィンドウ不足時の扱いを明確化（条件満たさない場合は None）。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルトは 1/5/21 営業日）。
    - IC（スピアマンの ρ）計算、ランク化ユーティリティ（同順位は平均ランク）と統計サマリー機能を提供。
    - pandas 等外部依存を避け、標準ライブラリ／DuckDB のみで実装。

- バックテストフレームワーク（src/kabusys/backtest）
  - ポートフォリオシミュレーター（src/kabusys/backtest/simulator.py）
    - メモリ内でのポジション管理、擬似約定ロジック（スリッページ、手数料）、BUY/SELL 処理（SELL を先に処理）、全量クローズの方針を実装。
    - DailySnapshot / TradeRecord データ構造を定義し、mark_to_market による日次評価を記録。
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - CAGR、Sharpe、最大ドローダウン、勝率、Payoff Ratio、取引数を計算するユーティリティを実装。
  - エンジン（src/kabusys/backtest/engine.py）
    - run_backtest: 本番からインメモリ DuckDB へ必要データをコピーし（signals/positions を汚染しない）、日次ループでシミュレーションを実行。
    - バックテスト用接続構築（テーブル別に日付フィルタしてコピー）や、当日始値/終値取得、positions の書き戻し、シグナル読み取り、ポジションサイズ計算の補助関数を実装。
    - デフォルトの取引パラメータ（初期資金、スリッページ率 0.1%、手数料率 0.055%、1銘柄最大 20%）を設定。

Changed
- （初回リリースのため過去変更なし）

Fixed
- （初回リリースのため過去修正なし）

Notes / Implementation details
- DuckDB を主要な OLAP エンジンとして採用し、prices_daily / features / ai_scores / raw_financials / market_calendar 等テーブルを前提とした実装になっています。
- 多くの処理（features 生成、signals 書込み、positions 書込み）は「日付単位の置換」を行い冪等性（トランザクション + bulk insert）を担保しています。
- .env パーサーはクォート内のエスケープやインラインコメント処理、export プレフィックス等に対応しており、実運用での .env 運用に配慮しています。
- ログ出力と警告が適切に配置されており、データ欠損時のスキップやロールバック失敗時の注意喚起を行います。
- 戦略ロジックは発注 API や実際の execution 層に直接依存しない設計（strategy 層は signals テーブル生成まで）です。

Security
- 特になし（初回リリース）

既知の制限 / TODO（リファクタ／機能拡張候補）
- signal_generator の SELL 条件: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- feature_engineering / research の一部は research 環境前提であり、追加のデータ準備手順が必要。
- バックテストでの資金配分ロジックや部分利確・部分損切りは現状サポートしていない（全量クローズのみ）。
- 単体テストの記載はコード内に見られないため、ユニットテスト整備が望まれる。

参照
- 各モジュールの詳細はソースコード内の docstring に設計方針・処理フローが記載されています。必要に応じて README やドキュメントを別途整備してください。