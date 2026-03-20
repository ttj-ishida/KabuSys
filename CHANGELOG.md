CHANGELOG
=========

すべての重要な変更履歴を記載します。本ファイルは Keep a Changelog の形式に準拠します。

フォーマットの意味:
- Added: 新規追加された機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Removed: 削除
- Security: セキュリティ関連
- Internal: 実装上の注記・設計意図や将来の TODO

[Unreleased]
------------

- 特になし（初回リリースは 0.1.0 を参照）。

[0.1.0] - 2026-03-20
--------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期構成を追加。バージョンは 0.1.0。
  - 公開モジュール: data, strategy, execution, monitoring（execution はパッケージ初期化のみ）。

- 設定管理 (.env / 環境変数)
  - 環境変数管理モジュールを追加（kabusys.config.Settings）。
  - プロジェクトルート自動検出機能: .git または pyproject.toml を起点に .env を探索。
  - 自動ロード順: OS 環境変数 > .env.local > .env。 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装: export プレフィックス対応、シングル/ダブルクォートおよびエスケープ処理、行内コメント処理。
  - 必須環境変数取得用の _require と、KABUSYS_ENV / LOG_LEVEL の検証（有効値チェック）。
  - Slack / J-Quants / kabu API / DB パス等の設定プロパティを提供。

- データ取得・保存 (J-Quants)
  - J-Quants API クライアントを追加（kabusys.data.jquants_client）。
  - レート制限管理 (120 req/min) の固定間隔スロットリング実装（内部 RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライする仕組みを実装（トークンキャッシュ共有）。
  - ページネーション処理を備えた fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への安全な保存関数を提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - 挿入は冪等（ON CONFLICT DO UPDATE）で実装。
    - PK 欠損行のスキップ、挿入件数のログ出力。

- ニュース収集
  - RSS 収集モジュールを追加（kabusys.data.news_collector）。
  - デフォルト RSS ソース（Yahoo Finance のカテゴリフィード）。
  - 記事 ID の生成方針（URL 正規化後の SHA-256 の先頭部）で冪等性を担保。
  - 受信サイズ上限（10MB）、トラッキングパラメータ除去、URL 正規化、テキスト前処理、バルク INSERT のチャンク処理を実装。
  - XML パーサに defusedxml を使用して XML-based 攻撃に備える。

- 研究用 / ファクター計算
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算関数を追加。
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200日移動平均の乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（true_range 取り扱いに注意）。
    - calc_value: 最新財務データ（raw_financials）と価格を組み合わせて PER / ROE を計算。
  - feature_exploration: 将来リターン計算、IC（Spearman の ρ）計算、ファクター統計サマリ、ランク付けユーティリティを追加。
    - calc_forward_returns: 複数ホライズン対応（デフォルト [1,5,21]）、入力検証あり。
    - calc_ic: ランク相関（Spearman）を自前実装（同順位は平均ランクで処理）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - 研究モジュールは外部ライブラリ（pandas 等）に依存しない設計。

- 特徴量エンジニアリング（戦略連携）
  - strategy.feature_engineering.build_features を実装。
    - research モジュールから raw factor を取得し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 正規化（zscore_normalize を利用）→ ±3 でクリップ → features テーブルへ日付単位で UPSERT（トランザクションで原子性保証）。
    - 休場日や当日の欠損に対応するため target_date 以前の最新価格を参照してユニバース判定。

- シグナル生成
  - strategy.signal_generator.generate_signals を実装。
    - features と ai_scores を統合し、各銘柄の component スコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントのシグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重みは momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10。閾値（BUY）デフォルトは 0.60。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、ただしサンプル数 3 未満は判定しない）時は BUY を抑制。
    - SELL 判定ロジック（positions テーブル参照）: ストップロス（終値/avg_price -1 < -8%）優先、final_score が threshold 未満の銘柄を SELL。
    - SELL を優先して BUY から除外し、signals テーブルへ日付単位で置換（トランザクションで原子性保証）。

- 公開 API の整理
  - strategy パッケージ __all__ に build_features / generate_signals を公開。
  - research パッケージに主要ユーティリティをエクスポート（calc_momentum 等、zscore_normalize も再エクスポート）。

Security
- ニュース収集で defusedxml を使用し XML Bomb 等への対策を実施。
- RSS 取得時の受信バイト数上限（10 MB）でメモリ DoS を軽減。
- URL 正規化によりトラッキングパラメータを削除し、記事 ID を安定化。
- J-Quants クライアントはタイムアウト・リトライ・token refresh を備え、過度なリクエストを防ぐためのレート制御を行う。

Internal / Implementation notes
- DuckDB 操作は多くの箇所でトランザクション（BEGIN/COMMIT/ROLLBACK）およびバルク挿入を用い、原子性とパフォーマンスを重視。
- データ変換ユーティリティ (_to_float / _to_int) は不正入力に寛容に None を返す実装。
- zscore_normalize は kabusys.data.stats 側で提供され、feature_engineering で利用。
- signal_generator の weights は入力検証を行い、未知キーや非数値・負値は無視して既知の重みのみを利用、合計が 1.0 でない場合は再スケールする。
- 一部仕様はコード内コメントで将来実装予定（例: トレーリングストップや時間決済は positions テーブルに peak_price / entry_date が必要で未実装）。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Notes / Known limitations
- 一部のエグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルの拡張が必要。
- news_collector のさらなる SSRF/IP ホワイトリスト検査やソケットレベルの検証は将来の強化対象。
- J-Quants API のレート制限やレスポンス仕様変更に伴う挙動は運用で監視が必要。

作者: kabusys コードベース（自動生成物の説明に基づき作成）