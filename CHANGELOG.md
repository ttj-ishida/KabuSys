# Changelog

すべての重大な変更はこのファイルに記録します。  
このファイルは「Keep a Changelog」仕様に準拠しています。  
安定版リリースはセマンティックバージョニングを使用します。

<!-- 次のリリースがあるまで Unreleased セクションを利用できます。 -->
## [Unreleased]

### 追加
- ドキュメント
  - パッケージのトップレベル docstring を追加（KabuSys - 日本株自動売買システム）。
- 環境設定（kabusys.config）
  - .env / .env.local 自動読み込み機能を実装。読み込み順序は OS 環境変数 > .env.local > .env。
  - プロジェクトルート検出は __file__ の親ディレクトリを遡る実装（.git または pyproject.toml を基準）。
  - .env パーサーの実装:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理、インラインコメント無視対応
    - クォートなしの値に対するコメントパーシング（# 前のスペース/タブ判定）
  - 自動読み込み無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを導入し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス等）をプロパティ経由で取得。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL の許容値）と補助プロパティ（is_live / is_paper / is_dev）を追加。

- データ取得／永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限対応（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xxに対してリトライ）、429 の Retry-After ヘッダ優先。
  - 401 受信時の自動トークンリフレッシュを実装（1回のみリフレッシュして再試行）。
  - モジュールレベルの ID トークンキャッシュを導入し、ページネーション間で共有。
  - データ保存用ユーティリティを実装（DuckDB へ冪等保存: INSERT ... ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices テーブル）
    - save_financial_statements（raw_financials テーブル）
    - save_market_calendar（market_calendar テーブル）
  - データ整形ユーティリティ _to_float / _to_int を追加（型安全・不正値処理）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集モジュール実装（デフォルトに Yahoo Finance business RSS を登録）。
  - URL 正規化機能を実装（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
  - セキュリティ対策:
    - defusedxml を利用して XML 攻撃（XML Bomb 等）を回避
    - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES）を導入してメモリDoS を軽減
    - RSS パース前の入力検証と SSRF を考慮した URL チェック方針（実装方針として明記）
  - 記事IDを正規化 URL の SHA-256（先頭32文字）で生成する方針を導入（冪等性確保）。
  - raw_news へのバルク挿入のチャンク処理とトランザクション方針を設計。

- リサーチ（kabusys.research）
  - ファクター計算と探索ツール群を実装:
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman の ρ 計算）、factor_summary、rank
  - 実装方針の明文化:
    - DuckDB の SQL + Python による実装（外部依存を避ける）
    - ルックアヘッドバイアスを避けるため target_date 時点のデータのみを用いる

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 関数を実装:
    - research モジュールの calc_* を結合
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）
    - 正規化（zscore_normalize を利用）、±3 でクリップ
    - features テーブルへの日付単位の置換（BEGIN/DELETE/INSERT/COMMIT）、冪等性
  - 正規化対象カラムや閾値等を定数で管理。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 関数を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算
    - final_score を重み付き合算してランク付け、BUY（閾値 0.60）・SELL（ストップロス、スコア低下）を生成
    - Bear レジーム検知（ai_scores の regime_score 平均が負でかつサンプル数しきい値を満たす場合）による BUY 抑制
    - weights の入力検証と合計スケーリング処理（デフォルト重みは StrategyModel.md に準拠）
    - positions テーブルと prices_daily を参照したエグジット判定
    - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）により冪等性を保証
  - スコア計算ユーティリティ（_sigmoid/_avg_scores 等）を提供。

- パッケージエントリ（kabusys.__init__）
  - __version__ を "0.1.0" に設定。
  - パッケージ公開 API として data, strategy, execution, monitoring を __all__ に含める（execution, monitoring の実体は別ファイルで管理）。

## [0.1.0] - 2026-03-19

初回公開リリース。上記「追加」に記載の全機能を含む初期実装。

### 既知の制約・未実装（重要）
- エグジット条件の一部（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date 等の追加が必要。
- news_collector の具体的な RSS 取得・パースの完全実装（ネットワーク周りの堅牢化や複数ソースの管理）は今後の改善対象。
- research モジュールは外部ライブラリへ依存しない設計のため、処理性能・互換性については実データでの検証が必要。
- J-Quants client は HTTP 周りを urllib で実装しているため、高度な接続管理（セッション再利用やコネクションプーリング）は未対応。大量リクエスト時の挙動は実環境での検証推奨。
- 一部の入力検証・例外メッセージは改善余地あり（ユーザ向けエラーの明確化など）。

### 今後の予定（例）
- execution 層の実装（kabu ステーション API との連携、注文発行ロジック）
- monitoring 用の Slack 通知・メトリクス収集実装
- news_collector の記事→銘柄マッチングロジック（news_symbols テーブル関連）の実装
- 単体テスト・統合テストの整備および CI ワークフローの追加

---

保持フォーマット:
- バージョンヘッダは [バージョン] - YYYY-MM-DD（公開日）形式
- 主要カテゴリ: Added, Changed, Deprecated, Removed, Fixed, Security, などを必要に応じて使用

お問い合わせ・修正提案があれば、変更内容を仮定して追記・修正します。