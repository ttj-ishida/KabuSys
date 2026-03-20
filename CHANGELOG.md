CHANGELOG
=========

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  
リリースはセマンティックバージョニングに従います。

目次
----
- [Unreleased](#unreleased)
- [0.1.0] - 2026-03-20

Unreleased
----------
（なし）

0.1.0 - 2026-03-20
------------------

初回公開リリース。日本株自動売買システムのコア機能群を実装しました。主要な追加点と設計上の注意点は以下の通りです。

Added
- パッケージ基盤
  - パッケージ初期化 (kabusys.__init__) とバージョン情報を追加。公開 API として data, strategy, execution, monitoring を列挙。
- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から検出）。
  - .env パーサ（export 形式、クォート処理、インラインコメント、有効/無効行判定）を実装。
  - 自動ロードを環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。
  - Settings クラスを追加し、J-Quants トークン、kabu API パスワード、Slack 設定、DB パス、環境（development/paper_trading/live）、ログレベル等をプロパティ経由で取得。未設定時の検出・エラー、値検証（許容値チェック）を行う。
- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。ページネーション対応のフェッチ関数を提供:
    - fetch_daily_quotes (日足)
    - fetch_financial_statements (財務)
    - fetch_market_calendar (JPX カレンダー)
  - レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
  - リトライ（指数バックオフ、最大 3 回）と 401 時の自動トークンリフレッシュ対応を実装。
  - DuckDB へ冪等に保存するユーティリティ（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE を用いて重複を排除。
  - 入力変換ユーティリティ（_to_float / _to_int）を実装。変換失敗時は None を返す安全設計。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集・正規化して DB 保存するための基盤を実装（RSS ソース定義、受信サイズ制限、URL 正規化方針、記事 ID の SHA-256 ベース生成方針など）。
  - defusedxml を利用した XML パースで安全性を確保。
  - トラッキングパラメータ除去・URL 正規化処理を実装。DB 挿入はバルクとトランザクションを用いる設計（ON CONFLICT DO NOTHING 想定）。
- 研究用分析（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1/3/6 ヶ月モメンタム、200 日移動平均乖離率を計算。
    - calc_volatility: 20 日 ATR（絶対値および相対値）、平均売買代金、出来高比率を計算。
    - calc_value: 財務データと株価を組み合わせて PER / ROE を計算（最新財務レコードを使用）。
    - DuckDB ベースの SQL + Python 実装で外部 API に依存しない。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン先の将来リターン (デフォルト: 1,5,21 営業日) をまとめて取得。
    - calc_ic: スピアマンランク相関（IC）を計算する実装。
    - factor_summary: 各ファクターのカウント/平均/分散/std/min/max/median を算出。
    - rank: 同順位の平均ランクを扱うランク化ユーティリティ。
- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - 重みをマージして再スケーリングするロジック（カスタム weights を許容）。
    - Sigmoid によるスコア変換、欠損コンポーネントは中立値(0.5)で補完。
    - Bear レジーム判定（ai_scores の regime_score 平均が負である場合、サンプル数閾値あり）により BUY シグナルを抑制。
    - 保有ポジションのエグジット判定（ストップロス / スコア低下）を実装。SELL シグナルを生成し、SELL 優先で BUY を除外。
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
- ロギングとエラーハンドリング
  - 各モジュールで適切なログ出力（info/warning/debug）を実装。DB 操作でのトランザクション失敗時に ROLLBACK を試行し、失敗ログを残す。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed / Deprecated / Security
- （初回リリースのため該当なし）

Notes / Known limitations
- signal_generator のエグジット条件に関して、コメントで示されている以下の条件は未実装:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過）
- news_collector は安全設計（XML パース保護、受信制限、SSRF 回避方針など）を盛り込んでいるが、RSS フィード解析の全ケース（各サイト特有の namepsace / 要素）に対する追加ハンドリングは今後の改善候補。
- J-Quants クライアントはリトライ・レート制御・自動トークン更新を備えるが、実運用ではネットワーク特性に応じた追加の監視・メトリクスが推奨される。
- config モジュールの自動 .env ロードはプロジェクトルートの検出に依存するため、配布パッケージや特殊な配置では KABUSYS_DISABLE_AUTO_ENV_LOAD を用いるか、明示的に環境変数を設定して使用すること。

使用上のヒント
- 設定:
  - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - KABUSYS_ENV は development / paper_trading / live のいずれかを指定
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれか
- データ保存先:
  - デフォルトの DuckDB パス: data/kabusys.duckdb
  - デフォルトの SQLite (monitoring) パス: data/monitoring.db

今後の予定（候補）
- execution 層の実装（kabu ステーション連携／注文管理）
- モニタリング/アラート機能（Slack 経由の通知整備）
- feature 追加: トレーリングストップ/時間決済、ニュースの銘柄マッピング精度向上、AI スコアの取得パイプライン
- テストカバレッジの拡充と CI 統合

ライセンス
- （コード中に記載がないため、パッケージ配布時に適切なライセンスを明示してください）

以上。