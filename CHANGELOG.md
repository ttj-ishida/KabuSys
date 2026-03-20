# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従います。
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-20

初回公開リリース。

### Added
- パッケージ初期構成を追加
  - src/kabusys/__init__.py にバージョン情報 (0.1.0) と公開 API モジュール一覧を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動ロードする仕組みを実装。
    - 行パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - .env と .env.local の読み込み順序と override 挙動（.env.local が優先）を実装。OS環境変数を保護する protected オプションを実装。
    - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム環境（env, log_level）などの設定をプロパティ経由で取得。必須環境変数未設定時は ValueError を送出、env/log_level に対する入力検証を実装。

- データ取得・保存（J-Quants API クライアント）
  - src/kabusys/data/jquants_client.py
    - J-Quants API への問い合わせを行うクライアントを実装（ページネーション対応）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）と特定ステータスコード(408,429,5xx)での再試行を実装。
    - 401 応答時にリフレッシュトークンを使って ID トークンを自動更新して再試行する仕組みを実装（無限再帰対策あり）。
    - fetch_* 系関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）と DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。保存は冪等（ON CONFLICT DO UPDATE）で行う。
    - レスポンスの JSON デコードエラーやページネーションでのトークン共有など実運用向けの堅牢性を考慮。

- ニュース収集
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュースを取得し raw_news テーブルへ保存する機能を実装するための基盤を追加。
    - URL 正規化関数（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）や記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成する方針を実装。
    - defusedxml を用いた XML パース、受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策などセキュリティ考慮を記載。
    - デフォルト RSS ソース（yahoo_finance）を含む設定。

- 研究（Research）モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6M リターン、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR、平均売買代金、出来高比率）、バリュー（PER, ROE）を DuckDB の prices_daily / raw_financials を用いて計算する関数を実装（calc_momentum, calc_volatility, calc_value）。
    - 計算でのスキャン範囲・窓幅・欠損時の扱い（partial window の扱い、十分データがない場合は None）を明記。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン算出（calc_forward_returns）、IC（Spearman の ρ）計算（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティ（rank）を実装。
    - calc_forward_returns は複数ホライズン対応、クエリをまとめて1回で取得する最適化を実施。
    - calc_ic は ties を平均ランクで扱い、サンプル不足（<3）では None を返す。

  - src/kabusys/research/__init__.py にエクスポートを追加。

- 戦略（Strategy）モジュール
  - src/kabusys/strategy/feature_engineering.py
    - 研究環境で計算した raw factor を取り込み、ユニバースフィルタ（最低株価・最低売買代金）、Zスコア正規化（外れ値 ±3 でクリップ）、features テーブルへの日付単位の置換（トランザクションで原子性）を行う build_features を実装。
    - ユニバースフィルタ基準（_MIN_PRICE=300 円, _MIN_TURNOVER=5e8 円）、及び正規化対象カラム定義を実装。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各銘柄の最終スコア（final_score）を計算し、BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティ（シグモイド変換、平均化、PER を用いた value スコアなど）を実装。
    - 重みの受け取りと検証（未知キー除外、負値や非数値は無視、合計が 1.0 に補正）を実装。
    - Bear レジーム判定（ai_scores の regime_score 平均が負、サンプル閾値あり）により BUY を抑制。
    - エグジット判定（停止損失: -8% 以下、スコア低下）を実装。SELL 優先で BUY リストから除外。
    - トランザクション＋バルク挿入で原子性を保つ。

- パッケージ API 統合
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を用いた安全な XML パース、受信サイズ制限、SSRF 対策の設計を反映。
- jquants_client でトークン自動リフレッシュや再試行の扱いを明確化し、トークン取得時の無限再帰を防止。

### Known limitations / Notes
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装（コメントで将来実装予定を記載）。
- src/kabusys/execution パッケージは空のプレースホルダ（実際の発注ロジックは含まれていません）。
- データ保存/正規化で使用される zscore_normalize は kabusys.data.stats から提供される前提（今回の差分に実装ファイルは含まれていません）。
- テスト・実運用では .env の取り扱い（自動ロード）を必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD で制御してください。

---

今後のリリースでは、実行（execution）層の実装、追加のエグジットロジック、CI/テスト、ドキュメント整備を予定しています。