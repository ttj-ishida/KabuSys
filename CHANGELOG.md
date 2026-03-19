# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います（例: MAJOR.MINOR.PATCH）。

## [0.1.0] - 2026-03-19
初回リリース。以下の主要機能・設計決定を実装しています。

### 追加 (Added)
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 に設定。
  - 公開モジュール: data, strategy, execution, monitoring を __all__ に登録。

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機構（プロジェクトルート判定に .git / pyproject.toml を使用）。
  - .env パーサーの実装: export プレフィックス対応、シングル/ダブルクォートのエスケープ処理、インラインコメント処理。
  - 自動ロード無効化フラグ (KABUSYS_DISABLE_AUTO_ENV_LOAD)。
  - 必須環境変数チェック (_require) と Settings クラスを提供。
  - J-Quants / kabuステーション / Slack / DB パスなどの設定プロパティを実装。
  - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の妥当性検証。

- データアクセス & 収集 (kabusys.data)
  - J-Quants API クライアント (jquants_client)
    - ページネーション対応の取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - API レート制限を守る固定間隔スロットリング実装（120 req/min）。
    - リトライ（指数バックオフ）、Retry-After 優先、HTTP 408/429/5xx 対応。
    - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE）。
    - データ型変換ユーティリティ (_to_float / _to_int)。
    - fetched_at に UTC タイムスタンプを記録して Look-ahead Bias を抑止。
  - ニュース収集モジュール (news_collector)
    - RSS フィード取得と記事正規化の実装（デフォルトに Yahoo Finance の RSS を含む）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - XML パースに defusedxml を利用（XML Bomb などへの対策）。
    - HTTP 応答のサイズ制限（MAX_RESPONSE_BYTES）と SSRF 対策の考慮。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）を使用し冪等性を担保。
    - large-bulk insert 対応（チャンク化によるパフォーマンス対策）。

- ファクター計算（Research） (kabusys.research)
  - factor_research モジュール
    - モメンタム: 約1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev)。
    - ボラティリティ: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率。
    - バリュー: PER, ROE（raw_financials から最新財務データを参照）。
    - DuckDB を用いた SQL ベース実装（prices_daily / raw_financials のみ参照）。
  - feature_exploration モジュール
    - 将来リターン計算 (calc_forward_returns)：複数ホライズン対応（デフォルト [1,5,21]）、範囲チェック。
    - IC 計算 (calc_ic)：Spearman（ランク相関）による Information Coefficient の計算。
    - ランク関数 (rank)：同順位は平均ランクとして処理（丸めで ties 検出の安定化）。
    - 統計サマリー (factor_summary)：count/mean/std/min/max/median を算出。
  - research パッケージのエクスポートに必要関数を登録。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research の生ファクターを取得し正規化→features テーブルに UPSERT する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
  - Z スコア正規化（kabusys.data.stats からの zscore_normalize）および ±3 でクリップ。
  - 日付単位で DELETE → INSERT のトランザクション置換（冪等性・原子性保証）。
  - 価格参照は target_date 以前の直近価格を利用（休場日対応）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算、signals テーブルへ保存する generate_signals を実装。
  - コンポーネントスコアの算出:
    - momentum（momentum_20/60, ma200_dev）
    - value（per を 20 を基準に変換）
    - volatility（atr_pct の反転シグモイド）
    - liquidity（volume_ratio のシグモイド）
    - news（AI スコアのシグモイド、未登録は中立）
  - スコアの欠損は中立値 0.5 で補完して不当な降格を防止。
  - デフォルト重みと閾値を実装（weights の検証と再スケーリング）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制。
  - エグジット判定（ストップロス -8%、final_score < threshold）を実装（SELL シグナル）。
  - SELL を優先して BUY から除外、ランクを再付与。
  - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。

### 変更 (Changed)
- （初回リリースのためなし）

### 修正 (Fixed)
- （初回リリースのためなし）

### 既知の制限 / 未実装 (Notes / TODO)
- signal_generator のエグジット条件で、トレーリングストップ（peak_price 依存）や時間決済（保有 60 営業日超）等は未実装。これらは positions テーブルに追加情報（peak_price / entry_date）が必要。
- news_collector の詳細なフィードリスト拡張や NLP 前処理パイプラインは追加作業が必要。
- jquants_client のレートリミッタは固定間隔（スロットリング）を採用。より高度なバースト許容や分散ワーカー環境での共有は未対応。
- 一部の入力検証・エラーメッセージは今後改善の余地あり（例: 環境変数のエラーメッセージの多言語化や詳細化）。

### セキュリティ (Security)
- news_collector で defusedxml を使用し XML 関連の攻撃を防止。
- ニュース取得における受信サイズ上限を設定（メモリ DoS 対策）。
- RSS 内の URL 正規化時に非 HTTP/HTTPS のスキームは拒否する方針（SSRF リスク軽減を想定）。

---

今後のリリースでは、テストカバレッジの追加、ドキュメント（StrategyModel.md / DataPlatform.md）との同期、運用監視（monitoring）・発注（execution）層の実装強化、及びパフォーマンス最適化を予定しています。必要があればリリース計画や個別機能の変更履歴を詳述します。