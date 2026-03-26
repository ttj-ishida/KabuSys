# CHANGELOG

すべての注目すべき変更履歴を記録します。本ファイルは「Keep a Changelog」形式に準拠します。

## [Unreleased]

- 今後のリリースに向けた未確定の変更点や機能追加はここに記載します。

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装しました。以下はコードベースから推測した主な追加内容と注意点です。

### Added

- パッケージ基礎
  - kabusys パッケージの初版を公開。
  - バージョン情報: 0.1.0（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local を自動で読み込む仕組み（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 高度な .env パース機能（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
  - OS 環境変数を保護する protected モードと override モードを実装。
  - 必須環境変数チェック（_require）と Settings クラス（J-Quants、kabu API、Slack、DB パス、ログレベル、環境種別の取得・検証）。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - 銘柄選定: select_candidates — スコア降順・タイブレーク実装。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコア0の場合は等配分へフォールバック）。
  - リスク調整: apply_sector_cap（セクターごとのエクスポージャー上限による候補除外。unknown セクターは制限対象外）および calc_regime_multiplier（市場レジームに応じた投資乗数: bull/neutral/bear のマッピング、未知レジームはフォールバック）。
  - ポジションサイジング: calc_position_sizes
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）で丸め、per-position 上限や aggregate cap（available_cash） に基づくスケーリング。
    - cost_buffer を用いた保守的なコスト見積り（スリッページ・手数料反映）。
    - スケールダウン時の残差分配アルゴリズム（fractional remainder に基づく lot 単位での追加配分）。

- 戦略（src/kabusys/strategy/）
  - 特徴量構築: build_features（research の factor 計算結果をマージしユニバースフィルタ、Z スコア正規化、±3 クリップ後に features テーブルへ UPSERT）。
    - ユニバース条件：株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - DuckDB を用いた SQL ベースのデータ取得／書き込み。
  - シグナル生成: generate_signals（features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成して signals テーブルへ書き込む）
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（ai_scores）。
    - 重みのマージ・検証・正規化ロジック（カスタム weights を安全に受け入れ、合計が 1 に調整）。
    - Bear レジーム検知時は BUY シグナルを抑制（regime 判定は ai_scores の regime_score 平均）。
    - SELL シグナル（エグジット）判定: ストップロス（-8%）・スコア低下。保有銘柄の価格欠損時は SELL 判定をスキップし警告を出す。
    - 日付単位の置換（DELETE + bulk INSERT）で冪等性を確保。

- 研究用モジュール（src/kabusys/research/）
  - ファクター計算: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照し、各種ファクターを算出）。
  - 特徴量探索: calc_forward_returns（複数ホライズンでの将来リターン）、calc_ic（Spearman ランク相関で IC 計算）、factor_summary（基本統計量）、rank（同順位は平均ランク扱い）。
  - 外部依存を極力避け、DuckDB と標準ライブラリで実装。

- バックテスト（src/kabusys/backtest/）
  - メトリクス: calc_metrics（CAGR、Sharpe、最大ドローダウン、勝率、payoff ratio、総トレード数を計算）。
  - シミュレータ: PortfolioSimulator（擬似約定・ポートフォリオ管理、SELL 先行処理、BUY 後処理、スリッページ・手数料モデル、TradeRecord/DailySnapshot を用いた履歴管理、lot_size 対応）。

- ロギング／警告
  - 各所で logging を活用し、異常やフォールバック（スコア 0.0、未知レジーム、ファイル読み込み失敗等）で警告/情報を出力。

### Changed

- （初版につき該当なし）

### Fixed

- （初版につき該当なし）

### Known issues / TODO（コード内コメントに基づく）

- sector_exposure の価格欠損時（price_map に無い/0.0）の取り扱いでエクスポージャーが過小見積りされ得る。将来的には前日終値や取得原価によるフォールバックを検討。
- position_sizing の lot_size は現状グローバル共通で 100 を想定。将来的には銘柄別 lot_map を受け取る設計に拡張予定（TODO コメントあり）。
- generate_signals の SELL 条件で未実装の項目（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の拡張が必要。
- feature_engineering: per カラムは正規化対象から除外（逆数を取る等の変換ロジックは既定の挙動に注意）。
- 一部の関数はデータ欠損時に None を返す設計。パイプライン側での欠損補完方針（中立値 0.5 など）が実装済みだが、運用時の挙動確認が必要。
- calc_regime_multiplier は未知レジームでフォールバックし警告を出す。運用で未知レジームが頻発する場合は検出ロジックの見直しを推奨。

---

この CHANGELOG はコード内容から推測して作成しています。実際のコミット履歴やリリースノートがある場合は、そちらを正としてください。必要であれば、各機能ごとの変更点をより詳細に分割して記載することも可能です。