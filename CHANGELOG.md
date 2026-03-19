Keep a Changelog準拠の形式で、コードベースから推測した変更履歴を日本語で作成しました。

CHANGELOG.md
=============
すべての注目すべき変更を記録します。  
このファイルは「Keep a Changelog」のガイドラインに従います。

[Unreleased]
------------

- （現在のリリース以降の未リリース変更はここに記載します）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初期リリース: kabusys v0.1.0 を追加。
  - パッケージエントリポイントを定義（src/kabusys/__init__.py）。
  - 公開 API: data, strategy, execution, monitoring を __all__ に登録。
- 環境変数/設定管理（src/kabusys/config.py）を追加。
  - .env / .env.local の自動ロード機能（プロジェクトルート検出: .git または pyproject.toml）。
  - .env パースの堅牢化（コメント・export 形式、クォート内エスケープ、インラインコメント処理）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル取得をプロパティで公開。
  - env / log_level に対する入力検証（許容値チェック）と is_live / is_paper / is_dev のヘルパー。
- データ取得・保存（J-Quants）クライアント（src/kabusys/data/jquants_client.py）を追加。
  - 固定間隔レートリミッタ実装（120 req/min 制約を尊重）。
  - HTTP リトライ（指数バックオフ、最大3回）、408/429/5xx を対象にリトライ、429 の Retry-After を尊重。
  - 401 受信時はリフレッシュトークンで自動的にトークン更新して単一再試行を行う設計。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への冪等保存関数 save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT DO UPDATE を使用）。
  - 型変換ユーティリティ _to_float / _to_int を追加し、不正な値や空値を安全に扱う。
  - 取得時間の追跡（fetched_at を UTC で記録）によりルックアヘッドバイアスのトレースを可能に。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）を追加。
  - RSS フィード取得・正規化、記事ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保。
  - defusedxml を使った XML パースで XML Bomb 等の攻撃対策。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）、URL 正規化（トラッキングパラメータ除去、クエリ整列、スキーム/ホスト小文字化、フラグメント除去）などの防御処理を実装。
  - DB 保存時のバルク挿入チャンク化とトランザクションまとめによる効率化。
- 研究用モジュール（src/kabusys/research/）を追加。
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクターを算出。
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日未満は None）
    - Volatility: atr_20, atr_pct, avg_turnover, volume_ratio（ATR/ウィンドウ不足時は None）
    - Value: per / roe（最新財務データを JOIN して計算）
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関による IC 計算）、factor_summary（基本統計量算出）、rank（同順位は平均ランク）を実装。
  - research パッケージの __all__ に主要関数を公開。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）を追加。
  - research モジュールで算出した生ファクターをマージし、ユニバースフィルタ（最低株価・平均売買代金）を適用。
  - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへ日付単位で置換（DELETE→INSERT）を行い、トランザクションで原子性を保証する build_features を実装。
- シグナル生成（src/kabusys/strategy/signal_generator.py）を追加。
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
  - コンポーネントを重み付き合算して final_score を算出（デフォルト重みを定義）。
  - 重みの入力検証と合計が 1.0 でない場合の再スケーリングを実装。
  - Bear レジーム判定（ai_scores の regime_score 平均 < 0 が基準、サンプル数閾値あり）により BUY シグナルを抑制。
  - BUY 閾値（デフォルト 0.60）を超える銘柄に BUY シグナルを生成。
  - 保有ポジションに対するエグジット判定（stop loss: -8% / score_drop）を実装し SELL シグナルを生成する _generate_sell_signals。
  - signals テーブルへ日付単位置換で書き込む（トランザクション＋バルク挿入）。
- トランザクション安全性とエラー取り扱いの強化。
  - build_features / generate_signals 等の DB 書き込みで BEGIN/COMMIT/ROLLBACK を明示的に使用し、ROLLBACK の失敗をログに出す仕組みを導入。

Changed
- なし（初回リリースのため）

Fixed
- なし（初回リリースのため）

Security
- ニュース収集で defusedxml を使用（XML-related 脅威への対策）。
- RSS/URL 処理でトラッキングパラメータ除去、スキーム検証、受信サイズ上限等の入力制御を追加。

Notes / Implementation details
- DuckDB を主要なデータストアとして前提（関数の引数に DuckDB の接続を受け取る設計）。
- ルックアヘッドバイアス対策: データ取得時に fetched_at を UTC で記録し、ファクター/シグナル計算は target_date 時点のデータのみを使用する方針。
- 冪等性: 外部データの保存は可能な限り ON CONFLICT（または INSERT DO NOTHING）で実装している。
- ロギングを各モジュールで利用し、警告や情報を出力する設計。

---

今後の改善候補（推測）
- news_collector の続きを実装（RSS パース→記事抽出→DB 保存の完全フロー）。
- execution 層（kabuステーション API への発注）や monitoring モジュールの実装/統合。
- zscore_normalize の実装詳細や unit test の追加。
- positions テーブルに peak_price / entry_date 等を保存してトレーリングストップや時間決済をサポート。

（以上）