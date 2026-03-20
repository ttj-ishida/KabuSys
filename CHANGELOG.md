# Changelog

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
以下の履歴はソースコードの内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース（コードベースから推測）

### Added
- パッケージ基盤
  - パッケージ初期化と公開 API を定義 (kabusys.__init__, kabusys.strategy.__init__)。
  - バージョン情報 __version__ = "0.1.0" を追加。

- 設定管理
  - 環境変数・.env の自動読み込み機能を実装（kabusys.config）。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索し、CWD に依存しない動作を実現。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
    - .env ファイルの読み込みは保護キーセットを尊重し、override オプションで上書き制御。
  - .env パーサの強化:
    - コメント行・空行のスキップ、export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - クォートなし値のインラインコメント判定（直前が空白・タブの場合のみ）。
  - Settings クラスを提供:
    - J-Quants / kabu API / Slack / DB パス等のプロパティを定義。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値に外れると ValueError）。
    - is_live / is_paper / is_dev のブール判定プロパティ。

- データ取得・保存（J-Quants）
  - J-Quants API クライアント実装（kabusys.data.jquants_client）。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - リトライロジック（指数バックオフ、最大 3 回）と 408/429/5xx のハンドリング。
    - 401 受信時はリフレッシュトークンでトークン再取得して 1 回リトライ（トークンキャッシュを module レベルで共有）。
    - ページネーション対応の fetch_* 関数（daily quotes, financial statements, market calendar）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装し、冪等性のため ON CONFLICT DO UPDATE を使用。
    - レスポンスからの型変換ユーティリティ (_to_float / _to_int) を追加し、不正値を安全に扱う。

- ニュース収集
  - RSS ベースのニュース収集モジュール（kabusys.data.news_collector）。
    - RSS 取得・XML パース（defusedxml を使用）・テキスト前処理・正規化を想定。
    - URL 正規化ユーティリティ（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、クエリソート）。
    - セキュリティ対策: XML Bomb 防止（defusedxml）、受信サイズ上限（MAX_RESPONSE_BYTES）、HTTP スキーム検証や SSRF 対策を想定。
    - バルク INSERT のチャンク処理、ハッシュによる記事 ID 生成（冪等性）等を設計に明記。

- リサーチ（ファクター計算・解析）
  - factor_research モジュールを実装（kabusys.research.factor_research）。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB 上の SQL ウィンドウ関数で計算。
    - 欠損・データ不足時の安全な None ハンドリング。
  - feature_exploration を追加（kabusys.research.feature_exploration）。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、1/5/21 日デフォルト）。
    - IC（Spearman の ρ）計算 calc_ic、rank、factor_summary（count/mean/std/min/max/median）。
    - 外部依存（pandas 等）を用いず標準ライブラリ＋DuckDB で完結する設計。
  - research パッケージの公開 API を定義。

- 特徴量エンジニアリング
  - feature_engineering.build_features を実装（kabusys.strategy.feature_engineering）。
    - research 側のファクターを取得してマージし、ユニバースフィルタ（最低株価 / 20 日平均売買代金）を適用。
    - z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）して冪等性を確保。
    - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。

- シグナル生成＆ポートフォリオロジック
  - signal_generator.generate_signals を実装（kabusys.strategy.signal_generator）。
    - features と ai_scores を組み合わせて各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損コンポーネントは中立値（0.5）で補完。
    - 重みのマージと正規化機能（ユーザ指定 weights を受け入れ、無効値はスキップ、合計を 1 に再スケール）。
    - Bear レジーム判定（ai_scores の regime_score の平均 < 0 かつサンプル数閾値を満たす場合）で BUY を抑制。
    - BUY シグナルは閾値（デフォルト 0.60）を超える銘柄に対して生成。SELL は保有ポジションに対してストップロス / スコア低下で判定。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）により冪等性を確保。
    - ロギングによる状況報告（INFO/DEBUG/WARNING）。

- トランザクション安全性・ロギング
  - 各 DB 更新処理で BEGIN/COMMIT/ROLLBACK を明示的に使用し、ROLLBACK に失敗した場合の警告ログ出力を追加。
  - 各主要処理で logger を用いた情報ログ/警告ログを豊富に追加。

### Changed
- （初出のため該当なし。上記機能は今回の初期実装として導入されていると推測されます）

### Fixed
- （初出のため該当なし。パーサ・保存処理等で堅牢化が施されている）

### Security
- ニュース XML のパースに defusedxml を使用し XML 関連攻撃（XML Bomb 等）を防止。
- RSS URL 正規化・ホスト小文字化・トラッキングパラメータ削除・受信サイズ上限などによりメモリ DoS やトラッキング耐性を強化。
- J-Quants クライアントはトークンリフレッシュを安全に行い、無限再帰を防ぐため allow_refresh フラグを使用。

### Known limitations / TODO (コード内コメントより)
- signal_generator の売り条件で未実装の項目:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- NewsCollector の完全な実装（RSS パースの詳細、記事→銘柄マッチング等）はファイル末尾の続きで実装される想定。
- 一部ユーティリティ（kabusys.data.stats.zscore_normalize 等）は別モジュールに依存（本スナップショットでは省略）。
- calc_ic は有効サンプルが 3 未満の場合 None を返す設計（サンプル不足での誤判定回避）。
- get_id_token は settings.jquants_refresh_token に依存。環境変数未設定時は例外を投げる。

---

（注）この CHANGELOG は提供されたソースコードの実装内容・コメントから推測して作成しています。より正確な変更履歴（コミットやリリースノート）を反映するには、実際の git コミット履歴やリリース文書をご提供ください。