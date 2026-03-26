# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
リリースバージョンはパッケージ内の __version__ を元に推測しています（0.1.0）。日付は現時点の想定リリース日です。

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買フレームワークの基本機能を実装しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = 0.1.0。
  - モジュール構成（data, strategy, execution, monitoring 等）をエクスポート。

- 設定管理 (`kabusys.config`)
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを追加。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を手がかり）で CWD に依存しない自動ロードを実現。
  - .env パース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - Settings クラスを実装し、必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や既定値（KABU_API_BASE_URL、データベースパス等）を提供。
  - 環境チェック（KABUSYS_ENV の許容値、LOG_LEVEL の検証）を実装。

- ポートフォリオ構築 (`kabusys.portfolio`)
  - 候補選定: select_candidates（スコア降順、タイブレークルール実装）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア比例、合計スコアがゼロなら等配分にフォールバック）。
  - リスク制御: apply_sector_cap（セクター集中制限、当日売却予定銘柄の除外対応）、calc_regime_multiplier（市場レジームに応じた投下資金乗数、bull/neutral/bear マッピング）。
  - 株数決定: calc_position_sizes（allocation_method に応じた株数計算。risk_based / equal / score をサポート、単元株丸め、per-stock 上限、aggregate cap によるスケーリング、cost_buffer による保守的見積り）。

- 戦略（feature / signal） (`kabusys.strategy`)
  - 特徴量構築: build_features（research モジュールのファクターを統合、ユニバースフィルタ適用、Z スコア正規化 ±3 クリップ、DuckDB に日付単位で UPSERT）。
  - シグナル生成: generate_signals（features と ai_scores を統合して final_score を計算、ファクター重みの正規化、Bear レジームでの BUY 抑制、SELL エグジット判定、signals テーブルへ日付単位の置換実装）。
  - シグナルの出力は BUY / SELL を含む構造で、SELL 優先ポリシーを実装（SELL 対象は BUY 候補から除外）。

- リサーチ関連 (`kabusys.research`)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials テーブルのみ参照、複数ホライズン・移動平均・ATR 等を算出）。
  - 特徴量探索: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量算出）、rank（同順位は平均ランクで処理）。
  - 外部依存を避ける設計（pandas 等を使用せず、DuckDB + 標準ライブラリで実装）。

- バックテスト (`kabusys.backtest`)
  - シミュレータ: PortfolioSimulator（DailySnapshot / TradeRecord を定義。SELL を先に処理、BUY は単元丸め、スリッページ・手数料モデルを適用して約定処理）。
  - メトリクス: calc_metrics（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、総トレード数を計算）。

- 並列・堅牢性のための設計上の配慮
  - DuckDB 書き込み時にトランザクション（BEGIN/COMMIT/ROLLBACK）を使用して日付単位で置換（冪等性確保）。
  - 価格欠損や不正値に対するログ出力とスキップ処理（例: 価格が取れない銘柄は判定をスキップ、features がない保有銘柄は score=0 で SELL 判定）。
  - weights 入力の検証とフォールバック（不正な値や未知キーの扱い）。

### 変更 (Changed)
- （初回リリースのため履歴なし）

### 修正 (Fixed)
- （初回リリースのため履歴なし）

### 注意事項 / 未実装・制約 (Notes / Known limitations)
- 一部機能は将来拡張を想定している：
  - position_sizing: 銘柄ごとの lot_size を持つ拡張（現状は全銘柄同一 lot_size）。
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）だとエクスポージャー過少評価になる可能性があり、将来的に前日終値や取得原価のフォールバックを検討予定。
  - signal_generator のエグジット条件: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date 等が必要）。
- AI スコア（ai_scores）が未登録の際はニュース成分を中立扱い（0.5）で補完。
- calc_score_weights は全スコアが 0.0 の場合に等配分へフォールバックして警告を出す。
- env ファイルの読み込みは OS 環境変数を保護するため .env.local の上書き時も既存 OS 環境キーは保護される。
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize 等）は別モジュールに実装されていることを前提。

### セキュリティ (Security)
- 機密情報（API トークン等）を環境変数経由で管理することを想定。`.env` 取り扱い時の注意を README/.env.example で案内することを推奨。

---

今後のリリースでは、以下のような改善を想定しています（優先度例）：
- 銘柄別単元情報の導入（lot_map）と position_sizing の拡張。
- エクスポージャー計算における価格フォールバックの実装。
- signal_generator の時間ベース・トレーリングストップなどのエグジット拡張。
- execution 層（kabuapi 連携）およびモニタリング機能の実装強化。
- 単体テストや CI パイプラインの整備。

（必要であれば、各モジュールごとの詳細な変更履歴や影響範囲、互換性に関する説明を追記します。）