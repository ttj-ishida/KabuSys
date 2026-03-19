# Changelog

すべての注目すべき変更点をこのファイルで管理します。フォーマットは「Keep a Changelog」に準拠します。  

最新のリリース: [0.1.0] - 2026-03-19

## [Unreleased]
- 今後の予定（コードから推測）
  - execution 層（発注実行ロジック）および kabu ステーション API 統合の実装強化
  - ニュース記事と銘柄紐付け（news_symbols）や NLP によるニュース評価の強化
  - トレーリングストップ・時間決済など追加のエグジット条件実装
  - 単体テスト・統合テストの追加、CI 設定

---

## [0.1.0] - 2026-03-19

初回リリース（推測）。日本株の自動売買システム「KabuSys」の基本コンポーネントを実装。

### Added
- パッケージ構成
  - 基本パッケージ定義（kabusys/__init__.py）。
  - サブパッケージ: data, strategy, execution, monitoring を公開。

- 環境設定 / 設定管理（kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサ実装（export 形式、クォート・エスケープ・インラインコメントへの対応）。
  - Settings クラスによる型付きアクセス（J-Quants トークン、kabu API 設定、Slack トークン、DB パス、環境モード、ログレベルなど）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。

- データ取得 / 保存（kabusys/data/jquants_client.py）
  - J-Quants API クライアント実装（株価日足、財務データ、マーケットカレンダー取得）。
  - レート制限制御（固定間隔スロットリングで 120 req/min を保護）。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx のハンドリング）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
  - ページネーション対応。
  - DuckDB への冪等的保存関数（raw_prices / raw_financials / market_calendar、ON CONFLICT を用いた更新）。
  - 入力値安全化ユーティリティ（_to_float, _to_int）。

- ニュース収集（kabusys/data/news_collector.py）
  - RSS からの記事収集フレームワーク（既定ソースに Yahoo Finance を登録）。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）。
  - セキュリティ考慮（defusedxml を用いた XML パース、受信サイズ制限、URL スキームチェック等）。
  - 挿入バルク/チャンク化、冪等性のためのハッシュベース ID 設計（説明に記載）。

- リサーチ（kabusys/research）
  - ファクター計算（kabusys/research/factor_research.py）
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日 MA の扱い、データ不足時は None）。
    - Volatility: 20 日 ATR、相対 ATR (atr_pct)、avg_turnover、volume_ratio（true_range の NULL 伝播制御）。
    - Value: per, roe（raw_financials からの最新財務データ結合）。
    - SQL ベースの DuckDB 実装（営業日窓の扱い、スキャン範囲のバッファ）。
  - 特徴量探索（kabusys/research/feature_exploration.py）
    - 将来リターン計算（horizons デフォルト [1,5,21]、範囲検証、1 クエリ実行）。
    - IC（Spearman の ρ）計算、ランク付けユーティリティ（rank）。
    - factor_summary による統計サマリー（count/mean/std/min/max/median）。
  - zscore_normalize を含む再利用可能 API をエクスポート。

- 特徴量エンジニアリング（kabusys/strategy/feature_engineering.py）
  - research モジュールから算出された raw factor をマージし、ユニバースフィルタを適用（最低株価・最低平均売買代金）。
  - 正規化（zscore_normalize 呼び出し）、±3 にクリップ。
  - features テーブルへの日付単位の置換（トランザクション + バルク挿入で原子性を保証）。
  - ルックアヘッドバイアス対策（target_date 時点のデータのみ使用）。

- シグナル生成（kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して最終スコア final_score を計算。
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI スコア）。
  - スコアの変換ユーティリティ（シグモイド、平均化、NaN/欠損処理）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負なら Bear。ただしサンプル不足は除外）。
  - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）の判定ロジック。
  - SELL 優先ポリシー（SELL 対象は BUY から除外）と signals テーブルへの日付単位置換。
  - 重み（weights）取り扱い（デフォルト重み、ユーザー入力のバリデーションと正規化）。

- パッケージエクスポート
  - strategy モジュールで build_features / generate_signals を公開。
  - research パッケージで主要ユーティリティを公開。

### Changed
- 初回リリースのため該当なし（新規実装中心）。

### Fixed
- 初回リリースのため該当なし（バグ修正履歴は今後追記予定）。

### Security
- news_collector で defusedxml を使用し XML 関係の脆弱性（XML Bomb 等）を回避。
- news_collector の受信サイズ制限、URL 正規化による SSRF/TRACKING パラメータ対策。

### Notes / Limitations (既知の未実装・設計上の注意点)
- execution パッケージは存在するが発注ロジックは実装されていない（初期構造のみ）。
- signal_generator のエグジット条件でトレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の記事→銘柄紐付け（news_symbols）や NLP によるニューススコアリングは設計のみ（実装は限定的）。
- DuckDB スキーマ（テーブル定義）はコード中に明記されていないため、利用時は適切なスキーマ準備が必要。
- 一部関数は外部依存（DuckDB 接続や環境変数）を前提としているため、テストではモックや KABUSYS_DISABLE_AUTO_ENV_LOAD を使用する想定。

---

## Authors & Thanks
- この CHANGELOG はコードベース（src/kabusys/ 以下）の実装内容から推測して作成しました。実際のリリースノートはコミット履歴・ISSUE を基に作成してください。