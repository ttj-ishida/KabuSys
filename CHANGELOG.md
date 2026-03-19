# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。  
バージョン番号はパッケージの __version__ に合わせています。

## [0.1.0] - 初回リリース

### 追加 (Added)
- パッケージ全体の基礎モジュールを追加
  - パッケージ名: kabusys（__init__ により data / strategy / execution / monitoring を公開）
- 環境設定管理 (kabusys.config)
  - .env / .env.local ファイルと OS 環境変数から設定をロードする自動ロード機構を実装
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない自動ロードを実現
  - .env の行パーサ実装（コメント処理、export KEY=val、シングル/ダブルクォートおよびバックスラッシュエスケープに対応）
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート
  - Settings クラスを提供し、必須設定の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や型変換（Path）・バリデーション（KABUSYS_ENV, LOG_LEVEL）を実装
- データ取得・保存（kabusys.data）
  - J-Quants API クライアント (jquants_client)
    - 固定間隔のレートリミッタ（120 req/min）を実装
    - 再試行（指数バックオフ、最大 3 回）と HTTP ステータス別の挙動（408/429/5xx 等）を実装
    - 401 受信時の自動トークンリフレッシュと 1 回のみのリトライ処理を実装
    - ページネーション対応の取得（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装（ON CONFLICT を利用）
    - 受信データの型変換ユーティリティ (_to_float, _to_int) を実装し不正値を安全に扱う
    - 取得履歴（fetched_at）を UTC で記録し、look-ahead bias の追跡を可能に
  - ニュース収集モジュール (news_collector)
    - RSS フィードから記事を収集し raw_news に保存する処理を実装
    - URL 正規化（クエリのトラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、パラメータソート）を実装
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
    - 受信サイズ上限（10 MB）や defusedxml を用いた XML 攻撃防御、HTTP/HTTPS 以外のスキーム拒否等の安全対策を導入
    - バルク挿入のチャンク化とトランザクション単位での保存を想定（INSERT チャンクサイズ定義）
- リサーチ機能（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー等のファクター計算（prices_daily / raw_financials を参照）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日ウィンドウ要件を考慮）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御）
    - calc_value: per, roe（target_date 以前の最新財務データ取得）
  - feature_exploration: 将来リターン計算, IC（Spearman の ρ）, 統計サマリー
    - calc_forward_returns: 任意ホライズンの将来リターンを一括取得（効率的なクエリで取得範囲を制限）
    - calc_ic: ランク相関（Spearman）実装、データ不足時の安全処理
    - factor_summary / rank: 基本統計量・同順位平均ランクの実装（丸めで ties を安定化）
  - research パッケージから主要関数をエクスポート
- 戦略ロジック（kabusys.strategy）
  - feature_engineering
    - research で計算した生ファクターをマージ・ユニバースフィルタ（最低株価 300 円 / 20 日平均売買代金 5 億円）適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 にクリップ
    - DuckDB の features テーブルへ日付単位の置換（トランザクション＋バルク挿入で原子性）
  - signal_generator
    - features と ai_scores を統合して各成分（momentum/value/volatility/liquidity/news）を計算
    - シグモイド関数や欠損補完（中立値 0.5）を用いた final_score の計算
    - 重みの受け取り・検証・正規化（デフォルトの重みは StrategyModel.md に基づく）
    - Bear レジーム検知（ai_scores の regime_score 平均）時は BUY を抑制
    - BUY（閾値デフォルト 0.60）・SELL（ストップロス -8% / スコア低下）シグナル生成
    - positions / prices を参照したエグジット判定、signals テーブルへの日付単位置換をトランザクションで実行
  - strategy パッケージから build_features / generate_signals を公開

### 変更 (Changed)
- DB 書き込みは基本的に「日付単位の置換」パターンを採用し冪等性を確保（DELETE + INSERT をトランザクションで実行）
- J-Quants クライアントでのページネーション処理はモジュールレベルのトークンキャッシュを共有し、ページ間でトークン再取得を最小化
- calc_forward_returns 等のホライズン指定は妥当性チェック（1..252）を追加

### 修正 (Fixed)
- .env パーシングの次のケースに対応
  - export キーワードのある行を正しく扱う
  - シングル/ダブルクォート内のバックスラッシュエスケープ処理
  - クォート無し値に対するインラインコメント扱いの改善（直前が空白/タブの場合のみコメントと認識）
- データ保存時の PK 欠損行をスキップし、スキップ件数をログに出力するよう改善
- ニュース収集における XML パース時の安全対策（defusedxml）を導入
- _to_int/_to_float の変換安全性を強化（"1.0" のような文字列は float 経由で int に変換するが、小数部がある場合は None）

### セキュリティ (Security)
- RSS パースに defusedxml を使用し XML 関連脆弱性（XML Bomb 等）を防止
- ニュース収集時に受信バイト数上限（10 MB）を設定してメモリ DoS を軽減
- URL 正規化でトラッキングパラメータを削除、また HTTP/HTTPS スキームのみを許可して SSRF リスクを低減
- J-Quants クライアントは認証トークンの自動リフレッシュ時に無限再帰を避けるガードを実装

### 既知の制限・今後の予定 (Notes)
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は positions テーブル側の追加情報（peak_price / entry_date 等）が必要であり未実装
- news_collector の記事→銘柄紐付け（news_symbols）などの詳細な NLP 処理は現バージョンでは省略
- execution / monitoring パッケージは最小実装（または空）で提供され、発注 API 連携やモニタリング機能は今後拡張予定
- 外部依存を抑える設計だが、実運用時のスケーリングや並列取得の最適化は今後の検討課題

---

今後のバージョンでは、execution 層（実際の発注ロジック・kabuステーション API 統合）、monitoring（Slack 通知・ジョブ監視）、およびニュース→銘柄リンク付けの強化を優先して取り組む予定です。