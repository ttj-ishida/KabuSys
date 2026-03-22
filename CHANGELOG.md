CHANGELOG
=========

すべての注目すべき変更を記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。  
（内容は提示されたコードベースから推測して作成しています）

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（未リリースの変更はありません）

0.1.0 - 2026-03-22
-----------------

初回リリース（アルファ相当）。日本株の自動売買システム「KabuSys」のコア機能群を含む基盤実装を追加しました。
主な追加点・設計方針・既知の制約を以下にまとめます。

追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にバージョン定義 (__version__ = "0.1.0") と公開モジュール一覧を追加。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml に基づく）から自動読み込みする仕組みを実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能（テスト用）。
    - export 形式やクォート・エスケープ・コメント処理に対応したパーサーを実装（_parse_env_line）。
    - OS 環境変数を保護する protected 上書きロジックを実装（.env.local は .env を上書きする挙動）。
    - Settings クラスを提供し、必須値取得時の検査（_require）や各種設定プロパティを定義（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DB パス 等）。
    - 環境（KABUSYS_ENV）のバリデーション（development / paper_trading / live）・ログレベルのバリデーションを追加。

- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - ボラティリティ/流動性（calc_volatility）：20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - バリュー（calc_value）：raw_financials から最新財務を取得し PER / ROE を計算。
    - DuckDB を用いた SQL+Python のハイブリッド計算を採用。

  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：指定ホライズンの将来リターンを一括取得。
    - IC 計算（calc_ic）：ファクターと将来リターンの Spearman ランク相関を実装（ties は平均ランクで処理）。
    - factor_summary / rank：ファクターの基本統計量・ランク変換ユーティリティを実装。
    - 外部ライブラリに依存しない純標準ライブラリ実装を意図。

  - research パッケージ __all__ を通した公開 API を整備。

- 特徴量エンジニアリング
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で算出された生ファクターをマージ・ユニバースフィルタ適用（最低株価・平均売買代金）し、Z スコア正規化（zscore_normalize を利用）→ ±3 でクリップして features テーブルへ UPSERT（トランザクションによる日付単位置換で冪等性を確保）。
    - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを参照。
    - 欠損・非有限値処理、価格の当日欠損や休場日対応（target_date 以前の最新価格参照）を実装。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し、コンポーネント（momentum/value/volatility/liquidity/news）ごとのスコアを算出。
    - final_score = 重み付き合算（デフォルト重みを定義）。ユーザー渡しの weights はバリデーション・補完・正規化（合計が 1 になるようリスケーリング）を実施。
    - Z スコア -> シグモイド変換を経て 0〜1 にマッピング。欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負である場合。ただしサンプル数不足時は Bear とみなさない）。
    - BUY シグナルは閾値（デフォルト 0.60）超で生成。Bear 時は BUY を抑制。
    - SELL（エグジット）判定を実装：ストップロス（-8%）優先、スコア低下（final_score < threshold）。
    - signals テーブルへの日付単位置換（トランザクションで原子性）により冪等性を担保。
    - 不整合や価格欠損時のログ警告、ROLLBACK の失敗を警告として記録。

- バックテストフレームワーク
  - src/kabusys/backtest/
    - simulator.py
      - PortfolioSimulator: メモリ内でポートフォリオ状態を管理し、SELL を先に全量約定・BUY は割当に基づき始値で約定（スリッページ・手数料モデルを適用）。
      - mark_to_market による日次スナップショット記録（価格欠損時は 0 として評価し WARNING ログ）。
      - TradeRecord / DailySnapshot の dataclass 定義。

    - metrics.py
      - バックテスト指標（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total_trades）を計算するユーティリティを追加。

    - engine.py
      - run_backtest: 本番 DuckDB からインメモリ DuckDB へデータをコピーして日次ループを実行するエンジンを実装。
      - _build_backtest_conn: 必要テーブルの日付範囲コピー（features, prices_daily, ai_scores, market_regime, market_calendar）を実装。コピー失敗時は警告を出して続行。
      - 日付別の open/close の取得ユーティリティ、positions テーブルへの書き戻し（冪等）、signals の読み取りロジック等を実装。
      - デフォルトパラメータ（初期資金、スリッページ、手数料、max_position_pct）を定義。

- パッケージ API エクスポート
  - strategy / backtest / research の __init__ で主要関数・クラスを公開。

設計上の改善点・安全対策 (Changed / Improved)
- DB 操作は日付単位の置換を多用しトランザクションで原子性を確保（features/signals/positions の DELETE + INSERT）。
- lookahead を避ける設計（target_date のみ使用）を徹底。
- 欠損値・非有限値（NaN, Inf）に対する安全なハンドリングを多所で実装。
- 重みパラメータや環境変数のバリデーションを導入して誤設定による致命的動作を抑制。
- 外部ライブラリ依存を極力避け、DuckDB と標準ライブラリ中心で実装。

不具合修正 / 既知の制約 (Fixed / Known Issues)
- 未実装 / 将来実装予定の機能を明示:
  - トレーリングストップ・時間決済（StrategyModel.md 記載の一部）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 部分利確・部分損切りは未サポート。SELL は保有全量をクローズする。
  - PBR・配当利回り等の一部バリューファクターは未実装。
- バックテスト用データコピーで列やスキーマ差異がある場合はコピーをスキップして警告を出す実装。これによりデータ不整合時に一部機能が限定される可能性あり。
- mark_to_market は終値欠損時に 0 として評価するため、欠損データがある場合の評価結果に注意が必要。
- ポジションサイジングは単純化（各銘柄の割当を floor して整数株数で約定）、端数切捨てにより資金が余ることがある。
- ai_scores が不足する場合、AI ニューススコアは中立（0.5）で補完。

開発上の注記
- 設計文書（StrategyModel.md, BacktestFramework.md 等）を参照する設計方針がソース内に多数記載されており、実装はそれらに従っていることを想定。
- ロギングを広範に活用しており、運用時の観測性を確保。
- .env パーサーはシェルスタイル（export、クォート、エスケープ、コメント）にかなり対応しているが、極端なケースは未検証の可能性あり。

互換性に関する注意 (Breaking Changes)
- 初回公開のため過去互換性の問題はありません。

今後の予定（推測）
- 部分利確 / トレーリングストップ等のエグジット戦略の実装。
- PBR・配当利回りなどバリューファクターの追加。
- positions テーブルにエントリー関連メタデータ（peak_price, entry_date）を保存してより高度なエグジットをサポート。
- CI / テストカバレッジの強化・ドキュメント整備。

問い合わせ
- 実装の想定・設計意図や未実装部分の優先度等はソース内の docstring / コメントを参照してください。必要であれば実装方針に基づいた追加の CHANGELOG エントリを作成します。