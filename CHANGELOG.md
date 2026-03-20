# Changelog

すべての変更は Keep a Changelog のフォーマットに従っています。  
このファイルはコードベース（初期リリース相当）から推測して作成した変更履歴です。

全般的な注記
- 本リリースでは日本株自動売買システム「KabuSys」のコアライブラリ群を提供します。
- 多くのモジュールが DuckDB を利用してオンプレ／ローカル分析環境で完結する設計になっています。
- 外部依存は最小限に抑え、研究（research）用のユーティリティは pandas 等に依存しない実装を心がけています。
- 一部の設計（発注実行層 / execution）は骨子のみで実装が未着手です（TODO/今後実装予定箇所あり）。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - kabusys パッケージ初期版を追加。パッケージバージョンは 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理（src/kabusys/config.py）
  - Settings クラスを追加し、環境変数経由で設定値を取得する API を提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャネル、DB パス等）。
  - 自動 .env 読み込み機能を実装（プロジェクトルート探索は .git / pyproject.toml を基準）。読み込み順: OS 環境変数 > .env.local > .env。
  - .env パーサーを堅牢化：export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理（空白直前の # をコメント扱い）等に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロードの無効化機能。
  - env（KABUSYS_ENV）と log_level（LOG_LEVEL）の検証（許容値チェック）を実装。

- データ取得 / 保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（株価日足 / 財務 / 市場カレンダーの取得）。
  - レートリミッタ（_RateLimiter）で固定間隔スロットリング（デフォルト 120 req/min）を実装。
  - 冪等性を考慮した保存処理：DuckDB への INSERT は ON CONFLICT DO UPDATE を使う（save_daily_quotes, save_financial_statements, save_market_calendar）。
  - ページネーション対応の fetch_* 関数を実装。
  - リトライ・指数バックオフ（最大 3 回）、HTTP 408/429/5xx に対する再試行、429 の Retry-After 優先処理を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回リトライする仕組みを実装（無限再帰保護あり）。
  - データ型変換ユーティリティ (_to_float, _to_int) を実装し、空値や不正値へ安全に対応。
  - レスポンス取得時に fetched_at を UTC ISO8601 で記録し、look-ahead bias のトラッキングが可能。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集して raw_news テーブルへ冪等保存する基礎実装を追加。
  - セキュリティ考慮点を実装／想定：defusedxml による XML パース（XML Bomb 回避）、受信サイズ上限（MAX_RESPONSE_BYTES=10MB）、URL 正規化とトラッキングパラメータ除去（_normalize_url）、挿入チャンク化（_INSERT_CHUNK_SIZE）など。
  - デフォルト RSS ソース定義（Yahoo Finance のビジネスカテゴリ等）。

- リサーチ（src/kabusys/research）
  - ファクタ計算（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離（ma200_dev）を計算する関数を実装。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算する関数を実装。
    - calc_value: raw_financials と当日株価を組み合わせて PER / ROE を計算する関数を実装。
    - 各関数は prices_daily / raw_financials テーブルのみ参照し、データ不足時は None を扱う。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得・計算する。
    - calc_ic: ファクターと将来リターンのスピアマン IC（ランク相関）を計算するユーティリティを追加（有効レコード数 < 3 の場合は None を返す）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）および基本統計量サマリを実装。
    - 研究モジュールは外部ライブラリに依存しない実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research の生ファクター（momentum/volatility/value）を取得、ユニバースフィルタ適用（最低株価 300 円、20日平均売買代金 >= 5 億円）、Z スコア正規化（指定列）、±3 でクリップして features テーブルへ日付単位の置換（トランザクションで原子性確保）する処理を実装。
  - ルックアヘッドバイアス対策として target_date 時点のデータのみを使用。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold, weights): features / ai_scores / positions を参照し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付け合算して final_score を作成。BUY（閾値超過）・SELL（エグジット条件）を生成し signals テーブルへ日付単位置換で保存。
  - AI スコア統合（ai_scores）と Bear レジーム検知ロジック（レジームスコア平均が負なら Bear。ただしサンプル数閾値あり）を実装。Bear レジーム時は BUY シグナルを抑制。
  - エグジット条件としてストップロス（終値/avg_price - 1 < -8%）とスコア低下（final_score < threshold）を実装。SELL 判定は保有ポジションの最新情報・最新価格を参照。価格欠損時は SELL 判定をスキップする安全策を導入。
  - weights の検証・正規化、未知キーや不正値の無視、合計が 1.0 でない場合の再スケール等を実装。
  - signals テーブルへの書き込みはトランザクションで原子性を担保。SELL 優先ルール（SELL 対象は BUY から除外）を適用。

- インターフェース整理
  - strategy パッケージとして build_features / generate_signals をエクスポート（src/kabusys/strategy/__init__.py）。
  - research パッケージとして主要ユーティリティをエクスポート（src/kabusys/research/__init__.py）。

### Changed
- 初期リリースのため該当なし（設計方針や実装上の決定事項を含む）。

### Fixed
- 初期リリースのため該当なし。

### Security
- ニュースパーサーで defusedxml を使用し XML による攻撃から保護する設計を明記。
- ニュース取得で受信サイズ制限（MAX_RESPONSE_BYTES）を導入しメモリ DoS を軽減する方針。
- J-Quants API クライアントで認証が切れた際に自動トークンリフレッシュを行い、かつ無限再帰にならないよう設計。
- API レート制限を守る固定間隔スロットリングにより過剰なリクエストを抑止。

### Known issues / TODOs
- execution パッケージは空（src/kabusys/execution/__init__.py）。発注ロジック・kabu ステーション連携は未実装。
- sell 条件のうちトレーリングストップ（peak_price に依存）や時間決済（保有 60 営業日超）の実装は未実装。positions テーブルに peak_price / entry_date の保存が必要。
- news_collector において IP/SSRF 制御や接続のホワイトリスト化の具体実装は注釈はあるが、コード内での厳密なバリデーション（IP アドレスチェック等）の完成度は要確認。
- research モジュールは標準ライブラリ中心で実装しているため、大規模データでのパフォーマンス/使い勝手は今後の改善余地あり。
- 単体テスト・統合テストはコードからは確認できないため、テスト整備が必要。

---

参考: 各モジュールの主要関数・動作はソースコードの docstring に詳述されています。実運用前に環境変数（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等）の設定、DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals 等）の準備を行ってください。