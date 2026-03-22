# Changelog

すべての主要な変更は Keep a Changelog の方針に従って記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

- なし

## [0.1.0] - 2026-03-22

Added
- パッケージ初期リリース。モジュール構成:
  - kabusys (トップレベル)
    - strategy: 特徴量生成・シグナル生成機能を提供
      - build_features: research で算出した生ファクターを結合、ユニバースフィルタ適用、Zスコア正規化・クリップ、features テーブルへ日付単位で置換（冪等）して保存
      - generate_signals: features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付き合算で final_score を計算、Bear レジーム抑制、BUY/SELL シグナルを生成し signals テーブルへ日付単位で置換（冪等）
    - research: ファクター計算・探索ツール
      - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を基にモメンタム・ボラティリティ・バリュー系ファクターを計算
      - calc_forward_returns: 将来リターン（指定ホライズン）を一括 SQL で取得
      - calc_ic / rank / factor_summary: Spearman ランク相関(IC)・ランク計算・統計サマリーを提供（ties の平均ランク処理を含む）
    - backtest: バックテストフレームワーク
      - PortfolioSimulator: 擬似約定（スリッページ・手数料モデル）とポートフォリオ状態管理、BUY/SELL の実行ロジック、時価評価（mark_to_market）、トレード記録保存
      - run_backtest / engine: 本番 DB からインメモリ DuckDB へデータコピーして日次ループを実行、シグナルの約定・ポジション書き戻し・時価評価・シグナル再生成を行うワークフローを実装
      - metrics: CAGR、シャープレシオ、最大ドローダウン、勝率、ペイオフレシオ等のバックテスト評価指標を計算
    - config: 環境変数・設定管理
      - 自動 .env ロード機能（プロジェクトルートの .git または pyproject.toml を探索して .env / .env.local を読み込み）
      - .env パーサは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い、override/protected 機能をサポート
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション
      - Settings クラスで必須値の検証と取得（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID など）、enum チェック（KABUSYS_ENV, LOG_LEVEL）とユーティリティプロパティ（is_live/is_paper/is_dev）
- データベース操作・整合性確保
  - features / signals の日付単位での削除→挿入をトランザクション（BEGIN/COMMIT/ROLLBACK）＋バルク挿入で実行し、原子性を確保
  - DuckDB を使用した SQL ベースの高速集計・ウィンドウ関数利用実装
- シグナル生成の堅牢化
  - 重み（weights）の外部入力を検証し、既知キーのみ受け付け、非数値・負値・NaN/Inf を無効扱い、合計が 1.0 になるようリスケーリング
  - コンポーネントスコア欠損時は中立（0.5）で補完して不当な降格を回避
  - AI スコアが欠ける場合の中立補完、レジームスコアを用いた Bear 相場判定（サンプル閾値あり）による BUY 抑制
  - SELL 優先ポリシー（SELL 対象は BUY から除外してランク再付与）
- 設計上の方針を明確化
  - ルックアヘッドバイアス回避: target_date 時点のデータのみを参照して計算
  - 発注 API / 実運用層への直接依存を持たない層分離（strategy/research/backtest は DB と純計算のみ）
  - research モジュールは標準ライブラリのみで依存を最小化

Changed
- 初期実装のため該当なし

Fixed
- 初期リリースのため該当なし

Notes / 実装上の注意
- .env の自動ロードはプロジェクトルート検出に依存するため、配布後や特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動ロードすることを推奨
- 一部の売買ルール（トレーリングストップ、時間決済など）は positions テーブルの追加情報（peak_price / entry_date 等）を要するため未実装（signal_generator 内コメント参照）
- calc_forward_returns の horizons は営業日ベースの連続レコード数であり、入力は 1–252 の正整数に制限
- バックテストでは本番 DB の signals / positions を汚染しないため、インメモリのコピーを用いて処理を行う

--- 

開発・運用で必要な追加情報や日付・バージョンの調整があれば教えてください。