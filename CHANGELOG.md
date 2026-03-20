# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
安定版のセマンティックバージョニングを採用しています。  

リンク: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-03-20

初期リリース。日本株自動売買システム KabuSys のコア機能を実装しました。主な機能、設計方針、注意点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ初期化 (src/kabusys/__init__.py) とバージョン番号 (`__version__ = "0.1.0"`)、公開 API の定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 自動ロード無効化用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パーサーの強化: コメント、`export ` プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理に対応。
  - .env の読み込みに際して OS 環境変数保護 (protected keys) と上書き制御（`.env` と `.env.local` の優先順位）。
  - 必須環境変数取得ヘルパ `_require` と Settings クラス:
    - J-Quants / kabu API / Slack / DB パス等の設定プロパティを提供。
    - `KABUSYS_ENV`（development/paper_trading/live）と `LOG_LEVEL` の検証ロジック。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得・保存 (src/kabusys/data/)
  - J-Quants クライアント (jquants_client.py)
    - API レート制限 (120 req/min) を固定間隔スロットリングで実装（RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 対応）。
    - 401 応答時の自動トークン再生成（1 回のみ）と ID トークンキャッシュ共有。
    - ページネーション対応の取得関数: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - レスポンスのパースに安全・堅牢な型変換ヘルパ `_to_float` / `_to_int` を追加。PK 欠損行はスキップしてログ出力。

  - ニュース収集モジュール (news_collector.py)
    - RSS フィード収集の基盤を実装。デフォルトソースに Yahoo Finance（businessカテゴリ）を設定。
    - 記事ID生成のための URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - defusedxml を用いた XML パース（XML Bomb 等への防御）。
    - SSRF 対策を含む URL 検証、受信サイズ上限（10 MB）、バルク挿入チャンク処理などの安全対策。
    - raw_news への冪等保存実装方針（ON CONFLICT DO NOTHING/INSERT RETURNING を想定）。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - ファクター計算モジュール (factor_research.py)
    - Momentum（mom_1m / mom_3m / mom_6m / ma200_dev）、Volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）、Value（per / roe）を DuckDB の prices_daily / raw_financials を用いて計算。
    - 計算に必要なスキャン範囲・ウィンドウ長、欠損時の None 戻しやカウント条件を適切に実装。
  - 特徴量探索モジュール (feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、入力バリデーションあり）。
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ、同順位は平均ランクで処理）。
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位は平均ランク、丸めによる ties 対応）。
  - research パッケージの公開 API エクスポート。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - build_features(conn, target_date): research で算出した生ファクターをマージし、
    - 株価・流動性によるユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）適用
    - 数値ファクターの Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）
    - ±3 で Z スコアをクリップ
    - features テーブルへ日付単位での置換（BEGIN/DELETE/INSERT/COMMIT + ROLLBACK ハンドリング）で冪等性と原子性を確保
  - 不正データ・欠損に対する堅牢性を考慮。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features / ai_scores / positions を参照して最終スコア final_score を計算。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティを実装。
    - AI レジームスコアを集計して Bear レジーム判定（サンプル数条件あり）。Bear 時は BUY を抑制。
    - BUY 生成は threshold ベース、SELL はストップロス（-8%）とスコア低下に基づくエグジット判定を実装。
    - 欠損コンポーネントは中立値 0.5 で補完するポリシー。
    - 重みの検証・正規化ロジック（未知キー・非数値・負値は無視、合計が 1 でない場合はリスケール）。
    - signals テーブルへの日付単位置換（トランザクション処理）で冪等性を確保。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。
  - デフォルト重み・閾値は StrategyModel.md の仕様に準拠して実装。

- モジュール設計・運用向け保護
  - ロギング（各処理での info/debug/warning）を包括。
  - トランザクション + 明示的な ROLLBACK 処理により DB 操作の安全性を確保。
  - 外部 API 呼び出しに対するレート制御・リトライ・トークン自動更新を導入。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- RSS パースに defusedxml を採用し XML パースに起因する攻撃を軽減。
- ニュース収集での URL 正規化・トラッキングパラメータ除去・スキーム検証・受信サイズ制限で SSRF / DoS リスクを低減。
- J-Quants クライアントはトークン自動刷新処理で直接的な認証情報露出を最小化。

### Known Issues / Not Implemented
- signal_generator のエグジット条件について未実装の点をコードで明示:
  - トレーリングストップ（peak_price に基づく -10%）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）も未実装。
- news_collector の完全な RSS パース・DB スキーマや INSERT RETURNING の利用は設計方針で示されているが、周辺ユーティリティや統合テストが必要。
- DuckDB スキーマ（テーブル定義）は本パッケージに含まれていないため、運用前に schema の準備が必要。
- zscore_normalize の実装は kabusys.data.stats 側に依存。外部テストでの振る舞い確認が必要。

### Migration / Compatibility notes
- 環境変数名や Settings のプロパティ名（例: JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN 等）に依存するため、既存環境へ導入する際は .env の整備が必要。
- 自動 .env ロードはプロジェクトルート検出に依存するので、パッケージを配布後に意図しない自動読み込みを避ける場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

今後の予定（例）
- ドキュメント（StrategyModel.md, DataPlatform.md）の整備とサンプルデータでの end-to-end テスト。
- ニュース → シンボル紐付け処理の実装強化。
- execution レイヤー（kabu ステーション API との発注ロジック）およびモニタリング / 通知機能の追加。

もし CHANGELOG に追記したい点や、特に強調したい変更（セキュリティや破壊的変更の注記など）があればご指示ください。