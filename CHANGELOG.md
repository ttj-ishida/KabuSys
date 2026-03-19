# CHANGELOG

すべての重要な変更点を保持するために Keep a Changelog の形式に準拠しています。  
このプロジェクトはセマンティックバージョニングを使用します。

※この CHANGELOG はソースコードから推測して作成した要約です。実装上の意図・設計注釈・未実装箇所も併記しています。

## [0.1.0] - 2026-03-19

### Added
- パッケージ基盤
  - kabusys パッケージの初期実装を追加。パッケージバージョンは 0.1.0。
  - パッケージ公開インターフェースを __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機構を実装（プロジェクトルートは .git または pyproject.toml から検出）。
  - .env パーサの堅牢化：
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメントの扱い（クォートあり/なしでの差分処理）。
    - 無効行スキップ、読み込み失敗時の警告出力。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加（テスト等で利用可能）。
  - Settings クラスを導入し、環境変数経由の設定アクセスを提供（型的に Path を返すDBパス等）。
  - 必須環境変数未設定時に ValueError を投げる _require ユーティリティ。
  - env / log_level の値検証（許可値集合でバリデーション）。
  - is_live / is_paper / is_dev のヘルパープロパティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限制御（固定間隔スロットリング: 120 req/min）を実装した _RateLimiter。
  - 再試行ロジック（指数バックオフ、最大3回、408/429/5xx 対象）と 429 の Retry-After 優先処理。
  - 401 レスポンス時にリフレッシュトークンから ID トークン自動再取得（1回のみリトライ）。
  - モジュールレベルの ID トークンキャッシュ（ページネーション間でトークン共有）。
  - ページネーション対応の fetch_*（daily_quotes / financial_statements / market_calendar）。
  - DuckDB への保存ユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）：
    - fetched_at を UTC で記録（ISO8601）。
    - PK 欠損行のスキップ／警告。
    - 冪等性を保つ INSERT ... ON CONFLICT DO UPDATE。
    - 型変換ユーティリティ _to_float / _to_int（安全な変換ルール）。
  - HTTP 呼び出しの JSON デコードエラー検出と明示的な例外。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集の骨組みを追加（デフォルトソースに Yahoo Finance のビジネスカテゴリを設定）。
  - セキュリティ・堅牢性向上策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - 受信最大バイト数制限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
    - 記事IDは正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を確保する方針（実装注記あり）。
    - HTTP(S) スキーム以外拒否や SSRF に留意した実装方針（実装中の安全チェックが見られる）。
  - DB へのバルク挿入のためのチャンク処理、トランザクションでのまとめ保存の方針。

- 研究（research）モジュール
  - factor_research: Momentum / Volatility / Value を計算する関数を実装（calc_momentum / calc_volatility / calc_value）。
    - DuckDB のウィンドウ関数を利用した効率的な実装。
    - データ不足時の None ハンドリング、営業日ベース（連続レコード）での窓定義。
    - ma200（200日移動平均）、ATR（20日）、出来高比率、avg_turnover、PER/ROE 取得ロジックを実装。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（Spearman）計算（calc_ic）、列統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - horizons 入力検証、単一クエリでのリード取得、Spearman の計算（ランクの平均重複処理対応）をサポート。
    - 外部依存（pandas 等）を用いず標準ライブラリのみで実装する方針。
  - research パッケージの公開 API を __all__ で整理（zscore_normalize を re-export）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date) を実装。
    - research の calc_* 結果を統合し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5億円）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）と ±3 クリップ。
    - features テーブルへ日付単位の置換（DELETE + bulk INSERT、トランザクションで原子性確保）。
    - target_date 時点の価格（休場日・当日欠損を考慮し target_date 以前の最新価格）を参照する設計でルックアヘッドバイアスを防止。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold, weights) を実装。
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントを計算。
    - コンポーネントは欠損時に中立値 0.5 で補完して不当な降格を防止。
    - final_score は重み付き合算。weights はデフォルト値からフォールバック・バリデーション（負値/NaN/未知キーを除外）・正規化（合計1にリスケール）を行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合に BUY 抑制）。
    - BUY は threshold（デフォルト 0.60）超のみ。SELL はポジション（positions テーブル）に対するストップロス（-8%）・スコア低下で判定。
    - SELL 優先ポリシー（SELL 対象は BUY から除外し、ランク再付与）。
    - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性を保証）。
    - ロギングにより操作の追跡を実施。

- API と DB 操作全般の堅牢化
  - 多くの箇所でトランザクション（BEGIN/COMMIT/ROLLBACK）を用いた原子操作を採用。
  - 例外発生時の ROLLBACK 試行と警告ログ出力。

### Changed
- （初期リリースにつき該当なし）

### Fixed
- （初期リリースにつき該当なし）

### Security
- news_collector で defusedxml を使用、受信サイズ制限、トラッキングパラメータ除去等により XEE / XML Bomb / メモリDoS / トラッキング対策を考慮。
- jquants_client の HTTP エラー・リトライ処理でトークン再発行時の無限再帰を防ぐ設計（allow_refresh フラグ）。

### Notes / Known limitations
- 一部エグジット条件（トレーリングストップ、時間決済）は仕様コメントとして残されており、positions テーブルに peak_price / entry_date が必要なため未実装。
- news_collector の記事ID生成・symbols 紐付けの完全な実装（news_symbols への格納等）は骨子が記載されているが、ファイル末尾で処理の続きがある想定（この差分では途中までの実装を確認）。
- research モジュールは pandas 等に依存しない実装を採用しているため、データ量が大きい環境ではパフォーマンス評価が必要（DuckDB を活用した SQL ベースの処理が中心）。
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize）は re-export されるが、本 CHANGELOG 作成時点ではその実装の詳細は別ファイルにある前提。

---

今後のリリースでは以下を検討・追記すると良い点
- news_collector の URL 安全性チェック（SSRF 対策）を明示的にテストでカバー。
- positions に関する追加メタデータ（peak_price, entry_date）を DB スキーマに組み込み、トレーリングストップや時間決済を実装。
- 単体テスト / 統合テストの導入と CI パイプラインでの自動検証。
- performance/プロファイリングに基づく DuckDB クエリ最適化や並列取得の検討。