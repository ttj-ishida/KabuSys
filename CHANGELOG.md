# Changelog

すべての注記は Keep a Changelog 準拠です。  
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点と設計上の注意点は以下のとおりです。

### Added
- パッケージ骨組み
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring（execution はパッケージ化済み、実装は分割）。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数読み込みの自動化（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 高度な .env パーサ実装（クォート処理、エスケープ、インラインコメント処理、`export KEY=val` 形式対応）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス: J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベル等のプロパティ（必須環境変数未設定時は ValueError を発生）。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限遵守（120 req/min）。
    - リトライ（指数バックオフ、最大 3 回）、HTTP 408/429/5xx に対応。
    - 401 発生時は自動的にリフレッシュトークンで ID トークンを更新して 1 回再試行。
    - ページネーション対応、モジュールレベルの ID トークンキャッシュ。
  - データ保存関数:
    - save_daily_quotes, save_financial_statements, save_market_calendar を提供。
    - DuckDB への冪等保存を実現（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC で記録（Look-ahead バイアス対策）。
    - 入力変換ユーティリティ (_to_float/_to_int) を実装し不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する仕組みを実装。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）を実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - SSRF を考慮したスキーム制限等の設計（実装方針）。
  - バルク INSERT のチャンク処理や記事IDの冪等化（SHA-256 ハッシュ利用）等を設計に明示。

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR(atr_pct)、20 日平均売買代金、volume_ratio を計算。
    - calc_value: EPS/ROE から PER 等のバリューファクターを計算（prices_daily / raw_financials を参照）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算（有効レコードが 3 未満の場合は None）。
    - factor_summary: 各ファクターの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクを返すランク関数（丸めで ties を安定化）。
  - 研究モジュールは外部大規模依存を避け、DuckDB と標準ライブラリのみで実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research モジュールの生ファクターを取得して
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）適用、
    - 指定カラムの Z スコア正規化（zscore_normalize を使用）、
    - ±3 でクリップ、
    - features テーブルへ日付単位の置換（DELETE + INSERT をトランザクションで実施し原子性を保証）、
    - 冪等性を保証する実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores（AI スコア）を統合しコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 各コンポーネントは欠損時に中立値 0.5 で補完（過度な降格防止）。
    - final_score を重み付け和で算出（デフォルト重みを実装、ユーザ指定 weights は検証・正規化して適用）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、かつサンプル数閾値を満たす場合）。Bear 時は BUY シグナルを抑制。
    - SELL シグナル生成（ストップロス -8%、final_score が閾値未満など）。保有ポジションの価格欠損時は SELL 判定をスキップして誤クローズを回避。
    - signals テーブルへ日付単位の置換。BUY と SELL の優先ルール（SELL を除外して再ランク付け）を実装。
  - 実運用を意識した多くの安全弁（欠損データの扱い、ログ出力、トランザクション処理）を備える。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- RSS パースに defusedxml を使用し XML 攻撃対策を実施。
- ニュース取得で受信サイズ制限を設け、メモリ DoS を軽減。
- J-Quants クライアントで認証トークンの取り扱いに注意し、401 の自動リフレッシュを限定回数のみ実行（無限再帰を防止）。
- .env 読み込みはプロジェクトルートベースで行い、OS 環境変数の保護（protected set）を考慮。

### Notes / Limitations / TODO
- シグナル生成において未実装のエグジット条件:
  - トレーリングストップ（peak_price の追跡が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- news_collector の記事 ID 生成・銘柄紐付け等は設計方針を記載済み。運用に応じた追加実装が必要。
- 一部の統計指標（IC など）は有効サンプルが不足すると None を返します（閾値は実装内に明記）。
- 実行環境（paper_trading / live 等）に応じた安全対策は Settings API を通して行う設計だが、運用手順の整備が必要。
- 外部 API（kabu ステーション等）への発注ロジックは execution 層に実装する予定（現バージョンでは依存を持たない）。

---

以上が v0.1.0 の変更点です。今後のリリースでは以下を優先で実装・改善予定です:
- execution 層の発注ロジック（kabuステーション連携、注文管理）
- news_collector の記事→銘柄マッピング精度改善（NLP/ルール強化）
- モニタリング・アラート機能の実装（monitoring）
- 各種単体・統合テスト、CI 設定の整備

（必要であればリリースノートの英語版やより詳細な技術ノートも作成します。）