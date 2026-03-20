CHANGELOG.md
=============

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に準拠しています。  

[Unreleased]
------------

- なし

0.1.0 - 2026-03-20
------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基盤機能を実装しました。以下の主要機能・設計方針を含みます。

Added
- パッケージ基盤
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
  - パッケージ API として data, strategy, execution, monitoring を公開（execution は空の初期モジュール）。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を提供（プロジェクトルートの検出に .git / pyproject.toml を使用）。
  - .env/.env.local の優先順位処理、OS 環境変数保護（protected set）に対応。
  - .env 行パーサーは export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必須値の検証（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN など）や env/log_level の妥当性チェック、パスの Path 型変換などを実装。
- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx のハンドリング）。429 時は Retry-After ヘッダを尊重。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を更新して 1 回リトライする仕組み。
  - 日足、財務、マーケットカレンダー等のフェッチ関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
  - DuckDB への冪等保存（ON CONFLICT DO UPDATE）を行う保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。取得時刻は UTC の ISO8601 で記録（fetched_at）。
  - 型変換ユーティリティ `_to_float` / `_to_int` を実装し、入力の堅牢性を確保。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を取得して raw_news に保存するモジュールを実装（既定ソースに Yahoo Finance）。
  - 記事ID は正規化 URL の SHA-256（先頭 32 文字）を用いるなど冪等性を考慮。
  - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント削除、クエリパラメータソート）を実装。
  - defusedxml を利用して XML 攻撃（XML Bomb 等）に対する防御を実装。
  - SSRF・不正スキーム除外、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、バルク INSERT のチャンク化など安全性・リソース対策を導入。
- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（mom_1m/mom_3m/mom_6m、ma200_dev）、Volatility（ATR 20 日、atr_pct、avg_turnover、volume_ratio）、Value（per、roe）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装。
    - 欠損やデータ不足に対する NULL ハンドリングを実装。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応、SQLで一括取得）。
    - IC（Information Coefficient, Spearman の ρ）計算（calc_ic）、ランク付けユーティリティ（rank）。
    - ファクター統計サマリー（factor_summary）。
  - モジュールエクスポートを __all__ で整理。
- ストラテジー（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
    - research の生ファクターを結合し、ユニバースフィルタ（最小株価、最小売買代金）を適用。
    - 指定カラムに対する Z スコア正規化（zscore_normalize を利用）・±3 でクリップ。
    - features テーブルへの日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）で冪等性・原子性を確保。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付き合算で final_score を算出。
    - 重みの入力検証と合計が 1.0 でない場合の再スケール処理を実装（不正なキーや負値は無視）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数がある場合）による BUY 抑制。
    - BUY 閾値（デフォルト 0.60）を超える銘柄の BUY シグナル生成、保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）による SELL シグナル生成。
    - signals テーブルへの日付単位置換で冪等性・原子性を確保。
    - 欠損コンポーネントは中立値 0.5 で補完するポリシーを採用。
- ロギング・エラーハンドリング
  - 各処理で詳細ログ（info/warning/debug）を出力し、トランザクション失敗時のロールバックや警告処理を実装。
- セキュリティ設計上の注意点
  - ニュースの XML パースに defusedxml を使い安全性を強化。
  - news_collector で不正スキーム排除・受信サイズ制限・URL 正規化等の対策を実装。
- ドキュメント風コメント
  - 各モジュールに設計方針・処理フロー・注意点を明記（look-ahead bias 回避、発注層への依存回避、冪等性の強調など）。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし、ただし多くのエッジケース向けの堅牢化処理を実装）

Security
- RSS パースに defusedxml を採用。
- ニュース収集の SSRF 対策や受信サイズ制限を導入。

Deprecated
- なし

Removed
- なし

既知の制限・未実装の機能
- トレーリングストップや時間ベースの決済など、StrategyModel に記載された一部のエグジット条件は未実装（positions テーブルに peak_price / entry_date 等が必要）。
- execution モジュール（発注層）と monitoring モジュールは骨格のみで、実際の発注・監視ロジックは未実装。
- features テーブルには avg_turnover を保存していない（ユニバースフィルタ専用に保持）。必要に応じて保存設計を拡張する余地あり。
- 外部依存は最小限に抑えているが、DuckDB と defusedxml は必須。
- 単体テストや統合テストの記述はこのリリース時点で含まれていない（テストは推奨）。

更新・移行上の注意
- 環境変数の読み込みロジックは自動で .env を読み込むため、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑止してください。
- J-Quants API の利用には JQUANTS_REFRESH_TOKEN の設定が必須です。settings のプロパティは未設定時に ValueError を投げます。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）が前提となります。導入前にスキーマを準備してください。

---

記載内容はソースコード（src/ 以下）から推測して作成しています。実際の運用・リリースノート作成時は、コミット履歴や実際の変更差分を参照のうえ適宜調整してください。