# CHANGELOG

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" and follows Semantic Versioning.

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース。日本株自動売買（KabuSys）のコアモジュールを追加。
- 基本パッケージ情報
  - src/kabusys/__init__.py に __version__ を設定（0.1.0）および主要サブパッケージを公開。
- 環境変数・設定管理
  - src/kabusys/config.py を追加。
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能（プロジェクトルート検出に .git または pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env のパース機能を実装（export プレフィックス対応、クォート内エスケープ、インラインコメントの扱いなどを考慮）。
  - OS 環境変数を保護する protected 機構を導入して .env.local で上書き制御。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / ログレベル / 環境種別等のプロパティを公開。入力検証やデフォルト値を実装。
- データ取得・保存（J-Quants API）
  - src/kabusys/data/jquants_client.py を追加。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - リトライ（指数バックオフ、最大 3 回）・429 の Retry-After 尊重・401 時のトークン自動リフレッシュを実装。
  - ページネーション対応の fetch_* 関数（株価日足 / 財務 / マーケットカレンダー）を追加。
  - DuckDB への冪等保存関数を追加（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT を用いて更新を行う。
  - レコード変換ユーティリティ（_to_float / _to_int）を実装し、入力の堅牢性を向上。
- ニュース収集
  - src/kabusys/data/news_collector.py を追加。
  - RSS フィード収集ロジックと前処理を実装（URL 正規化、トラッキングパラメータ除去、テキスト正規化）。
  - defusedxml を用いた XML パースで XML Bom・XXE 等に対処。
  - 受信サイズ上限（MAX_RESPONSE_BYTES: 10MB）、HTTP スキーム検証、SSRF 緩和の方針を導入。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成し冪等性を確保。
  - バルク INSERT のチャンク処理とトランザクション化で DB への効率的かつ原子的な保存を行う（INSERT RETURNING による挿入数取得方針）。
- リサーチ（ファクター計算・探索）
  - src/kabusys/research/factor_research.py を追加。
    - モメンタム（1/3/6M、MA200乖離）、ボラティリティ（20日 ATR、相対ATR、出来高指標）、バリュー（PER、ROE）などのファクター計算を実装。
    - DuckDB のウィンドウ関数を活用した効率的な SQL ベース計算。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算（任意ホライズン）calc_forward_returns。
    - スピアマンランク相関（IC）calc_ic、ランク関数 rank、factor_summary による統計サマリーを実装。
    - ties の平均ランク処理や丸め（round(v, 12)）による浮動小数点扱いの堅牢化。
  - research パッケージの __all__ を整備。
- 戦略（特徴量生成・シグナル）
  - src/kabusys/strategy/feature_engineering.py を追加。
    - 研究領域で算出した raw ファクターをマージしてユニバースフィルタ（最低株価/平均売買代金）を適用、Z スコアで正規化・±3クリップし features テーブルへ日付単位で UPSERT（トランザクション化で冪等）する build_features を実装。
    - 欠損データや休場日対応の価格取得（target_date 以前の最新価格参照）を考慮。
  - src/kabusys/strategy/signal_generator.py を追加。
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースのコンポーネントスコアを算出、重み付き合算で final_score を計算。
    - デフォルト重み・閾値を実装。ユーザー指定 weights の検証と正規化（合計が 1 になるよう再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負）で BUY を抑制。
    - BUY シグナル（閾値超過）・SELL シグナル（ストップロス/スコア低下）を生成し、signals テーブルへ日付単位で置換（トランザクション化で冪等）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外）や保有ポジション価格欠損時の予防的なスキップ/警告を実装。
  - strategy パッケージのエクスポートを整備（build_features, generate_signals）。

### Security
- news_collector で defusedxml を使用して XML 関連攻撃に対処。
- ニュース収集時に HTTP/HTTPS スキームの検証や受信サイズ制限を実装し、SSRF / DoS リスクを低減。
- config の .env 自動ロードで OS 環境変数を保護するため protected セットを利用。

### Performance
- J-Quants クライアントで固定間隔スロットリングと最小インターバルを導入し API レート制限に準拠。
- fetch_* はページネーション対応で大量データ取得に対応。
- DB 書き込みはバルク insert / executemany / チャンク化（news_collector）・トランザクション化により効率化。

### Reliability / Robustness
- 多数の入力検証を追加（Settings の env/log_level 値検証、weights の妥当性チェック、horizons の範囲チェック等）。
- JSON デコードエラーや HTTP エラー、ネットワークエラーへのリトライ/ログ処理を実装。
- データ欠損行（主キー欠損等）をスキップして警告を出す挙動を統一（save_* 系、news_collector）。
- ファクター計算やランク計算での特異ケース（サンプル不足、分散 0 など）に対して None を返す安全な設計。

### Notes / Known limitations
- 一部機能は未実装または簡易実装のまま（ドキュメント内に注記あり）:
  - signal_generator のトレーリングストップや時間決済は positions テーブルに peak_price / entry_date 等の追加が必要で未実装。
  - research の一部指標（PBR・配当利回り）は現バージョンでは未実装。
- DuckDB テーブルスキーマ・マイグレーションは本リリースに含まれていない（利用時は事前にスキーマ準備が必要）。
- news_collector の URL 正規化は既定のトラッキングプレフィックスに基づく簡易処理で、全てのトラッキングパラメータを網羅しない可能性がある。

---

今後の予定:
- テストカバレッジの追加（単体テスト・統合テスト）
- positions テーブル強化（peak/entry 日付管理）と SELL ロジック拡充（トレーリングストップ等）
- API クライアントの非同期化検討とフェイルオーバー改善
- ドキュメント整備（StrategyModel.md / DataPlatform.md の実装との差分解消）

-- End of CHANGELOG --