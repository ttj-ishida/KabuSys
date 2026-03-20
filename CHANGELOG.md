# Changelog

すべての注目すべき変更点をこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

（現時点で未リリースの項目はありません）

## [0.1.0] - 初回リリース
リリース日: 未設定

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（バージョン = 0.1.0）。
  - パッケージ外部 API: kabusys.config.settings, kabusys.strategy.build_features / generate_signals, 研究用ユーティリティ群を公開。

- 環境設定 / 設定管理
  - .env ファイルと環境変数を扱う設定モジュールを追加（kabusys.config）。
    - プロジェクトルート自動探索（.git または pyproject.toml を基準）を実装し、カレントワーキングディレクトリに依存しないロードを実現。
    - .env と .env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。テスト用途に KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化オプションを提供。
    - .env パーサを実装（コメント行、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理などをサポート）。
    - 環境変数取得ヘルパー _require と、各種設定プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン・チャンネル、DB パス、実行環境判定、ログレベル検証等）を提供。
    - OS 環境変数を保護する protected 上書きロジックを実装。

- データ収集（J-Quants）
  - J-Quants API クライアントを実装（kabusys.data.jquants_client）。
    - 固定間隔のレートリミッタ（120 req/min）を実装し、API レート制限を厳守。
    - リトライ（指数バックオフ、最大 3 回）と 408/429/5xx の取り扱い、429 の Retry-After 優先処理を実装。
    - 401 受信時のトークン自動リフレッシュ（1回）を実装し、ID トークンのモジュールレベルキャッシュを提供。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）を実装。
    - DuckDB への保存用の冪等 save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT DO UPDATE などの重複排除）。
    - データ変換ユーティリティ (_to_float / _to_int)、UTC fetched_at 記録など Look-ahead バイアス対策やデータ整合性を考慮。

- ニュース収集
  - RSS ベースのニュース収集モジュール（kabusys.data.news_collector）を追加。
    - デフォルトソース（例: Yahoo Finance）のサポート。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）を実装。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保。
    - defusedxml を利用した安全な XML パース、受信サイズ制限（10MB）、HTTP スキーム制限などセキュリティ対策。
    - raw_news へのバルク保存を考慮しチャンクサイズやトランザクション設計を採用。

- 研究（Research）用ユーティリティ
  - ファクター計算モジュール（kabusys.research.factor_research）を追加。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR・相対 ATR）、Value（PER / ROE）などの計算を DuckDB の SQL ウィンドウ関数と組合せて実装。
    - 欠損・データ不足時の安全な扱い（十分なウィンドウが無い場合は None を返す）を実装。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）を追加。
    - 将来リターン計算（複数ホライズン対応、1/5/21 営業日をデフォルト）を実装。
    - IC（Spearman の ρ）計算（ランク換算、同順位の平均ランク処理）を実装。
    - factor_summary による基本統計量（count/mean/std/min/max/median）出力を実装。
    - ランク計算ユーティリティ（rank）を提供。
  - 研究用 API のエクスポートを整備（__all__ に主要関数を公開）。

- 特徴量エンジニアリング（Production 側）
  - features テーブルを構築する build_features を実装（kabusys.strategy.feature_engineering）。
    - research の calc_momentum / calc_volatility / calc_value を利用して原始ファクターを取得しマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定列の Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリップを実施。
    - DuckDB 上で日付単位の置換（DELETE + INSERT をトランザクションで行い冪等性と原子性を保証）。
    - target_date 時点のデータのみを使う設計（ルックアヘッドバイアス対策）。

- シグナル生成
  - generate_signals を実装（kabusys.strategy.signal_generator）。
    - features と ai_scores を統合し、モメンタム / バリュー / ボラティリティ / 流動性 / news のコンポーネントスコアを算出、重み付け合算で final_score を計算（デフォルト閾値 0.60）。
    - シグモイド変換、欠損コンポーネントの中立補完（0.5）による頑健化。
    - Bear レジーム検知（ai_scores の regime_score 平均が負、サンプル閾値あり）で BUY シグナル抑制ロジックを実装。
    - 保有ポジションに対するエグジット判定（ストップロス -8% とスコア低下）を実装。SELL シグナルの優先付与（SELL 対象を BUY から除外）。
    - 重みの受け入れとバリデーション（既知キーのみ、非数値/負値のスキップ、合計 1.0 に正規化）を実装。
    - signals テーブルへ日付単位置換を実行し冪等性を担保。

### 変更 (Changed)
- 初期リリースのため該当なし（初出の機能群をまとめて追加）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### 廃止 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連の脆弱性（XML Bomb 等）を軽減。
- RSS ダウンロードの受信サイズ上限（10MB）や URL 正規化、HTTP(S) スキーム制限などで SSRF / DoS リスクを低減。
- J-Quants クライアントでタイムアウト / リトライ / トークン管理を実装し認証関連の堅牢性を向上。

---

注: 上記はソースコードから推測してまとめた変更点です。実際のリリース日やリリースノートの追記（例: 既知の制約、将来の TODO、互換性の注意事項など）はプロジェクト運用者にて補完してください。