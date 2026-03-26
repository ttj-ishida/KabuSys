Keep a Changelog に準拠した CHANGELOG.md を以下に作成しました。コードベースの内容から推測して記載しています。

なお本ファイルはプロジェクトの初回リリース相当（version 0.1.0）を想定したまとめです。必要に応じて調整してください。

--------------------------------------------------------------------

Keep a Changelog
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
バージョニングは SemVer を想定します。

--------------------------------------------------------------------

Unreleased
- （今後の変更をここに記載）

[0.1.0] - 2026-03-26
Added
- パッケージ初期リリース（kabusys v0.1.0）。
  - パッケージメタ情報: `src/kabusys/__init__.py` にて `__version__ = "0.1.0"`、公開 API の簡易定義。
- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local からの自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサー実装（コメント、クォート、export プレフィックス、エスケープ対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - `Settings` クラスで環境変数をラップし、必須キーチェック（`_require`）や既定値を提供。
  - サポートされる設定例: J-Quants / kabu ステーション API 情報、Slack、DB パス（DuckDB / SQLite）、実行環境フラグ・ログレベル等。
- ポートフォリオ構築（src/kabusys/portfolio/）
  - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
  - 配分重み: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等配分へフォールバック）。
  - ポジションサイズ計算: `calc_position_sizes`
    - 配分方式: `risk_based`, `equal`, `score` をサポート。
    - リスクベースの株数算出、単元株（lot_size）で丸め、銘柄毎上限・集計キャップ（available_cash）に基づくスケーリング。
    - cost_buffer を使った保守的コスト見積り、端数処理（残差に応じた lot 単位の追加配分）。
- リスク調整（src/kabusys/portfolio/risk_adjustment.py）
  - セクター集中制限: `apply_sector_cap`（既存ポジションのセクター比率が閾値を超える場合、新規候補から除外）。
  - レジーム乗数: `calc_regime_multiplier`（"bull"/"neutral"/"bear" に対して 1.0/0.7/0.3、未知レジームはフォールバック 1.0）。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - 研究用ファクター（momentum/volatility/value）を結合して特徴量を作成。
  - ユニバースフィルタ（最低株価・平均売買代金の閾値）適用。
  - 数値ファクターの Z スコア正規化と ±3 でのクリップ。
  - DuckDB を使用した日付単位の冪等アップサート（トランザクションで原子性確保）。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - `generate_signals` により features/A I スコアを統合して final_score を算出。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算とシグモイド変換／欠損補完（中立 0.5）。
  - レジーム（AI の regime_score）に基づく Bear 検出と BUY 抑制ロジック（サンプル数閾値あり）。
  - SELL（エグジット）判定の実装（ストップロス、スコア低下）。SELL を優先して BUY から除外。
  - DuckDB を用いた signals テーブルへの冪等書き込み（トランザクション管理）。
- 研究ユーティリティ（src/kabusys/research/）
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`（prices_daily / raw_financials 参照、DuckDB ベース）。
  - 特徴量探索: `calc_forward_returns`（複数ホライズン対応）、`calc_ic`（Spearman ランク相関）、`factor_summary`（基本統計量）、`rank`（平均ランクによる同順位処理）。
  - 外部ライブラリ依存を避け、標準ライブラリ + DuckDB SQL で実装。
- バックテスト（src/kabusys/backtest/）
  - メトリクス計算: `calc_metrics` と内部関数（CAGR、Sharpe、最大ドローダウン、勝率、ペイオフ比、総トレード数）。
  - シミュレータ: `PortfolioSimulator`（メモリ内状態管理）
    - `execute_orders` による疑似約定（SELL 先行、BUY 後処理、SELL は全量クローズ、スリッページ・手数料適用）。
    - 取引記録 (`TradeRecord`) と日次スナップショット (`DailySnapshot`) を保持し、バックテスト集計に供する。
- その他
  - 各所で DuckDB を用いた効率的なデータ参照と一括処理を採用。
  - ロギングを利用した詳細なデバッグ / 警告メッセージを多用（欠損データやフォールバックの可視化）。
  - 公開モジュールのエクスポート定義（strategy / portfolio / research / backtest 等）。

Fixed
- 該当なし（初回リリース）

Changed
- 該当なし（初回リリース）

Deprecated
- 該当なし（初回リリース）

Removed
- 該当なし（初回リリース）

Security
- 該当なし

Notes / Known limitations & TODOs
- apply_sector_cap:
  - price_map に 0.0（欠損）がある場合、セクター露出が過少見積りとなりブロックが外れる可能性がある旨の注記あり（将来的に前日終値等のフォールバックを検討）。
- position_sizing:
  - 現状 `lot_size` は全銘柄共通の引数。将来的に銘柄別単元を扱う拡張を想定した TODO コメントあり。
- signal_generator:
  - トレーリングストップや時間決済（保有期間による強制決済）は未実装で、positions テーブルに `peak_price` / `entry_date` 等が必要になる旨のコメントあり。
  - Bear レジーム時は設計上 BUY シグナルをそもそも生成しない仕様だが、レジーム乗数としての追加セーフガードも実装している。
- simulator:
  - SELL は全量クローズの実装（部分利確・部分損切り非対応）。
- DB 操作:
  - features / signals 等への書き込みは日付単位の削除→挿入で冪等性を確保している（トランザクション + bulk insert）。
- 自動環境読み込み:
  - 自動的に .env / .env.local をプロジェクトルートから読み込むが、テスト環境等で無効化するための `KABUSYS_DISABLE_AUTO_ENV_LOAD` を用意。
- 外部依存:
  - 研究・戦略系は DuckDB を前提に設計。pandas 等の外部依存は意図的に避けている。
- execution / monitoring:
  - パッケージ上にディレクトリは存在するが、execution 層（発注実装）や monitoring の詳細実装はプロジェクトの他箇所（または今後）に依存する可能性あり（現状のコードは主に戦略・研究・バックテストの実装に注力）。

--------------------------------------------------------------------

参考: 今後の CHANGELOG の書き方
- 破壊的変更は [Unreleased] セクションで目立つように記載し、次のリリースでバージョン見出しへ移すことを推奨します。
- バグ修正、性能改善、新機能追加をカテゴリ（Added/Changed/Fixed/Deprecated/Removed/Security）に分けて記載してください。

--------------------------------------------------------------------

必要であれば日付や記載の粒度（関数レベルの変更履歴やコミットハッシュの付与など）を調整します。