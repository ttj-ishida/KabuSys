Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。
このプロジェクトは Keep a Changelog のガイドラインに従っています。
安定版リリースはセマンティックバージョニングに従います。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-22

初回公開リリース。

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリ: src/kabusys/__init__.py に __version__ と __all__ を定義

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）
  - 行単位の高度な .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応）
  - .env 読み込み時の上書き制御と「保護」キー（OS 環境変数を保護）を実装
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート
  - Settings クラスを実装し、J-Quants / kabu API / Slack / DB パス / ログ環境などの設定プロパティを提供
  - 必須環境変数未設定時に ValueError を投げる _require() を実装
  - env/log_level の値検証（許容値の検査）を実装

- 戦略: 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - research の生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用
  - 指定カラムの Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ
  - features テーブルへの日付単位 UPSERT（トランザクション + バルク挿入で原子性を確保）
  - 欠損値 / 非有限値の扱いとログ出力を整備

- 戦略: シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
  - シグモイド変換・欠損値の中立補完（0.5）を採用して final_score を算出
  - 重みの入力を許容し、無効値の除外・合計が 1 でない場合のリスケーリングを実装（デフォルト重みあり）
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）により BUY を抑制
  - BUY/SELL 条件の実装（BUY: final_score >= threshold、SELL: ストップロスおよびスコア低下）
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入）

- research モジュール（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）
  - 解析ユーティリティ: calc_forward_returns（将来リターン）、calc_ic（Spearman ランク相関）、factor_summary（基本統計）、rank（平均ランク処理）
  - DuckDB を用いた SQL ベースの実装で、外部ライブラリに依存しない設計

- バックテストフレームワーク（src/kabusys/backtest/*）
  - シミュレータ（PortfolioSimulator）: 擬似約定、スリッページ・手数料モデル、ポートフォリオ履歴記録（DailySnapshot / TradeRecord）
  - メトリクス計算（BacktestMetrics / calc_metrics）: CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比、トレード数
  - バックテストエンジン run_backtest:
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（date 範囲フィルタ）
    - 日次ループで約定・positions 書き戻し・時価評価・シグナル生成・発注割当てを実行
    - デフォルトのスリッページ/手数料/最大ポジション比率を指定可能

- トランザクション・堅牢性
  - データベース操作（features / signals / positions への置換）はトランザクションと ROLLBACK 処理を伴う実装（ROLLBACK 失敗時にはログ出力）
  - 価格欠損・不正データに対する警告ログとスキップ処理を多数実装

### Fixed / Improved
- .env パーサの改善により、クォート内のエスケープや行内コメントの扱いを正確に処理するようになった
- 数値演算での非有限値（NaN/Inf）やゼロ除算等を事前にチェックして安全に扱うようにした（平均化・スコア計算・正規化など）
- generate_signals の重み処理で、ユーザー入力の検証（型/範囲/非数値の除外）を追加し安定化
- sell 判定時に価格が取得できない銘柄は SELL 判定全体をスキップして誤クローズを防止する挙動を導入
- バックテスト接続の構築で、コピー時に例外が発生したテーブルはスキップしてログ出力することで堅牢化

### Known limitations / Notes
- 未実装の SELL 条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数基準の自動決済）
  これらはコード中に TODO として明記されています。
- calc_momentum の ma200_dev は直近 200 行未満の場合は None を返す（データ不足の扱い）
- calc_ic は有効サンプルが 3 未満の場合は None を返す
- run_backtest は一部テーブルを日付範囲でコピーする設計のため、極端に古いデータが必要な解析は事前にデータ準備が必要
- generate_signals は AI スコア未登録時に中立値（0.5）で補完するため、AI スコアの有無で出力が変わります
- PortfolioSimulator の BUY は部分買い付け（分割注文）や複雑なサイジングロジックを含まず、SELL は保有全量クローズ（部分利確非対応）

### Migration / Upgrade notes
- 環境変数:
  - 実行前に必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）を設定してください
  - .env/.env.local をプロジェクトルートに配置することで自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
- DuckDB スキーマ:
  - features / signals / positions / prices_daily / raw_financials / ai_scores 等のスキーマを init_schema 等で準備してください（データ依存）
- ログレベルや実行環境（KABUSYS_ENV）は環境変数で設定可能（検証機構あり）

---

貢献・バグ報告・機能要望は Issue を立ててください。