# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは "Keep a Changelog" の形式に準拠します。
リリースはセマンティックバージョニングに従っています。

フォーマットの詳細: https://keepachangelog.com/（英語）

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初回公開リリース。日本株自動売買システムのコアライブラリを実装しました。主な機能、設計上の方針、既知の制限・未実装点を含みます。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（バージョン 0.1.0, エクスポート: data, strategy, execution, monitoring）。
- 環境設定
  - settings を提供する config モジュールを追加。
  - .env 自動読み込み機能: プロジェクトルート（.git または pyproject.toml を基準）を探索して .env / .env.local を読み込む（環境変数で自動ロード無効化可: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - .env パーサ実装: export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理に対応。
  - 必須設定取得ヘルパー (_require)、環境（development/paper_trading/live）およびログレベルの検証を実装。
  - デフォルト DB パス（DuckDB / SQLite）や API ベース URL の既定値を設定。
- データ収集・保存
  - J-Quants クライアント (data.jquants_client) を実装:
    - API 呼び出し用の HTTP ユーティリティ、ページネーション対応、レートリミット（120 req/min）を固定間隔スロットリングで実装。
    - リトライ（指数バックオフ、最大3回、408/429/5xx 対象）、429 の Retry-After 考慮、401 受信時のリフレッシュトークンによる自動再取得（1回のみ）。
    - fetch/save 関数: 日足（daily_quotes）、財務諸表（statements）、マーケットカレンダーの取得と DuckDB への冪等保存（ON CONFLICT を使用）。
    - 入力データの型変換ユーティリティ (_to_float / _to_int) と fetched_at（UTC）記録。
  - ニュース収集モジュール (data.news_collector) を実装:
    - RSS フィード取得・パース（defusedxml 使用で XML 攻撃対策）、URL 正規化（トラッキングパラメータ除去、ソート）、記事ID を SHA-256（先頭32文字）で生成して冪等性を確保。
    - 受信サイズ制限（10MB）、SSRF/非 http(s) スキーム対策、バルク挿入のチャンク化。
- リサーチ（研究）機能
  - factor_research:
    - モメンタム（1/3/6ヶ月、MA200乖離）、ボラティリティ（20日 ATR、相対 ATR）、流動性（20日平均売買代金、出来高比率）、バリュー（PER, ROE）計算の実装。DuckDB の prices_daily / raw_financials テーブルを参照。
    - スキャン範囲バッファを導入し、週末/祝日による欠損を吸収。
  - feature_exploration:
    - 将来リターン計算（複数ホライズン: デフォルト [1,5,21]）、IC（Spearman ρ）計算、ファクター統計サマリー、ランク関数（同順位は平均ランク）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージで主要関数をエクスポート。
- 特徴量エンジニアリング / シグナル生成（戦略）
  - strategy.feature_engineering:
    - 研究モジュールの生ファクターを取得し、ユニバースフィルタ（最小株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（冪等性、トランザクション）。
    - 価格参照は target_date 以前の最新価格を使用してルックアヘッドバイアスを防止。
  - strategy.signal_generator:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付きで final_score を算出（デフォルト重みを実装）。
    - Sigmoid 変換や欠損補完（中立値 0.5）により安定化。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - エグジット判定（ストップロス -8%、final_score が閾値未満）による SELL シグナル生成。
    - signals テーブルへ日付単位で置換（冪等、トランザクション）。
  - strategy パッケージで build_features / generate_signals をエクスポート。
- ロギング / 設計ドキュメント
  - モジュールに詳細な docstring を追加し、設計方針（ルックアヘッドバイアス回避、冪等性、発注層との分離等）を明示。

### 変更 (Changed)
- 該当なし（初回リリースのため変更履歴はなし）。

### 修正 (Fixed)
- 該当なし（初回リリースのため修正履歴はなし）。

### 除去 (Removed)
- 該当なし。

### 既知の制限・未実装 (Known issues / Not implemented)
- strategy.signal_generator における未実装のエグジット条件:
  - トレーリングストップ（直近最高値から -10%）および時間決済（保有 60 営業日超過）は未実装。これらの条件は positions テーブルに peak_price / entry_date が必要で、将来追加予定と注記。
- news_collector 内での銘柄紐付け（news_symbols）処理は実装方針は示されているが具体的な紐付けロジックは要実装／設定。
- data.stats の zscore_normalize 等ユーティリティ関数は外部モジュール（kabusys.data.stats）として参照されている（本リリースでは実装済みである前提だが、運用時に該当関数の検証が必要）。
- DuckDB のスキーマ（raw_prices / raw_financials / prices_daily / features / ai_scores / positions / signals / market_calendar 等）は本リポジトリに含まれていないため、初回セットアップでスキーマ作成 SQL が必要。

### セキュリティ (Security)
- news_collector: defusedxml を利用して XML パース時の攻撃（XML Bomb 等）に対処。
- news_collector: 受信サイズ上限を設定してメモリ DoS を軽減。
- news_collector: URL 正規化とトラッキングパラメータ除去、http/https 以外のスキーム拒否で SSRF リスクを低減。
- jquants_client: 401 時の安全なトークンリフレッシュ、無限再帰を避けるため get_id_token 呼び出し時は allow_refresh=False を使用。

---

今後の予定（Examples of planned improvements）
- execution 層の実装（kabuステーション API 経由の発注処理、注文管理、再試行/エラーハンドリング）。
- positions テーブル拡張（peak_price, entry_date 等）とトレーリングストップ / 時間決済の実装。
- news_collector の銘柄マッチング精度向上（NLP ベースのエンティティ抽出など）。
- 単体テスト・統合テストを整備し CI を導入。

もし CHANGELOG に含めたい追加のイベント（リリース日、注記、既知のバグの優先度など）があれば教えてください。必要に応じて日付・内容を調整して更新します。