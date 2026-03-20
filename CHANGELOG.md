# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコア機能を提供します。

### Added
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0、主要サブパッケージを __all__ で公開）。
- 設定/環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出（.git または pyproject.toml を基準）により CWD に依存しない自動読み込み。
  - .env と .env.local の読み込み優先度を実装（OS 環境変数保護のため protected set を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを提供。
  - 複雑な .env 行パース対応（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント判定）。
  - Settings クラスによりアプリケーション設定をプロパティとして提供（J-Quants トークン、kabu API 設定、Slack、DB パス、環境/ログレベル判定）。
  - 無効な環境値や未設定必須変数に対する明示的なエラーを実装。
- データ取得/保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - 固定間隔のスロットリングによるレート制限実装（120 req/min）。
  - リトライ（指数バックオフ、最大 3 回）・429 (Retry-After) の尊重、408/429/5xx に対する再試行。
  - 401 受信時の自動トークンリフレッシュ（1 回）と再試行ロジック。
  - fetch_* 系関数（株価・財務・マーケットカレンダー）と、それらを DuckDB に冪等保存する save_* 関数を提供（ON CONFLICT DO UPDATE を使用）。
  - 入力変換ユーティリティ（_to_float / _to_int）を実装し、データの不正値を安全に扱う。
  - 取得時の fetched_at を UTC で記録し、Look-ahead バイアスの追跡を可能に。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と raw_news への冪等保存ロジックを実装。
  - 記事 ID を URL 正規化後の SHA-256（先頭 32 文字）で生成して冪等性を担保。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - defusedxml を用いた XML 関係の安全パース、受信サイズ上限（10 MB）、HTTP(S) スキーム検証等のセキュリティ対策を実装。
  - DB へのバルク挿入のチャンク化・トランザクション集約・INSERT RETURNING を想定した実装方針。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）計算。
    - Volatility / Liquidity（atr_20, atr_pct, avg_turnover, volume_ratio）。
    - Value（per, roe）計算（raw_financials から最新の開示データを参照）。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース実装。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（複数ホライズン、データ不足時は None）。
    - IC（Spearman の ρ）計算（ランク平均処理、同順位は平均ランク）。
    - factor_summary による基本統計量（count/mean/std/min/max/median）。
    - rank ユーティリティ（同順位の平均ランク対応、丸めによる ties 回避）。
  - 研究モジュールは外部依存（pandas 等）無しで実装する方針。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で計算した raw factor をマージ・ユニバースフィルタ・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）。
  - Z スコア正規化（対象カラム指定）、±3 でのクリッピング、日付単位の置換（トランザクションで原子性を保証）。
- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ保存する generate_signals を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）計算ロジックを実装（シグモイド変換、欠損時は中立 0.5 補完）。
  - ファクター重みのマージ・検証・合計スケーリング機能を実装（不正値は警告して除外）。
  - Bear レジーム検出（ai_scores の regime_score 平均が負でサンプル数閾値を満たす場合）による BUY 抑制。
  - SELL（エグジット）判定: ストップロス（-8%）およびスコア低下を実装。トレーリングストップ等は未実装（将来実装予定）。
  - 日付単位の置換（DELETE してから INSERT、トランザクション内で実行）により冪等性を確保。
- execution / monitoring
  - パッケージレイアウトに placeholder サブパッケージを用意。

### Changed
- 設計上の明示:
  - ルックアヘッドバイアス回避を全コンポーネントで配慮（target_date 時点のデータのみ参照、fetched_at を記録）。
  - DuckDB を中心としたデータフロー（raw_* / prices_daily / features / ai_scores / signals / positions 等）設計。

### Fixed
- （初版につき既知のバグフィックス項目は特になし）

### Security
- news_collector: defusedxml による XML パース、受信サイズ制限、HTTP(S) スキーム検証、IP/SSRF に配慮した実装方針を追加。
- jquants_client: 401 自動リフレッシュ実装、429 の Retry-After を尊重するリトライ設計を導入し、API 認証/レートの堅牢性を確保。

### Notes / Known limitations
- signal_generator のトレーリングストップや時間決済など一部のエグジット条件は positions テーブル側に追加情報（peak_price / entry_date 等）が必要で、現バージョンでは未実装。
- research モジュールは prices_daily / raw_financials のデータ品質に依存する。データ欠損時は None が返され、後続処理で中立値補完が行われる。
- news_collector の記事 ID は URL 正規化に依存するため、今後ソースごとの特殊処理が必要になる場合がある。
- データベーススキーマ（テーブル名・カラム名）はリポジトリ外のドキュメント（DataPlatform.md / StrategyModel.md 等）に準拠している前提。

---

今後の予定（例）
- トレーリングストップ / 時間決済の実装（positions に peak_price/entry_date 情報が必要）。
- news_collector のマルチソース拡張と記事→銘柄マッピングの改善（NLP / シンボル抽出）。
- execution 層の kabu API 統合（注文発行・注文管理）およびモニタリング機能の実装。

(注) 上記はコードベースの内容から推測して記載しています。実際の運用・仕様書と差異がある場合はそちらを優先してください。