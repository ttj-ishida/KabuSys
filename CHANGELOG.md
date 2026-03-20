Keep a Changelog
=================

すべての注目すべき変更をこのファイルで管理します。  
この CHANGELOG は「Keep a Changelog」のフォーマットに準拠して記載しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

（現時点では未リリースの差分はありません）

[0.1.0] - 2026-03-20
-------------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点と設計上の要点は以下のとおりです。

Added
- パッケージ基盤
  - パッケージのエントリポイントを追加（kabusys.__init__、バージョン 0.1.0、公開 API の __all__ 定義）。
- 環境設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装。読み込み順は OS 環境変数 ＞ .env.local ＞ .env。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）により CWD 非依存で動作。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト等で利用可能）。
  - .env ファイルの細かいパーサを実装（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント取り扱い等）。
  - 環境変数取得ラッパ（Settings クラス）を追加。必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）を明示的に要求。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証（許容値チェック）、および is_live / is_paper / is_dev の便利プロパティ。
  - データベースパス設定（DUCKDB_PATH、SQLITE_PATH）の Path 型返却。

- データ取得 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（トークン取得・ページネーション・取得関数）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - HTTP リトライ（指数バックオフ、最大試行回数、429 の Retry-After 考慮、特定ステータスでのリトライ対象設定）。
  - 401 受信時の自動トークンリフレッシュロジック（1 回のみのリフレッシュとリトライ）とモジュール内トークンキャッシュ。
  - DuckDB への冪等保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT による更新、PK 欠損行のスキップと警告、UTC fetched_at の記録。
  - 値変換ユーティリティ（_to_float, _to_int）を実装し不正値を安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集機能を実装。デフォルトソースに Yahoo Finance のビジネス RSS を追加。
  - セキュリティ／堅牢性設計:
    - defusedxml による XML パース（XML Bomb 等の回避）。
    - 受信最大バイト数制限（10 MB）によるメモリ DoS 対策。
    - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント除去、クエリソート。
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）を使用して冪等性を確保。
    - SSRF を想定したスキームチェックや IP チェックの実装（設計の記述あり）。
  - DB へのバルク保存はチャンク化して効率化、INSERT RETURNING を想定した設計（実装コメント）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算（calc_momentum, calc_volatility, calc_value）を実装。prices_daily/raw_financials に基づく算出。
    - Momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200 日 MA を用いる。データ不足時は None）。
    - Volatility: ATR（20 日平均）、atr_pct、avg_turnover、volume_ratio（20 日ウィンドウ）。true_range の NULL 伝播を明示的に扱い正確にカウント。
    - Value: 最新の財務情報（raw_financials の target_date 以前の最新）と当日の株価を組み合わせて PER/ROE を計算。
  - 研究用ユーティリティ:
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト 1/5/21 営業日）を一度のクエリで取得、ホライズンの検証（1〜252）。
    - IC（Spearman の ρ）計算（calc_ic）: ランク相関（ties は平均ランク処理）を実装。
    - ランク変換ユーティリティ（rank）とファクター統計サマリー（factor_summary）。
  - 実装方針として DuckDB と標準ライブラリのみで動作するよう設計（本番発注 API へのアクセスなし）。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールで計算した raw factor をマージ、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）と ±3 でのクリップ。
    - features テーブルへの日付単位アップサート（トランザクションによる原子性）。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄の component スコアを計算（momentum/value/volatility/liquidity/news）。
    - コンポーネントはシグモイド変換、欠損は中立値 0.5 で補完。
    - final_score を重み付き合算（デフォルト重みを実装）。weights の検証と正規化、ユーザ指定重みの取り扱い（不正値は無視）。
    - Bear レジーム検知（ai_scores の regime_score の平均が負の場合。ただしサンプル数閾値あり）。
    - BUY 閾値（デフォルト 0.60）を超える銘柄を BUY。Bear レジーム時は BUY を抑制。
    - 保有ポジションのエグジット判定（ストップロス -8% とスコア低下）。
    - signals テーブルへ日付単位の置換（トランザクションによる原子性）。SELL 優先ポリシー（SELL の対象は BUY から除外）を実装。
- ロギング/堅牢性
  - 多数の処理で詳細な logger 呼び出しを追加し、警告・デバッグ情報を出力。
  - DB 操作はトランザクションで囲み、失敗時に ROLLBACK を試行。ROLLBACK 失敗時は警告。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Known limitations / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は comments に記載されているが未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector は設計で SSRF/IP チェック等を想定しているが、運用時の細部設定や外部ネットワークポリシーに応じた追加検証が必要。
- zscore_normalize 本体は data.stats 側に存在（本リリースでは参照実装で利用）。利用時は該当モジュールの動作確認を行ってください。
- 外部依存: defusedxml をニュース処理で使用。環境に導入が必要。

Security
- セキュリティ上重要な点
  - defusedxml を利用して XML 関連の攻撃を軽減。
  - 外部 URL を扱う際の正規化・トラッキング除去・受信サイズ制限等の対策を実施。
  - API トークンは環境変数経由で管理し、自動リフレッシュとキャッシュを安全に実装。

開発上の注記
- DuckDB を主要なデータストアとして想定しており、SQL は DuckDB のウィンドウ関数等を使用して最適化されています。
- ルックアヘッドバイアス回避のため、すべての計算は target_date 時点の利用可能データのみを使用する設計方針で統一されています。

---
この CHANGELOG はコードベースのソースから機能と設計意図を推測して作成しました。実際のリリースノートやユーザー向けドキュメント作成時は、運用上の追加情報（互換性、インストール手順、依存関係のバージョン等）を補足してください。