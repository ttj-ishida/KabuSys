# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルにはパッケージの主要な追加・変更点・修正点およびセキュリティ関連の注意点を日本語で記載しています。

全般的な方針: 後方互換性を重視し、データ取得・変換・保存・シグナル生成・研究用ユーティリティを明確に分離しています。DB 操作は可能な限り冪等・原子性を保証する実装になっています。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-20

### 追加 (Added)
- 初期公開リリース。
- パッケージ公開
  - パッケージ名: kabusys
  - public API エクスポート: strategy.build_features / strategy.generate_signals / research 関連ユーティリティ / data クライアント など。
- 環境設定管理 (kabusys.config.Settings)
  - .env / .env.local をプロジェクトルートから自動ロード（.git または pyproject.toml を手掛かりにプロジェクトルートを特定）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いをサポート。
  - OS 環境変数を保護する protected 上書きロジック（.env.local は override=True）。
  - 必須 env チェック (JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID)。
  - DB パス設定（DUCKDB_PATH, SQLITE_PATH）と実行環境判定（KABUSYS_ENV）・ログレベル検証（LOG_LEVEL）。
- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアント（fetch / save 関数群）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）。
  - リトライ戦略: 指数バックオフ（最大 3 回）、408/429/5xx を対象、429 の Retry-After を尊重。
  - 401 時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ。
  - ページネーションサポート（pagination_key によるループ）。
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE）で raw_prices / raw_financials / market_calendar を保存。
- ニュース収集 (kabusys.data.news_collector)
  - RSS フィード取得・正規化・安全パース（defusedxml を利用）・raw_news への冪等保存。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等をフィルタ）、受信サイズ制限（10MB）、チャンク化バルクインサート。
  - ニュース記事 ID の冪等化を想定した設計（URL 正規化後のハッシュ利用など、設計方針に記載）。
- 研究用ユーティリティ (kabusys.research)
  - ファクター計算: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照）。
  - 特徴量探索: calc_forward_returns（複数ホライズンを同一クエリで取得）、calc_ic（Spearman IC）、factor_summary、rank（同順位は平均ランク、丸めによる tie 対策）。
  - zscore_normalize を含む一連のユーティリティを re-export。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research で算出した生ファクターをマージ、ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用、Zスコア正規化、±3 でクリップし features テーブルへ日付単位の置換（トランザクションで原子性）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合し、モメンタム/バリュー/ボラティリティ/流動性/ニュースを組み合わせた final_score を算出。
    - AI スコアがない場合は中立値で補完、欠損コンポーネントは中立(0.5)で扱うことで欠損銘柄の不当な降格を防止。
    - 重みの検証・補完・再スケール機能（デフォルト重みは model 仕様に基づく）。
    - Bear レジーム検知（AI の regime_score 平均が負の場合、十分なサンプル数があるとき）により BUY を抑制。
    - BUY/SELL シグナルを作成し signals テーブルへ日付単位の置換（トランザクションで原子性）。
    - SELL 条件の一部（ストップロス -8% / スコア低下）は実装済み。トレーリングストップや時間決済は未実装（説明あり）。
- DB/トランザクション運用
  - features / signals への書き込みは対象日を削除してから挿入する日付単位の置換を採用し、トランザクション＋バルク挿入で原子性を保証。失敗時はロールバック処理（ロールバック失敗時の警告ログを出力）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）
  - 実装はエラー・例外ハンドリングに配慮しており、HTTP/ネットワークエラー時のリトライや DB 操作時のロールバック処理を組み込んでいます。

### セキュリティ (Security)
- XML パースに defusedxml を使用して XML ボム等の攻撃を防止。
- news_collector で HTTP(S) 以外のスキーム拒否や受信サイズ制限を設計方針に含む（SSRF / メモリ DoS 緩和の設計）。
- .env 自動ロード時に OS 環境変数を保護する protected ロジックを採用（.env.local の強制上書きを防ぎつつ安全に補完する設計）。
- J-Quants クライアントは 401 時のトークンリフレッシュを安全に行い、無限再帰を防ぐため allow_refresh フラグを用意。

### 既知の制限 / TODO
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date を保存する仕組みが必要。
- news_collector の記事 ID 生成や symbols とのマッピングの完全実装は設計方針に示されているが、運用に合わせた追加のテスト/チューニングが必要。
- 一部の処理は DuckDB の機能（ウィンドウ関数等）に依存しており、テーブルスキーマ整備と実データでの負荷試験が推奨される。
- 外部 API のレート/エラー特性に応じてバックオフ戦略や並列取得ロジックの調整余地あり。

---

開発者向けメモ:
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動ロードを無効化してユニットテストを容易にする: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

ご要望があれば、リリースノートをより細かく（関数単位の変更履歴や互換性注意点を明示）作成します。